"""Walking-skeleton / smoke DAG: proves the scheduler, executor and project venv work."""

from __future__ import annotations

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag


@dag(
    dag_id="hello_gridpulse",
    schedule=None,
    start_date=pendulum.datetime(2026, 11, 1, tz="Asia/Kolkata"),
    catchup=False,
    tags=["gridpulse", "smoke"],
    default_args={"retries": 1, "retry_delay": pendulum.duration(seconds=10)},
)
def hello_gridpulse() -> None:
    """Single task printing the versions available in the project venv."""
    BashOperator(
        task_id="check_project_venv",
        bash_command=(
            '"$GRIDPULSE_PYTHON" -c "import duckdb, dbt.version, great_expectations as gx; '
            "print('duckdb', duckdb.__version__, 'dbt', dbt.version.__version__, "
            "'gx', gx.__version__)\""
        ),
    )


hello_gridpulse()
