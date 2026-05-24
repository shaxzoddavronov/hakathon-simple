# QueryMind AI

**Ask your own database questions in plain language — get answers, charts, and dashboards.**

QueryMind AI is a **self-hosted** analytics assistant. You connect your own database, it
introspects the schema, and a [LangGraph](https://langchain-ai.github.io/langgraph/) agent
turns natural-language questions into **read-only** queries, runs them, and replies with a
written answer plus an optional chart or multi-panel dashboard. All inference runs against a
**local, OpenAI-compatible vLLM** server — no external AI APIs.

---

## Highlights

- 🔌 **Six database engines** behind one abstraction — PostgreSQL, SQLite, ClickHouse,
  Oracle, Elasticsearch, and MongoDB.
- 🔒 **Read-only by design** — defense in depth at three layers (see below), enforced by
  QueryMind itself regardless of the connecting credential's permissions.
- 🧠 **Two-model agent** — a *fast* model powers the chat; a *standard* model runs a
  database-"learning" pass on connect (semantic schema understanding).
- 📊 **Charts & dashboards** — answers render as KPIs, bar/line/pie charts, tables, or a
  multi-panel dashboard (toggle **Dashboard-Diagram** mode in chat).
- 🎨 **"Neural Dark" UI** — a Next.js glassmorphism interface (chat, schema explorer,
  connect wizard, settings).
- ⚙️ **Editable settings, per user** — endpoint, API token, and model choices persist in the
  DB across logout/login.

## Supported data sources

| Engine | Family | How it queries | Runtime read-only guard |
|---|---|---|---|
| PostgreSQL | SQL | generated SQL | read-only transaction + statement timeout |
| SQLite | SQL | generated SQL | `mode=ro` + `PRAGMA query_only` |
| ClickHouse | SQL | generated SQL | `readonly=2` setting |
| Oracle | SQL | generated SQL | `SET TRANSACTION READ ONLY` |
| Elasticsearch | SQL | the read-only `_sql` API | `_sql` cannot mutate data |
| MongoDB | non-SQL | aggregation pipeline | `aggregate()` only, never a write method |

Adding a new engine = register one adapter in `backend/app/engines/registry.py`; the agent is
engine-agnostic because every engine returns a uniform `ResultSet` (columns + rows).

## How it works (the agent)

```
coordinator → schema_loader → query_planner ↔ query_validator → query_executor → {chart_designer ∥ answer_writer} → finalizer
```

1. **coordinator** classifies the question (chitchat / metadata / data query / dashboard).
2. **schema_loader** loads the profiled schema and picks the relevant tables.
3. **query_planner** writes a read-only query (SQL or a Mongo pipeline) for the target engine.
4. **query_validator** rejects anything unsafe (parse layer) — retries the planner if needed.
5. **query_executor** runs it read-only and returns rows.
6. **chart_designer** + **answer_writer** (in parallel) build the visualization and the prose.
7. **finalizer** merges them into the UI response.

**Read-only — three layers:** (1) a connect-time write probe, (2) a parse-layer validator
(`sqlglot` for SQL, a pipeline validator for Mongo) that blocks DML/DDL/JS/write stages, and
(3) the per-engine runtime guards in the table above.

## Tech stack

- **Backend:** FastAPI · LangGraph · Celery · SQLAlchemy (async) · Postgres (metadata) · Redis
- **Frontend:** Next.js (App Router) · Tailwind · Recharts
- **LLM:** vLLM (OpenAI-compatible, `response_format` JSON-schema / xgrammar guided decoding)
- **Security:** JWT auth · AES-GCM credential encryption at rest

## Quick start (Docker)

```bash
cp .env.prod.example .env          # set QM_MASTER_KEY, JWT_SECRET, VLLM_* (endpoint/token)
docker compose -f infra/docker-compose.prod.yml up -d --build
```

Brings up Postgres + Redis + API + Celery worker + frontend (with migrations run
automatically). The model server (vLLM) stays external — point `VLLM_ENDPOINT` at a host-run
vLLM or a shared endpoint and set `VLLM_API_KEY`.

- Frontend → `http://<host>:3000`
- API → `http://<host>:8080`

To serve on a server IP, set `NEXT_PUBLIC_API_BASE_URL=http://<ip>:8080` and
`CORS_ORIGINS=http://<ip>:3000` before `up --build`.

## Local development

**Infra only (Postgres + Redis):**
```bash
docker compose -f infra/docker-compose.dev.yml up -d
```

**Backend** (`cd backend`, after `pip install -r requirements.txt`):
```bash
alembic upgrade head                                   # migrations
uvicorn app.main:app --port 8080                       # API (must be 8080)
celery -A app.workers.celery_app worker -l info        # schema profiling worker
pytest tests/unit/                                     # unit tests (no DB needed)
```

**Frontend** (`cd frontend`):
```bash
npm install && npm run dev        # http://localhost:3000
```

**vLLM (example):**
```bash
vllm serve <model> --max-model-len 8192 --port 8000
```

## Configuration

Key env vars (`.env` / `backend/.env.example`):

| Var | Purpose |
|---|---|
| `DATABASE_URL` | metadata DB (async SQLAlchemy URL) |
| `QM_MASTER_KEY` | base64 (url-safe) 32-byte AES-GCM key for credential encryption |
| `JWT_SECRET` | JWT signing secret |
| `VLLM_ENDPOINT` | OpenAI-compatible model endpoint (`…/v1`) |
| `VLLM_API_KEY` | token for the model endpoint (blank for a local keyless vLLM) |
| `VLLM_MODEL` / `VLLM_MODEL_PROFILE` | chat (fast) / learning (standard) models |
| `CORS_ORIGINS` | allowed browser origins (`*` allows any) |

Endpoint, token, and model choices are also editable per user in **Settings** (persisted).

## Repository layout

```
backend/   FastAPI app — agents/ (LangGraph nodes), engines/ (DB adapters),
           services/ (read-only validators, crypto, profiler), api/, db/, workers/
frontend/  Next.js app — app/ (pages), components/ (RenderSpec, charts, Chrome)
infra/     docker-compose (dev / test / prod), seed SQL, smoke test
```

## License

See [LICENSE](LICENSE).
