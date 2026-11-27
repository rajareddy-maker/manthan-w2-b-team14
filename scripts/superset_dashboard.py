"""US-16: GridPulse network-operations dashboard as code (idempotent, Superset REST API).

Tabs: Feeder consumption · Anomalies · Completeness per zone · Pipeline health.
Every chart is re-created/updated from the definitions below; re-running is safe.
Usage: python scripts/superset_dashboard.py [--url http://127.0.0.1:8088]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from superset_first_chart import DATABASE_NAME, Superset, load_env  # noqa: E402

TITLE = "GridPulse — Network Operations"
SLUG = "gridpulse"


def kwh_sum(col: str = "consumption_kwh", label: str = "kWh") -> dict:
    return {
        "expressionType": "SIMPLE",
        "column": {"column_name": col},
        "aggregate": "SUM",
        "label": label,
    }


def sql_metric(sql: str, label: str) -> dict:
    return {"expressionType": "SQL", "sqlExpression": sql, "label": label}


def raw_table(cols: list[str], order: str) -> dict:
    return {
        "viz_type": "table",
        "query_mode": "raw",
        "all_columns": cols,
        "order_by_cols": [json.dumps([order, False])],
        "row_limit": 1000,
    }


COMPLETENESS = sql_metric("100.0 * SUM(intervals_received) / SUM(intervals_expected)", "complete %")

# (tab, chart name, schema, table, form data)
CHARTS: list[tuple[str, str, str, str, dict]] = [
    (
        "Feeder consumption",
        "Daily consumption by feeder (kWh)",
        "marts",
        "mart_feeder_consumption_daily",
        {
            "viz_type": "echarts_timeseries_bar",
            "x_axis": "interval_date_ist",
            "time_grain_sqla": "P1D",
            "metrics": [kwh_sum()],
            "groupby": ["feeder_id"],
            "stack": "Stack",
            "row_limit": 10000,
        },
    ),
    (
        "Feeder consumption",
        "Hourly consumption by feeder (kWh)",
        "marts",
        "mart_feeder_consumption_hourly",
        {
            "viz_type": "echarts_timeseries_line",
            "x_axis": "hour_start_ts",
            "time_grain_sqla": "PT1H",
            "metrics": [kwh_sum()],
            "groupby": ["feeder_id"],
            "row_limit": 50000,
        },
    ),
    (
        "Feeder consumption",
        "Daily consumption by zone (kWh)",
        "marts",
        "mart_zone_consumption_daily",
        {
            "viz_type": "echarts_timeseries_bar",
            "x_axis": "interval_date_ist",
            "time_grain_sqla": "P1D",
            "metrics": [kwh_sum()],
            "groupby": ["zone_name"],
            "stack": "Stack",
            "row_limit": 10000,
        },
    ),
    (
        "Anomalies",
        "Anomaly events by type",
        "marts",
        "mart_anomalies",
        {
            "viz_type": "pie",
            "groupby": ["anomaly_type"],
            "metric": sql_metric("COUNT(*)", "events"),
            "row_limit": 100,
        },
    ),
    (
        "Anomalies",
        "Anomaly list",
        "marts",
        "mart_anomalies",
        raw_table(
            [
                "anomaly_type",
                "meter_id",
                "feeder_id",
                "zone_id",
                "start_ts",
                "end_ts",
                "intervals",
                "metric_name",
                "metric_value",
                "threshold",
                "affected_meters",
            ],
            "start_ts",
        ),
    ),
    (
        "Completeness per zone",
        "Completeness % by zone and day",
        "marts",
        "mart_zone_completeness_daily",
        {
            "viz_type": "echarts_timeseries_line",
            "x_axis": "interval_date_ist",
            "time_grain_sqla": "P1D",
            "metrics": [COMPLETENESS],
            "groupby": ["zone_name"],
            "row_limit": 10000,
        },
    ),
    (
        "Completeness per zone",
        "Low-completeness meter-days by zone",
        "marts",
        "mart_zone_completeness_daily",
        {
            "viz_type": "echarts_timeseries_bar",
            "x_axis": "interval_date_ist",
            "time_grain_sqla": "P1D",
            "metrics": [kwh_sum("low_completeness_meter_days", "meter-days < 90%")],
            "groupby": ["zone_name"],
            "stack": "Stack",
            "row_limit": 10000,
        },
    ),
    (
        "Pipeline health",
        "Pipeline runs",
        "ops",
        "pipeline_runs",
        raw_table(
            [
                "logical_date_ist",
                "dag_id",
                "status",
                "duration_s",
                "bronze_rows",
                "quarantined_rows",
                "duplicate_rate_pct",
                "completeness_pct",
                "ingest_lag_p50_min",
                "ingest_lag_p95_min",
                "late_beyond_window_events",
                "finished_ts",
            ],
            "finished_ts",
        ),
    ),
    (
        "Pipeline health",
        "Alerts",
        "ops",
        "alerts",
        raw_table(["raised_ts", "severity", "alert_type", "scope", "message"], "raised_ts"),
    ),
]


def ensure_dataset(api: Superset, db_id: int, schema: str, table: str) -> int:
    for ds in api.call(
        "GET",
        "/api/v1/dataset/?q="
        + urllib.parse.quote(
            json.dumps({"filters": [{"col": "table_name", "opr": "eq", "value": table}]})
        ),
    )["result"]:
        if ds.get("schema") == schema:
            return int(ds["id"])
    return int(
        api.call(
            "POST", "/api/v1/dataset/", {"database": db_id, "schema": schema, "table_name": table}
        )["id"]
    )


def ensure_chart(api: Superset, name: str, ds_id: int, form: dict) -> int:
    params = {"datasource": f"{ds_id}__table", **form}
    body = {
        "slice_name": name,
        "viz_type": form["viz_type"],
        "datasource_id": ds_id,
        "datasource_type": "table",
        "params": json.dumps(params),
    }
    existing = api.find("chart", "slice_name", name)
    if existing:
        api.call("PUT", f"/api/v1/chart/{existing['id']}", body)
        return int(existing["id"])
    return int(api.call("POST", "/api/v1/chart/", body)["id"])


def layout(tabs: dict[str, list[tuple[int, str]]]) -> dict:
    """Superset v2 position JSON: one TAB per group, charts two per row."""
    pos: dict = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["TABS-1"]},
        "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": TITLE}},
        "TABS-1": {"type": "TABS", "id": "TABS-1", "children": [], "parents": ["ROOT_ID"]},
    }
    for t, (tab, charts) in enumerate(tabs.items(), start=1):
        tab_id = f"TAB-{t}"
        pos["TABS-1"]["children"].append(tab_id)
        pos[tab_id] = {
            "type": "TAB",
            "id": tab_id,
            "children": [],
            "parents": ["ROOT_ID", "TABS-1"],
            "meta": {"text": tab},
        }
        width = 12 if len(charts) == 1 else 6
        for r in range(0, len(charts), 2):
            row_id = f"ROW-{t}-{r}"
            pos[tab_id]["children"].append(row_id)
            pos[row_id] = {
                "type": "ROW",
                "id": row_id,
                "children": [],
                "parents": ["ROOT_ID", "TABS-1", tab_id],
                "meta": {"background": "BACKGROUND_TRANSPARENT"},
            }
            for chart_id, name in charts[r : r + 2]:
                cid = f"CHART-{chart_id}"
                pos[row_id]["children"].append(cid)
                pos[cid] = {
                    "type": "CHART",
                    "id": cid,
                    "children": [],
                    "parents": ["ROOT_ID", "TABS-1", tab_id, row_id],
                    "meta": {"chartId": chart_id, "width": width, "height": 60, "sliceName": name},
                }
    return pos


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--url", default="http://127.0.0.1:8088")
    a = p.parse_args(argv)
    env = load_env()
    api = Superset(a.url, env["SUPERSET_ADMIN_USER"], env["SUPERSET_ADMIN_PASSWORD"])
    db = api.find("database", "database_name", DATABASE_NAME)
    if db is None:
        raise SystemExit(f"database {DATABASE_NAME!r} not registered")

    tabs: dict[str, list[tuple[int, str]]] = {}
    for tab, name, schema, table, form in CHARTS:
        ds_id = ensure_dataset(api, db["id"], schema, table)
        chart_id = ensure_chart(api, name, ds_id, form)
        tabs.setdefault(tab, []).append((chart_id, name))
        print(f"chart {chart_id:>3} [{tab}] {name} <- {schema}.{table}")

    dash = api.find("dashboard", "slug", SLUG)
    body = {
        "dashboard_title": TITLE,
        "slug": SLUG,
        "published": True,
        "position_json": json.dumps(layout(tabs)),
        "json_metadata": json.dumps({"timed_refresh_immune_slices": [], "refresh_frequency": 0}),
    }
    if dash:
        dash_id = int(dash["id"])
        api.call("PUT", f"/api/v1/dashboard/{dash_id}", body)
    else:
        dash_id = int(api.call("POST", "/api/v1/dashboard/", body)["id"])
    for charts in tabs.values():
        for chart_id, _ in charts:
            api.call("PUT", f"/api/v1/chart/{chart_id}", {"dashboards": [dash_id]})
    print(f"dashboard {dash_id}: {a.url}/superset/dashboard/{SLUG}/")

    # prove every chart's dataset answers through the read-only warehouse connection
    failures = 0
    for _tab, name, schema, table, _ in CHARTS:
        ds_id = ensure_dataset(api, db["id"], schema, table)
        qc = {
            "datasource": {"id": ds_id, "type": "table"},
            "force": True,
            "queries": [{"metrics": [sql_metric("COUNT(*)", "n")], "columns": []}],
            "result_format": "json",
            "result_type": "full",
        }
        res = api.call("POST", "/api/v1/chart/data", qc)["result"][0]
        n = res["data"][0]["n"] if res.get("data") else 0
        failures += n == 0 and table != "alerts"  # no alerts is a valid state
        print(f"  data check {schema}.{table:<32} rows={n:>6}  ({name})")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
