#!/bin/bash
# Runs once when the Postgres container is first created (development only).
# The application connects as DB_APP_USER, which is NOT a superuser, so
# row-level security is enforced. Flyway migrates as the admin role.
# The password comes from the environment so it always matches what the API sends.
set -euo pipefail
: "${DB_APP_USER:=tidyfile_app}"
: "${DB_APP_PASSWORD:=tidyfile_app}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_user="$DB_APP_USER" -v app_password="$DB_APP_PASSWORD" <<'EOSQL'
CREATE ROLE :"app_user" LOGIN PASSWORD :'app_password' NOSUPERUSER NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO :"app_user";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"app_user";
EOSQL
