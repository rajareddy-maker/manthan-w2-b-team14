"""Unit tests for the task-failure alert callback (US-26)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from ingestion.ops import alerting

IST = timezone(timedelta(hours=5, minutes=30))


def ctx() -> dict:
    ti = SimpleNamespace(dag_id="gridpulse_daily", task_id="dbt_build", try_number=3)
    run = SimpleNamespace(
        run_id="scheduled__x", start_date=datetime(2026, 11, 26, 20, 0, tzinfo=UTC)
    )
    return {"ti": ti, "dag_run": run, "run_id": "scheduled__x", "exception": RuntimeError("boom")}


def test_build_alert_names_task_recipient_and_ist_date() -> None:
    a = alerting.build_alert(ctx(), "sagar.kalthiya@nucleusteq.com")
    assert a["scope"] == "dag=gridpulse_daily task=dbt_build"
    assert a["subject"] == "[GridPulse CRITICAL] gridpulse_daily.dbt_build failed"
    assert "boom" in a["message"] and "sagar.kalthiya@nucleusteq.com" in a["message"]
    assert "try 3" in a["message"]
    # 20:00 UTC on 26-Nov is 01:30 IST on 27-Nov: dates are IST
    assert str(a["logical_date_ist"]) == "2026-11-27"


def test_email_disabled_without_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMTP_HOST", raising=False)
    assert alerting._email(alerting.build_alert(ctx(), "x@y"), "x@y") is False


def test_callback_records_and_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    written = []
    monkeypatch.setenv("ALERT_EMAIL", "sagar.kalthiya@nucleusteq.com")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setattr(alerting, "_write", written.append)
    alerting.on_failure(ctx())
    assert written and written[0]["dag_id"] == "gridpulse_daily"

    def broken(_alert: dict) -> None:
        raise ConnectionError("warehouse down")

    monkeypatch.setattr(alerting, "_write", broken)
    alerting.on_failure(ctx())  # must not raise: the task failure stays the reported error


def test_email_sent_via_smtp_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict = {}

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            sent["server"] = (host, port)

        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def starttls(self) -> None:
            sent["tls"] = True

        def login(self, user: str, password: str) -> None:
            sent["user"] = user

        def send_message(self, msg) -> None:  # noqa: ANN001
            sent["to"], sent["subject"], sent["body"] = msg["To"], msg["Subject"], msg.get_content()

    monkeypatch.setattr(alerting.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("SMTP_HOST", "smtp.office365.com")
    monkeypatch.setenv("SMTP_USER", "alerts@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "x")
    alert = alerting.build_alert(ctx(), "sagar.kalthiya@nucleusteq.com")
    assert alerting._email(alert, "sagar.kalthiya@nucleusteq.com") is True
    assert sent["server"] == ("smtp.office365.com", 587) and sent["tls"]
    assert sent["to"] == "sagar.kalthiya@nucleusteq.com"
    assert sent["subject"] == "[GridPulse CRITICAL] gridpulse_daily.dbt_build failed"
    assert "boom" in sent["body"]
