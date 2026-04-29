import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def iter_prerequisite_leaf_conditions(node):
    """Yield typed prerequisite leaf conditions from a prerequisite tree."""
    if isinstance(node, dict):
        if 'type' in node:
            yield node
        for value in node.values():
            if isinstance(value, (dict, list)):
                yield from iter_prerequisite_leaf_conditions(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_prerequisite_leaf_conditions(item)


class DisciplinePrerequisiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / 'data' / 'disciplinas_v5_catalogo.json').read_text(encoding='utf-8'))
        cls.index = json.loads((ROOT / 'derived' / 'amalgamas_v5_index_derivado.json').read_text(encoding='utf-8'))
        cls.aliases = json.loads((ROOT / 'data' / 'aliases.json').read_text(encoding='utf-8'))
        cls.records = cls.catalog['records']
        cls.records_by_id = {record['id']: record for record in cls.records}
        cls.record_ids = set(cls.records_by_id)

    def test_prerequisite_logic_shapes_are_consistent(self):
        for record in self.records:
            prerequisite = record['prerequisite']
            logic = prerequisite['logic']
            conditions = prerequisite['conditions']

            if logic == 'none':
                self.assertEqual(
                    conditions,
                    [],
                    f"{record['id']} has logic none but non-empty prerequisite conditions",
                )
            elif logic == 'single':
                self.assertEqual(
                    len(conditions),
                    1,
                    f"{record['id']} has logic single but not exactly one condition",
                )
            elif logic in {'allOf', 'anyOf'}:
                self.assertGreaterEqual(
                    len(conditions),
                    2,
                    f"{record['id']} has logic {logic} but fewer than two conditions",
                )
            else:
                self.fail(f"{record['id']} has unsupported prerequisite logic {logic!r}")

    def test_no_unresolved_or_free_text_prerequisite_leaf_conditions(self):
        allowed_types = {'record', 'clan'}
        for record in self.records:
            for condition in iter_prerequisite_leaf_conditions(record['prerequisite']):
                self.assertIn(
                    condition['type'],
                    allowed_types,
                    f"{record['id']} has unsupported or unresolved prerequisite condition {condition}",
                )
                self.assertNotEqual(
                    condition['type'],
                    'unresolved',
                    f"{record['id']} still has unresolved prerequisite condition {condition}",
                )

    def test_record_prerequisites_have_canonical_candidate_ids(self):
        for record in self.records:
            for condition in iter_prerequisite_leaf_conditions(record['prerequisite']):
                if condition['type'] != 'record':
                    continue

                self.assertTrue(condition.get('raw'), f"{record['id']} record prerequisite lacks raw text")
                self.assertTrue(condition.get('name'), f"{record['id']} record prerequisite lacks canonical English name")
                self.assertTrue(condition.get('nameEs'), f"{record['id']} record prerequisite lacks canonical Spanish name")
                self.assertTrue(condition.get('candidateIds'), f"{record['id']} record prerequisite lacks candidateIds")
                self.assertEqual(
                    len(condition['candidateIds']),
                    len(set(condition['candidateIds'])),
                    f"{record['id']} has duplicated prerequisite candidateIds in {condition}",
                )

                for candidate_id in condition['candidateIds']:
                    self.assertIn(
                        candidate_id,
                        self.record_ids,
                        f"{record['id']} references missing prerequisite candidateId {candidate_id}",
                    )
                    self.assertNotEqual(
                        candidate_id,
                        record['id'],
                        f"{record['id']} cannot require itself as a prerequisite",
                    )

    def test_record_prerequisite_candidates_are_powers(self):
        for record in self.records:
            for condition in iter_prerequisite_leaf_conditions(record['prerequisite']):
                if condition['type'] != 'record':
                    continue
                for candidate_id in condition['candidateIds']:
                    candidate = self.records_by_id[candidate_id]
                    self.assertEqual(
                        candidate['kind'],
                        'power',
                        f"{record['id']} prerequisite candidate {candidate_id} must resolve to a power, not {candidate['kind']}",
                    )

    def test_clan_prerequisites_are_structured(self):
        clan_conditions = []
        for record in self.records:
            for condition in iter_prerequisite_leaf_conditions(record['prerequisite']):
                if condition['type'] == 'clan':
                    clan_conditions.append((record, condition))

        self.assertEqual(len(clan_conditions), 1)
        record, condition = clan_conditions[0]
        self.assertEqual(record['id'], 'hechiceria_de_sangre_1_koldunic_sorcery')
        self.assertEqual(condition['clan'], 'Tzimisce')
        self.assertEqual(condition['raw'], 'Tzimisce')

    def test_alias_resolved_prerequisites_are_registered(self):
        registered_aliases = {
            (alias['raw'], alias['canonicalId'])
            for alias in self.aliases['disciplineRecordAliases']
            if alias['status'] == 'active'
        }

        alias_resolved_conditions = []
        for record in self.records:
            for condition in iter_prerequisite_leaf_conditions(record['prerequisite']):
                if condition['type'] != 'record':
                    continue
                if condition.get('raw') and condition.get('name') and condition['raw'] != condition['name']:
                    alias_resolved_conditions.append((record, condition))
                    for candidate_id in condition['candidateIds']:
                        self.assertIn(
                            (condition['raw'], candidate_id),
                            registered_aliases,
                            f"{record['id']} uses unregistered prerequisite alias {condition['raw']!r} -> {candidate_id!r}",
                        )

        self.assertGreaterEqual(len(alias_resolved_conditions), 2)

    def test_known_oblivion_aliases_remain_resolved_to_expected_ids(self):
        expected = {
            "Oblivion's Sight": 'olvido_1_oblivion_sight',
            'Where the Shroud Thins': 'olvido_2_where_the_veil_thins',
        }
        found = set()

        for record in self.records:
            for condition in iter_prerequisite_leaf_conditions(record['prerequisite']):
                raw = condition.get('raw')
                if raw in expected:
                    self.assertEqual(condition['type'], 'record')
                    self.assertIn(expected[raw], condition['candidateIds'])
                    found.add(raw)

        self.assertEqual(found, set(expected))

    def test_amalgam_requirements_are_valid_discipline_level_pairs(self):
        known_disciplines = {record['discipline'] for record in self.records if record.get('discipline')}
        for record in self.records:
            requirement = record.get('amalgamRequirement')
            if requirement is None:
                continue

            self.assertIn(
                requirement['discipline'],
                known_disciplines,
                f"{record['id']} has unknown amalgam discipline {requirement['discipline']!r}",
            )
            self.assertIsInstance(requirement['level'], int)
            self.assertGreaterEqual(requirement['level'], 1)
            self.assertLessEqual(requirement['level'], 5)
            self.assertTrue(requirement.get('raw'), f"{record['id']} amalgam requirement lacks raw source text")

    def test_amalgam_index_contains_no_stale_or_missing_entries(self):
        expected_record_ids = {
            record['id'] for record in self.records if record.get('amalgamRequirement') is not None
        }
        indexed_record_ids = {entry['recordId'] for entry in self.index['entries']}

        self.assertEqual(indexed_record_ids, expected_record_ids)

        for entry in self.index['entries']:
            record = self.records_by_id[entry['recordId']]
            requirement = record['amalgamRequirement']
            self.assertEqual(entry['requiredDiscipline'], requirement['discipline'])
            self.assertEqual(entry['requiredLevel'], requirement['level'])
            self.assertEqual(entry['recordKind'], record['kind'])
            self.assertEqual(entry['recordDiscipline'], record['discipline'])
            self.assertEqual(entry['recordLevel'], record['level'])
            self.assertEqual(entry['recordName'], record['name'])

    def test_amalgam_requirements_are_only_on_powers(self):
        for record in self.records:
            if record.get('amalgamRequirement') is not None:
                self.assertEqual(
                    record['kind'],
                    'power',
                    f"{record['id']} has an amalgam requirement but is not a discipline power",
                )


if __name__ == '__main__':
    unittest.main()
