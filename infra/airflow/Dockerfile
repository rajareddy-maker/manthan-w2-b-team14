# GridPulse Airflow image: Airflow 3.3.2 (Python 3.13) + an isolated project venv
# (/opt/gridpulse-venv) with DuckDB, dbt-duckdb, Great Expectations and the ingestion deps.
# The project venv keeps dbt/GX dependencies from clashing with Airflow's own (ADR-001).
FROM apache/airflow:3.3.2

USER root
RUN mkdir -p /opt/gridpulse-venv /opt/duckdb_ext \
    && chown -R airflow:0 /opt/gridpulse-venv /opt/duckdb_ext \
    && chmod -R g+rwX /opt/duckdb_ext

USER airflow
COPY --chown=airflow:0 requirements.txt /tmp/requirements.txt
RUN uv venv --python "$(which python)" /opt/gridpulse-venv \
    && uv pip install --python /opt/gridpulse-venv/bin/python --no-cache -r /tmp/requirements.txt \
    && /opt/gridpulse-venv/bin/python -c "import duckdb, dbt.version, great_expectations as gx; print('duckdb', duckdb.__version__, 'gx', gx.__version__)"

# Pre-install the DuckDB postgres extension so runtime needs no internet access.
RUN /opt/gridpulse-venv/bin/python -c "import duckdb; c = duckdb.connect(); c.execute(\"SET extension_directory='/opt/duckdb_ext'\"); c.execute('INSTALL postgres')" \
    && chmod -R g+rwX /opt/duckdb_ext

ENV GRIDPULSE_PYTHON=/opt/gridpulse-venv/bin/python \
    DUCKDB_EXTENSION_DIR=/opt/duckdb_ext \
    DBT_PROFILES_DIR=/opt/gridpulse/dbt_project
