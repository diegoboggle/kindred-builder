"""Skill spread validator module."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

try:
    from character_skill_tools import validate_initial_skills, apply_skill_maximum_rules
except ModuleNotFoundError as exc:
    if exc.name != "character_skill_tools":
        raise
    from ..character_skill_tools import validate_initial_skills, apply_skill_maximum_rules


def validate(
    character_state: Mapping[str, Any],
    creator_data: Mapping[str, Any],
    *,
    rule_effects: Iterable[Mapping[str, Any]] | None = None,
    **_: Any,
) -> list[dict[str, Any]]:
    """Validate initial skill distribution and already-resolved skill maximum effects.

    This module intentionally does not evaluate validation-rules conditions.
    Step 20 will decide which rule effects are active for a given character
    and then pass those active effects here.
    """
    errors = validate_initial_skills(
        character_state.get("skills", {}),
        creator_data.get("skills", []),
        skill_sequence=character_state.get("skillSequence"),
    )
    if rule_effects:
        errors.extend(apply_skill_maximum_rules(character_state.get("skills", {}), rule_effects))
    return errors
