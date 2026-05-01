"""Individual Advantage and Flaw validator module."""

from __future__ import annotations

from typing import Any, Mapping

from .common import as_list, as_mapping, catalog_by_id, dot_options, make_error


def _validate_selection(
    selection: Mapping[str, Any],
    *,
    expected_type: str,
    catalog: Mapping[str, Mapping[str, Any]],
    path: str,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    trait_id = selection.get("traitId")
    dots = selection.get("dots")

    if trait_id not in catalog:
        return [
            make_error(
                "advantage_trait_id_unknown",
                "El rasgo individual no existe en advantagesCatalog.",
                path=path,
                traitId=trait_id,
            )
        ]

    record = catalog[str(trait_id)]
    if record.get("type") != expected_type:
        errors.append(
            make_error(
                "advantage_trait_type_mismatch",
                "El rasgo no corresponde al contenedor usado.",
                path=path,
                traitId=trait_id,
                expectedType=expected_type,
                actualType=record.get("type"),
            )
        )

    options = dot_options(record)
    if options and (not isinstance(dots, int) or isinstance(dots, bool) or dots not in options):
        errors.append(
            make_error(
                "advantage_trait_dots_invalid",
                "Los puntos del rasgo no son válidos para el catálogo.",
                path=path,
                traitId=trait_id,
                dots=dots,
                dotOptions=sorted(options),
            )
        )

    if record.get("requiresDetail") and not (selection.get("detail") or selection.get("detailDefault")):
        errors.append(
            make_error(
                "advantage_trait_detail_missing",
                "El rasgo requiere detalle.",
                path=path,
                traitId=trait_id,
            )
        )

    if selection.get("purchaseScope", "character") == "domain":
        errors.append(
            make_error(
                "domain_purchase_in_character_advantages",
                "Los rasgos comprados con Dominio personal no deben guardarse en advantages.",
                path=path,
                traitId=trait_id,
            )
        )

    return errors


def validate(character_state: Mapping[str, Any], creator_data: Mapping[str, Any], **_: Any) -> list[dict[str, Any]]:
    """Validate character-scoped merits and flaws against advantagesCatalog."""
    catalog = catalog_by_id(creator_data.get("advantagesCatalog", []))
    advantages = as_mapping(character_state.get("advantages", {}))
    errors: list[dict[str, Any]] = []

    for index, item in enumerate(as_list(advantages.get("merits", []))):
        if not isinstance(item, Mapping):
            continue
        errors.extend(
            _validate_selection(
                item,
                expected_type="merit",
                catalog=catalog,
                path=f"advantages.merits[{index}]",
            )
        )

    for index, item in enumerate(as_list(advantages.get("flaws", []))):
        if not isinstance(item, Mapping):
            continue
        errors.extend(
            _validate_selection(
                item,
                expected_type="flaw",
                catalog=catalog,
                path=f"advantages.flaws[{index}]",
            )
        )

    return errors
