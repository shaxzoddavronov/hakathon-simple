from __future__ import annotations

import pytest

from app.services.readonly_validator import validate_readonly

MALICIOUS = [
    ("drop_table", "DROP TABLE users;", "postgres"),
    ("multi_drop", "SELECT 1; DROP TABLE users;", "postgres"),
    (
        "cte_with_delete",
        "WITH x AS (DELETE FROM t RETURNING *) SELECT * FROM x;",
        "postgres",
    ),
    ("system_table_pg_authid", "SELECT * FROM pg_authid;", "postgres"),
    ("pg_sleep", "SELECT pg_sleep(60);", "postgres"),
    ("load_file", "SELECT load_file('/etc/passwd');", "mysql"),
    (
        "into_outfile",
        "SELECT * INTO OUTFILE '/tmp/x' FROM users;",
        "mysql",
    ),
    ("copy_to_file", "COPY users TO '/tmp/leak.csv';", "postgres"),
    (
        "create_temp_table",
        "CREATE TEMP TABLE t AS SELECT * FROM users;",
        "postgres",
    ),
    ("grant_all", "GRANT ALL ON users TO public;", "postgres"),
    ("truncate", "TRUNCATE users;", "postgres"),
    ("update", "UPDATE users SET pw='x';", "postgres"),
    (
        "merge",
        "MERGE INTO t USING s ON t.id=s.id WHEN MATCHED THEN UPDATE SET x = s.x;",
        "postgres",
    ),
    (
        "dblink",
        "SELECT * FROM dblink('host=evil', 'DROP TABLE x') AS t(x int);",
        "postgres",
    ),
]


BENIGN = [
    ("simple_select", "SELECT * FROM users LIMIT 5", "postgres"),
    (
        "inner_join_where",
        "SELECT u.id, o.amount FROM users u JOIN orders o ON o.user_id = u.id WHERE o.amount > 100",
        "postgres",
    ),
    (
        "left_join_group_having",
        "SELECT u.region, COUNT(*) AS c FROM users u LEFT JOIN orders o ON o.user_id = u.id GROUP BY u.region HAVING COUNT(*) > 0",
        "postgres",
    ),
    (
        "cte_chain",
        "WITH a AS (SELECT id FROM users), b AS (SELECT id FROM a) SELECT * FROM b",
        "postgres",
    ),
    (
        "window_func",
        "SELECT id, SUM(amount) OVER (PARTITION BY region ORDER BY ts) FROM sales",
        "postgres",
    ),
    (
        "rollup",
        "SELECT region, COUNT(*) FROM sales GROUP BY ROLLUP(region, ts::date)",
        "postgres",
    ),
    (
        "lateral",
        "SELECT u.id, t.cnt FROM users u, LATERAL (SELECT COUNT(*) AS cnt FROM orders o WHERE o.user_id = u.id) t",
        "postgres",
    ),
    (
        "union_subselect",
        "SELECT id FROM (SELECT id FROM users WHERE active) s UNION ALL SELECT id FROM admins",
        "postgres",
    ),
]


@pytest.mark.parametrize(
    "sql,dialect",
    [(s, d) for _, s, d in MALICIOUS],
    ids=[name for name, _, _ in MALICIOUS],
)
def test_malicious_rejected(sql: str, dialect: str) -> None:
    result = validate_readonly(sql, dialect=dialect)
    assert result.ok is False, f"Expected REJECT, got OK for: {sql}"
    assert result.findings, f"Expected at least one finding for: {sql}"
    assert result.findings[0].code, "Finding must carry a code"


@pytest.mark.parametrize(
    "sql,dialect",
    [(s, d) for _, s, d in BENIGN],
    ids=[name for name, _, _ in BENIGN],
)
def test_benign_accepted(sql: str, dialect: str) -> None:
    result = validate_readonly(sql, dialect=dialect)
    assert result.ok is True, f"Expected OK, got REJECT for: {sql}; findings: {result.findings}"


def test_limit_injected_when_missing() -> None:
    result = validate_readonly(
        "SELECT id FROM users", dialect="postgres"
    )
    assert result.ok is True
    assert result.rewritten_sql is not None
    assert "LIMIT 1000" in result.rewritten_sql.upper()


def test_limit_preserved_when_present() -> None:
    result = validate_readonly(
        "SELECT id FROM users LIMIT 5", dialect="postgres"
    )
    assert result.ok is True
    assert result.rewritten_sql is not None
    upper = result.rewritten_sql.upper()
    assert "LIMIT 5" in upper
    assert "LIMIT 1000" not in upper


def test_multi_statement_explicit_code() -> None:
    result = validate_readonly(
        "SELECT 1; SELECT 2", dialect="postgres"
    )
    assert result.ok is False
    assert any(f.code == "MULTI_STATEMENT" for f in result.findings)


def test_parse_error_handled() -> None:
    result = validate_readonly("SELEKT * FROMM", dialect="postgres")
    assert result.ok is False
    assert any(f.code in {"PARSE_ERROR", "NOT_SELECT", "WRITE_OPERATION"} for f in result.findings)
