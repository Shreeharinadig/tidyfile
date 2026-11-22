# tidyfile: guidance for Claude Code

Multi-tenant report automation platform. Portfolio project on synthetic data. Read `README.md` for current status before starting work.

## Layout and commands

- `api/`: Spring Boot 3, Java 21, Flyway, PostgreSQL. `make test-api`
- `worker/`: Python 3.13, pandas, openpyxl, boto3. `make test`
- `benchmark/`: synthetic data generator and evaluation. `make data`, `make eval`
- Run `make test` and `make eval` before finishing any change to `worker/` or `benchmark/`.

## Rules

1. **Tenant isolation.** Every tenant-owned table has `tenant_id` and row-level security. Set `app.tenant_id` on the database session for every request and job. Cross-tenant access returns 404. Add an isolation test for every new endpoint and worker path.
2. **The LLM proposes, code validates.** Validate every model output against a JSON schema. Retry once with the error message, then fall back to rules or human review. The model never writes SQL or writes data directly; it returns structured specs that code executes.
3. **Approval before side effects.** Agent steps that write cleaned data or send anything outside the system need explicit approval.
4. **Mask before sending.** Mask sensitive columns (phone, email, account numbers) before any text goes to a model API.
5. **Cost limits.** Read model name, API key, and limits from environment variables. Never commit keys. Cap agent steps and tokens per run, and tokens per tenant per day. Cache model results by input hash.
6. **Tests never call paid APIs.** Use the mocked LLM client in tests and CI. Live evals run only from a separate `make eval-live` command (added in week 5).
7. **Benchmark discipline.** Tune prompts and rules on the `dev` split only. Never read mistakes from the `heldout` split. Record results per prompt version.
8. **Idempotency.** A job is keyed by tenant and file content hash. A re-delivered message must not create duplicate rows.
9. **Small steps.** One milestone at a time, tests alongside each module, and explain design choices in `docs/DESIGN.md` in the author's own words.

## Build order

Week 1 foundation and benchmark (done) · Week 2 pipeline core · Week 3 tenancy and auth · Week 4 reliability · Week 5 LLM features · Week 6 agent, polish, deploy.
