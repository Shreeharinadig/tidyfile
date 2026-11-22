-- Runs once when the Postgres container is first created (development only).
-- The application connects as tidyfile_app, which is NOT a superuser, so
-- row-level security is enforced. Flyway migrates as the admin role.
CREATE ROLE tidyfile_app LOGIN PASSWORD 'tidyfile_app' NOSUPERUSER NOBYPASSRLS;

GRANT USAGE ON SCHEMA public TO tidyfile_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO tidyfile_app;
