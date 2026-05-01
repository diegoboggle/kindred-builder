"""Discipline validator module."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from .common import as_list, as_mapping, make_error, normalize_identifier


def validate(
    character_state: Mapping[str, Any],
    creator_data: Mapping[str, Any],
    *,
    discipline_catalog: Mapping[str, Any] | None = None,
    **_: Any,
) -> list[dict[str, Any]]:
    """Validate discipline ratings and selected powers against the discipline catalog."""
    if discipline_catalog is None:
        return []

    records = discipline_catalog.get("records", [])
    records_by_id = {
        str(record["id"]): record
        for record in records
        if isinstance(record, Mapping) and "id" in record
    }
    discipline_ids = {
        normalize_identifier(record.get("discipline", ""))
        for record in records
        if isinstance(record, Mapping)
    }
    errors: list[dict[str, Any]] = []

    disciplines = as_mapping(character_state.get("disciplines", {}))

    ratings = as_mapping(disciplines.get("ratings", {}))
    valid_ratings: dict[str, int] = {}
    for discipline_id, dots in ratings.items():
        discipline_known = discipline_id in discipline_ids
        if not discipline_known:
            errors.append(
                make_error(
                    "discipline_rating_id_unknown",
                    "La disciplina puntuada no existe en el catálogo.",
                    path=f"disciplines.ratings.{discipline_id}",
                    disciplineId=discipline_id,
                )
            )
        if not isinstance(dots, int) or isinstance(dots, bool) or dots < 0 or dots > 5:
            errors.append(
                make_error(
                    "discipline_rating_invalid",
                    "Los puntos de disciplina deben estar entre 0 y 5.",
                    path=f"disciplines.ratings.{discipline_id}",
                    disciplineId=discipline_id,
                    dots=dots,
                )
            )
            continue
        if not discipline_known:
            continue
        valid_ratings[str(discipline_id)] = dots

    selected_power_counts: Counter[str] = Counter()
    seen_power_ids: set[str] = set()
    for index, power in enumerate(as_list(disciplines.get("powers", []))):
        if not isinstance(power, Mapping):
            continue
        record_id = power.get("recordId")
        if not isinstance(record_id, str) or record_id not in records_by_id:
            errors.append(
                make_error(
                    "discipline_power_record_unknown",
                    "El poder seleccionado no existe en el catálogo.",
                    path=f"disciplines.powers[{index}].recordId",
                    recordId=record_id,
                )
            )
            continue

        if record_id in seen_power_ids:
            errors.append(
                make_error(
                    "discipline_power_duplicate",
                    "El poder seleccionado está duplicado.",
                    path=f"disciplines.powers[{index}].recordId",
                    recordId=record_id,
                )
            )
            continue
        seen_power_ids.add(record_id)

        record = records_by_id[record_id]
        if record.get("kind") != "power":
            errors.append(
                make_error(
                    "discipline_power_record_not_power",
                    "Sólo los registros kind=power pueden seleccionarse como poderes iniciales.",
                    path=f"disciplines.powers[{index}].recordId",
                    recordId=record_id,
                    kind=record.get("kind"),
                )
            )
            continue

        expected_discipline_id = normalize_identifier(record.get("discipline", ""))
        selected_power_counts[expected_discipline_id] += 1
        supplied_discipline_id = power.get("disciplineId")
        if supplied_discipline_id is not None and supplied_discipline_id != expected_discipline_id:
            errors.append(
                make_error(
                    "discipline_power_discipline_mismatch",
                    "El disciplineId del poder no coincide con el catálogo.",
                    path=f"disciplines.powers[{index}].disciplineId",
                    recordId=record_id,
                    expectedDisciplineId=expected_discipline_id,
                    actualDisciplineId=supplied_discipline_id,
                )
            )

        rating = valid_ratings.get(expected_discipline_id, 0)
        level = record.get("level")
        if isinstance(level, int) and not isinstance(level, bool) and level > rating:
            errors.append(
                make_error(
                    "discipline_power_level_above_rating",
                    "El poder seleccionado está por encima de la puntuación actual de la disciplina.",
                    path=f"disciplines.powers[{index}].recordId",
                    recordId=record_id,
                    disciplineId=expected_discipline_id,
                    powerLevel=level,
                    disciplineRating=rating,
                )
            )

        requirement = record.get("amalgamRequirement")
        if isinstance(requirement, Mapping):
            required_discipline = normalize_identifier(str(requirement.get("discipline", "")))
            required_level = requirement.get("level")
            actual_level = valid_ratings.get(required_discipline, 0)
            if (
                isinstance(required_level, int)
                and not isinstance(required_level, bool)
                and actual_level < required_level
            ):
                errors.append(
                    make_error(
                        "discipline_power_amalgam_requirement_missing",
                        "El poder seleccionado incumple su requisito de amalgama.",
                        path=f"disciplines.powers[{index}].recordId",
                        recordId=record_id,
                        requiredDisciplineId=required_discipline,
                        requiredLevel=required_level,
                        actualLevel=actual_level,
                    )
                )

    for discipline_id, rating in sorted(valid_ratings.items()):
        expected_count = rating
        actual_count = selected_power_counts.get(discipline_id, 0)
        if actual_count != expected_count:
            errors.append(
                make_error(
                    "discipline_power_count_mismatch",
                    "La cantidad de poderes seleccionados debe coincidir con la puntuación de la disciplina.",
                    path="disciplines.powers",
                    disciplineId=discipline_id,
                    expectedCount=expected_count,
                    actualCount=actual_count,
                )
            )

    return errors
