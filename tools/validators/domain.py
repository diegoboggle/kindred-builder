"""Personal Domain validator module."""

from __future__ import annotations

from typing import Any, Mapping

from .common import as_list, as_mapping, catalog_by_id, dot_options, make_error
try:
    from character_budget_tools import domain_pool_available, domain_pool_spent
except ModuleNotFoundError as exc:
    if exc.name != "character_budget_tools":
        raise
    from ..character_budget_tools import domain_pool_available, domain_pool_spent


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _validate_domain_selection(
    selection: Mapping[str, Any],
    *,
    catalog: Mapping[str, Mapping[str, Any]],
    allowed_types: set[str],
    path: str,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    trait_id = selection.get("domainTraitId")
    dots = selection.get("dots")

    if trait_id not in catalog:
        return [
            make_error(
                "domain_trait_id_unknown",
                "El rasgo de Dominio personal no existe en domainCatalog.",
                path=path,
                domainTraitId=trait_id,
            )
        ]

    record = catalog[str(trait_id)]
    if record.get("type") not in allowed_types:
        errors.append(
            make_error(
                "domain_trait_type_invalid_for_container",
                "El tipo de rasgo de Dominio no corresponde al contenedor usado.",
                path=path,
                domainTraitId=trait_id,
                allowedTypes=sorted(allowed_types),
                actualType=record.get("type"),
            )
        )

    if record.get("spendPool") != "domain" or selection.get("purchaseScope") != "domain":
        errors.append(
            make_error(
                "domain_purchase_scope_invalid",
                "Los rasgos de Dominio deben comprarse y guardarse con scope domain.",
                path=path,
                domainTraitId=trait_id,
            )
        )

    options = dot_options(record)
    if options and (not isinstance(dots, int) or isinstance(dots, bool) or dots not in options):
        errors.append(
            make_error(
                "domain_trait_dots_invalid",
                "Los puntos del rasgo de Dominio no son válidos para el catálogo.",
                path=path,
                domainTraitId=trait_id,
                dots=dots,
                dotOptions=sorted(options),
            )
        )

    return errors


def validate(character_state: Mapping[str, Any], creator_data: Mapping[str, Any], **_: Any) -> list[dict[str, Any]]:
    """Validate personal Domain traits, backgrounds, merits, flaws, and pool limits."""
    domain = as_mapping(character_state.get("domain", {}))
    catalog = catalog_by_id(creator_data.get("domainCatalog", []))
    errors: list[dict[str, Any]] = []

    if domain.get("enabled") is not True:
        errors.append(make_error("domain_disabled", "Dominio personal debe estar habilitado.", path="domain.enabled"))

    pool = as_mapping(domain.get("pool", {}))
    if _safe_int(pool.get("baseDots")) < 1:
        errors.append(
            make_error(
                "domain_base_dots_missing",
                "Dominio personal debe partir con al menos 1 punto base.",
                path="domain.pool.baseDots",
            )
        )

    for index, item in enumerate(as_list(domain.get("backgrounds", []))):
        if not isinstance(item, Mapping):
            continue
        errors.extend(
            _validate_domain_selection(
                item,
                catalog=catalog,
                allowed_types={"domainBackground"},
                path=f"domain.backgrounds[{index}]",
            )
        )

    for index, item in enumerate(as_list(domain.get("merits", []))):
        if not isinstance(item, Mapping):
            continue
        errors.extend(
            _validate_domain_selection(
                item,
                catalog=catalog,
                allowed_types={"domainMerit", "domainBackground", "domainTrait"},
                path=f"domain.merits[{index}]",
            )
        )

    for index, item in enumerate(as_list(domain.get("flaws", []))):
        if not isinstance(item, Mapping):
            continue
        errors.extend(
            _validate_domain_selection(
                item,
                catalog=catalog,
                allowed_types={"domainBackgroundFlaw", "domainFlaw"},
                path=f"domain.flaws[{index}]",
            )
        )

    spent = domain_pool_spent(dict(character_state))
    available = domain_pool_available(dict(character_state))
    if spent > available:
        errors.append(
            make_error(
                "domain_pool_overspent",
                "El Dominio personal está gastando más puntos de los disponibles.",
                path="domain.pool",
                spentDots=spent,
                availableDots=available,
            )
        )

    return errors
