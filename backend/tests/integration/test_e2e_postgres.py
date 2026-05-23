"""End-to-end chat test against a live Postgres (docker-compose.test.yml).

Unlike the SQLite e2e, this exercises the real asyncpg paths: the
read-only transaction wrapper, information_schema introspection, and
pg_class row-count estimates. The metadata DB and the user-data DB are
separate Postgres databases on the same test instance.

Skipped automatically unless the test Postgres is reachable on
localhost:55432. Bring it up with:

    docker compose -f infra/docker-compose.test.yml up -d
    docker exec qm_postgres_test psql -U querymind -d querymind_test -c "CREATE DATABASE sales_demo;"
    # then seed sales_demo (see infra/seed/seed_sales.sql)
"""
from __future__ import annotations

import base64
import json
import os
import socket
from uuid import UUID

import pytest

_PG_HOST = os.environ.get("QM_TEST_PG_HOST", "localhost")
_PG_PORT = int(os.environ.get("QM_TEST_PG_PORT", "55432"))
_META_DB = "querymind_test"
_DATA_DB = "sales_demo"
_PG_USER = "querymind"
_PG_PASSWORD = "querymind"


def _pg_reachable() -> bool:
    try:
        with socket.create_connection((_PG_HOST, _PG_PORT), timeout=1.0):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not _pg_reachable(),
    reason=f"test Postgres not reachable at {_PG_HOST}:{_PG_PORT}",
)

# Env must be set before app modules import Settings.
os.environ["DATABASE_URL"] = (
    f"postgresql+asyncpg://{_PG_USER}:{_PG_PASSWORD}@{_PG_HOST}:{_PG_PORT}/{_META_DB}"
)
os.environ["JWT_SECRET"] = "test-secret-very-long-very-secret-123456"
os.environ["QM_MASTER_KEY"] = base64.b64encode(os.urandom(32)).decode()
os.environ["VLLM_ENDPOINT"] = "http://localhost:65535/v1"

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.agents import llm as llm_module  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import Base, models as orm  # noqa: E402
from app.engines import register_all as register_engines  # noqa: E402
from app.schemas.llm_io import AnswerDraft, IntentDecision, SqlPlan  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
async def metadata_schema():
    # Set our DATABASE_URL at fixture time so a sibling integration module
    # (e.g. the SQLite e2e) can't win the import-order race.
    os.environ["DATABASE_URL"] = (
        f"postgresql+asyncpg://{_PG_USER}:{_PG_PASSWORD}@{_PG_HOST}:{_PG_PORT}/{_META_DB}"
    )
    get_settings.cache_clear()  # type: ignore[attr-defined]
    new_settings = get_settings()
    import app.config as cfg
    cfg.settings = new_settings

    sa_engine = create_async_engine(new_settings.DATABASE_URL)
    async with sa_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        # Clean slate so reruns don't trip the unique(owner_id, name) etc.
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await sa_engine.dispose()
    register_engines()
    yield


class StubLLM:
    def __init__(self) -> None:
        self._by_type: dict[type, object] = {}

    def register(self, cls, value) -> None:
        self._by_type[cls] = value

    async def structured(self, _messages, response_model, **_kw):
        if response_model not in self._by_type:
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
            dialect="postgres",
            sql="SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY region",
            rationale="revenue per region",
            expected_columns=["region", "total"],
        ),
    )
    stub.register(
        AnswerDraft,
        AnswerDraft(headline="Revenue by region", body_md="EU 225, NA 150, APAC 75."),
    )
    monkeypatch.setattr(llm_module, "_default_client", stub)
    yield stub
    monkeypatch.setattr(llm_module, "_default_client", None)


async def _seed_user_and_workspace() -> tuple[UUID, str]:
    from app.api.deps import create_access_token
    from app.engines.registry import get_engine
    from app.services import crypto
    from app.services.schema_profiler import profile

    settings = get_settings()
    sa_engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(sa_engine, expire_on_commit=False)

    async with Session() as session:
        user = orm.User(email="pg-e2e@test", password_hash="not-used")
        session.add(user)
        await session.flush()

        conn_meta = {
            "host": _PG_HOST,
            "port": _PG_PORT,
            "db_name": _DATA_DB,
            "ssl": False,
        }
        ws = orm.Workspace(
            owner_id=user.id,
            name="sales_demo_pg",
            dialect="postgres",
            connection_meta=conn_meta,
            status="profiling",
        )
        session.add(ws)
        await session.flush()

        creds_blob = json.dumps({"user": _PG_USER, "password": _PG_PASSWORD}).encode()
        ct, nonce, kv = crypto.encrypt(creds_blob, aad=str(ws.id).encode())
        session.add(
            orm.WorkspaceCredentials(
                workspace_id=ws.id,
                auth_kind="password",
                ciphertext=ct,
                nonce=nonce,
                key_version=kv,
            )
        )

        # Profile the real data DB through the Postgres engine.
        ws._credentials = {"user": _PG_USER, "password": _PG_PASSWORD}  # type: ignore[attr-defined]
        engine = get_engine(ws)
        bundle = await profile(engine)
        await engine.aclose()

        session.add(
            orm.SchemaBundle(
                workspace_id=ws.id,
                bundle=bundle.model_dump(mode="json"),
                schema_hash="p" * 64,
                status="ready",
            )
        )
        ws.status = "ready"
        await session.commit()
        ws_id = ws.id
        user_id = user.id

        # Sanity: the profiler must have found the sales + customers tables.
        table_names = {t.name for t in bundle.tables}
        assert "sales" in table_names, f"profiler missed sales: {table_names}"
        assert "customers" in table_names

    await sa_engine.dispose()
    return ws_id, create_access_token(str(user_id))


@pytest.mark.asyncio
async def test_postgres_chat_end_to_end(stub_llm: StubLLM) -> None:
    import httpx
    from httpx import ASGITransport

    from app.main import create_app

    ws_id, token = await _seed_user_and_workspace()
    app = create_app()

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://t"
    ) as client:
        events: list[tuple[str, object]] = []
        async with client.stream(
            "POST",
            "/chat",
            json={"message": "revenue by region", "active_workspace_id": str(ws_id)},
            headers={"Authorization": f"Bearer {token}"},
        ) as resp:
            assert resp.status_code == 200, await resp.aread()
            buf = ""
            async for chunk in resp.aiter_text():
                buf += chunk
                while "\n\n" in buf:
                    raw, buf = buf.split("\n\n", 1)
                    evt, data = "message", ""
                    for line in raw.split("\n"):
                        if line.startswith("event:"):
                            evt = line.split(":", 1)[1].strip()
                        elif line.startswith("data:"):
                            data += line.split(":", 1)[1].strip()
                    try:
                        events.append((evt, json.loads(data)))
                    except Exception:
                        events.append((evt, data))

    final = next(d for k, d in events if k == "final")
    assert isinstance(final, dict)
    assert final.get("ui_spec") is not None
    assert final.get("sql")
    assert "LIMIT" in final["sql"].upper()
