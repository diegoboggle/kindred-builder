"""Predator-type validator module."""

from __future__ import annotations

from typing import Any, Mapping

from .common import as_mapping, make_error, normalize_identifier


def validate(character_state: Mapping[str, Any], creator_data: Mapping[str, Any], **_: Any) -> list[dict[str, Any]]:
    """Validate the selected predator type and its direct selections."""
    predator_state = as_mapping(character_state.get("predator", {}))
    predator_id = predator_state.get("predatorId")
    predators = {predator.get("id"): predator for predator in creator_data.get("predatorTypes", [])}
    errors: list[dict[str, Any]] = []

    if predator_id not in predators:
        return [
            make_error(
                "predator_id_unknown",
                "El tipo de depredador seleccionado no existe.",
                path="predator.predatorId",
                predatorId=predator_id,
            )
        ]

    predator = predators[str(predator_id)]

    selected_discipline = predator_state.get("selectedDisciplineId")
    if selected_discipline:
        allowed = {normalize_identifier(value) for value in predator.get("disciplineChoices", [])}
        if selected_discipline not in allowed:
            errors.append(
                make_error(
                    "predator_discipline_choice_invalid",
                    "La disciplina elegida no está entre las opciones del depredador.",
                    path="predator.selectedDisciplineId",
                    selectedDisciplineId=selected_discipline,
                    allowed=sorted(allowed),
                )
            )

    selected_specialty = predator_state.get("selectedSpecialty")
    if isinstance(selected_specialty, Mapping):
        normalized_choice = f"{selected_specialty.get('skill')}: {selected_specialty.get('name')}"
        allowed_specialties = set(predator.get("specialtyChoices", []))
        if normalized_choice not in allowed_specialties:
            errors.append(
                make_error(
                    "predator_specialty_choice_invalid",
                    "La especialidad elegida no está entre las opciones del depredador.",
                    path="predator.selectedSpecialty",
                    selectedSpecialty=normalized_choice,
                    allowed=sorted(allowed_specialties),
                )
            )

    return errors
