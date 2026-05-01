"""Attribute validator module."""

from __future__ import annotations

from typing import Any, Mapping

try:
    from character_attribute_tools import validate_initial_attributes
except ModuleNotFoundError as exc:
    if exc.name != "character_attribute_tools":
        raise
    from ..character_attribute_tools import validate_initial_attributes


def validate(character_state: Mapping[str, Any], creator_data: Mapping[str, Any], **_: Any) -> list[dict[str, Any]]:
    """Validate initial attribute names, values, distribution, and sequence coherence."""
    model = creator_data.get("attributeCreationModel", {})
    return validate_initial_attributes(
        character_state.get("attributes", {}),
        creator_data.get("attributes", []),
        attr_sequence=character_state.get("attrSequence"),
        expected_distribution=model.get("finalDistribution"),
    )
