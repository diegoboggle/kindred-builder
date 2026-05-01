import importlib.util
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validators import get_validator, list_validators
from validators import attributes, skills, specialties, budget, advantages, domain, disciplines, predator, validation_rules, character_state


def _load_complete_state_fixture():
    fixture_path = ROOT / "tests" / "test_character_state_schema.py"
    spec = importlib.util.spec_from_file_location("character_state_fixture", fixture_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    state = module.complete_character_state()

    # The export fixture is schema-valid. For the semantic specialty validator
    # we add the mandatory specialties required by the trained Academicismo,
    # Artesanía, Ciencias, and Interpretación family rule.
    state["disciplines"]["powers"] = [{"recordId": "celeridad_1_cat_s_grace", "disciplineId": "celeridad", "source": "creation"}]
    state["specialties"] = [
        {"skill": "Academicismo", "name": "Historia", "source": "free"},
        {"skill": "Artesanía", "name": "Forja", "source": "manual"},
        {"skill": "Ciencias", "name": "Química", "source": "manual"},
    ]
    return state


class ValidatorModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.creator = json.loads((ROOT / "data" / "creator-data.json").read_text(encoding="utf-8"))
        cls.discipline_catalog = json.loads((ROOT / "data" / "disciplinas_v5_catalogo.json").read_text(encoding="utf-8"))
        cls.validation_rules = json.loads((ROOT / "data" / "validation-rules.json").read_text(encoding="utf-8"))
        cls.character_schema = json.loads((ROOT / "schemas" / "character-state.schema.json").read_text(encoding="utf-8"))
        cls.state = _load_complete_state_fixture()

    def test_registry_lists_separated_validator_modules(self):
        self.assertEqual(
            list_validators(),
            [
                "attributes",
                "skills",
                "specialties",
                "budget",
                "advantages",
                "domain",
                "disciplines",
                "predator",
                "validation_rules",
                "character_state",
            ],
        )
        for name in list_validators():
            self.assertTrue(callable(get_validator(name)))

    def test_modules_expose_validate_functions(self):
        for module in (
            attributes,
            skills,
            specialties,
            budget,
            advantages,
            domain,
            disciplines,
            predator,
            validation_rules,
            character_state,
        ):
            self.assertTrue(callable(module.validate), module.__name__)

    def test_semantic_validators_accept_valid_complete_state(self):
        state = deepcopy(self.state)
        checks = [
            attributes.validate(state, self.creator),
            skills.validate(state, self.creator),
            specialties.validate(state, self.creator),
            budget.validate(state, self.creator),
            advantages.validate(state, self.creator),
            domain.validate(state, self.creator),
            disciplines.validate(state, self.creator, discipline_catalog=self.discipline_catalog),
            predator.validate(state, self.creator),
            validation_rules.validate(state, self.creator, validation_rules=self.validation_rules, discipline_catalog=self.discipline_catalog),
            character_state.validate(state, self.creator, character_schema=self.character_schema),
        ]
        combined = [error for errors in checks for error in errors]
        self.assertEqual(combined, [])

    def test_attribute_validator_reports_distribution_errors(self):
        state = deepcopy(self.state)
        state["attributes"]["Fuerza"] = 5
        errors = attributes.validate(state, self.creator)
        self.assertTrue(any(error["code"] == "attribute_distribution_invalid" for error in errors))

    def test_skill_validator_reports_distribution_errors(self):
        state = deepcopy(self.state)
        state["skills"]["Pelea"] = 4
        errors = skills.validate(state, self.creator)
        self.assertTrue(any(error["code"] == "skill_distribution_invalid" for error in errors))

    def test_specialty_validator_reports_duplicate_normalized_specialties(self):
        state = deepcopy(self.state)
        state["skills"]["Academicismo"] = 2
        state["specialties"] = [
            {"skill": "Academicismo", "name": "Historia", "source": "free"},
            {"skill": "Academicismo", "name": "HISTÓRIA", "source": "manual"},
        ]
        errors = specialties.validate(state, self.creator)
        self.assertTrue(any(error["code"] == "specialty_duplicate" for error in errors))

    def test_budget_validator_reports_duplicate_domain_spending(self):
        state = deepcopy(self.state)
        state["domain"]["pool"]["contributedAdvantageDots"] = 1
        state["advantages"]["budget"]["contributedToDomainDots"] = 0
        state["domain"]["contributions"] = [
            {
                "id": "domain_contribution_test",
                "source": "characterAdvantages",
                "sourceBudget": "advantages.meritDots",
                "dots": 1,
                "reason": "Planificación",
                "targetPool": "domain.pool.contributedAdvantageDots",
                "reversibleDuringCreation": True,
                "lockedAfterFinalization": True,
                "allocationStatus": "planned",
            }
        ]
        errors = budget.validate(state, self.creator)
        self.assertTrue(any(error["code"] == "budget_integrity_error" for error in errors))

    def test_advantage_validator_rejects_unknown_trait_id(self):
        state = deepcopy(self.state)
        state["advantages"]["merits"] = [{"traitId": "merit_no_existe", "dots": 1, "source": "manual"}]
        errors = advantages.validate(state, self.creator)
        self.assertTrue(any(error["code"] == "advantage_trait_id_unknown" for error in errors))

    def test_advantage_validator_rejects_boolean_dots(self):
        state = deepcopy(self.state)
        state["advantages"]["merits"] = [
            {"traitId": "merit_aspecto_rostro_famoso", "dots": True, "source": "manual", "purchaseScope": "character"}
        ]
        errors = advantages.validate(state, self.creator)
        self.assertTrue(any(error["code"] == "advantage_trait_dots_invalid" for error in errors))

    def test_domain_validator_rejects_character_scope_purchase(self):
        state = deepcopy(self.state)
        state["domain"]["backgrounds"] = [
            {"domainTraitId": "domain_background_rebano", "dots": 1, "purchaseScope": "character"}
        ]
        errors = domain.validate(state, self.creator)
        self.assertTrue(any(error["code"] == "domain_purchase_scope_invalid" for error in errors))

    def test_domain_validator_rejects_boolean_dots(self):
        state = deepcopy(self.state)
        state["domain"]["backgrounds"] = [
            {"domainTraitId": "domain_background_contactos", "dots": True, "purchaseScope": "domain"}
        ]
        errors = domain.validate(state, self.creator)
        self.assertTrue(any(error["code"] == "domain_trait_dots_invalid" for error in errors))

    def test_discipline_validator_rejects_unknown_power(self):
        state = deepcopy(self.state)
        state["disciplines"]["powers"] = [{"recordId": "no_existe", "disciplineId": "celeridad", "source": "creation"}]
        errors = disciplines.validate(state, self.creator, discipline_catalog=self.discipline_catalog)
        self.assertTrue(any(error["code"] == "discipline_power_record_unknown" for error in errors))

    def test_discipline_validator_rejects_power_above_rating(self):
        state = deepcopy(self.state)
        state["disciplines"]["ratings"] = {"celeridad": 1}
        state["disciplines"]["powers"] = [
            {"recordId": "celeridad_2_fleetness", "disciplineId": "celeridad", "source": "creation"}
        ]
        errors = disciplines.validate(state, self.creator, discipline_catalog=self.discipline_catalog)
        self.assertTrue(any(error["code"] == "discipline_power_level_above_rating" for error in errors))

    def test_discipline_validator_rejects_unsatisfied_amalgam_requirement(self):
        state = deepcopy(self.state)
        state["disciplines"]["ratings"] = {"animalismo": 2}
        state["disciplines"]["powers"] = [
            {"recordId": "animalismo_1_bond_famulus", "disciplineId": "animalismo", "source": "creation"},
            {"recordId": "animalismo_2_animal_messenger", "disciplineId": "animalismo", "source": "creation"},
        ]
        errors = disciplines.validate(state, self.creator, discipline_catalog=self.discipline_catalog)
        self.assertTrue(
            any(error["code"] == "discipline_power_amalgam_requirement_missing" for error in errors)
        )

    def test_discipline_validator_rejects_power_count_mismatch(self):
        state = deepcopy(self.state)
        state["disciplines"]["ratings"] = {"celeridad": 2}
        state["disciplines"]["powers"] = [
            {"recordId": "celeridad_1_cat_s_grace", "disciplineId": "celeridad", "source": "creation"}
        ]
        errors = disciplines.validate(state, self.creator, discipline_catalog=self.discipline_catalog)
        self.assertTrue(any(error["code"] == "discipline_power_count_mismatch" for error in errors))

    def test_predator_validator_rejects_invalid_choice(self):
        state = deepcopy(self.state)
        state["predator"]["selectedDisciplineId"] = "auspex"
        errors = predator.validate(state, self.creator)
        self.assertTrue(any(error["code"] == "predator_discipline_choice_invalid" for error in errors))

    def test_character_state_validator_reports_schema_errors(self):
        state = deepcopy(self.state)
        state["unexpected"] = True
        errors = character_state.validate(state, self.creator, character_schema=self.character_schema)
        self.assertTrue(any(error["code"] == "character_state_schema_error" for error in errors))

    def test_validation_rules_validator_rejects_nested_unknown_references(self):
        rules = deepcopy(self.validation_rules)
        rules["rules"][0]["effect"]["traitId"] = "trait_no_existe"
        errors = validation_rules.validate(
            self.state,
            self.creator,
            validation_rules=rules,
            discipline_catalog=self.discipline_catalog,
        )
        self.assertTrue(any(error["code"] == "validation_rule_trait_reference_unknown" for error in errors))


if __name__ == "__main__":
    unittest.main()
