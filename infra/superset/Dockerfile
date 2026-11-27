# GridPulse Superset image: Superset 6.1.0 (lean) + Postgres driver + config + init script.
FROM apache/superset:6.1.0

USER root
RUN uv pip install --python /app/.venv/bin/python --no-cache psycopg2-binary==2.9.13
COPY infra/superset/superset_config.py /app/pythonpath/superset_config.py
COPY infra/superset/superset_init.sh /app/docker/superset_init.sh
RUN chmod 0755 /app/docker/superset_init.sh

USER superset
