"""Utilities for validating V5 character attribute creation.

The initial V5 attribute spread used by this builder is:
4/3/3/3/2/2/2/2/1.

The UI sequence model stores only the five modified attributes:
position 1 -> 4
position 2 -> 1
positions 3-5 -> 3
unselected attributes -> 2
"""

from collections import Counter
from typing import Any, Mapping

ATTRIBUTE_DISTRIBUTION = [4, 3, 3, 3, 2, 2, 2, 2, 1]
ATTRIBUTE_SEQUENCE_VALUES = [4, 1, 3, 3, 3]
UNSELECTED_ATTRIBUTE_VALUE = 2
ATTRIBUTE_SEQUENCE_LENGTH = 5
MIN_ATTRIBUTE_DOTS = 1
MAX_ATTRIBUTE_DOTS = 5


def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    payload.update(extra)
    return payload


def _sort_for_error(values):
    return sorted(values, key=lambda value: (type(value).__name__, repr(value)))


def sorted_attribute_values(attributes):
    """Return final attribute values sorted from highest to lowest."""
    return sorted(attributes.values(), reverse=True)


def build_attributes_from_sequence(attr_sequence, expected_attribute_names):
    """Build the final attribute map from the five-item attrSequence."""
    attributes = {name: UNSELECTED_ATTRIBUTE_VALUE for name in expected_attribute_names}

    for index, attribute in enumerate(attr_sequence):
        if (
            index < len(ATTRIBUTE_SEQUENCE_VALUES)
            and isinstance(attribute, str)
            and attribute in attributes
        ):
            attributes[attribute] = ATTRIBUTE_SEQUENCE_VALUES[index]

    return attributes


def validate_attribute_names(attributes, expected_attribute_names):
    """Validate that an attribute map contains exactly the expected keys."""
    expected = set(expected_attribute_names)
    actual = set(attributes.keys())

    errors = []
    missing = _sort_for_error(expected - actual)
    extra = _sort_for_error(actual - expected)

    if missing:
        errors.append({
            "code": "attributes_missing",
            "message": "Faltan atributos obligatorios.",
            "attributes": missing,
        })

    if extra:
        errors.append({
            "code": "attributes_unknown",
            "message": "Existen atributos no reconocidos.",
            "attributes": extra,
        })

    return errors


def validate_attribute_values(attributes, minimum=MIN_ATTRIBUTE_DOTS, maximum=MAX_ATTRIBUTE_DOTS):
    """Validate that every attribute value is an integer inside the allowed range."""
    errors = []

    for name, value in attributes.items():
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append({
                "code": "attribute_value_not_integer",
                "message": "El valor del atributo debe ser un entero.",
                "attribute": name,
                "value": value,
            })
            continue

        if value < minimum or value > maximum:
            errors.append({
                "code": "attribute_value_out_of_range",
                "message": "El valor del atributo está fuera del rango permitido.",
                "attribute": name,
                "value": value,
                "minimum": minimum,
                "maximum": maximum,
            })

    return errors


def validate_attribute_distribution(attributes, expected_distribution=None):
    """Validate the exact final V5 initial attribute distribution."""
    expected_distribution = expected_distribution or ATTRIBUTE_DISTRIBUTION
    actual_distribution = sorted_attribute_values(attributes)

    if actual_distribution != expected_distribution:
        return [{
            "code": "attribute_distribution_invalid",
            "message": "La distribución final de atributos no coincide con 4/3/3/3/2/2/2/2/1.",
            "expected": expected_distribution,
            "actual": actual_distribution,
            "expectedCounts": dict(Counter(expected_distribution)),
            "actualCounts": dict(Counter(actual_distribution)),
        }]

    return []


def validate_attr_sequence(attr_sequence, expected_attribute_names, required_length=ATTRIBUTE_SEQUENCE_LENGTH):
    """Validate that attrSequence contains the five modified attributes exactly once."""
    expected_set = set(expected_attribute_names)
    errors = []

    if not isinstance(attr_sequence, list):
        return [{
            "code": "attr_sequence_not_array",
            "message": "attrSequence debe ser una lista.",
        }]

    if len(attr_sequence) != required_length:
        errors.append({
            "code": "attr_sequence_wrong_length",
            "message": "attrSequence debe contener exactamente cinco atributos modificados.",
            "expectedLength": required_length,
            "actualLength": len(attr_sequence),
        })

    non_strings = [name for name in attr_sequence if not isinstance(name, str)]
    if non_strings:
        errors.append({
            "code": "attr_sequence_non_string",
            "message": "attrSequence sólo puede contener nombres de atributo como texto.",
            "values": non_strings,
        })

    string_items = [name for name in attr_sequence if isinstance(name, str)]
    duplicates = sorted([name for name, count in Counter(string_items).items() if count > 1])
    if duplicates:
        errors.append({
            "code": "attr_sequence_duplicates",
            "message": "attrSequence contiene atributos duplicados.",
            "attributes": duplicates,
        })

    unknown = sorted(set(string_items) - expected_set)
    if unknown:
        errors.append({
            "code": "attr_sequence_unknown_attributes",
            "message": "attrSequence contiene atributos no reconocidos.",
            "attributes": unknown,
        })

    return errors


def validate_attributes_match_sequence(attributes, attr_sequence, expected_attribute_names):
    """Validate that the saved attribute map matches the deterministic sequence model."""
    sequence_errors = validate_attr_sequence(attr_sequence, expected_attribute_names)
    if sequence_errors:
        return sequence_errors

    expected_attributes = build_attributes_from_sequence(attr_sequence, expected_attribute_names)
    if attributes != expected_attributes:
        return [{
            "code": "attributes_do_not_match_sequence",
            "message": "El mapa final de atributos no coincide con attrSequence.",
            "expected": expected_attributes,
            "actual": attributes,
        }]

    return []


def validate_initial_attributes(attributes, expected_attribute_names, attr_sequence=None, expected_distribution=None):
    """Validate the full initial attribute state.

    Returns a list of blocking error dictionaries. An empty list means valid.
    """
    if not isinstance(attributes, Mapping):
        return [_error("attributes_not_object", "attributes debe ser un objeto con nombres de atributo y puntos.")]

    errors = []
    errors.extend(validate_attribute_names(attributes, expected_attribute_names))
    errors.extend(validate_attribute_values(attributes))

    # Distribution only makes sense after key/value validation has not found
    # missing, unknown, non-integer, or out-of-range values.
    if not errors:
        errors.extend(validate_attribute_distribution(attributes, expected_distribution))

    if attr_sequence is not None:
        errors.extend(validate_attributes_match_sequence(attributes, attr_sequence, expected_attribute_names))

    return errors


def is_valid_initial_attributes(attributes, expected_attribute_names, attr_sequence=None, expected_distribution=None):
    """Boolean convenience wrapper for validate_initial_attributes."""
    return not validate_initial_attributes(
        attributes,
        expected_attribute_names,
        attr_sequence=attr_sequence,
        expected_distribution=expected_distribution,
    )
