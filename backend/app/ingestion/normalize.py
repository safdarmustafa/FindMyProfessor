from __future__ import annotations

import re


_HYPHEN_RE = re.compile(r"[-–—_]+")
_SPACE_RE = re.compile(r"\s+")


def normalize_research_area_key(name: str) -> str:
    text = name.strip()
    text = _HYPHEN_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text)
    return text.casefold()


def canonical_research_area_name(name: str) -> str:
    text = name.strip()
    text = _HYPHEN_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text)
    return text


def identity_key(*parts: str) -> str:
    return "|".join(part.strip().casefold() for part in parts)


def is_http_url(value: str | None) -> bool:
    if not value:
        return False
    return value.startswith("http://") or value.startswith("https://")
