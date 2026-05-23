from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture()
def sales_db() -> Path:
    """Build a small file-backed SQLite with sales(order_id, customer_id, ts, amount, region)."""
    tmp = Path(tempfile.mkdtemp()) / "sales.db"
    conn = sqlite3.connect(str(tmp))
    conn.executescript(
        """
        CREATE TABLE customers(
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE sales(
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER REFERENCES customers(customer_id),
            ts TEXT NOT NULL,
            amount REAL NOT NULL,
            region TEXT NOT NULL
        );
        INSERT INTO customers(customer_id, name) VALUES
            (1, 'Alice'), (2, 'Bob'), (3, 'Carol'), (4, 'Dan');
        INSERT INTO sales(order_id, customer_id, ts, amount, region) VALUES
            (1, 1, '2024-01-01', 50.0, 'NA'),
            (2, 2, '2024-01-02', 100.0, 'NA'),
            (3, 3, '2024-01-03', 25.0, 'EU'),
            (4, 4, '2024-01-04', 200.0, 'EU'),
            (5, 1, '2024-01-05', 75.0, 'APAC');
        """
    )
    conn.commit()
    conn.close()
    return tmp


def _engine(db_path: Path):
    # Imports inside to avoid touching app package at collection time.
    from app.engines.sqlite import SqliteEngine

    workspace = SimpleNamespace(
        dialect="sqlite",
        connection_meta={"path": str(db_path)},
    )
    return SqliteEngine(workspace)


@pytest.mark.asyncio
async def test_introspect_returns_tables_columns_fks(sales_db: Path) -> None:
    engine = _engine(sales_db)
    bundle = await engine.introspect_schema()
    table_names = {t.name for t in bundle.tables}
    assert table_names == {"customers", "sales"}
    sales = next(t for t in bundle.tables if t.name == "sales")
    col_names = [c.name for c in sales.columns]
    assert col_names == ["order_id", "customer_id", "ts", "amount", "region"]
    pk = next(c for c in sales.columns if c.name == "order_id")
    assert pk.is_pk is True
    fk = next(c for c in sales.columns if c.name == "customer_id")
    assert fk.fk_to == "main.customers.customer_id"
    assert sales.row_count_estimate == 5


@pytest.mark.asyncio
async def test_execute_respects_row_cap(sales_db: Path) -> None:
    engine = _engine(sales_db)
    rs = await engine.execute("SELECT * FROM sales", row_cap=2)
    assert rs.row_count == 2
    assert rs.truncated is True
    assert rs.columns == ["order_id", "customer_id", "ts", "amount", "region"]


@pytest.mark.asyncio
async def test_execute_returns_columns_and_rows(sales_db: Path) -> None:
    engine = _engine(sales_db)
    rs = await engine.execute("SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY region")
    assert rs.columns == ["region", "total"]
    assert rs.row_count == 3
    regions = {row[0] for row in rs.rows}
    assert regions == {"APAC", "EU", "NA"}


@pytest.mark.asyncio
async def test_write_attempt_fails_at_runtime(sales_db: Path) -> None:
    """PRAGMA query_only=ON + URI mode=ro both block writes even if the
    validator is bypassed. We bypass it intentionally by calling .execute()
    directly with a write statement."""
    engine = _engine(sales_db)
    with pytest.raises(Exception):
        await engine.execute("DELETE FROM sales")


def test_validate_readonly_delegates_to_validator(sales_db: Path) -> None:
    engine = _engine(sales_db)
    ok = engine.validate_readonly("SELECT * FROM sales")
    assert ok.ok is True
    bad = engine.validate_readonly("DROP TABLE sales")
    assert bad.ok is False


def test_missing_path_raises() -> None:
    from app.engines.sqlite import SqliteEngine

    workspace = SimpleNamespace(dialect="sqlite", connection_meta={})
    with pytest.raises(ValueError, match="path"):
        SqliteEngine(workspace)


@pytest.mark.asyncio
async def test_probe_write_access_always_false(sales_db: Path) -> None:
    # SQLite is opened mode=ro unconditionally, so it can never write.
    engine = _engine(sales_db)
    assert await engine.probe_write_access() is False
