"""Blocking: generate candidate pairs without comparing all-vs-all.

A record can appear in multiple blocks. Two records become a candidate pair if
they share ANY block key. This keeps comparisons near-linear for MVP volumes.
"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import combinations


def block_keys(rec: object) -> set[str]:
    def g(attr: str):
        return getattr(rec, attr, None)

    keys: set[str] = set()
    last = g("normalized_last_name")
    state = g("state")
    zip5 = (g("zip_code") or "")[:5] or None
    case = g("case_number")
    norm_name = g("normalized_name")

    if last and state:
        keys.add(f"last_state:{last}|{state.upper()}")
    if last and zip5:
        keys.add(f"last_zip:{last}|{zip5}")
    if zip5 and norm_name:
        first_tok = norm_name.split(" ")[0] if norm_name else ""
        if first_tok:
            keys.add(f"zip_first:{zip5}|{first_tok[:1]}")
    if case:
        keys.add(f"case:{case.strip().upper()}")
    addr = g("normalized_address")
    if addr:
        keys.add(f"addr:{addr[:24]}")
    return keys


def generate_pairs(records: Iterable[object]) -> set[tuple[int, int]]:
    """Return index pairs (i<j) that share at least one block key."""
    records = list(records)
    buckets: dict[str, list[int]] = {}
    for idx, rec in enumerate(records):
        for key in block_keys(rec):
            buckets.setdefault(key, []).append(idx)

    pairs: set[tuple[int, int]] = set()
    for members in buckets.values():
        if len(members) < 2 or len(members) > 400:
            # Skip degenerate oversized blocks to avoid quadratic blowups.
            if len(members) > 400:
                continue
        for i, j in combinations(sorted(members), 2):
            pairs.add((i, j))
    return pairs
