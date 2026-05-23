"""End-to-end chat test on a pure-SQLite stack.

Exercises the full request path: POST /chat → workspace resolver →
LangGraph (with a stubbed LLM) → SQLite engine.execute on a seeded
file-backed DB → SSE stream → persisted assistant Message + QueryHistory.

Skipped if the SQLAlchemy/aiosqlite stack isn't installed.
"""
from __future__ import annotations

import base64
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

import pytest

# Configure env BEFORE any app modules import so Settings picks them up.
_TMP_DIR = Path(tempfile.mkdtemp())
_META_DB_PATH = _TMP_DIR / "qm-meta.db"
_DATA_DB_PATH = _TMP_DIR / "sales.db"

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_META_DB_PATH}"
os.environ["JWT_SECRET"] = "test-secret-very-long-very-secret-123456"
os.environ["QM_MASTER_KEY"] = base64.b64encode(os.urandom(32)).decode()
os.environ["VLLM_ENDPOINT"] = "http://localhost:65535/v1"

from sqlalchemy import String, event, types  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402


class _StringUUID(types.TypeDecorator):
    """Round-trips UUID ↔ String(36) for SQLite. Tests use this in place
    of the production PG_UUID type so bind parameters and SELECT
    parameters both Just Work without changing production code."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, _dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, _dialect):
        if value is None:
            return None
        return UUID(value)

from app.agents import llm as llm_module  # noqa: E402
from app.config import get_settings, settings as _settings  # noqa: E402
from app.db import Base  # noqa: E402
from app.db import models as orm  # noqa: E402
from app.engines import register_all as register_engines  # noqa: E402
from app.schemas.llm_io import AnswerDraft, IntentDecision, SqlPlan  # noqa: E402
from app.services import crypto  # noqa: E402


# Set UUID and timestamp Python-side defaults so SQLite (no gen_random_uuid)
# doesn't choke. Applied to all UUID-PK tables.
def _patch_uuid_defaults(cls) -> None:
    @event.listens_for(cls, "before_insert", propagate=True)
    def _set_uuid(_mapper, _conn, target):  # noqa: ARG001
        for col in cls.__table__.primary_key.columns:
            # Match both the original PG_UUID and our test _StringUUID swap.
            tname = str(col.type).upper()
            if ("UUID" in tname or "VARCHAR(36)" in tname) and getattr(target, col.name, None) is None:
                setattr(target, col.name, uuid4())


for _model in (
    orm.User,
    orm.Workspace,
    orm.WorkspaceCredentials,
    orm.SchemaBundle,
    orm.ChatSession,
    orm.Message,
    orm.QueryHistory,
    orm.ProfileJob,
):
    _patch_uuid_defaults(_model)


@pytest.fixture(scope="module")
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
def seed_data_db() -> Path:
    """Build the sales.db that the test workspace connects to."""
    conn = sqlite3.connect(str(_DATA_DB_PATH))
    conn.executescript(
        """
        CREATE TABLE sales(
          order_id INTEGER PRIMARY KEY,
          customer_id INTEGER,
          ts TEXT NOT NULL,
          amount REAL NOT NULL,
          region TEXT NOT NULL
        );
        INSERT INTO sales VALUES
          (1, 1, '2024-01-01', 50.0, 'NA'),
          (2, 2, '2024-01-02', 100.0, 'NA'),
          (3, 3, '2024-01-03', 25.0, 'EU'),
          (4, 4, '2024-01-04', 200.0, 'EU'),
          (5, 1, '2024-01-05', 75.0, 'APAC');
        """
    )
    conn.commit()
    conn.close()
    return _DATA_DB_PATH


def _swap_uuid_types_for_sqlite() -> None:
    """Replace every UUID column's type with _StringUUID so SQLite
    parameter binding works in either direction."""
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if "UUID" in str(col.type).upper():
                col.type = _StringUUID()


def _strip_pg_only_server_defaults() -> None:
    """The Postgres-flavored server_defaults (gen_random_uuid(),
    '{}'::jsonb) make CREATE TABLE fail on SQLite. We have Python-side
    UUID defaults via event hooks above, so drop the SQL defaults for
    the test stack."""
    from sqlalchemy.schema import DefaultClause

    for table in Base.metadata.tables.values():
        for col in table.columns:
            sd = col.server_default
            if sd is None:
                continue
            text = ""
            if isinstance(sd, DefaultClause):
                arg = getattr(sd, "arg", None)
                text = str(arg) if arg is not None else ""
            else:
                text = str(sd)
            if "gen_random_uuid" in text or "jsonb" in text:
                col.server_default = None


@pytest.fixture(scope="module", autouse=True)
async def init_metadata_db():
    """Create the metadata schema in the SQLite test DB."""
    get_settings.cache_clear()  # type: ignore[attr-defined]
    new_settings = get_settings()
    # Refresh the module-level `settings` reference too — crypto reads through it.
    import app.config as cfg
    cfg.settings = new_settings

    _strip_pg_only_server_defaults()
    _swap_uuid_types_for_sqlite()

    sa_engine = create_async_engine(new_settings.DATABASE_URL, pool_pre_ping=True)
    async with sa_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await sa_engine.dispose()
    register_engines()
    yield
    if _META_DB_PATH.exists():
        _META_DB_PATH.unlink()


class StubLLM:
    """Maps response-model class → canned instance."""

    def __init__(self) -> None:
        self._by_type: dict[type, object] = {}

    def register(self, cls, value) -> None:
        self._by_type[cls] = value

    async def structured(self, _messages, response_model, **_kw):
        if response_model not in self._by_type:
            # Be liberal: if a node asks for something we didn't stub, fall
            # back to a tolerable default rather than crashing the stream.
            if response_model is AnswerDraft:
                return AnswerDraft(headline="ok", body_md="ok")
            raise AssertionError(f"StubLLM missing {response_model.__name__}")
        return self._by_type[response_model]


@pytest.fixture()
def stub_llm(monkeypatch):
    stub = StubLLM()
    stub.register(IntentDecision, IntentDecision(intent="data_query", workspace_hint=None))
    stub.register(
        SqlPlan,
        SqlPlan(
            dialect="sqlite",
            sql="SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY region",
            rationale="aggregate revenue per region",
            expected_columns=["region", "total"],
        ),
    )
    stub.register(
        AnswerDraft,
        AnswerDraft(
            headline="Revenue by region",
            body_md="EU leads at 225, NA at 150, APAC at 75.",
        ),
    )
    monkeypatch.setattr(llm_module, "_default_client", stub)
    yield stub
    monkeypatch.setattr(llm_module, "_default_client", None)


async def _seed_user_and_workspace(data_db_path: Path) -> tuple[UUID, UUID, str]:
    """Insert a User + Workspace + Credentials + SchemaBundle directly,
    returning (user_id, workspace_id, jwt_token)."""
    from app.api.deps import create_access_token
    from app.engines.sqlite import SqliteEngine
    from app.services.schema_profiler import profile

    settings = get_settings()
    sa_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    Session = async_sessionmaker(sa_engine, expire_on_commit=False)

    # We mint the JWT directly so we don't go through /auth/login. The hash
    # field is required by the model but never verified in this test.
    async with Session() as session:
        user = orm.User(email="e2e@test", password_hash="not-used-in-test")
        session.add(user)
        await session.flush()

        ws = orm.Workspace(
            owner_id=user.id,
            name="sales_e2e",
            dialect="sqlite",
            connection_meta={"path": str(data_db_path)},
            status="profiling",
        )
        session.add(ws)
        await session.flush()

        # No credentials needed for SQLite file paths.

        # Profile the data DB so the agent has a schema bundle to lean on.
        from types import SimpleNamespace
        engine = SqliteEngine(SimpleNamespace(dialect="sqlite", connection_meta={"path": str(data_db_path)}))
        bundle = await profile(engine)
        await engine.aclose()
        payload = bundle.model_dump(mode="json")

        session.add(
            orm.SchemaBundle(
                workspace_id=ws.id,
                bundle=payload,
                schema_hash="x" * 64,
                status="ready",
            )
        )
        ws.status = "ready"
        await session.commit()
        user_id, ws_id = user.id, ws.id

    await sa_engine.dispose()
    token = create_access_token(str(user_id))
    return user_id, ws_id, token


@pytest.mark.asyncio
async def test_chat_end_to_end_returns_ui_spec(stub_llm: StubLLM) -> None:
    import httpx
    from httpx import ASGITransport

    from app.main import create_app

    _user_id, ws_id, token = await _seed_user_and_workspace(_DATA_DB_PATH)
    app = create_app()
    transport = ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        # Smoke: workspace list
        r = await client.get("/workspaces", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        names = [w["name"] for w in r.json()]
        assert "sales_e2e" in names

        # Stream the chat
        events: list[tuple[str, object]] = []
        async with client.stream(
            "POST",
            "/chat",
            json={
                "message": "show me revenue by region",
                "active_workspace_id": str(ws_id),
            },
            headers={"Authorization": f"Bearer {token}"},
        ) as resp:
            assert resp.status_code == 200, await resp.aread()
            buf = ""
            async for chunk in resp.aiter_text():
                buf += chunk
                while "\n\n" in buf:
                    raw, buf = buf.split("\n\n", 1)
                    evt = "message"
                    data = ""
                    for line in raw.split("\n"):
                        if line.startswith("event:"):
                            evt = line.split(":", 1)[1].strip()
                        elif line.startswith("data:"):
                            data += line.split(":", 1)[1].strip()
                    parsed: object = data
                    try:
                        parsed = json.loads(data)
                    except Exception:
                        pass
                    events.append((evt, parsed))

        # Assertions on the stream
        kinds = [e[0] for e in events]
        assert "session" in kinds
        assert "final" in kinds
        assert any(k == "node" for k in kinds)

        final = next(d for k, d in events if k == "final")
        assert isinstance(final, dict)
        assert final.get("ui_spec") is not None
        assert final.get("sql"), "final event should carry the executed SQL"
        # The validator injects LIMIT 1000 — confirm it survived.
        assert "LIMIT" in final["sql"].upper()
