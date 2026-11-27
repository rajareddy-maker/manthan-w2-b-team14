"""US-23 AC3: register a published mart as a Superset dataset and create one chart (idempotent).

Uses the Superset REST API as the admin from .env, then runs the chart's query through
/api/v1/chart/data to prove Superset can read the published table via the read-only warehouse
connection. Never prints secrets.

Usage: python scripts/superset_first_chart.py [--url http://127.0.0.1:8088]
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import urllib.request
from pathlib import Path

DATABASE_NAME = "GridPulse Warehouse"
SCHEMA, TABLE = "marts", "mart_zone_consumption_daily"
CHART_NAME = "Daily consumption by zone (kWh)"


def load_env(path: Path = Path(".env")) -> dict[str, str]:
    """Read KEY=VALUE pairs from .env, falling back to the process environment."""
    env = dict(os.environ)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())
    return env


class Superset:
    """Minimal authenticated Superset API client (JWT + CSRF)."""

    def __init__(self, base: str, user: str, password: str) -> None:
        self.base = base.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )
        self.token = self.call(
            "POST",
            "/api/v1/security/login",
            {"username": user, "password": password, "provider": "db", "refresh": False},
        )["access_token"]
        self.csrf = self.call("GET", "/api/v1/security/csrf_token/")["result"]

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, method=method, data=data)  # noqa: S310
        req.add_header("Content-Type", "application/json")
        if getattr(self, "token", None):
            req.add_header("Authorization", f"Bearer {self.token}")
        if getattr(self, "csrf", None):
            req.add_header("X-CSRFToken", self.csrf)
            req.add_header("Referer", self.base)
        with self.opener.open(req, timeout=120) as resp:
            return json.loads(resp.read())

    def find(self, resource: str, col: str, value: str) -> dict | None:
        q = json.dumps({"filters": [{"col": col, "opr": "eq", "value": value}]})
        rows = self.call("GET", f"/api/v1/{resource}/?q={urllib.request.quote(q)}")["result"]
        return rows[0] if rows else None


def form_data(dataset_id: int) -> dict:
    return {
        "datasource": f"{dataset_id}__table",
        "viz_type": "echarts_timeseries_bar",
        "x_axis": "interval_date_ist",
        "time_grain_sqla": "P1D",
        "metrics": [
            {
                "expressionType": "SIMPLE",
                "column": {"column_name": "consumption_kwh"},
                "aggregate": "SUM",
                "label": "kWh",
            }
        ],
        "groupby": ["zone_name"],
        "row_limit": 10000,
        "stack": "Stack",
        "show_legend": True,
    }


def query_context(dataset_id: int) -> dict:
    fd = form_data(dataset_id)
    return {
        "datasource": {"id": dataset_id, "type": "table"},
        "force": True,
        "form_data": fd,
        "queries": [
            {
                "columns": ["interval_date_ist", "zone_name"],
                "metrics": fd["metrics"],
                "orderby": [["interval_date_ist", True]],
                "row_limit": 10000,
            }
        ],
        "result_format": "json",
        "result_type": "full",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--url", default="http://127.0.0.1:8088")
    a = p.parse_args(argv)
    env = load_env()
    api = Superset(a.url, env["SUPERSET_ADMIN_USER"], env["SUPERSET_ADMIN_PASSWORD"])

    db = api.find("database", "database_name", DATABASE_NAME)
    if db is None:
        raise SystemExit(f"database {DATABASE_NAME!r} not registered (superset-init)")
    ds = api.find("dataset", "table_name", TABLE)
    if ds is None:
        ds = api.call(
            "POST", "/api/v1/dataset/", {"database": db["id"], "schema": SCHEMA, "table_name": TABLE}
        )
    ds_id = ds["id"]
    print(f"dataset: {SCHEMA}.{TABLE} id={ds_id}")

    chart = api.find("chart", "slice_name", CHART_NAME)
    body = {
        "slice_name": CHART_NAME,
        "viz_type": "echarts_timeseries_bar",
        "datasource_id": ds_id,
        "datasource_type": "table",
        "params": json.dumps(form_data(ds_id)),
        "query_context": json.dumps(query_context(ds_id)),
    }
    if chart is None:
        chart_id = api.call("POST", "/api/v1/chart/", body)["id"]
    else:
        chart_id = chart["id"]
        api.call("PUT", f"/api/v1/chart/{chart_id}", body)
    print(f"chart: {CHART_NAME!r} id={chart_id} url={a.url}/explore/?slice_id={chart_id}")

    result = api.call("POST", "/api/v1/chart/data", query_context(ds_id))["result"][0]
    rows = result["data"]
    total = sum(r["kWh"] for r in rows)
    print(f"chart query: status={result.get('status')} rows={len(rows)} total_kwh={total:.4f}")
    for r in rows[:3]:
        print("  sample:", r)
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
