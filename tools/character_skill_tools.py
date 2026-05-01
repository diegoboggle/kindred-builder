"""Validation helpers for initial V5 skill creation.

The creator stores the skill draft as a 10-item ``skillSequence``. The
position in that sequence determines the final dot value:

    1 -> 4
    2-4 -> 3
    5-7 -> 2
    8-10 -> 1

All unselected skills remain at 0. These helpers intentionally return stable
machine-readable error codes so UI code can map them to localized messages.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping, Sequence
import unicodedata


SKILL_SEQUENCE_VALUES: list[int] = [4, 3, 3, 3, 2, 2, 2, 1, 1, 1]
SKILL_DISTRIBUTION: list[int] = SKILL_SEQUENCE_VALUES + [0] * 17
SPECIAL_REQUIRED_SKILLS: set[str] = {
    "Academicismo",
    "Artesanía",
    "Ciencias",
    "Interpretación",
}

SPECIALTY_SOURCE_VALUES: set[str] = {
    "free",
    "predator",
    "advantage",
    "manual",
    "other",
}


def normalize_specialty_name(name: str) -> str:
    """Normalize specialty names for exact duplicate detection.

    This is intentionally not semantic matching. It folds case, strips leading
    and trailing whitespace, collapses internal whitespace, and removes
    diacritics so values such as "Seducción", "seduccion" and " SEDUCCIÓN "
    are treated as the same specialty.
    """

    decomposed = unicodedata.normalize("NFKD", name.strip())
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(without_marks.casefold().split())


def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    payload.update(extra)
    return payload


def _skill_dots(skills: Mapping[str, Any], skill: str) -> int:
    value = skills.get(skill, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return value


def build_skills_from_sequence(skill_sequence: Sequence[str], all_skills: Sequence[str]) -> dict[str, int]:
    """Build the final skill map from a valid skill sequence.

    Unknown or duplicate sequence entries are still applied by name; validation
    is handled by ``validate_skill_sequence``. This makes the function useful
    for deterministic UI previews as well as tests.
    """

    result = {skill: 0 for skill in all_skills}
    for skill, value in zip(skill_sequence, SKILL_SEQUENCE_VALUES):
        result[skill] = value
    return result


def validate_skill_sequence(skill_sequence: Any, all_skills: Sequence[str]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    valid_skills = set(all_skills)

    if not isinstance(skill_sequence, list):
        return [_error("skill_sequence_not_list", "skillSequence must be a list.")]

    if len(skill_sequence) != len(SKILL_SEQUENCE_VALUES):
        errors.append(
            _error(
                "skill_sequence_wrong_length",
                "skillSequence must contain exactly 10 skills.",
                expected=len(SKILL_SEQUENCE_VALUES),
                actual=len(skill_sequence),
            )
        )

    non_strings = [skill for skill in skill_sequence if not isinstance(skill, str)]
    if non_strings:
        errors.append(
            _error(
                "skill_sequence_non_string",
                "skillSequence may only contain skill names as strings.",
                values=non_strings,
            )
        )

    unknown = sorted({skill for skill in skill_sequence if isinstance(skill, str) and skill not in valid_skills})
    if unknown:
        errors.append(
            _error(
                "skill_sequence_unknown_skills",
                "skillSequence contains unknown skills.",
                skills=unknown,
            )
        )

    duplicates = sorted(
        skill
        for skill, count in Counter(skill_sequence).items()
        if count > 1 and isinstance(skill, str)
    )
    if duplicates:
        errors.append(
            _error(
                "skill_sequence_duplicates",
                "skillSequence cannot contain duplicate skills.",
                skills=duplicates,
            )
        )

    return errors


def validate_initial_skills(
    skills: Any,
    all_skills: Sequence[str],
    *,
    skill_sequence: Any | None = None,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    valid_skills = set(all_skills)

    if not isinstance(skills, Mapping):
        return [
            _error(
                "skills_not_object",
                "skills must be an object mapping skill names to dots.",
            )
        ]

    skill_names = set(skills.keys())
    missing = sorted(valid_skills - skill_names)
    unknown = sorted(skill_names - valid_skills)

    if missing:
        errors.append(_error("skills_missing", "The skill map is missing skills.", skills=missing))
    if unknown:
        errors.append(_error("skills_unknown", "The skill map contains unknown skills.", skills=unknown))

    for skill, value in skills.items():
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(
                _error(
                    "skill_value_not_integer",
                    "Skill dots must be integers.",
                    skill=skill,
                    value=value,
                )
            )
            continue
        if value < 0 or value > 4:
            errors.append(
                _error(
                    "skill_value_out_of_range",
                    "Initial skill dots must be between 0 and 4.",
                    skill=skill,
                    value=value,
                )
            )

    if (
        not missing
        and not unknown
        and all(isinstance(value, int) and not isinstance(value, bool) for value in skills.values())
    ):
        distribution = sorted((int(skills[skill]) for skill in all_skills), reverse=True)
        if distribution != SKILL_DISTRIBUTION:
            errors.append(
                _error(
                    "skill_distribution_invalid",
                    "Initial skills must match 4/3/3/3/2/2/2/1/1/1 with all others at 0.",
                    expected=SKILL_DISTRIBUTION,
                    actual=distribution,
                )
            )

    if skill_sequence is not None:
        seq_errors = validate_skill_sequence(skill_sequence, all_skills)
        errors.extend(seq_errors)
        if not seq_errors:
            expected = build_skills_from_sequence(skill_sequence, all_skills)
            if dict(skills) != expected:
                errors.append(
                    _error(
                        "skills_do_not_match_sequence",
                        "The skill map must match skillSequence.",
                    )
                )

    return errors


def is_valid_initial_skills(
    skills: Mapping[str, int],
    all_skills: Sequence[str],
    *,
    skill_sequence: Sequence[str] | None = None,
) -> bool:
    return not validate_initial_skills(skills, all_skills, skill_sequence=skill_sequence)


def validate_specialties(
    skills: Mapping[str, int],
    specialties: Any,
    all_skills: Sequence[str],
    *,
    special_required_skills: Iterable[str] = SPECIAL_REQUIRED_SKILLS,
    free_specialty_skill: str | None = None,
    free_specialty_name: str | None = None,
) -> list[dict[str, Any]]:
    """Validate specialties for initial creation.

    Rules enforced here:
    - Every specialty must point to a known trained skill.
    - The free specialty is mandatory for every character and must be present
      as a specialty with ``source == "free"``.
    - Predator and other automatic specialties are allowed only if the related
      skill has at least 1 dot.
    - A skill may not have more specialties than its dot rating.
    - Duplicate specialties are blocked within the same skill using normalized
      exact matching: case, accents and whitespace do not create distinct names.
    - Specialty names are free text, but cannot be empty.
    """

    errors: list[dict[str, Any]] = []
    valid_skills = set(all_skills)
    required = set(special_required_skills)

    if not isinstance(skills, Mapping):
        return [
            _error(
                "skills_not_object",
                "skills must be an object mapping skill names to dots.",
            )
        ]

    if not isinstance(specialties, list):
        return [_error("specialties_not_list", "specialties must be a list.")]

    specialty_pairs: set[tuple[str, str]] = set()
    specialty_skills_with_named_specialty: set[str] = set()
    specialty_count_by_skill: dict[str, int] = defaultdict(int)
    free_specialty_entries: list[Mapping[str, Any]] = []

    for index, specialty in enumerate(specialties):
        if not isinstance(specialty, Mapping):
            errors.append(_error("specialty_not_object", "Each specialty must be an object.", index=index))
            continue

        skill = specialty.get("skill")
        name = specialty.get("name")
        source = specialty.get("source")

        skill_is_valid = isinstance(skill, str) and skill in valid_skills
        name_is_valid = isinstance(name, str) and bool(name.strip())
        source_is_valid = isinstance(source, str) and source in SPECIALTY_SOURCE_VALUES

        if not skill_is_valid:
            errors.append(
                _error(
                    "specialty_skill_invalid",
                    "Specialty skill must be known.",
                    index=index,
                    skill=skill,
                )
            )
            continue

        if not name_is_valid:
            errors.append(
                _error(
                    "specialty_name_missing",
                    "Specialty name must not be empty.",
                    index=index,
                    skill=skill,
                )
            )
            continue

        if not source_is_valid:
            errors.append(
                _error(
                    "specialty_source_invalid",
                    "Specialty source must be one of the supported source values.",
                    index=index,
                    skill=skill,
                    source=source,
                    allowed=sorted(SPECIALTY_SOURCE_VALUES),
                )
            )
            continue

        if _skill_dots(skills, skill) <= 0:
            errors.append(
                _error(
                    "specialty_skill_untrained",
                    "A specialty can only be assigned to a trained skill.",
                    index=index,
                    skill=skill,
                    source=source,
                )
            )

        normalized_name = normalize_specialty_name(name)
        key = (skill, normalized_name)
        if key in specialty_pairs:
            errors.append(_error("specialty_duplicate", "Duplicate specialty.", index=index, skill=skill, name=name))
        specialty_pairs.add(key)

        specialty_count_by_skill[skill] += 1
        specialty_skills_with_named_specialty.add(skill)

        if source == "free":
            free_specialty_entries.append(specialty)

    for skill, specialty_count in sorted(specialty_count_by_skill.items()):
        skill_dots = _skill_dots(skills, skill)
        if specialty_count > skill_dots:
            errors.append(
                _error(
                    "specialty_count_exceeds_skill_dots",
                    "A skill cannot have more specialties than its dot rating.",
                    skill=skill,
                    specialtyCount=specialty_count,
                    skillDots=skill_dots,
                )
            )

    missing_required = sorted(
        skill
        for skill in required
        if _skill_dots(skills, skill) > 0 and skill not in specialty_skills_with_named_specialty
    )
    if missing_required:
        errors.append(
            _error(
                "mandatory_specialty_missing",
                "Some skills require a specialty when they have at least 1 dot.",
                skills=missing_required,
            )
        )

    if not isinstance(free_specialty_skill, str) or not free_specialty_skill:
        errors.append(
            _error(
                "free_specialty_skill_missing",
                "Every character must select one free specialty.",
            )
        )
    elif free_specialty_skill not in valid_skills:
        errors.append(
            _error(
                "free_specialty_skill_unknown",
                "The free specialty skill must be known.",
                skill=free_specialty_skill,
            )
        )
    elif _skill_dots(skills, free_specialty_skill) <= 0:
        errors.append(
            _error(
                "free_specialty_skill_untrained",
                "The free specialty must belong to a trained skill.",
                skill=free_specialty_skill,
            )
        )

    if not isinstance(free_specialty_name, str) or not free_specialty_name.strip():
        errors.append(_error("free_specialty_name_missing", "The free specialty name is required."))

    if len(free_specialty_entries) != 1:
        errors.append(
            _error(
                "free_specialty_entry_count_invalid",
                "Exactly one specialty entry must have source 'free'.",
                count=len(free_specialty_entries),
            )
        )
    elif isinstance(free_specialty_skill, str) and isinstance(free_specialty_name, str):
        free_entry = free_specialty_entries[0]
        if (
            free_entry.get("skill") != free_specialty_skill
            or normalize_specialty_name(str(free_entry.get("name", "")))
            != normalize_specialty_name(free_specialty_name)
        ):
            errors.append(
                _error(
                    "free_specialty_entry_mismatch",
                    "The source 'free' specialty entry must match freeSpecialtySkill and freeSpecialtyName.",
                    entrySkill=free_entry.get("skill"),
                    entryName=free_entry.get("name"),
                    freeSpecialtySkill=free_specialty_skill,
                    freeSpecialtyName=free_specialty_name,
                )
            )

    return errors


def apply_skill_maximum_rules(
    skills: Mapping[str, int],
    rule_effects: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Apply validation-rules effects of type ``skillMaximum`` to a skill map."""

    errors: list[dict[str, Any]] = []
    for effect in rule_effects:
        if effect.get("type") != "skillMaximum":
            continue
        max_dots = effect.get("maxDots")
        for skill in effect.get("skills", []):
            value = skills.get(skill, 0)
            if isinstance(max_dots, int) and value > max_dots:
                errors.append(
                    _error(
                        "skill_maximum_rule_violation",
                        "A validation rule limits this skill.",
                        skill=skill,
                        value=value,
                        maxDots=max_dots,
                    )
                )
    return errors
