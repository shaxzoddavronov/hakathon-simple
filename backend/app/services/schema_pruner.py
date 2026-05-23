from __future__ import annotations

import math
import re
from dataclasses import dataclass

from app.engines.base import SchemaBundle, TableMeta


@dataclass
class PrunedSchema:
    bundle: SchemaBundle
    selected_tables: list[str]   # "schema.table" qualified names, in score order
    pinned: list[str]            # explicitly named by the user — never dropped


_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]*")

# BM25 hyperparameters — standard defaults.
_K1 = 1.2
_B = 0.75


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_PATTERN.findall(text)]


def _table_doc(table: TableMeta) -> list[str]:
    """A table's bag-of-words for ranking: name + every column name."""
    parts = [table.name]
    parts.extend(c.name for c in table.columns)
    return _tokenize(" ".join(parts))


def prune(
    bundle: SchemaBundle,
    question: str,
    *,
    top_k: int = 8,
) -> PrunedSchema:
    """Keep the top-K most relevant tables for a question.

    Tables whose name appears literally in the question are *pinned*
    (always kept). Remaining slots are filled by BM25 score over
    `name + column-names` documents.
    """
    qtokens = set(_tokenize(question))
    qual_names = {f"{t.schema}.{t.name}": t for t in bundle.tables}
    docs = {qn: _table_doc(t) for qn, t in qual_names.items()}

    # Pin tables whose unqualified name is mentioned in the question.
    pinned: list[str] = []
    for qn, t in qual_names.items():
        if t.name.lower() in qtokens:
            pinned.append(qn)

    if len(pinned) >= top_k:
        return PrunedSchema(
            bundle=_subset(bundle, pinned[:top_k]),
            selected_tables=pinned[:top_k],
            pinned=pinned[:top_k],
        )

    # BM25 over the remaining tables.
    candidates = [qn for qn in qual_names if qn not in pinned]
    if not candidates:
        return PrunedSchema(bundle=_subset(bundle, pinned), selected_tables=pinned, pinned=pinned)

    avgdl = sum(len(docs[qn]) for qn in candidates) / max(len(candidates), 1)
    n_docs = len(candidates)
    df: dict[str, int] = {}
    for qn in candidates:
        for tok in set(docs[qn]):
            df[tok] = df.get(tok, 0) + 1

    scored: list[tuple[str, float]] = []
    for qn in candidates:
        doc = docs[qn]
        dl = len(doc) or 1
        score = 0.0
        # Term-frequency map for this doc
        tf: dict[str, int] = {}
        for tok in doc:
            tf[tok] = tf.get(tok, 0) + 1
        for tok in qtokens:
            if tok not in tf:
                continue
            f = tf[tok]
            n = df.get(tok, 0)
            idf = math.log(1 + (n_docs - n + 0.5) / (n + 0.5))
            score += idf * (f * (_K1 + 1)) / (f + _K1 * (1 - _B + _B * dl / avgdl))
        scored.append((qn, score))

    # Take only those with positive score; if none, fall back to alphabetical
    scored.sort(key=lambda x: x[1], reverse=True)
    selected = pinned + [qn for qn, s in scored if s > 0]
    if len(selected) < min(top_k, len(qual_names)):
        # No tokens overlap — fall back to alphabetical order of remaining
        rest_alpha = sorted(qn for qn in candidates if qn not in selected)
        selected.extend(rest_alpha)

    selected = selected[:top_k]
    return PrunedSchema(bundle=_subset(bundle, selected), selected_tables=selected, pinned=pinned)


def _subset(bundle: SchemaBundle, qual_names: list[str]) -> SchemaBundle:
    keep = set(qual_names)
    tables = [t for t in bundle.tables if f"{t.schema}.{t.name}" in keep]
    samples = {k: v for k, v in bundle.samples.items() if k in keep}
    return SchemaBundle(dialect=bundle.dialect, tables=tables, samples=samples)


__all__ = ["prune", "PrunedSchema"]
