# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

The app is **built and wired end to end** — `backend/` (FastAPI + LangGraph + Celery), `frontend/` (Next.js app router), and `infra/` (docker-compose + seed SQL) all exist. Two specs remain the source of truth and should stay in sync with the code:
- `PLAN.md` — the implementation spec. Read it first for any non-trivial change; if you change an architecture invariant, update it.
- `ui_images/DESIGN.md` + PNGs — the "Neural Dark" glassmorphism design tokens and reference screens.

The prior Elasticsearch-flavored scaffold was deleted on purpose; do not restore it from `git log`.

## Product in one paragraph

**QueryMind AI** — users connect their own data source (Postgres, SQLite, ClickHouse, Oracle, Elasticsearch, or MongoDB), the backend deterministically introspects the schema, and a LangGraph agent generates a **read-only** query from natural-language questions — SQL for the SQL family (ES uses its read-only `_sql` API), a MongoDB aggregation pipeline for Mongo — executes it, and returns a written answer plus an optional chart spec. It is self-hosted and runs **only** against a local vLLM server (`Qwen/Qwen2.5-0.5B-Instruct` with `xgrammar` guided decoding) — no external AI APIs.

## Architecture invariants (do not violate without updating PLAN.md)

- **No external LLM APIs.** vLLM at `http://localhost:8000/v1` is the only model endpoint. Structured output goes through `response_format={"type":"json_schema", ...}` against Pydantic-derived schemas, not free-text JSON parsing.
- **Dialect abstraction lives in one place: `backend/app/engines/base.py`.** Every other module talks to the `QueryEngine` Protocol. Six engines are registered today: `postgres`, `sqlite`, `clickhouse`, `oracle`, `elasticsearch`, `mongodb`. **Engines do not auto-register on import** — `app.engines.register_all()` must be called once before `get_engine` (already wired in `main.py`, `services/engine_loader.py`, `workers/profile_task.py`, `api/workspaces.py`; call it in new scripts/tests too).
  - **Code outside `engines/` must never branch on the specific `dialect`** — but it *may* branch on `query_kind` (the language family: `sql | es_dsl | mongo_agg`, declared per dialect in `registry.QUERY_KIND` and on each engine). A new **SQL-family** dialect plugs in by registering in `DIALECT_REGISTRY` with no other file changes. A new **non-SQL** backend (its own `query_kind`) additionally needs: an LLM plan model in `llm_io.py`, a parse-layer validator (like `services/mongo_validator.py`), and `query_kind` branches in `query_planner`/`query_validator`/`query_executor`. `schema_loader` sets `state["query_kind"]` from the workspace dialect.
- **Read-only is defense in depth, all three layers required:**
  1. Boundary — the connect form documents the read-only GRANT recipe and probes write access.
  2. Parse — `services/readonly_validator.py` (signature `validate_readonly(sql, dialect=...)`) uses `sqlglot.parse(sql, read=dialect)`, walks the AST, rejects any DML/DDL/`SET`/`COPY`/`GRANT`/multi-statement input and a denylist of system tables and dangerous functions (`pg_sleep`, `pg_read_file`, `dblink`, `load_file`, …). Elasticsearch SQL is parsed as `postgres` for the AST checks (`_SQLGLOT_DIALECT`). The malicious corpus in `tests/unit/test_readonly_validator.py` is the spec — it must reject every line. **The `mongo_agg` kind has its own parse layer**, `services/mongo_validator.py` → `validate_mongo_pipeline()`, which rejects `$out`/`$merge`/`$function`/`$accumulator`/`$where` anywhere in the pipeline.
  3. Runtime — Postgres executes inside `BEGIN; SET LOCAL transaction_read_only=on; SET LOCAL statement_timeout='10s'; … ROLLBACK;`. SQLite opens with `file:<path>?mode=ro` URI plus `PRAGMA query_only=ON`. MongoDB only ever calls `aggregate()` (never a write method); the connect-form GRANT recipes cover all six backends. Note: `probe_write_access` is **advisory** — over-privileged credentials are warned about, not rejected.
- **Agent graph topology** (`backend/app/agents/graph.py`): `coordinator` routes by `intent` — `chitchat`→`answer_writer`, `clarify`→`finalizer`, and `metadata`/`data_query`/`dashboard`→`schema_loader`. From `schema_loader`: `metadata`→`answer_writer`, `dashboard`→`dashboard_builder`, else→`query_planner ↔ query_validator → query_executor → {chart_designer, answer_writer}`. Every branch terminates at `finalizer → END`. The graph edges are dialect-agnostic: `query_planner`/`query_validator`/`query_executor` branch *internally* on `state["query_kind"]` — `mongo_agg` plans a `MongoAggPlan`, validates via `validate_mongo_pipeline`, and runs `engine.run_pipeline(collection, pipeline)` instead of `engine.execute(sql)`. **Dashboards are SQL-only**: `schema_loader` downgrades `intent="dashboard"`→`"data_query"` for non-SQL backends. Planner↔validator and planner↔executor each have **retry≤2** (`MAX_PLANNER_ATTEMPTS`/`MAX_EXECUTOR_ATTEMPTS`), then route to `error_responder`. `chart_designer` and `answer_writer` fan out in parallel via LangGraph reducer semantics — `chart` and `answer` are independent state slots merged in `finalizer`.
- **LLM-driven nodes:** `coordinator`, `query_planner`, `chart_designer`, `answer_writer`, `dashboard_builder`. **Deterministic nodes:** `schema_loader`, `query_validator`, `query_executor`, `finalizer`, `error_responder`. Don't move a node between groups without a reason. (`dashboard_builder` is LLM-driven — it emits a `DashboardPlan` — but it still runs each panel's SQL through `validate_readonly` and the engine before building the `Dashboard` spec.)
- **Frontend/backend contract is `backend/app/schemas/ui_spec.py`.** `UISpec` is a discriminated union (`text_only | kpi | bar | line | pie | table | dashboard`). `frontend/components/RenderSpec.tsx` dispatches on `spec.type`. Any change to one side must update the other in the same PR.
- **Chart designer never sees raw result rows.** It receives only the result *shape* (columns, dtypes, row_count, 5 sample rows). Same for `answer_writer`. This is for prompt size and to prevent the LLM from inventing numbers.
- **LLM I/O contracts live in `backend/app/schemas/llm_io.py`** (`IntentDecision`, `SqlPlan`, `AnswerDraft`, plus `DashboardPlan`/`DashboardPanel` for the dashboard path and `MongoAggPlan` for the Mongo path — the model emits the pipeline as a JSON-array *string* (`pipeline_json`) because that decodes more reliably than a deeply-nested object). Every vLLM call must pass `response_format={"type":"json_schema", "json_schema": {..., "schema": Model.model_json_schema(), "strict": True}}` — never parse free-text JSON from the model.
- **Planner prompt size is gated by `services/schema_pruner.py`** (BM25 top-K over `f"{table} {col}"`, K=8). Any table named in the user message is pinned. Drop sampled values before dropping table entries when over budget (~6K tokens).
- **Workspace resolution** (`services/workspace_resolver.py`) merges three signals — dropdown selection, `@name`/`[name]` mentions, and bare-word matches against the user's workspace names. Anything that isn't a clean `Resolved` becomes `intent="clarify"` and a `text_only` UISpec with quick-reply chips. Don't bypass this — the coordinator depends on its outcomes.
- **DB credentials are encrypted at rest with AES-GCM** via `services/crypto.py`, master key from env `QM_MASTER_KEY` (base64, 256-bit). `key_version` column is reserved for rotation; v1 hard-codes 1.
- **Chat streaming is node-level SSE events only.** Token-level streaming is explicitly out of v1 — don't add it. Frontend renders the final `UISpec` once `finalizer` emits.

## Critical files (the architecture lives or dies on these)

- `backend/app/engines/base.py` — `QueryEngine` Protocol + `SchemaBundle`/`ResultSet` types + `Dialect`/`QueryKind` literals.
- `backend/app/engines/registry.py` — `DIALECT_REGISTRY`, `QUERY_KIND` map, `register()`/`get_engine()`/`query_kind_for()`.
- `backend/app/services/readonly_validator.py` + `backend/app/services/mongo_validator.py` — security-critical parse layers (SQL family / Mongo); the test corpus is the spec, write tests first.
- `backend/app/agents/graph.py` — retry loops + parallel fan-out.
- `backend/app/schemas/ui_spec.py` — cross-stack contract.
- `backend/app/schemas/llm_io.py` — Pydantic models that become the vLLM JSON-schema; changing field names changes the LLM contract.
- `frontend/components/RenderSpec.tsx` — discriminated-union dispatcher.

## Build order (front-loads risk)

PLAN.md §"Build Order" is canonical. The ordering is deliberate: security-critical pieces (read-only validator, engine adapter) come **before** LLM wiring so the riskiest code is also the most-tested. Don't reorder to start with LLM work first.

## Design system

`ui_images/DESIGN.md` defines the "Neural Dark" tokens (colors, typography, spacing). All visualizations are wrapped in `<GlassPanel>` so glassmorphism styling lives in one place. Fonts: Space Grotesk (headlines), Inter (body), JetBrains Mono (data + SQL code blocks). Below every assistant message in chat is a collapsible `<CodeBlock language="sql">` showing the generated SQL.

## Commands

The scaffolding has landed. Real commands:

**Backend** (run from `backend/`, after `pip install -r requirements.txt`):
- Tests: `pytest tests/` — single test: `pytest tests/unit/test_readonly_validator.py::test_malicious_rejected`
- Unit only (no DB needed): `pytest tests/unit/`
- The Postgres e2e (`tests/integration/test_e2e_postgres.py`) auto-skips unless a Postgres is reachable on `localhost:55432`; it also needs a `sales_demo` database seeded from `infra/seed/seed_sales.sql`.
- Migrations: `alembic upgrade head` (creates `pgcrypto` + all 9 tables; needs `DATABASE_URL` set to the Postgres metadata DB).
- API: `uvicorn app.main:app --port 8080` — **must be 8080**, since vLLM owns 8000 and the frontend hardcodes `localhost:8080` (override via `NEXT_PUBLIC_API_BASE_URL`).
- Worker: `celery -A app.workers.celery_app worker -l info` — required for schema profiling. Must share the same `.env` as the API (same `QM_MASTER_KEY` + `DATABASE_URL`).
- vLLM probe: `python scripts/check_vllm.py` — run before the stack to confirm guided-JSON works against your vLLM build.

**Frontend** (from `frontend/`): `npm install`, then `npm run dev` / `npm run build` / `npm run lint` / `npm run type-check`.

**Infra**: `docker compose -f infra/docker-compose.dev.yml up -d` (Postgres 16 + Redis; vLLM commented out — run it on the host for GPU access). Test Postgres: `infra/docker-compose.test.yml` (ephemeral, port 55432).

**vLLM**: `vllm serve Qwen/Qwen2.5-0.5B-Instruct --max-model-len 8192 --port 8000` (xgrammar is vLLM's default structured-outputs backend; the old `--guided-decoding-backend` flag was removed in vLLM 0.21. On a host without the CUDA toolkit, add `--enforce-eager` + `VLLM_USE_FLASHINFER_SAMPLER=0`. See PLAN.md §"vLLM + Structured Output").

**End-to-end API smoke** (no browser): `infra/smoke_test.sh` — health → register → login → create workspace → poll profiling → SSE chat.

**Env essentials**: `QM_MASTER_KEY` (base64 32-byte AES-GCM key — same value for API and worker), `DATABASE_URL` (defaults to SQLite; set to Postgres for the real stack), `JWT_SECRET`, `VLLM_ENDPOINT`. See `backend/.env.example`.

CI runs the full backend suite (against a Postgres service) + the frontend build on every push — see `.github/workflows/ci.yml`.
