"""Validation-rule file validator module."""

from __future__ import annotations

from typing import Any, Mapping

from .common import make_error


def _ids(records: Any) -> set[str]:
    if not isinstance(records, list):
        return set()
    return {str(item["id"]) for item in records if isinstance(item, Mapping) and "id" in item}


def _values(records: Any, key: str) -> set[str]:
    if not isinstance(records, list):
        return set()
    return {str(item[key]) for item in records if isinstance(item, Mapping) and key in item}


def _check_trait_ids(
    errors: list[dict[str, Any]],
    values: Any,
    valid_ids: set[str],
    *,
    path: str,
    rule_id: Any,
) -> None:
    values_to_check = values if isinstance(values, list) else [values]
    for trait_id in values_to_check:
        if isinstance(trait_id, str) and trait_id not in valid_ids:
            errors.append(
                make_error(
                    "validation_rule_trait_reference_unknown",
                    "La regla apunta a un rasgo inexistente.",
                    path=path,
                    ruleId=rule_id,
                    traitId=trait_id,
                )
            )


def _check_named_values(
    errors: list[dict[str, Any]],
    values: Any,
    valid_values: set[str],
    *,
    path: str,
    rule_id: Any,
    code: str,
    message: str,
    field_name: str,
) -> None:
    values_to_check = values if isinstance(values, list) else [values]
    for value in values_to_check:
        if isinstance(value, str) and value not in valid_values:
            errors.append(make_error(code, message, path=path, ruleId=rule_id, **{field_name: value}))


def validate(
    character_state: Mapping[str, Any] | None,
    creator_data: Mapping[str, Any],
    *,
    validation_rules: Mapping[str, Any] | None = None,
    discipline_catalog: Mapping[str, Any] | None = None,
    **_: Any,
) -> list[dict[str, Any]]:
    """Validate the validation-rules registry at a lightweight reference level.

    Full rule application belongs to step 20. This module checks that the rule
    registry remains declarative, blocking, and source-labeled.
    """
    if validation_rules is None:
        return []

    errors: list[dict[str, Any]] = []
    seen: set[str] = set()
    advantage_ids = _ids(creator_data.get("advantagesCatalog", []))
    domain_ids = _ids(creator_data.get("domainCatalog", []))
    all_trait_ids = advantage_ids | domain_ids
    advantage_categories = _values(creator_data.get("advantagesCatalog", []), "category")
    domain_categories = _values(creator_data.get("domainCatalog", []), "category")
    clan_ids = _ids(creator_data.get("clanCatalog", []))
    skills = set(creator_data.get("skills", [])) if isinstance(creator_data.get("skills", []), list) else set()
    discipline_names = set()
    if isinstance(discipline_catalog, Mapping):
        discipline_names = {
            str(record["discipline"])
            for record in discipline_catalog.get("records", [])
            if isinstance(record, Mapping) and record.get("discipline")
        }
    declared_effect_types = set(validation_rules.get("effectTypes", []))

    for index, rule in enumerate(validation_rules.get("rules", [])):
        path = f"rules[{index}]"
        if not isinstance(rule, Mapping):
            errors.append(make_error("validation_rule_not_object", "Cada regla debe ser un objeto.", path=path))
            continue

        rule_id = rule.get("id")
        normalized_rule_id = str(rule_id)
        if normalized_rule_id in seen:
            errors.append(
                make_error(
                    "validation_rule_duplicate_id",
                    "ID de regla duplicado.",
                    path=path,
                    ruleId=rule_id,
                )
            )
        seen.add(normalized_rule_id)

        if rule.get("severity") != "error":
            errors.append(
                make_error(
                    "validation_rule_not_blocking",
                    "Todas las reglas del paso 14 deben ser bloqueantes.",
                    path=path,
                    ruleId=rule_id,
                )
            )

        if rule.get("origin") not in {"official", "logical"}:
            errors.append(
                make_error(
                    "validation_rule_origin_invalid",
                    "La regla debe indicar si es official o logical.",
                    path=path,
                    ruleId=rule_id,
                )
            )

        source = rule.get("source", {})
        if isinstance(source, Mapping) and isinstance(source.get("traitId"), str):
            source_valid_ids = all_trait_ids
            if source.get("kind") == "advantageText":
                source_valid_ids = advantage_ids
            elif source.get("kind") in {"domainText", "domainCatalog"}:
                source_valid_ids = domain_ids
            _check_trait_ids(
                errors,
                source.get("traitId"),
                source_valid_ids,
                path=f"{path}.source.traitId",
                rule_id=rule_id,
            )

        when = rule.get("when", {})
        if isinstance(when, Mapping):
            _check_named_values(
                errors,
                when.get("clanId"),
                clan_ids,
                path=f"{path}.when.clanId",
                rule_id=rule_id,
                code="validation_rule_clan_reference_unknown",
                message="La regla apunta a un clan inexistente.",
                field_name="clanId",
            )
            _check_trait_ids(
                errors,
                when.get("hasTraitId"),
                advantage_ids,
                path=f"{path}.when.hasTraitId",
                rule_id=rule_id,
            )
            _check_trait_ids(
                errors,
                when.get("hasAnyTraitId", []),
                advantage_ids,
                path=f"{path}.when.hasAnyTraitId",
                rule_id=rule_id,
            )
            _check_trait_ids(
                errors,
                when.get("hasDomainTraitId"),
                domain_ids,
                path=f"{path}.when.hasDomainTraitId",
                rule_id=rule_id,
            )
            _check_trait_ids(
                errors,
                when.get("hasAnyDomainTraitId", []),
                domain_ids,
                path=f"{path}.when.hasAnyDomainTraitId",
                rule_id=rule_id,
            )
            _check_trait_ids(
                errors,
                when.get("exceptTraitIds", []),
                advantage_ids,
                path=f"{path}.when.exceptTraitIds",
                rule_id=rule_id,
            )
            _check_named_values(
                errors,
                when.get("hasTraitCategory"),
                advantage_categories,
                path=f"{path}.when.hasTraitCategory",
                rule_id=rule_id,
                code="validation_rule_category_reference_unknown",
                message="La regla apunta a una categoría inexistente.",
                field_name="category",
            )

        effect = rule.get("effect", {})
        if not isinstance(effect, Mapping):
            errors.append(
                make_error(
                    "validation_rule_effect_not_object",
                    "El efecto de regla debe ser un objeto.",
                    path=f"{path}.effect",
                    ruleId=rule_id,
                )
            )
            continue

        effect_type = effect.get("type")
        if declared_effect_types and effect_type not in declared_effect_types:
            errors.append(
                make_error(
                    "validation_rule_effect_type_unknown",
                    "El tipo de efecto no está declarado.",
                    path=f"{path}.effect.type",
                    ruleId=rule_id,
                    effectType=effect_type,
                )
            )

        if effect.get("catalog") == "advantages":
            valid_trait_ids = advantage_ids
            valid_categories = advantage_categories
        elif effect.get("catalog") == "domain":
            valid_trait_ids = domain_ids
            valid_categories = domain_categories
        else:
            valid_trait_ids = all_trait_ids
            valid_categories = advantage_categories | domain_categories

        _check_trait_ids(errors, effect.get("traitId"), valid_trait_ids, path=f"{path}.effect.traitId", rule_id=rule_id)
        for key in ("traitIds", "exceptTraitIds", "additionalForbiddenTraitIds"):
            _check_trait_ids(errors, effect.get(key, []), valid_trait_ids, path=f"{path}.effect.{key}", rule_id=rule_id)

        _check_named_values(
            errors,
            effect.get("category"),
            valid_categories,
            path=f"{path}.effect.category",
            rule_id=rule_id,
            code="validation_rule_category_reference_unknown",
            message="La regla apunta a una categoría inexistente.",
            field_name="category",
        )
        _check_named_values(
            errors,
            effect.get("skills", []),
            skills,
            path=f"{path}.effect.skills",
            rule_id=rule_id,
            code="validation_rule_skill_reference_unknown",
            message="La regla apunta a una habilidad inexistente.",
            field_name="skill",
        )
        if discipline_names:
            _check_named_values(
                errors,
                effect.get("discipline"),
                discipline_names,
                path=f"{path}.effect.discipline",
                rule_id=rule_id,
                code="validation_rule_discipline_reference_unknown",
                message="La regla apunta a una disciplina inexistente.",
                field_name="discipline",
            )
            _check_named_values(
                errors,
                effect.get("disciplines", []),
                discipline_names,
                path=f"{path}.effect.disciplines",
                rule_id=rule_id,
                code="validation_rule_discipline_reference_unknown",
                message="La regla apunta a una disciplina inexistente.",
                field_name="discipline",
            )

    return errors
