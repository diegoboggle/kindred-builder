"""Specialty validator module."""

from __future__ import annotations

from typing import Any, Mapping

try:
    from character_skill_tools import validate_specialties
except ModuleNotFoundError as exc:
    if exc.name != "character_skill_tools":
        raise
    from ..character_skill_tools import validate_specialties


def validate(character_state: Mapping[str, Any], creator_data: Mapping[str, Any], **_: Any) -> list[dict[str, Any]]:
    """Validate free, predator, advantage, manual, and other specialties."""
    return validate_specialties(
        character_state.get("skills", {}),
        character_state.get("specialties", []),
        creator_data.get("skills", []),
        special_required_skills=creator_data.get("specialRequiredSkills", []),
        free_specialty_skill=character_state.get("freeSpecialtySkill"),
        free_specialty_name=character_state.get("freeSpecialtyName"),
    )
