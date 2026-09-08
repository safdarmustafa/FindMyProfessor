from __future__ import annotations

import re


GENERIC_RESEARCH_AREAS = frozenset({"computer science"})


def normalize_label(value: str | None) -> str:
    if not value:
        return ""
    collapsed = re.sub(r"\s+", " ", value.strip())
    return collapsed.casefold()


def is_generic_area(value: str | None) -> bool:
    return normalize_label(value) in GENERIC_RESEARCH_AREAS


def catalog_index(names: list[str]) -> dict[str, str]:
    """Map normalized label -> canonical catalog name (first wins)."""
    index: dict[str, str] = {}
    for name in names:
        key = normalize_label(name)
        if key and key not in index:
            index[key] = name
    return index


def canonical_catalog_name(value: str, catalog: dict[str, str]) -> str | None:
    return catalog.get(normalize_label(value))


def unique_catalog_labels(values: list[str], catalog: dict[str, str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        canonical = canonical_catalog_name(value, catalog)
        if not canonical:
            continue
        key = normalize_label(canonical)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(canonical)
    return ordered


def scoring_labels(values: list[str], catalog: dict[str, str]) -> list[str]:
    return [name for name in unique_catalog_labels(values, catalog) if not is_generic_area(name)]
