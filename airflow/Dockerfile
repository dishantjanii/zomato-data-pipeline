# Airflow 3.x image + Snowflake provider + FAB auth (for admin/admin login) + dbt venv + openai.
FROM apache/airflow:3.0.3

USER root

# Create directory for dbt venv and grant ownership to the airflow user
RUN mkdir -p /opt/airflow/dbt_venv && \
    chown -R airflow:root /opt/airflow/dbt_venv

# Switch back to airflow user for python/pip installations
USER airflow

# Providers: snowflake, fab (classic username/password login), google-generativeai (AI task)
RUN pip install --no-cache-dir \
    apache-airflow-providers-snowflake \
    apache-airflow-providers-fab \
    google-generativeai

# dbt in its own venv so it never clashes with Airflow's dependencies.
# DAG tasks call /opt/airflow/dbt_venv/bin/dbt
# dbt in its own venv so it never clashes with Airflow's dependencies.
RUN python -m venv /opt/airflow/dbt_venv && \
    /opt/airflow/dbt_venv/bin/pip install --no-cache-dir --prefer-binary "dbt-snowflake==1.8.*"