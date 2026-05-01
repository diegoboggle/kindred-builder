import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from character_skill_tools import (
    SKILL_DISTRIBUTION,
    SKILL_SEQUENCE_VALUES,
    build_skills_from_sequence,
    is_valid_initial_skills,
    validate_initial_skills,
    validate_skill_sequence,
    validate_specialties,
    apply_skill_maximum_rules,
    normalize_specialty_name,
)


class SkillRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.creator = json.loads((ROOT / "data" / "creator-data.json").read_text(encoding="utf-8"))
        cls.character_schema = json.loads((ROOT / "schemas" / "character-state.schema.json").read_text(encoding="utf-8"))
        cls.creator_schema = json.loads((ROOT / "schemas" / "creator-data.schema.json").read_text(encoding="utf-8"))
        cls.validation_rules = json.loads((ROOT / "data" / "validation-rules.json").read_text(encoding="utf-8"))
        cls.skills = cls.creator["skills"]
        cls.valid_sequence = [
            "Pelea",
            "Persuasión",
            "Sigilo",
            "Callejeo",
            "Academicismo",
            "Artesanía",
            "Ciencias",
            "Interpretación",
            "Atletismo",
            "Consciencia",
        ]
        cls.valid_map = {skill: 0 for skill in cls.skills}
        cls.valid_map.update(
            {
                "Pelea": 4,
                "Persuasión": 3,
                "Sigilo": 3,
                "Callejeo": 3,
                "Academicismo": 2,
                "Artesanía": 2,
                "Ciencias": 2,
                "Interpretación": 1,
                "Atletismo": 1,
                "Consciencia": 1,
            }
        )
        cls.valid_specialties = [
            {"skill": "Academicismo", "name": "Historia", "source": "manual"},
            {"skill": "Artesanía", "name": "Carpintería", "source": "manual"},
            {"skill": "Ciencias", "name": "Química", "source": "manual"},
            {"skill": "Interpretación", "name": "Canto", "source": "manual"},
            {"skill": "Pelea", "name": "Mordidas", "source": "free"},
        ]

    def test_skill_creation_model_is_declared(self):
        model = self.creator["skillCreationModel"]
        self.assertEqual(model["initialDots"], 0)
        self.assertEqual(model["minimumDots"], 0)
        self.assertEqual(model["maximumDots"], 4)
        self.assertEqual(model["requiredSkillCount"], 27)
        self.assertEqual(model["finalDistribution"], SKILL_DISTRIBUTION)
        self.assertEqual(model["sequenceLength"], 10)
        self.assertTrue(model["sequenceMustContainUniqueSkills"])
        self.assertEqual(model["sequencePositionValues"], SKILL_SEQUENCE_VALUES)
        self.assertEqual(model["unselectedSkillValue"], 0)
        self.assertEqual(model["validationMode"], "exactFinalDistribution")
        self.assertEqual(set(model["specialtyRequiredSkills"]), set(self.creator["specialRequiredSkills"]))

        free_rule = model["freeSpecialtyRule"]
        self.assertTrue(free_rule["required"])
        self.assertTrue(free_rule["skillMustBeTrained"])
        self.assertTrue(free_rule["nameMustBeNonEmpty"])
        self.assertEqual(free_rule["mustExistInSpecialtiesWithSource"], "free")
        self.assertTrue(free_rule["exactlyOneFreeSpecialty"])

        specialty_rules = model["specialtyRules"]
        self.assertTrue(specialty_rules["sourceRequired"])
        self.assertEqual(set(specialty_rules["sourceOptions"]), {"free", "predator", "advantage", "manual", "other"})
        self.assertEqual(specialty_rules["duplicateDetection"], "normalizedExactBySkill")
        self.assertEqual(specialty_rules["maxSpecialtiesPerSkill"], "skillDots")
        self.assertTrue(specialty_rules["predatorSpecialtyRequiresTrainedSkill"])
        self.assertFalse(specialty_rules["semanticDuplicateDetection"])

    def test_creator_data_schema_requires_skill_creation_model(self):
        self.assertIn("skillCreationModel", self.creator_schema["required"])
        model_schema = self.creator_schema["properties"]["skillCreationModel"]
        self.assertIn("finalDistribution", model_schema["required"])
        self.assertIn("sequencePositionValues", model_schema["required"])
        self.assertIn("specialtyRules", model_schema["required"])
        self.assertFalse(model_schema["additionalProperties"])

        free_rule_schema = model_schema["properties"]["freeSpecialtyRule"]
        self.assertIn("required", free_rule_schema["required"])
        self.assertIn("mustExistInSpecialtiesWithSource", free_rule_schema["required"])

    def test_character_state_schema_defines_skill_sequence(self):
        skill_sequence_schema = self.character_schema["properties"]["skillSequence"]
        self.assertEqual(skill_sequence_schema["minItems"], 10)
        self.assertEqual(skill_sequence_schema["maxItems"], 10)
        self.assertTrue(skill_sequence_schema["uniqueItems"])
        self.assertEqual(set(skill_sequence_schema["items"]["enum"]), set(self.skills))

    def test_character_state_schema_defines_skill_map_strictly(self):
        skills_schema = self.character_schema["properties"]["skills"]
        self.assertEqual(set(skills_schema["required"]), set(self.skills))
        self.assertFalse(skills_schema["additionalProperties"])

        for skill in self.skills:
            rule = skills_schema["properties"][skill]
            self.assertEqual(rule["type"], "integer")
            self.assertEqual(rule["minimum"], 0)
            self.assertEqual(rule["maximum"], 4)

    def test_character_state_schema_defines_specialty_fields(self):
        for field in ("specialties", "freeSpecialtySkill", "freeSpecialtyName"):
            self.assertIn(field, self.character_schema["required"])
            self.assertIn(field, self.character_schema["properties"])

        specialty_schema = self.character_schema["properties"]["specialties"]["items"]
        self.assertEqual(set(specialty_schema["required"]), {"skill", "name", "source"})
        self.assertFalse(specialty_schema["additionalProperties"])
        self.assertEqual(set(specialty_schema["properties"]["skill"]["enum"]), set(self.skills))
        self.assertEqual(set(specialty_schema["properties"]["source"]["enum"]), {"free", "predator", "advantage", "manual", "other"})
        self.assertEqual(self.character_schema["properties"]["freeSpecialtyName"]["minLength"], 1)

    def test_sequence_builds_expected_skill_map(self):
        self.assertEqual(
            build_skills_from_sequence(self.valid_sequence, self.skills),
            self.valid_map,
        )

    def test_valid_initial_skill_distribution_passes(self):
        self.assertTrue(
            is_valid_initial_skills(
                self.valid_map,
                self.skills,
                skill_sequence=self.valid_sequence,
            )
        )

    def test_skill_distribution_must_be_exact(self):
        invalid = dict(self.valid_map)
        invalid["Consciencia"] = 0
        errors = validate_initial_skills(invalid, self.skills)
        self.assertIn("skill_distribution_invalid", {error["code"] for error in errors})

    def test_missing_skill_is_blocking(self):
        invalid = dict(self.valid_map)
        invalid.pop("Consciencia")
        errors = validate_initial_skills(invalid, self.skills)
        self.assertIn("skills_missing", {error["code"] for error in errors})

    def test_unknown_skill_is_blocking(self):
        invalid = dict(self.valid_map)
        invalid["Astrología"] = 1
        errors = validate_initial_skills(invalid, self.skills)
        self.assertIn("skills_unknown", {error["code"] for error in errors})

    def test_skill_below_minimum_is_blocking(self):
        invalid = dict(self.valid_map)
        invalid["Consciencia"] = -1
        errors = validate_initial_skills(invalid, self.skills)
        self.assertIn("skill_value_out_of_range", {error["code"] for error in errors})

    def test_skill_above_maximum_is_blocking(self):
        invalid = dict(self.valid_map)
        invalid["Pelea"] = 5
        errors = validate_initial_skills(invalid, self.skills)
        self.assertIn("skill_value_out_of_range", {error["code"] for error in errors})

    def test_skill_non_integer_is_blocking(self):
        invalid = dict(self.valid_map)
        invalid["Pelea"] = "4"
        errors = validate_initial_skills(invalid, self.skills)
        self.assertIn("skill_value_not_integer", {error["code"] for error in errors})

    def test_skill_boolean_is_not_integer(self):
        invalid = dict(self.valid_map)
        invalid["Pelea"] = True
        errors = validate_initial_skills(invalid, self.skills)
        self.assertIn("skill_value_not_integer", {error["code"] for error in errors})

    def test_skill_sequence_must_be_ten_unique_known_skills(self):
        self.assertEqual(validate_skill_sequence(self.valid_sequence, self.skills), [])

    def test_skill_sequence_duplicate_is_blocking(self):
        invalid_sequence = list(self.valid_sequence)
        invalid_sequence[-1] = invalid_sequence[0]
        errors = validate_skill_sequence(invalid_sequence, self.skills)
        self.assertIn("skill_sequence_duplicates", {error["code"] for error in errors})

    def test_skill_sequence_unknown_is_blocking(self):
        invalid_sequence = list(self.valid_sequence)
        invalid_sequence[-1] = "Astrología"
        errors = validate_skill_sequence(invalid_sequence, self.skills)
        self.assertIn("skill_sequence_unknown_skills", {error["code"] for error in errors})

    def test_skill_sequence_non_string_is_blocking_without_crashing(self):
        invalid_sequence = list(self.valid_sequence)
        invalid_sequence[-1] = ["Sigilo"]
        errors = validate_skill_sequence(invalid_sequence, self.skills)
        self.assertIn("skill_sequence_non_string", {error["code"] for error in errors})

    def test_skill_sequence_wrong_length_is_blocking(self):
        errors = validate_skill_sequence(self.valid_sequence[:-1], self.skills)
        self.assertIn("skill_sequence_wrong_length", {error["code"] for error in errors})

    def test_skills_must_match_sequence(self):
        mismatched = dict(self.valid_map)
        mismatched["Pelea"] = 3
        mismatched["Consciencia"] = 2
        errors = validate_initial_skills(mismatched, self.skills, skill_sequence=self.valid_sequence)
        self.assertIn("skills_do_not_match_sequence", {error["code"] for error in errors})

    def test_valid_specialties_pass(self):
        errors = validate_specialties(
            self.valid_map,
            self.valid_specialties,
            self.skills,
            free_specialty_skill="Pelea",
            free_specialty_name="Mordidas",
        )
        self.assertEqual(errors, [])

    def test_mandatory_specialty_required_for_trained_required_skills(self):
        specialties = [
            {"skill": "Academicismo", "name": "Historia", "source": "manual"},
            {"skill": "Artesanía", "name": "Carpintería", "source": "manual"},
            {"skill": "Pelea", "name": "Mordidas", "source": "free"},
            # Ciencias e Interpretación están entrenadas, pero faltan.
        ]
        errors = validate_specialties(
            self.valid_map,
            specialties,
            self.skills,
            free_specialty_skill="Pelea",
            free_specialty_name="Mordidas",
        )
        self.assertIn("mandatory_specialty_missing", {error["code"] for error in errors})

    def test_free_specialty_must_be_on_trained_skill(self):
        specialties = [
            {"skill": "Academicismo", "name": "Historia", "source": "manual"},
            {"skill": "Artesanía", "name": "Carpintería", "source": "manual"},
            {"skill": "Ciencias", "name": "Química", "source": "manual"},
            {"skill": "Interpretación", "name": "Canto", "source": "manual"},
            {"skill": "Tecnología", "name": "Redes", "source": "free"},
        ]
        errors = validate_specialties(
            self.valid_map,
            specialties,
            self.skills,
            free_specialty_skill="Tecnología",
            free_specialty_name="Redes",
        )
        self.assertIn("free_specialty_skill_untrained", {error["code"] for error in errors})
        self.assertIn("specialty_skill_untrained", {error["code"] for error in errors})

    def test_free_specialty_name_is_required(self):
        specialties = [
            {"skill": "Academicismo", "name": "Historia", "source": "manual"},
            {"skill": "Artesanía", "name": "Carpintería", "source": "manual"},
            {"skill": "Ciencias", "name": "Química", "source": "manual"},
            {"skill": "Interpretación", "name": "Canto", "source": "manual"},
        ]
        errors = validate_specialties(
            self.valid_map,
            specialties,
            self.skills,
            free_specialty_skill="Pelea",
            free_specialty_name="",
        )
        self.assertIn("free_specialty_name_missing", {error["code"] for error in errors})
        self.assertIn("free_specialty_entry_count_invalid", {error["code"] for error in errors})

    def test_free_specialty_entry_must_exist_and_match(self):
        specialties = [
            {"skill": "Academicismo", "name": "Historia", "source": "manual"},
            {"skill": "Artesanía", "name": "Carpintería", "source": "manual"},
            {"skill": "Ciencias", "name": "Química", "source": "manual"},
            {"skill": "Interpretación", "name": "Canto", "source": "manual"},
            {"skill": "Pelea", "name": "Garras", "source": "free"},
        ]
        errors = validate_specialties(
            self.valid_map,
            specialties,
            self.skills,
            free_specialty_skill="Pelea",
            free_specialty_name="Mordidas",
        )
        self.assertIn("free_specialty_entry_mismatch", {error["code"] for error in errors})

    def test_exactly_one_free_specialty_entry_is_required(self):
        specialties = self.valid_specialties + [
            {"skill": "Persuasión", "name": "Negociación", "source": "free"}
        ]
        errors = validate_specialties(
            self.valid_map,
            specialties,
            self.skills,
            free_specialty_skill="Pelea",
            free_specialty_name="Mordidas",
        )
        self.assertIn("free_specialty_entry_count_invalid", {error["code"] for error in errors})

    def test_specialty_cannot_be_assigned_to_untrained_skill(self):
        errors = validate_specialties(
            self.valid_map,
            self.valid_specialties + [{"skill": "Tecnología", "name": "Redes", "source": "manual"}],
            self.skills,
            free_specialty_skill="Pelea",
            free_specialty_name="Mordidas",
        )
        self.assertIn("specialty_skill_untrained", {error["code"] for error in errors})

    def test_predator_specialty_requires_trained_skill(self):
        errors = validate_specialties(
            self.valid_map,
            self.valid_specialties + [{"skill": "Tecnología", "name": "Redes", "source": "predator", "sourceId": "predator_example"}],
            self.skills,
            free_specialty_skill="Pelea",
            free_specialty_name="Mordidas",
        )
        self.assertIn("specialty_skill_untrained", {error["code"] for error in errors})

    def test_specialty_source_is_required(self):
        invalid = [
            {"skill": "Academicismo", "name": "Historia"},
            {"skill": "Artesanía", "name": "Carpintería", "source": "manual"},
            {"skill": "Ciencias", "name": "Química", "source": "manual"},
            {"skill": "Interpretación", "name": "Canto", "source": "manual"},
            {"skill": "Pelea", "name": "Mordidas", "source": "free"},
        ]
        errors = validate_specialties(
            self.valid_map,
            invalid,
            self.skills,
            free_specialty_skill="Pelea",
            free_specialty_name="Mordidas",
        )
        self.assertIn("specialty_source_invalid", {error["code"] for error in errors})

    def test_specialty_duplicates_are_blocking_with_case_and_accents_normalized(self):
        errors = validate_specialties(
            self.valid_map,
            self.valid_specialties + [
                {"skill": "Pelea", "name": "Mordidas", "source": "manual"},
                {"skill": "Pelea", "name": "  MÓRDIDAS  ", "source": "manual"},
            ],
            self.skills,
            free_specialty_skill="Pelea",
            free_specialty_name="Mordidas",
        )
        self.assertIn("specialty_duplicate", {error["code"] for error in errors})

    def test_semantic_duplicates_are_not_blocked(self):
        specialties = [
            {"skill": "Academicismo", "name": "Historia", "source": "manual"},
            {"skill": "Artesanía", "name": "Carpintería", "source": "manual"},
            {"skill": "Ciencias", "name": "Química", "source": "manual"},
            {"skill": "Interpretación", "name": "Cantar", "source": "manual"},
            {"skill": "Interpretación", "name": "Bailar", "source": "free"},
        ]
        errors = validate_specialties(
            self.valid_map,
            specialties,
            self.skills,
            free_specialty_skill="Interpretación",
            free_specialty_name="Bailar",
        )
        self.assertIn("specialty_count_exceeds_skill_dots", {error["code"] for error in errors})

        valid_with_more_interpretacion = dict(self.valid_map)
        valid_with_more_interpretacion["Interpretación"] = 2
        errors = validate_specialties(
            valid_with_more_interpretacion,
            specialties,
            self.skills,
            free_specialty_skill="Interpretación",
            free_specialty_name="Bailar",
        )
        self.assertNotIn("specialty_duplicate", {error["code"] for error in errors})
        self.assertNotIn("specialty_count_exceeds_skill_dots", {error["code"] for error in errors})

    def test_specialty_count_cannot_exceed_skill_dots(self):
        specialties = self.valid_specialties + [
            {"skill": "Consciencia", "name": "Vigilancia", "source": "manual"},
            {"skill": "Consciencia", "name": "Emboscadas", "source": "manual"},
        ]
        errors = validate_specialties(
            self.valid_map,
            specialties,
            self.skills,
            free_specialty_skill="Pelea",
            free_specialty_name="Mordidas",
        )
        self.assertIn("specialty_count_exceeds_skill_dots", {error["code"] for error in errors})

    def test_normalize_specialty_name_ignores_case_accents_and_whitespace(self):
        self.assertEqual(normalize_specialty_name("  SEDUCCIÓN  "), normalize_specialty_name("seduccion"))
        self.assertEqual(normalize_specialty_name("Canto   Coral"), "canto coral")

    def test_skill_maximum_rules_apply_to_character_skill_map(self):
        effects = [rule["effect"] for rule in self.validation_rules["rules"] if rule["effect"]["type"] == "skillMaximum"]
        invalid = dict(self.valid_map)
        invalid["Academicismo"] = 2
        invalid["Ciencias"] = 2
        invalid["Subterfugio"] = 1
        errors = apply_skill_maximum_rules(invalid, effects)
        self.assertTrue(any(error["skill"] == "Academicismo" and error["maxDots"] == 1 for error in errors))
        self.assertTrue(any(error["skill"] == "Ciencias" and error["maxDots"] == 1 for error in errors))
        self.assertTrue(any(error["skill"] == "Subterfugio" and error["maxDots"] == 0 for error in errors))

    def test_skill_maximum_rules_ignore_non_integer_values_without_crashing(self):
        errors = apply_skill_maximum_rules(
            {"Academicismo": "4", "Ciencias": True},
            [{"type": "skillMaximum", "skills": ["Academicismo", "Ciencias"], "maxDots": 1}],
        )
        self.assertEqual(errors, [])

    def test_documentation_mentions_step_16_skill_rules(self):
        spec = (ROOT / "docs" / "creator-logic-spec.md").read_text(encoding="utf-8")
        self.assertIn("Distribución de habilidades", spec)
        self.assertIn("4/3/3/3/2/2/2/1/1/1", spec)
        self.assertIn("skillCreationModel", spec)
        self.assertIn("Especialidades", spec)
        self.assertIn("source", spec)
        self.assertIn("cantidad de puntos de esa habilidad", spec)


if __name__ == "__main__":
    unittest.main()
