import json
import unittest
from copy import deepcopy
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]


def complete_character_state():
    attributes = {
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
    skills = {
        "Academicismo": 4,
        "Armas de Fuego": 3,
        "Artesanía": 3,
        "Atletismo": 3,
        "Callejeo": 2,
        "Ciencias": 2,
        "Conducir": 2,
        "Consciencia": 1,
        "Etiqueta": 1,
        "Finanzas": 1,
        "Interpretación": 0,
        "Intimidación": 0,
        "Investigación": 0,
        "Latrocinio": 0,
        "Liderazgo": 0,
        "Medicina": 0,
        "Ocultismo": 0,
        "Pelea": 0,
        "Pelea con Armas": 0,
        "Perspicacia": 0,
        "Persuasión": 0,
        "Política": 0,
        "Sigilo": 0,
        "Subterfugio": 0,
        "Supervivencia": 0,
        "Tecnología": 0,
        "Trato con Animales": 0,
    }
    return {
        "schemaVersion": "character-state-v17",
        "exportStatus": "complete",
        "creationStatus": "finalized",
        "metadata": {
            "characterId": "character_test_001",
            "createdAt": "2026-04-28T00:00:00Z",
            "updatedAt": "2026-04-28T00:00:00Z",
            "appVersion": "test",
            "exportedAt": "2026-04-28T00:00:00Z",
        },
        "discordId": "123456789012345678",
        "basics": {
            "name": "Ejemplo",
            "concept": "Investigador nocturno",
            "ambition": "Descubrir la verdad",
            "desire": "Encontrar una pista",
        },
        "clan": {"clanId": "clan_ventrue"},
        "generation": {"generationId": "generation_decimotercera", "bloodPotencyBase": 1},
        "sire": {"status": "unknown"},
        "predator": {
            "predatorId": "predator_gato_callejero",
            "selectedDisciplineId": "celeridad",
            "selectedSpecialty": {"skill": "Intimidación", "name": "Atracos"},
            "automaticAwardsApplied": True,
        },
        "attrSequence": ["Fuerza", "Resolución", "Destreza", "Resistencia", "Carisma"],
        "attributes": attributes,
        "skillSequence": [
            "Academicismo",
            "Armas de Fuego",
            "Artesanía",
            "Atletismo",
            "Callejeo",
            "Ciencias",
            "Conducir",
            "Consciencia",
            "Etiqueta",
            "Finanzas",
        ],
        "skills": skills,
        "freeSpecialtySkill": "Academicismo",
        "freeSpecialtyName": "Historia",
        "specialties": [{"skill": "Academicismo", "name": "Historia", "source": "free"}],
        "disciplines": {
            "ratings": {"celeridad": 1},
            "powers": [{"recordId": "celeridad_1_gatos_gracia", "disciplineId": "celeridad", "source": "creation"}],
        },
        "advantages": {
            "merits": [],
            "flaws": [],
            "budget": {
                "totalMeritDots": 7,
                "spentMeritDots": 0,
                "contributedToDomainDots": 0,
                "availableMeritDots": 7,
                "totalFlawDots": 0,
                "spentFlawDots": 0,
                "receivedFromDomainDots": 0,
            },
        },
        "domain": {
            "enabled": True,
            "pool": {
                "baseDots": 1,
                "contributedAdvantageDots": 0,
                "flawDots": 0,
                "grantedDots": 0,
                "spentDots": 0,
            },
            "traits": {"chasse": 0, "lien": 0, "portillon": 0},
            "merits": [],
            "flaws": [],
            "contributions": [],
            "backgrounds": [],
        },
        "convictions": [
            {
                "id": "conviction_001",
                "text": "Protege a quienes no pueden defenderse.",
                "touchstoneId": "touchstone_001",
            }
        ],
        "touchstones": [
            {
                "id": "touchstone_001",
                "name": "Lucía",
                "relationship": "Hermana",
                "description": "Recuerda al personaje su humanidad.",
                "linkedConvictionId": "conviction_001",
            }
        ],
        "profile": {
            "biography": "Biografía suficiente para exportar.",
            "appearance": "Apariencia suficiente para exportar.",
        },
        "derived": {
            "health": {"max": 6, "current": 6},
            "willpower": {"max": 3, "current": 3},
            "humanity": 7,
            "bloodPotency": 1,
            "budgets": {
                "advantages": {"availableMeritDots": 7},
                "domain": {"availableDots": 1},
            },
            "validation": {
                "valid": True,
                "errors": [],
                "warnings": [],
                "lastValidatedAt": "2026-04-28T00:00:00Z",
            },
        },
        "creationProgress": {
            "currentStep": "complete",
            "completedSteps": ["basics", "clan", "attributes", "skills", "export"],
            "uiOnly": True,
        },
    }


class CharacterStateSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / "schemas" / "character-state.schema.json").read_text(encoding="utf-8"))
        cls.creator = json.loads((ROOT / "data" / "creator-data.json").read_text(encoding="utf-8"))

    def test_schema_itself_is_valid_json_schema(self):
        jsonschema.Draft202012Validator.check_schema(self.schema)

    def test_schema_represents_complete_exportable_character(self):
        self.assertEqual(self.schema["properties"]["exportStatus"]["const"], "complete")
        self.assertEqual(self.schema["properties"]["creationStatus"]["const"], "finalized")
        self.assertIn("derived", self.schema["required"])
        self.assertIn("creationProgress", self.schema["required"])

    def test_major_choices_use_ids(self):
        self.assertIn("clanId", self.schema["properties"]["clan"]["required"])
        self.assertIn("generationId", self.schema["properties"]["generation"]["required"])
        self.assertIn("predatorId", self.schema["properties"]["predator"]["required"])
        self.assertNotIn("clanName", self.schema["properties"]["clan"]["properties"])
        self.assertNotIn("predatorName", self.schema["properties"]["predator"]["properties"])

    def test_narrative_fields_are_required_for_export(self):
        self.assertEqual(
            set(self.schema["properties"]["basics"]["required"]),
            {"name", "concept", "ambition", "desire"},
        )
        self.assertIn("convictions", self.schema["required"])
        self.assertIn("touchstones", self.schema["required"])
        self.assertEqual(
            set(self.schema["properties"]["profile"]["required"]),
            {"biography", "appearance"},
        )

    def test_domain_is_mandatory_and_has_base_dot(self):
        domain = self.schema["properties"]["domain"]
        self.assertIn("domain", self.schema["required"])
        self.assertEqual(domain["properties"]["enabled"]["const"], True)
        self.assertEqual(domain["properties"]["pool"]["properties"]["baseDots"]["minimum"], 1)

    def test_creator_data_exposes_state_id_catalogs(self):
        self.assertIn("clanCatalog", self.creator)
        self.assertIn("generationCatalog", self.creator)
        self.assertIn("characterStateModel", self.creator)
        self.assertTrue(self.creator["characterStateModel"]["usesIdsForMajorSelections"])
        self.assertTrue(all("id" in predator for predator in self.creator["predatorTypes"]))

    def test_complete_character_state_validates(self):
        jsonschema.validate(complete_character_state(), self.schema)

    def test_incomplete_character_state_cannot_validate_for_export(self):
        state = complete_character_state()
        del state["profile"]["biography"]
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(state, self.schema)

    def test_draft_character_state_cannot_validate_for_export(self):
        state = complete_character_state()
        state["exportStatus"] = "draft"
        state["creationStatus"] = "in_creation"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(state, self.schema)

    def test_derived_validation_storage_is_defined(self):
        derived = self.schema["properties"]["derived"]
        self.assertIn("validation", derived["required"])
        validation = derived["properties"]["validation"]
        self.assertEqual(set(validation["required"]), {"valid", "errors", "warnings"})


if __name__ == "__main__":
    unittest.main()
