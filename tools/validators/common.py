"""Shared helpers for modular validators."""

from __future__ import annotations

from typing import Any, Mapping
import unicodedata


def make_error(code: str, message: str, *, path: str = "", **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if path:
        payload["path"] = path
    payload.update(extra)
    return payload


def normalize_identifier(value: str) -> str:
    """Return a stable lowercase ASCII-ish identifier for display names."""
    decomposed = unicodedata.normalize("NFKD", value.strip())
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return "_".join(without_marks.casefold().replace(":", " ").replace("-", " ").split())


def catalog_by_id(records: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(record["id"]): record for record in records if "id" in record}


def dot_options(record: Mapping[str, Any]) -> set[int]:
    return {value for value in record.get("dotOptions", []) if isinstance(value, int) and not isinstance(value, bool)}


def as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
