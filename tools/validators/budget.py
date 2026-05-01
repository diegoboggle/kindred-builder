"""Budget validator module."""

from __future__ import annotations

from typing import Any, Mapping

try:
    from character_budget_tools import validate_budget_integrity
except ModuleNotFoundError as exc:
    if exc.name != "character_budget_tools":
        raise
    from ..character_budget_tools import validate_budget_integrity


def validate(
    character_state: Mapping[str, Any],
    creator_data: Mapping[str, Any] | None = None,
    **_: Any,
) -> list[dict[str, Any]]:
    """Validate individual Advantage budget and personal Domain budget coherence."""
    return [
        {"code": "budget_integrity_error", "message": message}
        for message in validate_budget_integrity(dict(character_state))
    ]
