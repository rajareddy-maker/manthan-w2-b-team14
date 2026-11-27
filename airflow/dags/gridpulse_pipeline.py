"""GridPulse pipeline DAGs (US-15, US-19). Thin: every task calls ingestion/ or dbt.

gridpulse_daily     01:30 IST. Logical date D = yesterday in IST (override: conf logical_date_ist).
                    Reloads landing [D-3, D+1] into bronze (ADR-004 lookback), dbt build,
                    GX gates (silver + gold; failure blocks publish), publish to Postgres,
                    ops metrics + alerts, retention.
gridpulse_backfill  manual, params start/end (IST dates): same tasks over the range.
"""

from __future__ import annotations

from datetime import date, timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG, Param

from ingestion.ops.alerting import on_failure

TZ = "Asia/Kolkata"
PY = '"$GRIDPULSE_PYTHON"'
DBT = "/opt/gridpulse-venv/bin/dbt"
CD = 'cd "$GRIDPULSE_HOME" && '
DEFAULTS = {
    "retries": 2,
    "retry_delay": pendulum.duration(minutes=2),
    "pool": "duckdb",
    "on_failure_callback": on_failure,  # ops.alerts CRITICAL + ALERT_EMAIL (US-19)
}


def shift(day: str, days: int) -> str:
    """ISO date string shifted by ``days`` (Jinja macro)."""
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


MACROS = {"shift": shift, "days_between": days_between}


def build(dag: DAG, start: str, end: str, lookback: str, load_from: str, load_to: str) -> None:
    """Shared task chain. Arguments are Jinja expressions rendered per run."""
    with dag:
        ingest = BashOperator(
            task_id="ingest_bronze",
            bash_command=CD
            + f"{PY} -m ingestion.extractors.landing_to_bronze "
            + f"--from {{{{ {load_from} }}}} --to {{{{ {load_to} }}}}",
        )
        dbt_build = BashOperator(
            task_id="dbt_build",
            bash_command=CD
            + f"{DBT} build --project-dir dbt_project --profiles-dir dbt_project --no-use-colors",
            execution_timeout=pendulum.duration(minutes=30),
        )
        gx_gates = BashOperator(
            task_id="gx_gates",
            bash_command=CD + f"{PY} data_quality/gx/run_checkpoint.py --suite silver --suite gold",
        )
        publish = BashOperator(
            task_id="publish_postgres",
            bash_command=CD + f"{PY} -m ingestion.publish.to_postgres",
        )
        ops = BashOperator(
            task_id="ops_metrics_alerts",
            bash_command=CD
            + f"{PY} -m ingestion.ops.metrics --run-id '{{{{ run_id }}}}' "
            + "--dag-id {{ dag.dag_id }} "
            + f"--logical-date {{{{ {end} }}}} --lookback {{{{ {lookback} }}}} "
            + "--started '{{ dag_run.start_date.isoformat() }}'",
        )
        retention = BashOperator(
            task_id="retention",
            bash_command=CD + f"{PY} -m ingestion.extractors.retention --reference {{{{ {end} }}}}",
        )
        ingest >> dbt_build >> gx_gates >> publish >> ops >> retention


LOGICAL = (
    "dag_run.conf.get('logical_date_ist') "
    f"or data_interval_end.in_timezone('{TZ}').subtract(days=1).strftime('%Y-%m-%d')"
)

daily = DAG(
    dag_id="gridpulse_daily",
    schedule="30 1 * * *",
    start_date=pendulum.datetime(2026, 11, 1, tz=TZ),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULTS,
    user_defined_macros=MACROS,
    tags=["gridpulse", "daily"],
    doc_md=__doc__,
)
build(
    daily,
    start=f"shift({LOGICAL}, -3)",
    end=f"({LOGICAL})",
    lookback="3",
    load_from=f"shift({LOGICAL}, -3)",
    load_to=f"shift({LOGICAL}, 1)",
)

backfill = DAG(
    dag_id="gridpulse_backfill",
    schedule=None,
    start_date=pendulum.datetime(2026, 11, 1, tz=TZ),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULTS,
    user_defined_macros=MACROS,
    params={
        "start": Param("2026-11-20", type="string", format="date"),
        "end": Param("2026-11-26", type="string", format="date"),
    },
    tags=["gridpulse", "backfill"],
    doc_md=__doc__,
)
build(
    backfill,
    start="params.start",
    end="params.end",
    lookback="days_between(params.start, params.end)",
    load_from="params.start",
    load_to="shift(params.end, 4)",
)


# Alert drill (runbook §3): one task that always fails, no retries -> proves the failure alert.
drill = DAG(
    dag_id="gridpulse_alert_drill",
    schedule=None,
    start_date=pendulum.datetime(2026, 11, 1, tz=TZ),
    catchup=False,
    default_args={"retries": 0, "on_failure_callback": on_failure},
    tags=["gridpulse", "drill"],
)
with drill:
    BashOperator(task_id="simulated_failure", bash_command="echo 'simulated failure'; exit 1")
