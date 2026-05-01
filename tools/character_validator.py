"""Integrated character validator for the V5 character creator.

Step 20 orchestrates the modular validators introduced in step 19 and applies
the declarative rules from ``data/validation-rules.json`` against a complete
exportable character state.

Public API:
    validate_character(...)
    validateCharacter(...)

The camelCase alias is intentionally provided for frontend integrations.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
import json

try:  # Supports tests that put Documentacion/tools directly on sys.path.
    from validators.registry import VALIDATOR_MODULES
    from validators.common import make_error, normalize_identifier
    from character_budget_tools import (
        advantage_available_merit_dots,
        domain_pool_available,
        domain_pool_spent,
    )
except ModuleNotFoundError as exc:  # Supports package-style imports: tools.character_validator.
    if exc.name not in {"validators", "validators.registry", "validators.common", "character_budget_tools"}:
        raise
    from .validators.registry import VALIDATOR_MODULES
    from .validators.common import make_error, normalize_identifier
    from .character_budget_tools import (
        advantage_available_merit_dots,
        domain_pool_available,
        domain_pool_spent,
    )


DEFAULT_MODULE_ORDER: list[str] = [
    "character_state",
    "attributes",
    "skills",
    "specialties",
    "budget",
    "advantages",
    "domain",
    "disciplines",
    "predator",
    "validation_rules",
]


def load_json(path: str | Path) -> dict[str, Any]:
    """Load a UTF-8 JSON file."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_project_data(root: str | Path) -> dict[str, Any]:
    """Load the project catalogs and schemas required by ``validate_character``.

    ``root`` may point to the ``Documentacion`` directory.
    """

    root_path = Path(root)
    return {
        "creator_data": load_json(root_path / "data" / "creator-data.json"),
        "discipline_catalog": load_json(root_path / "data" / "disciplinas_v5_catalogo.json"),
        "validation_rules": load_json(root_path / "data" / "validation-rules.json"),
        "character_schema": load_json(root_path / "schemas" / "character-state.schema.json"),
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp_int(value: Any, minimum: int, maximum: int) -> int:
    return max(minimum, min(_safe_int(value, maximum), maximum))


def _list_from_mapping(value: Any, key: str) -> list[Any]:
    if not isinstance(value, Mapping):
        return []
    items = value.get(key, [])
    return list(items) if isinstance(items, list) else []


def _selected_advantage_entries(character_state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    advantages = character_state.get("advantages", {})
    return [
        entry
        for entry in _list_from_mapping(advantages, "merits") + _list_from_mapping(advantages, "flaws")
        if isinstance(entry, Mapping)
    ]


def _selected_domain_entries(character_state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    domain = character_state.get("domain", {})
    return [
        entry
        for entry in (
            _list_from_mapping(domain, "backgrounds")
            + _list_from_mapping(domain, "merits")
            + _list_from_mapping(domain, "flaws")
        )
        if isinstance(entry, Mapping)
    ]


def _trait_dots(character_state: Mapping[str, Any], trait_id: str) -> int:
    for entry in _selected_advantage_entries(character_state):
        if entry.get("traitId") == trait_id:
            return _safe_int(entry.get("dots"))
    return 0


def _domain_trait_dots(character_state: Mapping[str, Any], domain_trait_id: str) -> int:
    for entry in _selected_domain_entries(character_state):
        if entry.get("domainTraitId") == domain_trait_id:
            return _safe_int(entry.get("dots"))
    return 0


def _has_trait(character_state: Mapping[str, Any], trait_id: str) -> bool:
    return _trait_dots(character_state, trait_id) > 0


def _has_domain_trait(character_state: Mapping[str, Any], domain_trait_id: str) -> bool:
    return _domain_trait_dots(character_state, domain_trait_id) > 0


def _catalog_by_id(records: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(record["id"]): record for record in records if "id" in record}


def _clan_id(character_state: Mapping[str, Any]) -> str | None:
    clan = character_state.get("clan", {})
    clan_id = clan.get("clanId") if isinstance(clan, Mapping) else None
    return str(clan_id) if clan_id else None


def _discipline_rating(character_state: Mapping[str, Any], discipline_name_or_id: str) -> int:
    discipline_id = normalize_identifier(discipline_name_or_id)
    disciplines = character_state.get("disciplines", {})
    ratings = disciplines.get("ratings", {}) if isinstance(disciplines, Mapping) else {}
    if not isinstance(ratings, Mapping):
        return 0
    return _safe_int(ratings.get(discipline_id))


def _condition_matches(
    condition: Mapping[str, Any] | None,
    character_state: Mapping[str, Any],
    creator_data: Mapping[str, Any],
) -> bool:
    """Evaluate the ``when`` object of a validation rule.

    Unknown condition keys raise ``ValueError`` so that typos in
    ``validation-rules.json`` surface immediately instead of silently
    disabling the rule.
    """

    if not condition:
        return True

    KNOWN_CONDITION_KEYS = {
        "clanId",
        "hasTraitId",
        "hasAnyTraitId",
        "hasDomainTraitId",
        "hasAnyDomainTraitId",
        "hasTraitCategory",
        "exceptTraitIds",   # modifier of hasTraitCategory, not a standalone condition
    }
    unknown = set(condition.keys()) - KNOWN_CONDITION_KEYS
    if unknown:
        raise ValueError(
            f"_condition_matches: claves de condición desconocidas {sorted(unknown)!r}. "
            "Verifica validation-rules.json."
        )

    handled = False

    if "clanId" in condition:
        handled = True
        if _clan_id(character_state) != condition.get("clanId"):
            return False

    if "hasTraitId" in condition:
        handled = True
        if not _has_trait(character_state, str(condition.get("hasTraitId"))):
            return False

    if "hasAnyTraitId" in condition:
        handled = True
        trait_ids = condition.get("hasAnyTraitId") or []
        if not any(_has_trait(character_state, str(trait_id)) for trait_id in trait_ids):
            return False

    if "hasDomainTraitId" in condition:
        handled = True
        if not _has_domain_trait(character_state, str(condition.get("hasDomainTraitId"))):
            return False

    if "hasAnyDomainTraitId" in condition:
        handled = True
        trait_ids = condition.get("hasAnyDomainTraitId") or []
        if not any(_has_domain_trait(character_state, str(trait_id)) for trait_id in trait_ids):
            return False

    if "hasTraitCategory" in condition:
        handled = True
        category = condition.get("hasTraitCategory")
        except_trait_ids = set(condition.get("exceptTraitIds") or [])
        catalog = _catalog_by_id(creator_data.get("advantagesCatalog", []))
        matched = False
        for entry in _selected_advantage_entries(character_state):
            trait_id = entry.get("traitId")
            if trait_id in except_trait_ids:
                continue
            record = catalog.get(str(trait_id))
            if record and record.get("category") == category:
                matched = True
                break
        if not matched:
            return False

    return handled


def _rule_error(rule: Mapping[str, Any], code: str, message: str, *, path: str = "", **extra: Any) -> dict[str, Any]:
    return make_error(
        code,
        message,
        path=path,
        ruleId=str(rule.get("id")),
        severity=str(rule.get("severity", "error")),
        origin=rule.get("origin"),
        **extra,
    )


def _apply_rule_effect(
    rule: Mapping[str, Any],
    character_state: Mapping[str, Any],
    creator_data: Mapping[str, Any],
) -> list[dict[str, Any]]:
    effect = rule.get("effect", {})
    effect_type = effect.get("type")
    errors: list[dict[str, Any]] = []
    advantage_catalog = _catalog_by_id(creator_data.get("advantagesCatalog", []))
    domain_catalog = _catalog_by_id(creator_data.get("domainCatalog", []))

    if effect_type == "forbidTrait":
        trait_id = str(effect.get("traitId"))
        if _has_trait(character_state, trait_id):
            errors.append(
                _rule_error(
                    rule,
                    "validation_rule_forbidden_trait",
                    "La regla bloquea este rasgo individual.",
                    traitId=trait_id,
                )
            )
        return errors

    if effect_type == "forbidTraitCategory":
        category = effect.get("category")
        trait_type = effect.get("traitType")
        except_trait_ids = set(effect.get("exceptTraitIds") or [])
        for entry in _selected_advantage_entries(character_state):
            trait_id = str(entry.get("traitId"))
            if trait_id in except_trait_ids:
                continue
            record = advantage_catalog.get(trait_id)
            if not record:
                continue
            if record.get("category") == category and (trait_type is None or record.get("type") == trait_type):
                errors.append(
                    _rule_error(
                        rule,
                        "validation_rule_forbidden_trait_category",
                        "La regla bloquea esta categoría de rasgos.",
                        traitId=trait_id,
                        category=category,
                        traitType=trait_type,
                    )
                )
        return errors

    if effect_type == "requireTrait":
        required_id = str(effect.get("traitId"))
        min_dots = int(effect.get("minDots", 1) or 1)
        actual = _trait_dots(character_state, required_id)
        if actual < min_dots:
            errors.append(
                _rule_error(
                    rule,
                    "validation_rule_required_trait_missing",
                    "La regla exige un rasgo individual con puntos suficientes.",
                    traitId=required_id,
                    requiredDots=min_dots,
                    actualDots=actual,
                )
            )
        return errors

    if effect_type == "incompatibleTraitPair":
        trait_ids = [str(value) for value in effect.get("traitIds", [])]
        catalog = effect.get("catalog")
        if catalog == "domain":
            present = [trait_id for trait_id in trait_ids if _has_domain_trait(character_state, trait_id)]
        else:
            present = [trait_id for trait_id in trait_ids if _has_trait(character_state, trait_id)]
        if len(present) == len(trait_ids) and len(trait_ids) >= 2:
            errors.append(
                _rule_error(
                    rule,
                    "validation_rule_incompatible_trait_pair",
                    "La regla bloquea esta combinación de rasgos.",
                    traitIds=trait_ids,
                )
            )
        return errors

    if effect_type == "skillMaximum":
        max_dots = int(effect.get("maxDots", 0) or 0)
        skills = character_state.get("skills", {})
        if not isinstance(skills, Mapping):
            skills = {}
        for skill in effect.get("skills", []):
            actual = _safe_int(skills.get(skill))
            if actual > max_dots:
                errors.append(
                    _rule_error(
                        rule,
                        "validation_rule_skill_maximum_exceeded",
                        "La regla limita esta habilidad.",
                        path=f"skills.{skill}",
                        skill=skill,
                        maxDots=max_dots,
                        actualDots=actual,
                    )
                )
        return errors

    if effect_type == "disciplineMaximum":
        max_dots = int(effect.get("maxDots", 0) or 0)
        for discipline in effect.get("disciplines", []):
            actual = _discipline_rating(character_state, str(discipline))
            if actual > max_dots:
                errors.append(
                    _rule_error(
                        rule,
                        "validation_rule_discipline_maximum_exceeded",
                        "La regla limita esta disciplina.",
                        path=f"disciplines.ratings.{normalize_identifier(str(discipline))}",
                        discipline=discipline,
                        maxDots=max_dots,
                        actualDots=actual,
                    )
                )
        return errors

    if effect_type == "requireDiscipline":
        discipline = str(effect.get("discipline"))
        min_dots = int(effect.get("minDots", 1) or 1)
        actual = _discipline_rating(character_state, discipline)
        if actual < min_dots:
            errors.append(
                _rule_error(
                    rule,
                    "validation_rule_required_discipline_missing",
                    "La regla exige una disciplina con puntos suficientes.",
                    path=f"disciplines.ratings.{normalize_identifier(discipline)}",
                    discipline=discipline,
                    requiredDots=min_dots,
                    actualDots=actual,
                )
            )
        return errors

    if effect_type == "forbidDomainTrait":
        trait_ids = []
        if effect.get("traitId"):
            trait_ids.append(str(effect.get("traitId")))
        trait_ids.extend(str(value) for value in effect.get("traitIds", []))
        except_trait_ids = set(effect.get("exceptTraitIds") or [])
        for trait_id in trait_ids:
            if trait_id in except_trait_ids:
                continue
            if _has_domain_trait(character_state, trait_id):
                errors.append(
                    _rule_error(
                        rule,
                        "validation_rule_forbidden_domain_trait",
                        "La regla bloquea este rasgo de Dominio personal.",
                        domainTraitId=trait_id,
                    )
                )
        return errors

    if effect_type == "requireDomainTrait":
        required_id = str(effect.get("traitId"))
        min_dots = int(effect.get("minDots", 1) or 1)
        actual = _domain_trait_dots(character_state, required_id)
        if actual < min_dots:
            errors.append(
                _rule_error(
                    rule,
                    "validation_rule_required_domain_trait_missing",
                    "La regla exige un rasgo de Dominio personal con puntos suficientes.",
                    domainTraitId=required_id,
                    requiredDots=min_dots,
                    actualDots=actual,
                )
            )
        return errors

    if effect_type in {
        "spendingPoolRestriction",
        "advantageToDomainContribution",
        "forbidDomainToAdvantageContribution",
    }:
        # These structural budget policies are enforced by the budget and domain
        # validators. The integrated validator still records the rules as loaded
        # through the validation_rules module.
        return errors

    errors.append(
        _rule_error(
            rule,
            "validation_rule_effect_not_implemented",
            "El validador integral no reconoce este tipo de efecto.",
            effectType=effect_type,
        )
    )
    return errors


def apply_validation_rules(
    character_state: Mapping[str, Any],
    creator_data: Mapping[str, Any],
    validation_rules: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Apply declarative blocking rules to a character state."""

    if not validation_rules:
        return []

    errors: list[dict[str, Any]] = []
    for rule in validation_rules.get("rules", []):
        if rule.get("severity") != "error":
            errors.append(
                _rule_error(
                    rule,
                    "validation_rule_non_blocking_in_integrated_pipeline",
                    "El pipeline integral sólo acepta reglas bloqueantes.",
                )
            )
            continue
        if _condition_matches(rule.get("when"), character_state, creator_data):
            errors.extend(_apply_rule_effect(rule, character_state, creator_data))
    return errors


def derive_character_state(character_state: Mapping[str, Any]) -> dict[str, Any]:
    """Build stable derived values from the current character state.

    These values are persisted in ``derived`` by the caller when desired, but
    they are always recomputable from explicit user choices.
    """

    attributes = character_state.get("attributes", {})
    advantages = character_state.get("advantages", {})
    domain = character_state.get("domain", {})
    advantages_budget = advantages.get("budget", {}) if isinstance(advantages, Mapping) else {}
    domain_pool = domain.get("pool", {}) if isinstance(domain, Mapping) else {}

    resistance = _safe_int(attributes.get("Resistencia")) if isinstance(attributes, Mapping) else 0
    compostura = _safe_int(attributes.get("Compostura")) if isinstance(attributes, Mapping) else 0
    resolucion = _safe_int(attributes.get("Resolución")) if isinstance(attributes, Mapping) else 0

    health_max = resistance + 3 if resistance else 0
    willpower_max = compostura + resolucion

    generation = character_state.get("generation", {})
    blood_potency = _safe_int(generation.get("bloodPotencyBase") if isinstance(generation, Mapping) else None, 1)
    existing_derived = character_state.get("derived", {})
    if not isinstance(existing_derived, Mapping):
        existing_derived = {}
    humanity = _safe_int(existing_derived.get("humanity"), 7)

    existing_health = existing_derived.get("health", {})
    existing_willpower = existing_derived.get("willpower", {})
    current_health = _clamp_int(
        existing_health.get("current") if isinstance(existing_health, Mapping) else health_max,
        0,
        health_max,
    ) if health_max else 0
    current_willpower = _clamp_int(
        existing_willpower.get("current") if isinstance(existing_willpower, Mapping) else willpower_max,
        0,
        willpower_max,
    ) if willpower_max else 0

    return {
        "health": {"max": health_max, "current": current_health},
        "willpower": {"max": willpower_max, "current": current_willpower},
        "humanity": humanity,
        "bloodPotency": blood_potency,
        "budgets": {
            "advantages": {
                "totalMeritDots": (
                    _safe_int(advantages_budget.get("totalMeritDots"))
                    if isinstance(advantages_budget, Mapping)
                    else 0
                ),
                "spentMeritDots": (
                    _safe_int(advantages_budget.get("spentMeritDots"))
                    if isinstance(advantages_budget, Mapping)
                    else 0
                ),
                "contributedToDomainDots": (
                    _safe_int(advantages_budget.get("contributedToDomainDots"))
                    if isinstance(advantages_budget, Mapping)
                    else 0
                ),
                "availableMeritDots": max(0, advantage_available_merit_dots(dict(character_state))),
                "totalFlawDots": (
                    _safe_int(advantages_budget.get("totalFlawDots"))
                    if isinstance(advantages_budget, Mapping)
                    else 0
                ),
                "spentFlawDots": (
                    _safe_int(advantages_budget.get("spentFlawDots"))
                    if isinstance(advantages_budget, Mapping)
                    else 0
                ),
                "receivedFromDomainDots": 0,
            },
            "domain": {
                "baseDots": _safe_int(domain_pool.get("baseDots")) if isinstance(domain_pool, Mapping) else 0,
                "contributedAdvantageDots": (
                    _safe_int(domain_pool.get("contributedAdvantageDots"))
                    if isinstance(domain_pool, Mapping)
                    else 0
                ),
                "flawDots": _safe_int(domain_pool.get("flawDots")) if isinstance(domain_pool, Mapping) else 0,
                "grantedDots": _safe_int(domain_pool.get("grantedDots")) if isinstance(domain_pool, Mapping) else 0,
                "spentDots": domain_pool_spent(dict(character_state)),
                "availableDots": max(
                    0,
                    domain_pool_available(dict(character_state)) - domain_pool_spent(dict(character_state)),
                ),
            },
        },
    }


def _sanitize_validation_item(item: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {"code", "message", "path", "ruleId", "severity"}
    result = {key: value for key, value in item.items() if key in allowed and value is not None}
    result.setdefault("severity", "error")
    return result


def build_derived_validation(
    errors: list[Mapping[str, Any]],
    warnings: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    warnings = warnings or []
    return {
        "valid": len(errors) == 0,
        "errors": [_sanitize_validation_item(error) for error in errors],
        "warnings": [_sanitize_validation_item(warning) for warning in warnings],
        "lastValidatedAt": _now_iso(),
    }


def _dedupe_errors(errors: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[dict[str, Any]] = []
    for error in errors:
        normalized = dict(error)
        normalized.setdefault("severity", "error")
        key = (
            str(normalized.get("code", "")),
            str(normalized.get("path", "")),
            str(normalized.get("ruleId", "")),
            str(normalized.get("message", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def validate_character(
    character_state: Mapping[str, Any],
    creator_data: Mapping[str, Any],
    *,
    discipline_catalog: Mapping[str, Any] | None = None,
    validation_rules: Mapping[str, Any] | None = None,
    character_schema: Mapping[str, Any] | None = None,
    module_order: list[str] | None = None,
    update_derived: bool = False,
) -> dict[str, Any]:
    """Run the full step-20 validation pipeline.

    Returns a stable payload:

    ``{"valid": bool, "errors": [], "warnings": [], "derived": {}, "moduleResults": []}``
    """

    if not isinstance(character_state, Mapping):
        error = make_error(
            "character_state_not_object",
            "El estado de personaje debe ser un objeto.",
            path="",
            module="character_state",
        )
        warnings: list[dict[str, Any]] = []
        derived = {"validation": build_derived_validation([error], warnings)}
        return {
            "valid": False,
            "errors": [error],
            "warnings": warnings,
            "derived": derived,
            "moduleResults": [{"module": "character_state", "valid": False, "errorCount": 1}],
            "characterState": None,
        }

    module_order = module_order or DEFAULT_MODULE_ORDER
    working_state = character_state if update_derived else deepcopy(character_state)

    all_errors: list[dict[str, Any]] = []
    module_results: list[dict[str, Any]] = []

    for module_name in module_order:
        validator = VALIDATOR_MODULES[module_name]
        errors = validator(
            working_state,
            creator_data,
            discipline_catalog=discipline_catalog,
            validation_rules=validation_rules,
            character_schema=character_schema,
        )
        normalized_errors = _dedupe_errors(errors)
        module_results.append(
            {
                "module": module_name,
                "valid": len(normalized_errors) == 0,
                "errorCount": len(normalized_errors),
            }
        )
        for error in normalized_errors:
            error.setdefault("module", module_name)
        all_errors.extend(normalized_errors)

    rule_errors = _dedupe_errors(apply_validation_rules(working_state, creator_data, validation_rules))
    module_results.append(
        {
            "module": "rule_engine",
            "valid": len(rule_errors) == 0,
            "errorCount": len(rule_errors),
        }
    )
    for error in rule_errors:
        error.setdefault("module", "rule_engine")
    all_errors.extend(rule_errors)

    all_errors = _dedupe_errors(all_errors)
    warnings: list[dict[str, Any]] = []
    derived = derive_character_state(working_state)
    derived["validation"] = build_derived_validation(all_errors, warnings)

    if update_derived and isinstance(working_state, dict):
        working_state.setdefault("derived", {})
        working_state["derived"].update(derived)

    return {
        "valid": len(all_errors) == 0,
        "errors": all_errors,
        "warnings": warnings,
        "derived": derived,
        "moduleResults": module_results,
        "characterState": working_state if update_derived else None,
    }


validateCharacter = validate_character
