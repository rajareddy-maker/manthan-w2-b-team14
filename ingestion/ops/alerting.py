"""Airflow task-failure alerting (US-26, FR-25).

``on_failure`` is the ``on_failure_callback`` of every GridPulse DAG. It runs after a task's
last retry fails and:
1. writes a CRITICAL ``task_failed`` row to ``warehouse.ops.alerts`` (shown on the dashboard's
   Pipeline health tab) naming the recipient (``ALERT_EMAIL``);
2. upserts a ``status = failed`` row in ``warehouse.ops.pipeline_runs``;
3. logs an ERROR line;
4. e-mails ``ALERT_EMAIL`` when ``SMTP_HOST`` is configured (else logs that e-mail is disabled).

Only stdlib + psycopg2 (present in the Airflow image), so the DAG processor can import it.
A failure inside the callback is logged, never raised (it must not mask the task failure).
"""

from __future__ import annotations

import logging
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any

log = logging.getLogger("gridpulse.alerting")
IST = timezone(timedelta(hours=5, minutes=30))

DDL = """
create table if not exists ops.alerts (
    alert_id bigserial primary key, raised_ts timestamptz not null default now(),
    run_id text, severity text not null, alert_type text not null, scope text not null,
    message text not null);
create table if not exists ops.pipeline_runs (
    run_id text primary key, dag_id text not null, logical_date_ist date not null,
    started_ts timestamptz not null, finished_ts timestamptz, status text not null,
    bronze_rows bigint, quarantined_rows bigint, duplicate_rate_pct numeric(6,3),
    completeness_pct numeric(6,2), ingest_lag_p50_min numeric(8,1),
    ingest_lag_p95_min numeric(8,1), late_beyond_window_events bigint, duration_s int);
"""


def build_alert(context: dict[str, Any], recipient: str) -> dict[str, Any]:
    """Pure: turn an Airflow callback context into the alert/run record."""
    ti = context.get("ti") or context.get("task_instance")
    dag_run = context.get("dag_run")
    dag_id = getattr(ti, "dag_id", None) or getattr(context.get("dag"), "dag_id", "unknown")
    task_id = getattr(ti, "task_id", "unknown")
    run_id = str(context.get("run_id") or getattr(dag_run, "run_id", "unknown"))
    started = getattr(dag_run, "start_date", None) or datetime.now(IST)
    error = str(context.get("exception") or "task failed")[:500]
    try_number = getattr(ti, "try_number", "?")
    return {
        "run_id": run_id,
        "dag_id": dag_id,
        "task_id": task_id,
        "started_ts": started,
        "logical_date_ist": started.astimezone(IST).date(),
        "scope": f"dag={dag_id} task={task_id}",
        "subject": f"[GridPulse CRITICAL] {dag_id}.{task_id} failed",
        "message": (
            f"Task {dag_id}.{task_id} failed after try {try_number} (run {run_id}): {error}. "
            f"Notify: {recipient}. Runbook: docs/runbook.md section 3."
        ),
    }


def _write(alert: dict[str, Any]) -> None:
    import psycopg2  # in the Airflow image; imported lazily for the DAG processor

    conn = psycopg2.connect(
        host=os.environ.get("WAREHOUSE_HOST", "postgres"),
        port=os.environ.get("WAREHOUSE_PORT", "5432"),
        dbname=os.environ.get("WAREHOUSE_DB", "warehouse"),
        user=os.environ.get("WAREHOUSE_USER", "gridpulse"),
        password=os.environ["WAREHOUSE_DB_PASSWORD"],
        connect_timeout=10,
    )
    try:
        with conn, conn.cursor() as cur:
            cur.execute(DDL)
            cur.execute(
                "insert into ops.alerts (run_id, severity, alert_type, scope, message) "
                "values (%s, 'CRITICAL', 'task_failed', %s, %s)",
                (alert["run_id"], alert["scope"], alert["message"]),
            )
            cur.execute(
                "insert into ops.pipeline_runs (run_id, dag_id, logical_date_ist, started_ts,"
                " finished_ts, status) values (%s, %s, %s, %s, now(), 'failed') "
                "on conflict (run_id) do update set status = 'failed', finished_ts = now()",
                (alert["run_id"], alert["dag_id"], alert["logical_date_ist"], alert["started_ts"]),
            )
    finally:
        conn.close()


def _email(alert: dict[str, Any], recipient: str) -> bool:
    host = os.environ.get("SMTP_HOST")
    if not host or not recipient:
        log.warning("alert e-mail disabled (SMTP_HOST not set) recipient=%s", recipient)
        return False
    msg = EmailMessage()
    msg["Subject"], msg["To"] = alert["subject"], recipient
    msg["From"] = os.environ.get("SMTP_FROM", "gridpulse-alerts@localhost")
    msg.set_content(alert["message"])
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=20) as smtp:
        if os.environ.get("SMTP_STARTTLS", "true").lower() == "true":
            smtp.starttls()
        if os.environ.get("SMTP_USER"):
            smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)
    return True


def on_failure(context: dict[str, Any]) -> None:
    """Airflow ``on_failure_callback``: record + log (+ e-mail) a task failure."""
    recipient = os.environ.get("ALERT_EMAIL", "")
    alert = build_alert(context, recipient)
    log.error("ALERT task_failed %s %s", alert["scope"], alert["message"])
    try:
        _write(alert)
        sent = _email(alert, recipient)
        log.error("alert recorded in ops.alerts run_id=%s emailed=%s", alert["run_id"], sent)
    except Exception:  # noqa: BLE001 - never mask the original task failure
        log.exception("failed to record alert for %s", alert["scope"])
