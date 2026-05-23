from __future__ import annotations

from app.engines.base import ColumnMeta, SchemaBundle, TableMeta
from app.services.schema_pruner import prune


def _t(name: str, cols: list[str]) -> TableMeta:
    return TableMeta(
        schema="main",
        name=name,
        columns=[ColumnMeta(name=c, data_type="text", nullable=True) for c in cols],
    )


def _bundle() -> SchemaBundle:
    return SchemaBundle(
        dialect="sqlite",
        tables=[
            _t("orders", ["id", "customer_id", "amount", "region", "ts"]),
            _t("customers", ["id", "name", "email"]),
            _t("products", ["id", "name", "price", "category"]),
            _t("inventory", ["product_id", "warehouse", "qty"]),
            _t("events", ["id", "kind", "payload"]),
            _t("audit_log", ["actor", "action", "ts"]),
            _t("hr_employees", ["id", "name", "title"]),
            _t("payroll", ["employee_id", "amount", "ts"]),
            _t("invoices", ["id", "customer_id", "total"]),
            _t("regions", ["code", "name"]),
        ],
    )


def test_named_table_is_pinned() -> None:
    b = _bundle()
    out = prune(b, "show me orders by region in the last quarter", top_k=3)
    assert "main.orders" in out.pinned
    assert "main.orders" in out.selected_tables


def test_bm25_ranks_relevant_tables_higher() -> None:
    b = _bundle()
    out = prune(b, "average price per category for products", top_k=3)
    # products has all three relevant tokens (price/category/products)
    assert "main.products" in out.selected_tables


def test_top_k_caps_selection() -> None:
    b = _bundle()
    out = prune(b, "orders", top_k=2)
    assert len(out.selected_tables) <= 2


def test_falls_back_when_no_overlap() -> None:
    b = _bundle()
    out = prune(b, "xyzzy fooblar quuux", top_k=4)
    # No tokens overlap any table → alphabetical fill, still returns top_k
    assert len(out.selected_tables) == 4


def test_returned_bundle_only_contains_selected() -> None:
    b = _bundle()
    out = prune(b, "show me orders", top_k=2)
    bundle_table_names = {f"{t.schema}.{t.name}" for t in out.bundle.tables}
    assert bundle_table_names == set(out.selected_tables)
