-- Initial schema. Every tenant-owned table carries tenant_id and is protected by
-- row-level security. The application sets the tenant per request or job with:
--     SET LOCAL app.tenant_id = '<tenant uuid>';
-- If it is not set, no rows are visible.
--
-- `tenants` and `users` are intentionally excluded from row-level security for now:
-- login must look up a user before the tenant is known. Week 3 adds a restricted
-- login lookup and a policy for `users`.

CREATE TABLE tenants (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      uuid        NOT NULL REFERENCES tenants (id),
    email          text        NOT NULL,
    password_hash  text        NOT NULL,
    role           text        NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member')),
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, email)
);

CREATE TABLE uploads (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid        NOT NULL REFERENCES tenants (id),
    uploaded_by   uuid        REFERENCES users (id),
    filename      text        NOT NULL,
    s3_key        text        NOT NULL,
    content_hash  text        NOT NULL,
    status        text        NOT NULL DEFAULT 'UPLOADED',
    created_at    timestamptz NOT NULL DEFAULT now(),
    -- Idempotency: the same file content is only processed once per tenant.
    UNIQUE (tenant_id, content_hash)
);

CREATE TABLE jobs (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    uuid        NOT NULL REFERENCES tenants (id),
    upload_id    uuid        NOT NULL REFERENCES uploads (id),
    status       text        NOT NULL DEFAULT 'QUEUED'
                 CHECK (status IN ('QUEUED', 'PROFILING', 'NEEDS_REVIEW', 'PROCESSING', 'DONE', 'FAILED')),
    attempts     integer     NOT NULL DEFAULT 0,
    error        text,
    started_at   timestamptz,
    finished_at  timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, upload_id)
);

CREATE TABLE schema_templates (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      uuid        NOT NULL REFERENCES tenants (id),
    name           text        NOT NULL,
    dataset_type   text        NOT NULL,
    target_schema  jsonb       NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name)
);

CREATE TABLE column_mappings (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id      uuid         NOT NULL REFERENCES tenants (id),
    upload_id      uuid         NOT NULL REFERENCES uploads (id),
    source_column  text         NOT NULL,
    target_column  text,
    confidence     numeric(4, 3) NOT NULL DEFAULT 0,
    origin         text         NOT NULL CHECK (origin IN ('rule', 'llm', 'user')),
    confirmed      boolean      NOT NULL DEFAULT false,
    created_at     timestamptz  NOT NULL DEFAULT now(),
    UNIQUE (upload_id, source_column)
);

CREATE TABLE datasets (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    uuid        NOT NULL REFERENCES tenants (id),
    upload_id    uuid        NOT NULL REFERENCES uploads (id),
    template_id  uuid        REFERENCES schema_templates (id),
    row_count    integer     NOT NULL DEFAULT 0,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE dataset_rows (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   uuid  NOT NULL REFERENCES tenants (id),
    dataset_id  uuid  NOT NULL REFERENCES datasets (id) ON DELETE CASCADE,
    data        jsonb NOT NULL
);
CREATE INDEX idx_dataset_rows_dataset ON dataset_rows (tenant_id, dataset_id);

CREATE TABLE reports (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid        NOT NULL REFERENCES tenants (id),
    dataset_id  uuid        NOT NULL REFERENCES datasets (id),
    config      jsonb       NOT NULL DEFAULT '{}'::jsonb,
    format      text        NOT NULL CHECK (format IN ('xlsx', 'pdf')),
    s3_key      text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE report_schedules (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        uuid        NOT NULL REFERENCES tenants (id),
    report_config    jsonb       NOT NULL,
    cron             text        NOT NULL,
    delivery_target  text        NOT NULL,
    active           boolean     NOT NULL DEFAULT true,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE llm_calls (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        uuid          NOT NULL REFERENCES tenants (id),
    job_id           uuid          REFERENCES jobs (id),
    purpose          text          NOT NULL,
    model            text          NOT NULL,
    prompt_version   text          NOT NULL,
    tokens_in        integer       NOT NULL DEFAULT 0,
    tokens_out       integer       NOT NULL DEFAULT 0,
    latency_ms       integer       NOT NULL DEFAULT 0,
    output_valid     boolean       NOT NULL,
    cost_estimate    numeric(12, 6),
    created_at       timestamptz   NOT NULL DEFAULT now()
);

CREATE TABLE agent_runs (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid        NOT NULL REFERENCES tenants (id),
    job_id        uuid        REFERENCES jobs (id),
    status        text        NOT NULL DEFAULT 'RUNNING',
    step_budget   integer     NOT NULL,
    token_budget  integer     NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    finished_at   timestamptz
);

CREATE TABLE agent_steps (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid        NOT NULL REFERENCES tenants (id),
    run_id          uuid        NOT NULL REFERENCES agent_runs (id) ON DELETE CASCADE,
    step_no         integer     NOT NULL,
    tool            text        NOT NULL,
    input           jsonb,
    output          jsonb,
    needs_approval  boolean     NOT NULL DEFAULT false,
    approved_by     uuid        REFERENCES users (id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, step_no)
);

CREATE TABLE audit_log (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id  uuid        NOT NULL REFERENCES tenants (id),
    actor      uuid,
    action     text        NOT NULL,
    entity     text        NOT NULL,
    entity_id  text,
    at         timestamptz NOT NULL DEFAULT now()
);

-- Row-level security on every tenant-owned table.
DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'uploads', 'jobs', 'schema_templates', 'column_mappings', 'datasets', 'dataset_rows',
        'reports', 'report_schedules', 'llm_calls', 'agent_runs', 'agent_steps', 'audit_log'
    ]
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON %I
                 USING (tenant_id = nullif(current_setting(''app.tenant_id'', true), '''')::uuid)
                 WITH CHECK (tenant_id = nullif(current_setting(''app.tenant_id'', true), '''')::uuid)',
            t
        );
    END LOOP;
END
$$;
