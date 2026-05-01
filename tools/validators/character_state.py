"""JSON Schema validator module for exportable character state."""

from __future__ import annotations

from typing import Any, Mapping
import jsonschema

from .common import make_error


def _schema_error_sort_key(error: jsonschema.ValidationError) -> tuple[tuple[str, str], ...]:
    return tuple((type(part).__name__, repr(part)) for part in error.path)


def _jsonschema_safe_instance(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonschema_safe_instance(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonschema_safe_instance(item) for item in value]
    return value


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
    schema_instance = _jsonschema_safe_instance(character_state)
    errors: list[dict[str, Any]] = []
    for error in sorted(validator.iter_errors(schema_instance), key=_schema_error_sort_key):
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
