from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.engines.base import ColumnMeta
from app.services.schema_profiler import _apply_id_heuristic, profile


@pytest.fixture()
def sales_db() -> Path:
    tmp = Path(tempfile.mkdtemp()) / "sales.db"
    conn = sqlite3.connect(str(tmp))
    conn.executescript(
        """
        CREATE TABLE sales(
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            amount REAL NOT NULL,
            region TEXT NOT NULL
        );
        INSERT INTO sales(order_id, customer_id, amount, region) VALUES
            (1, 1, 50.0, 'NA'),
            (2, 2, 100.0, 'NA'),
            (3, 3, 25.0, 'EU'),
            (4, 4, 200.0, 'EU'),
            (5, 1, 75.0, 'APAC');
        """
    )
    conn.commit()
    conn.close()
    return tmp


def _engine(db_path: Path):
    from app.engines.sqlite import SqliteEngine

    workspace = SimpleNamespace(
        dialect="sqlite",
        connection_meta={"path": str(db_path)},
    )
    return SqliteEngine(workspace)


def test_id_heuristic_pk() -> None:
    col = ColumnMeta(name="anything", data_type="integer", nullable=False, is_pk=True)
    _apply_id_heuristic(col)
    assert col.is_id is True


def test_id_heuristic_name_match() -> None:
    for name in ("id", "customer_id", "uuid", "guid", "user_id"):
        col = ColumnMeta(name=name, data_type="text", nullable=True)
        _apply_id_heuristic(col)
        assert col.is_id is True, f"{name} should be classified as ID"


def test_id_heuristic_skips_value_col() -> None:
    col = ColumnMeta(name="amount", data_type="real", nullable=False)
    _apply_id_heuristic(col)
    assert col.is_id is False


def test_id_heuristic_unique_monotonic_int() -> None:
    col = ColumnMeta(name="seq", data_type="bigint", nullable=False, is_unique=True)
    _apply_id_heuristic(col)
    assert col.is_id is True


@pytest.mark.asyncio
async def test_profile_classifies_columns(sales_db: Path) -> None:
    engine = _engine(sales_db)
    bundle = await profile(engine)
    sales = next(t for t in bundle.tables if t.name == "sales")
    by_name = {c.name: c for c in sales.columns}

    assert by_name["order_id"].is_id is True
    assert by_name["customer_id"].is_id is True
    assert by_name["amount"].is_id is False
    assert by_name["region"].is_id is False

    samples = bundle.samples["main.sales"]
    # Region is low-cardinality string -> categorical sample
    region_sample = samples["region"]
    assert region_sample.distinct_values is not None
    assert set(region_sample.distinct_values) == {"NA", "EU", "APAC"}
    assert region_sample.distinct_truncated is False

    # Amount is numeric -> stats
    amount_sample = samples["amount"]
    assert amount_sample.numeric_stats is not None
    assert amount_sample.numeric_stats["min"] == 25.0
    assert amount_sample.numeric_stats["max"] == 200.0

    # IDs skip value profiling
    order_sample = samples["order_id"]
    assert order_sample.distinct_values is None
    assert order_sample.numeric_stats is None
