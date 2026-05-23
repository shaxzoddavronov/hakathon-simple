from __future__ import annotations

import sqlglot
from sqlglot import exp

from app.engines.base import ValidationFinding, ValidationResult

# Statement node types that are unconditionally write/admin operations.
# Built by name so missing-from-installed-sqlglot classes don't crash the import.
_WRITE_NODE_NAMES = {
    "Insert",
    "Update",
    "Delete",
    "Drop",
    "Alter",
    "Create",
    "TruncateTable",
    "Truncate",
    "Grant",
    "Revoke",
    "Merge",
    "Set",
    "SetItem",
    "Use",
    "Copy",
    "Command",
    "Call",
}


def _write_node_types() -> tuple[type, ...]:
    types: list[type] = []
    for name in _WRITE_NODE_NAMES:
        cls = getattr(exp, name, None)
        if isinstance(cls, type):
            types.append(cls)
    return tuple(types)


_WRITE_TYPES = _write_node_types()

_SYSTEM_TABLES = {
    "pg_authid",
    "pg_shadow",
    "pg_settings",
    "pg_user",
    "pg_roles",
    "user_privileges",
    "role_table_grants",
}

_DANGEROUS_FUNCS = {
    "pg_sleep",
    "pg_read_file",
    "pg_read_binary_file",
    "pg_ls_dir",
    "lo_import",
    "lo_export",
    "dblink",
    "dblink_exec",
    "load_file",
    "system",
}

_DEFAULT_ROW_CAP = 1000


def validate_readonly(sql: str, dialect: str = "postgres") -> ValidationResult:
    findings: list[ValidationFinding] = []

    try:
        statements = sqlglot.parse(sql, read=dialect)
    except Exception as e:
        return ValidationResult(
            ok=False,
            findings=[ValidationFinding(code="PARSE_ERROR", message=str(e))],
        )

    statements = [s for s in statements if s is not None]
    if len(statements) == 0:
        return ValidationResult(
            ok=False,
            findings=[ValidationFinding(code="EMPTY", message="No statement found")],
        )
    if len(statements) > 1:
        return ValidationResult(
            ok=False,
            findings=[
                ValidationFinding(
                    code="MULTI_STATEMENT",
                    message=f"Expected a single statement, got {len(statements)}",
                )
            ],
        )

    root = statements[0]

    # Must be a Select (possibly wrapped in WITH).
    if not isinstance(root, (exp.Select, exp.With, exp.Subquery, exp.Union)):
        findings.append(
            ValidationFinding(
                code="NOT_SELECT",
                message=f"Top-level statement is {type(root).__name__}, not SELECT",
                node_kind=type(root).__name__,
            )
        )
        return ValidationResult(ok=False, findings=findings)

    # Walk the AST. Reject write nodes, system tables, dangerous funcs, INTO OUTFILE.
    for node in root.walk():
        # walk() yields nodes in sqlglot 25+ (older versions yielded tuples — handle both)
        if isinstance(node, tuple):
            node = node[0]

        if _WRITE_TYPES and isinstance(node, _WRITE_TYPES):
            findings.append(
                ValidationFinding(
                    code="WRITE_OPERATION",
                    message=f"{type(node).__name__} is not allowed",
                    node_kind=type(node).__name__,
                )
            )

        # Table references against system catalogs.
        if isinstance(node, exp.Table):
            tname = (node.name or "").lower()
            db = (node.db or "").lower()
            schema = ""
            schema_arg = node.args.get("db")
            if schema_arg is not None:
                schema = (schema_arg.name if hasattr(schema_arg, "name") else str(schema_arg)).lower()
            qual = ".".join(p for p in (db, schema, tname) if p)
            if tname in _SYSTEM_TABLES or any(s in qual for s in _SYSTEM_TABLES):
                findings.append(
                    ValidationFinding(
                        code="SYSTEM_TABLE",
                        message=f"Reference to system table {qual or tname!r} is not allowed",
                        node_kind="Table",
                    )
                )

        # Function calls. Both Func subclasses and Anonymous-named funcs.
        if isinstance(node, exp.Func):
            fname = None
            if isinstance(node, exp.Anonymous):
                fname = (node.name or "").lower()
            else:
                # sql_name() returns the canonical SQL name for builtins
                try:
                    fname = node.sql_name().lower() if hasattr(node, "sql_name") else None
                except Exception:
                    fname = None
                if not fname:
                    fname = type(node).__name__.lower()
            if fname and fname in _DANGEROUS_FUNCS:
                findings.append(
                    ValidationFinding(
                        code="DANGEROUS_FUNC",
                        message=f"Function {fname!r} is not allowed",
                        node_kind=type(node).__name__,
                    )
                )

        # INTO OUTFILE / DUMPFILE — sqlglot may parse these as Into or as Command.
        if isinstance(node, exp.Into):
            kind = (node.args.get("kind") or "")
            text = str(kind).lower()
            if "outfile" in text or "dumpfile" in text:
                findings.append(
                    ValidationFinding(
                        code="INTO_OUTFILE",
                        message="SELECT ... INTO OUTFILE/DUMPFILE is not allowed",
                        node_kind="Into",
                    )
                )

    # Raw string fallbacks for things sqlglot parses as Command/raw tokens.
    sql_lc = sql.lower()
    if "into outfile" in sql_lc or "into dumpfile" in sql_lc:
        if not any(f.code == "INTO_OUTFILE" for f in findings):
            findings.append(
                ValidationFinding(
                    code="INTO_OUTFILE",
                    message="SELECT ... INTO OUTFILE/DUMPFILE is not allowed",
                )
            )

    if findings:
        return ValidationResult(ok=False, findings=findings)

    # Inject LIMIT 1000 on the outermost SELECT if missing.
    rewritten_sql = _maybe_inject_limit(root, dialect, _DEFAULT_ROW_CAP)
    return ValidationResult(ok=True, rewritten_sql=rewritten_sql)


def _maybe_inject_limit(root: exp.Expression, dialect: str, cap: int) -> str:
    target: exp.Expression | None = None
    if isinstance(root, exp.Select):
        target = root
    elif isinstance(root, exp.With):
        inner = root.this
        if isinstance(inner, exp.Select):
            target = inner
    elif isinstance(root, exp.Union):
        # Apply LIMIT to the union itself
        target = root

    if target is None:
        return root.sql(dialect=dialect)

    existing_limit = target.args.get("limit") if hasattr(target, "args") else None
    if existing_limit is None:
        target.set("limit", exp.Limit(expression=exp.Literal.number(cap)))

    return root.sql(dialect=dialect)
