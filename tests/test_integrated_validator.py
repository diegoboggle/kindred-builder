import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from character_validator import (
    apply_validation_rules,
    derive_character_state,
    load_project_data,
    validate_character,
    validateCharacter,
)


def _load_complete_state_fixture():
    fixture_path = ROOT / "tests" / "test_character_state_schema.py"
    spec = importlib.util.spec_from_file_location("character_state_fixture", fixture_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    state = module.complete_character_state()
    state["disciplines"]["powers"] = [
        {"recordId": "celeridad_1_cat_s_grace", "disciplineId": "celeridad", "source": "creation"}
    ]
    state["specialties"] = [
        {"skill": "Academicismo", "name": "Historia", "source": "free"},
        {"skill": "Artesanía", "name": "Forja", "source": "manual"},
        {"skill": "Ciencias", "name": "Química", "source": "manual"},
    ]
    return state


class IntegratedCharacterValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        loaded = load_project_data(ROOT)
        cls.creator = loaded["creator_data"]
        cls.discipline_catalog = loaded["discipline_catalog"]
        cls.validation_rules = loaded["validation_rules"]
        cls.character_schema = loaded["character_schema"]

    def validate(self, state, **kwargs):
        return validate_character(
            state,
            self.creator,
            discipline_catalog=self.discipline_catalog,
            validation_rules=self.validation_rules,
            character_schema=self.character_schema,
            **kwargs,
        )

    def test_integrated_validator_accepts_valid_complete_state(self):
        result = self.validate(_load_complete_state_fixture())
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])
        self.assertIn("derived", result)
        self.assertEqual(result["derived"]["validation"]["valid"], True)
        self.assertIn("rule_engine", [item["module"] for item in result["moduleResults"]])

    def test_camel_case_alias_matches_snake_case_entrypoint(self):
        state = _load_complete_state_fixture()
        result_a = self.validate(state)
        result_b = validateCharacter(
            state,
            self.creator,
            discipline_catalog=self.discipline_catalog,
            validation_rules=self.validation_rules,
            character_schema=self.character_schema,
        )
        self.assertEqual(result_a["valid"], result_b["valid"])
        self.assertEqual(result_a["errors"], result_b["errors"])

    def test_integrated_validator_updates_derived_when_requested(self):
        state = _load_complete_state_fixture()
        result = self.validate(state, update_derived=True)
        self.assertIs(result["characterState"], state)
        self.assertTrue(state["derived"]["validation"]["valid"])
        self.assertEqual(state["derived"]["health"]["max"], state["attributes"]["Resistencia"] + 3)
        self.assertEqual(
            state["derived"]["willpower"]["max"],
            state["attributes"]["Compostura"] + state["attributes"]["Resolución"],
        )
        self.assertEqual(state["derived"]["budgets"]["domain"]["availableDots"], 1)

    def test_schema_errors_are_reported_by_integrated_pipeline(self):
        state = _load_complete_state_fixture()
        del state["profile"]["biography"]
        result = self.validate(state)
        self.assertFalse(result["valid"])
        self.assertTrue(any(error["module"] == "character_state" for error in result["errors"]))
        self.assertTrue(any(error["code"] == "character_state_schema_error" for error in result["errors"]))

    def test_validation_rules_are_applied_to_character_state(self):
        state = _load_complete_state_fixture()
        state["advantages"]["flaws"].append(
            {"traitId": "flaw_alimentacion_granjero", "dots": 2, "source": "manual", "purchaseScope": "character"}
        )
        result = self.validate(state)
        codes = {error["code"] for error in result["errors"]}
        self.assertIn("validation_rule_forbidden_trait", codes)
        self.assertTrue(
            any(error.get("ruleId") == "rule_ventrue_cannot_take_farmer" for error in result["errors"])
        )

    def test_skill_maximum_rules_are_applied_to_character_state(self):
        state = _load_complete_state_fixture()
        state["advantages"]["flaws"].append(
            {"traitId": "flaw_linguistica_analfabeto", "dots": 2, "source": "manual", "purchaseScope": "character"}
        )
        result = self.validate(state)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any(error.get("ruleId") == "rule_illiterate_limits_academics_and_science" for error in result["errors"])
        )
        self.assertTrue(any(error["code"] == "validation_rule_skill_maximum_exceeded" for error in result["errors"]))

    def test_discipline_rules_are_applied_to_character_state(self):
        state = _load_complete_state_fixture()
        state["advantages"]["merits"].append(
            {"traitId": "merit_otros_voluntad_templada", "dots": 3, "source": "manual", "purchaseScope": "character"}
        )
        state["disciplines"]["ratings"]["presencia"] = 1
        result = self.validate(state)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any(error.get("ruleId") == "rule_tempered_will_forbids_domination_and_presence" for error in result["errors"])
        )
        self.assertTrue(any(error["code"] == "validation_rule_discipline_maximum_exceeded" for error in result["errors"]))

    def test_domain_rules_are_applied_to_character_state(self):
        state = _load_complete_state_fixture()
        state["domain"]["pool"]["spentDots"] = 2
        state["domain"]["flaws"].append(
            {
                "domainTraitId": "domain_background_flaw_refugio_sin_refugio",
                "dots": 1,
                "purchaseScope": "domain",
            }
        )
        state["domain"]["backgrounds"].append(
            {
                "domainTraitId": "domain_background_refugio",
                "dots": 1,
                "purchaseScope": "domain",
            }
        )
        result = self.validate(state)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any(error.get("ruleId") == "rule_domain_no_haven_blocks_domain_haven_traits" for error in result["errors"])
        )
        self.assertTrue(any(error["code"] == "validation_rule_forbidden_domain_trait" for error in result["errors"]))

    def test_derived_values_are_recomputed_from_current_state(self):
        state = _load_complete_state_fixture()
        state["attributes"]["Resistencia"] = 5
        derived = derive_character_state(state)
        self.assertEqual(derived["health"]["max"], 8)
        self.assertEqual(derived["bloodPotency"], state["generation"]["bloodPotencyBase"])

    def test_derived_current_tracks_are_clamped_to_valid_ranges(self):
        state = _load_complete_state_fixture()
        state["derived"]["health"]["current"] = -2
        state["derived"]["willpower"]["current"] = 999
        derived = derive_character_state(state)
        self.assertEqual(derived["health"]["current"], 0)
        self.assertEqual(derived["willpower"]["current"], derived["willpower"]["max"])

    def test_integrated_validator_reports_bad_numeric_shapes_without_crashing(self):
        state = _load_complete_state_fixture()
        state["attributes"]["Resistencia"] = "tres"
        state["advantages"]["budget"]["availableMeritDots"] = "siete"
        state["domain"]["pool"]["baseDots"] = "uno"
        result = self.validate(state)
        self.assertFalse(result["valid"])
        self.assertTrue(any(error["code"] == "character_state_schema_error" for error in result["errors"]))
        self.assertTrue(any(error["code"] == "attribute_value_not_integer" for error in result["errors"]))

    def test_integrated_validator_reports_bad_container_shapes_without_crashing(self):
        state = _load_complete_state_fixture()
        state["attributes"] = []
        state["skills"] = []
        state["skillSequence"] = 123
        result = self.validate(state)
        codes = {error["code"] for error in result["errors"]}
        self.assertFalse(result["valid"])
        self.assertIn("character_state_schema_error", codes)
        self.assertIn("attributes_not_object", codes)
        self.assertIn("skills_not_object", codes)

    def test_integrated_validator_rejects_non_object_state_without_crashing(self):
        result = self.validate([])
        self.assertFalse(result["valid"])
        self.assertEqual(result["errors"][0]["code"], "character_state_not_object")
        self.assertEqual(result["moduleResults"][0]["module"], "character_state")

    def test_rule_application_can_be_called_independently(self):
        state = _load_complete_state_fixture()
        errors = apply_validation_rules(state, self.creator, self.validation_rules)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
