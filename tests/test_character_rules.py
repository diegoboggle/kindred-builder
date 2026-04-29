import json, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class CharacterRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.creator = json.loads((ROOT / 'data' / 'creator-data.json').read_text(encoding='utf-8'))

    def test_base_catalog_sizes(self):
        self.assertEqual(len(self.creator['clans']), 7)
        self.assertEqual(len(self.creator['attributes']), 9)
        self.assertEqual(len(self.creator['skills']), 27)
        self.assertEqual(len(self.creator['predatorTypes']), 18)

    def test_ventrue_predator_restrictions_exist(self):
        forbidden = {p['name']: p for p in self.creator['predatorTypes'] if 'forbiddenClans' in p}
        self.assertIn('Bolsero', forbidden)
        self.assertIn('Granjero', forbidden)
        self.assertIn('Ventrue', forbidden['Bolsero']['forbiddenClans'])
        self.assertIn('Ventrue', forbidden['Granjero']['forbiddenClans'])

    def test_discord_id_pattern_documented(self):
        spec = (ROOT / 'docs' / 'creator-logic-spec.md').read_text(encoding='utf-8')
        self.assertIn('^[0-9]{17,20}$', spec)

    def test_no_legacy_discipline_powers_name_in_logic(self):
        spec = (ROOT / 'docs' / 'creator-logic-spec.md').read_text(encoding='utf-8')
        self.assertNotIn('DISCIPLINE_POWERS', spec)

if __name__ == '__main__':
    unittest.main()
