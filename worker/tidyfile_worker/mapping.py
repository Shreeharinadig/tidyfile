"""Rule-based column mapping: the baseline that the LLM mapper must beat."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from .profiling import ColumnProfile
from .schemas import KNOWN_ALIASES, SCHEMAS

ABBREVIATIONS = {
    "amt": "amount",
    "nm": "name",
    "dt": "date",
    "cust": "customer",
    "inv": "invoice",
    "qty": "quantity",
    "pmt": "payment",
    "prod": "product",
    "stat": "status",
    "lvl": "level",
    "stk": "stock",
    "no": "number",
    "num": "number",
    "ord": "order",
}

EXACT_CONFIDENCE = 0.95
FUZZY_THRESHOLD = 0.85
FUZZY_WEIGHT = 0.85


@dataclass(frozen=True)
class Mapping:
    source_column: str
    target_column: str | None
    confidence: float
    origin: str = "rule"


def normalize(header: str) -> str:
    """Lowercase, strip punctuation, and expand common abbreviations."""
    tokens = re.sub(r"[^a-z0-9]+", " ", header.lower()).split()
    return " ".join(ABBREVIATIONS.get(token, token) for token in tokens)


def _compatible(kind: str, inferred: str) -> bool:
    if kind == "string":
        return inferred != "empty"
    if kind == "date":
        return inferred == "date"
    if kind == "integer":
        return inferred in ("integer", "number")
    if kind == "number":
        return inferred in ("integer", "number")
    return False


def _score(header: str, aliases: list[str]) -> float:
    best = 0.0
    for alias in aliases:
        alias_norm = normalize(alias)
        if header == alias_norm:
            return EXACT_CONFIDENCE
        ratio = SequenceMatcher(None, header, alias_norm).ratio()
        if ratio >= FUZZY_THRESHOLD:
            best = max(best, ratio * FUZZY_WEIGHT)
    return best


def map_columns(profiles: list[ColumnProfile], dataset_type: str) -> list[Mapping]:
    """Map each profiled column to at most one target column, one-to-one."""
    schema = SCHEMAS[dataset_type]
    aliases = KNOWN_ALIASES[dataset_type]

    candidates: list[tuple[float, int, str]] = []
    for position, profile in enumerate(profiles):
        header = normalize(profile.name)
        for target, kind in schema.items():
            if not _compatible(kind, profile.inferred_type):
                continue
            confidence = _score(header, aliases[target])
            if confidence > 0:
                candidates.append((confidence, position, target))

    candidates.sort(key=lambda c: (-c[0], c[1]))
    chosen: dict[int, tuple[str, float]] = {}
    taken_targets: set[str] = set()
    for confidence, position, target in candidates:
        if position in chosen or target in taken_targets:
            continue
        chosen[position] = (target, confidence)
        taken_targets.add(target)

    results = []
    for position, profile in enumerate(profiles):
        target, confidence = chosen.get(position, (None, 0.0))
        results.append(Mapping(profile.name, target, round(confidence, 3)))
    return results
