"""JSON Schema validator module for exportable character state."""

from __future__ import annotations

from typing import Any, Mapping
import jsonschema

from .common import make_error


def validate(
    character_state: Mapping[str, Any],
    creator_data: Mapping[str, Any] | None = None,
    *,
    character_schema: Mapping[str, Any] | None = None,
    **_: Any,
) -> list[dict[str, Any]]:
    """Validate the whole character state against character-state.schema.json."""
    if character_schema is None:
        return []
    validator = jsonschema.Draft202012Validator(character_schema)
    errors: list[dict[str, Any]] = []
    for error in sorted(validator.iter_errors(character_state), key=lambda item: list(item.path)):
        path = ".".join(str(part) for part in error.path)
        errors.append(
            make_error(
                "character_state_schema_error",
                error.message,
                path=path,
                validator=error.validator,
            )
        )
    return errors
