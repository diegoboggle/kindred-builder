import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from character_attribute_tools import (
    ATTRIBUTE_DISTRIBUTION,
    ATTRIBUTE_SEQUENCE_VALUES,
    build_attributes_from_sequence,
    is_valid_initial_attributes,
    validate_attr_sequence,
    validate_initial_attributes,
)


class AttributeRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.creator = json.loads((ROOT / "data" / "creator-data.json").read_text(encoding="utf-8"))
        cls.character_schema = json.loads((ROOT / "schemas" / "character-state.schema.json").read_text(encoding="utf-8"))
        cls.creator_schema = json.loads((ROOT / "schemas" / "creator-data.schema.json").read_text(encoding="utf-8"))
        cls.attributes = cls.creator["attributes"]
        cls.valid_sequence = ["Fuerza", "Resolución", "Destreza", "Resistencia", "Carisma"]
        cls.valid_map = {
            "Fuerza": 4,
            "Destreza": 3,
            "Resistencia": 3,
            "Carisma": 3,
            "Manipulación": 2,
            "Compostura": 2,
            "Inteligencia": 2,
            "Astucia": 2,
            "Resolución": 1,
        }

    def test_attribute_creation_model_is_declared(self):
        model = self.creator["attributeCreationModel"]
        self.assertEqual(model["initialDots"], 2)
        self.assertEqual(model["minimumDots"], 1)
        self.assertEqual(model["maximumDots"], 5)
        self.assertEqual(model["requiredAttributeCount"], 9)
        self.assertEqual(model["finalDistribution"], ATTRIBUTE_DISTRIBUTION)
        self.assertEqual(model["sequenceLength"], 5)
        self.assertTrue(model["sequenceMustContainUniqueAttributes"])
        self.assertEqual(model["sequencePositionValues"], ATTRIBUTE_SEQUENCE_VALUES)
        self.assertEqual(model["unselectedAttributeValue"], 2)
        self.assertEqual(model["validationMode"], "exactFinalDistribution")

    def test_creator_data_schema_requires_attribute_creation_model(self):
        self.assertIn("attributeCreationModel", self.creator_schema["required"])
        model_schema = self.creator_schema["properties"]["attributeCreationModel"]
        self.assertIn("finalDistribution", model_schema["required"])
        self.assertIn("sequencePositionValues", model_schema["required"])
        self.assertFalse(model_schema["additionalProperties"])

    def test_character_state_schema_defines_attr_sequence(self):
        attr_sequence_schema = self.character_schema["properties"]["attrSequence"]
        self.assertEqual(attr_sequence_schema["minItems"], 5)
        self.assertEqual(attr_sequence_schema["maxItems"], 5)
        self.assertTrue(attr_sequence_schema["uniqueItems"])
        self.assertEqual(set(attr_sequence_schema["items"]["enum"]), set(self.attributes))

    def test_character_state_schema_defines_attribute_map_strictly(self):
        attributes_schema = self.character_schema["properties"]["attributes"]
        self.assertEqual(set(attributes_schema["required"]), set(self.attributes))
        self.assertFalse(attributes_schema["additionalProperties"])

        for attribute in self.attributes:
            rule = attributes_schema["properties"][attribute]
            self.assertEqual(rule["type"], "integer")
            self.assertEqual(rule["minimum"], 1)
            self.assertEqual(rule["maximum"], 5)

    def test_sequence_builds_expected_attribute_map(self):
        self.assertEqual(
            build_attributes_from_sequence(self.valid_sequence, self.attributes),
            self.valid_map,
        )

    def test_valid_initial_attribute_distribution_passes(self):
        self.assertTrue(
            is_valid_initial_attributes(
                self.valid_map,
                self.attributes,
                attr_sequence=self.valid_sequence,
            )
        )

    def test_distribution_must_be_exact(self):
        invalid = dict(self.valid_map)
        invalid["Resolución"] = 2

        errors = validate_initial_attributes(invalid, self.attributes)
        self.assertIn("attribute_distribution_invalid", {error["code"] for error in errors})

    def test_missing_attribute_is_blocking(self):
        invalid = dict(self.valid_map)
        invalid.pop("Resolución")

        errors = validate_initial_attributes(invalid, self.attributes)
        self.assertIn("attributes_missing", {error["code"] for error in errors})

    def test_unknown_attribute_is_blocking(self):
        invalid = dict(self.valid_map)
        invalid["Suerte"] = 1

        errors = validate_initial_attributes(invalid, self.attributes)
        self.assertIn("attributes_unknown", {error["code"] for error in errors})

    def test_attribute_below_minimum_is_blocking(self):
        invalid = dict(self.valid_map)
        invalid["Resolución"] = 0

        errors = validate_initial_attributes(invalid, self.attributes)
        self.assertIn("attribute_value_out_of_range", {error["code"] for error in errors})

    def test_attribute_above_maximum_is_blocking(self):
        invalid = dict(self.valid_map)
        invalid["Fuerza"] = 6

        errors = validate_initial_attributes(invalid, self.attributes)
        self.assertIn("attribute_value_out_of_range", {error["code"] for error in errors})

    def test_attribute_non_integer_is_blocking(self):
        invalid = dict(self.valid_map)
        invalid["Fuerza"] = "4"

        errors = validate_initial_attributes(invalid, self.attributes)
        self.assertIn("attribute_value_not_integer", {error["code"] for error in errors})

    def test_attribute_boolean_is_not_integer(self):
        invalid = dict(self.valid_map)
        invalid["Fuerza"] = True

        errors = validate_initial_attributes(invalid, self.attributes)
        self.assertIn("attribute_value_not_integer", {error["code"] for error in errors})

    def test_attr_sequence_must_be_five_unique_known_attributes(self):
        self.assertEqual(validate_attr_sequence(self.valid_sequence, self.attributes), [])

    def test_attr_sequence_duplicate_is_blocking(self):
        invalid_sequence = list(self.valid_sequence)
        invalid_sequence[-1] = invalid_sequence[0]

        errors = validate_attr_sequence(invalid_sequence, self.attributes)
        self.assertIn("attr_sequence_duplicates", {error["code"] for error in errors})

    def test_attr_sequence_unknown_is_blocking(self):
        invalid_sequence = list(self.valid_sequence)
        invalid_sequence[-1] = "Suerte"

        errors = validate_attr_sequence(invalid_sequence, self.attributes)
        self.assertIn("attr_sequence_unknown_attributes", {error["code"] for error in errors})

    def test_attr_sequence_non_string_is_blocking_without_crashing(self):
        invalid_sequence = list(self.valid_sequence)
        invalid_sequence[-1] = ["Resolución"]

        errors = validate_attr_sequence(invalid_sequence, self.attributes)
        self.assertIn("attr_sequence_non_string", {error["code"] for error in errors})

    def test_attr_sequence_wrong_length_is_blocking(self):
        errors = validate_attr_sequence(self.valid_sequence[:-1], self.attributes)
        self.assertIn("attr_sequence_wrong_length", {error["code"] for error in errors})

    def test_attributes_must_match_sequence(self):
        mismatched = dict(self.valid_map)
        mismatched["Manipulación"] = 3
        mismatched["Carisma"] = 2

        errors = validate_initial_attributes(mismatched, self.attributes, attr_sequence=self.valid_sequence)
        self.assertIn("attributes_do_not_match_sequence", {error["code"] for error in errors})

    def test_documentation_mentions_step_15_attribute_rules(self):
        spec = (ROOT / "docs" / "creator-logic-spec.md").read_text(encoding="utf-8")
        self.assertIn("Distribución de atributos", spec)
        self.assertIn("4/3/3/3/2/2/2/2/1", spec)
        self.assertIn("attributeCreationModel", spec)


if __name__ == "__main__":
    unittest.main()
