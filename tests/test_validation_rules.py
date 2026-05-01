import json
import sys
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class ValidationRulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.creator = json.loads((ROOT / "data" / "creator-data.json").read_text(encoding="utf-8"))
        cls.disciplines = json.loads((ROOT / "data" / "disciplinas_v5_catalogo.json").read_text(encoding="utf-8"))
        cls.rules = json.loads((ROOT / "data" / "validation-rules.json").read_text(encoding="utf-8"))
        cls.schema = json.loads((ROOT / "schemas" / "validation-rules.schema.json").read_text(encoding="utf-8"))

        cls.advantage_ids = {item["id"] for item in cls.creator["advantagesCatalog"]}
        cls.domain_ids = {item["id"] for item in cls.creator["domainCatalog"]}
        cls.advantage_categories = {item["category"] for item in cls.creator["advantagesCatalog"]}
        cls.domain_categories = {item["category"] for item in cls.creator["domainCatalog"]}
        cls.clans = {clan["id"] for clan in cls.creator["clanCatalog"]}
        cls.skills = set(cls.creator["skills"])
        cls.discipline_names = {record["discipline"] for record in cls.disciplines["records"]}
        cls.effect_types = set(cls.rules["effectTypes"])

    def test_validation_rules_file_exists_and_schema_validates(self):
        self.assertTrue((ROOT / "data" / "validation-rules.json").exists())
        self.assertTrue((ROOT / "schemas" / "validation-rules.schema.json").exists())
        jsonschema.validate(instance=self.rules, schema=self.schema)

    def test_creator_data_does_not_embed_validation_rules(self):
        self.assertNotIn("validationRules", self.creator)
        self.assertNotIn("validation-rules", self.creator)

    def test_rule_ids_are_unique_and_blocking(self):
        ids = [rule["id"] for rule in self.rules["rules"]]
        self.assertEqual(len(ids), len(set(ids)))
        for rule in self.rules["rules"]:
            self.assertEqual(rule["severity"], "error")
        self.assertTrue(self.rules["policy"]["allRulesAreBlocking"])

    def test_rules_classify_origin_as_official_or_logical(self):
        origins = {rule["origin"] for rule in self.rules["rules"]}
        self.assertIn("official", origins)
        self.assertIn("logical", origins)
        self.assertTrue(origins <= {"official", "logical"})

    def test_all_effect_types_are_declared(self):
        for rule in self.rules["rules"]:
            self.assertIn(rule["effect"]["type"], self.effect_types)

    def test_when_clan_references_exist(self):
        for rule in self.rules["rules"]:
            when = rule.get("when", {})
            if "clanId" in when:
                self.assertIn(when["clanId"], self.clans, rule["id"])

    def test_when_trait_references_exist(self):
        for rule in self.rules["rules"]:
            when = rule.get("when", {})
            for key in ("hasTraitId",):
                if key in when:
                    self.assertIn(when[key], self.advantage_ids, rule["id"])
            for key in ("hasAnyTraitId",):
                for trait_id in when.get(key, []):
                    self.assertIn(trait_id, self.advantage_ids, rule["id"])
            if "hasTraitCategory" in when:
                self.assertIn(when["hasTraitCategory"], self.advantage_categories, rule["id"])
            for trait_id in when.get("exceptTraitIds", []):
                self.assertIn(trait_id, self.advantage_ids, rule["id"])

    def test_when_domain_trait_references_exist(self):
        for rule in self.rules["rules"]:
            when = rule.get("when", {})
            if "hasDomainTraitId" in when:
                self.assertIn(when["hasDomainTraitId"], self.domain_ids, rule["id"])
            for trait_id in when.get("hasAnyDomainTraitId", []):
                self.assertIn(trait_id, self.domain_ids, rule["id"])

    def test_effect_trait_references_exist_in_correct_catalog(self):
        for rule in self.rules["rules"]:
            effect = rule["effect"]
            catalog = effect.get("catalog")
            if catalog == "advantages":
                valid_ids = self.advantage_ids
                valid_categories = self.advantage_categories
            elif catalog == "domain":
                valid_ids = self.domain_ids
                valid_categories = self.domain_categories
            else:
                valid_ids = self.advantage_ids | self.domain_ids
                valid_categories = self.advantage_categories | self.domain_categories

            if "traitId" in effect:
                self.assertIn(effect["traitId"], valid_ids, rule["id"])
            for key in ("traitIds", "exceptTraitIds", "additionalForbiddenTraitIds"):
                for trait_id in effect.get(key, []):
                    self.assertIn(trait_id, valid_ids, rule["id"])
            if "category" in effect:
                self.assertIn(effect["category"], valid_categories, rule["id"])

    def test_source_trait_references_exist_when_declared(self):
        for rule in self.rules["rules"]:
            source = rule["source"]
            if "traitId" not in source:
                continue
            trait_id = source["traitId"]
            if source.get("kind") == "advantageText":
                self.assertIn(trait_id, self.advantage_ids, rule["id"])
            elif source.get("kind") in {"domainText", "domainCatalog"}:
                self.assertIn(trait_id, self.domain_ids, rule["id"])
            else:
                self.assertIn(trait_id, self.advantage_ids | self.domain_ids, rule["id"])

    def test_skill_and_discipline_references_exist(self):
        for rule in self.rules["rules"]:
            effect = rule["effect"]
            for skill in effect.get("skills", []):
                self.assertIn(skill, self.skills, rule["id"])
            if "discipline" in effect:
                self.assertIn(effect["discipline"], self.discipline_names, rule["id"])
            for discipline in effect.get("disciplines", []):
                self.assertIn(discipline, self.discipline_names, rule["id"])

    def test_required_official_rules_are_present(self):
        expected = {
            "rule_ventrue_cannot_take_farmer",
            "rule_illiterate_limits_academics_and_science",
            "rule_transparent_forbids_subterfuge",
            "rule_tempered_will_forbids_domination_and_presence",
            "rule_bonds_of_fealty_requires_domination",
            "rule_influencer_requires_fame_two",
            "rule_enduring_fame_requires_fame_three",
            "rule_obvious_predator_blocks_herd",
        }
        present = {rule["id"] for rule in self.rules["rules"]}
        self.assertTrue(expected <= present)

    def test_required_logical_rules_are_present(self):
        expected = {
            "rule_nosferatu_cannot_take_appearance_merits",
            "rule_no_haven_blocks_haven_traits",
            "rule_haven_traits_require_haven",
            "rule_domain_personal_backgrounds_spend_domain_pool",
            "rule_domain_no_haven_blocks_domain_haven_traits",
            "rule_domain_haven_flaws_require_domain_haven",
            "rule_domain_obvious_predator_blocks_domain_herd",
            "rule_domain_haven_incompatible_with_domain_no_haven",
        }
        present = {rule["id"] for rule in self.rules["rules"]}
        self.assertTrue(expected <= present)

    def test_domain_rules_only_reference_domain_catalog_for_domain_effects(self):
        for rule in self.rules["rules"]:
            if rule["scope"] != "domain":
                continue
            effect = rule["effect"]
            if effect.get("catalog") == "domain":
                for key in ("traitId",):
                    if key in effect:
                        self.assertIn(effect[key], self.domain_ids, rule["id"])
                for key in ("traitIds", "exceptTraitIds", "additionalForbiddenTraitIds"):
                    for trait_id in effect.get(key, []):
                        self.assertIn(trait_id, self.domain_ids, rule["id"])

    def test_logical_rules_explain_project_or_inference_basis(self):
        for rule in self.rules["rules"]:
            if rule["origin"] == "logical":
                source = rule["source"]
                self.assertIn(source.get("kind"), {"logicalInference", "projectAdaptation"})
                self.assertTrue(source.get("basis"), rule["id"])


    def test_domain_pool_reallocation_rules_are_present(self):
        by_id = {rule["id"]: rule for rule in self.rules["rules"]}
        realloc = by_id["rule_advantage_points_reallocatable_to_domain_during_creation"]
        self.assertEqual(realloc["effect"]["type"], "advantageToDomainContribution")
        self.assertTrue(realloc["effect"]["reversibleDuringCreation"])
        self.assertEqual(realloc["effect"]["fromPool"], "advantages.budget.totalMeritDots")
        self.assertEqual(realloc["effect"]["trackingField"], "advantages.budget.contributedToDomainDots")
        self.assertEqual(realloc["effect"]["toPool"], "domain.pool.contributedAdvantageDots")

        native_lock = by_id["rule_domain_native_points_cannot_fund_character_advantages"]
        self.assertEqual(native_lock["effect"]["type"], "forbidDomainToAdvantageContribution")
        self.assertIn("domain.pool.baseDots", native_lock["effect"]["fromPools"])
        self.assertIn("domain.pool.grantedDots", native_lock["effect"]["fromPools"])
        self.assertIn("advantages.budget.availableMeritDots", native_lock["effect"]["forbiddenTargetPools"])

    def test_domain_spending_rule_lists_valid_pool_components(self):
        by_id = {rule["id"]: rule for rule in self.rules["rules"]}
        rule = by_id["rule_domain_personal_backgrounds_spend_domain_pool"]
        self.assertEqual(rule["effect"]["allowedPool"], "domain")
        self.assertEqual(
            set(rule["effect"]["allowedPoolComponents"]),
            {
                "domain.pool.baseDots",
                "domain.pool.contributedAdvantageDots",
                "domain.pool.flawDots",
                "domain.pool.grantedDots",
            },
        )

    def test_budget_tool_allows_reallocating_advantage_contributions_without_double_counting(self):
        from tools.character_budget_tools import validate_budget_integrity

        state = {
            "advantages": {
                "budget": {
                    "totalMeritDots": 7,
                    "spentMeritDots": 3,
                    "contributedToDomainDots": 2,
                    "availableMeritDots": 2,
                    "receivedFromDomainDots": 0,
                }
            },
            "domain": {
                "pool": {
                    "baseDots": 1,
                    "contributedAdvantageDots": 2,
                    "flawDots": 0,
                    "grantedDots": 0,
                    "spentDots": 3,
                },
                "traits": {"chasse": 1, "lien": 1, "portillon": 0},
                "backgrounds": [{"domainTraitId": "domain_background_rebano", "dots": 1}],
                "merits": [],
                "contributions": [
                    {
                        "id": "domain_contribution_test",
                        "source": "characterAdvantages",
                        "sourceBudget": "advantages.meritDots",
                        "dots": 2,
                        "targetPool": "domain.pool.contributedAdvantageDots",
                        "reversibleDuringCreation": True,
                        "reason": "Planificación de Dominio personal",
                    }
                ],
            },
        }
        self.assertEqual(validate_budget_integrity(state), [])

        # Simula echar pie atrás durante la creación: se elimina la contribución,
        # y los campos calculados vuelven al presupuesto de Ventajas.
        state["domain"]["contributions"] = []
        state["domain"]["pool"]["contributedAdvantageDots"] = 0
        state["domain"]["pool"]["spentDots"] = 1
        state["domain"]["traits"] = {"chasse": 1, "lien": 0, "portillon": 0}
        state["domain"]["backgrounds"] = []
        state["advantages"]["budget"]["contributedToDomainDots"] = 0
        state["advantages"]["budget"]["availableMeritDots"] = 4
        self.assertEqual(validate_budget_integrity(state), [])

    def test_budget_tool_rejects_domain_native_points_returning_to_advantages(self):
        from tools.character_budget_tools import validate_budget_integrity

        state = {
            "advantages": {
                "budget": {
                    "totalMeritDots": 7,
                    "spentMeritDots": 3,
                    "contributedToDomainDots": 0,
                    "availableMeritDots": 4,
                    "receivedFromDomainDots": 1,
                }
            },
            "domain": {
                "pool": {
                    "baseDots": 1,
                    "contributedAdvantageDots": 0,
                    "flawDots": 0,
                    "grantedDots": 0,
                    "spentDots": 0,
                },
                "traits": {"chasse": 0, "lien": 0, "portillon": 0},
                "backgrounds": [],
                "merits": [],
                "contributions": [],
            },
        }
        errors = validate_budget_integrity(state)
        self.assertTrue(any("Domain-native dots cannot be transferred" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
