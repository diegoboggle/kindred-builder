import json, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from catalog_tools import catalog_record_checksum, generate_amalgam_index
from character_budget_tools import (
    advantage_available_merit_dots,
    domain_contribution_dots,
    domain_pool_available,
    domain_pool_spent,
    validate_budget_integrity,
)

class CatalogIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / 'data' / 'disciplinas_v5_catalogo.json').read_text(encoding='utf-8'))
        cls.creator = json.loads((ROOT / 'data' / 'creator-data.json').read_text(encoding='utf-8'))
        cls.index = json.loads((ROOT / 'derived' / 'amalgamas_v5_index_derivado.json').read_text(encoding='utf-8'))
        cls.aliases = json.loads((ROOT / 'data' / 'aliases.json').read_text(encoding='utf-8'))

    def test_catalog_counts(self):
        records = self.catalog['records']
        self.assertEqual(len(records), 402)
        by_kind = {kind: sum(1 for record in records if record['kind'] == kind) for kind in {r['kind'] for r in records}}
        self.assertEqual(by_kind['power'], 209)
        self.assertEqual(by_kind['ritual'], 105)
        self.assertEqual(by_kind['ceremony'], 28)
        self.assertEqual(by_kind['thin_blood_formula'], 60)

    def test_unique_record_ids(self):
        ids = [record['id'] for record in self.catalog['records']]
        self.assertEqual(len(ids), len(set(ids)))

    def test_localized_names_exist(self):
        for record in self.catalog['records']:
            self.assertTrue(record['name']['en'])
            self.assertTrue(record['name']['es'])


    def test_no_missing_display_name_translations(self):
        for record in self.catalog['records']:
            self.assertNotEqual(record.get('translationStatus'), 'missing', record['name']['en'])

    def test_sources_are_structured(self):
        for record in self.catalog['records']:
            self.assertIn('raw', record['source'])
            self.assertIn('items', record['source'])
            self.assertFalse(record['source']['raw'].startswith('/'))
            self.assertGreaterEqual(len(record['source']['items']), 1)

    def test_prerequisites_are_structured(self):
        for record in self.catalog['records']:
            prereq = record['prerequisite']
            self.assertIn(prereq['logic'], {'none', 'single', 'allOf', 'anyOf'})
            self.assertIn('conditions', prereq)

    def test_prerequisite_candidate_ids_exist(self):
        record_ids = {record['id'] for record in self.catalog['records']}

        def iter_conditions(node):
            if isinstance(node, dict):
                yield node
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        yield from iter_conditions(value)
            elif isinstance(node, list):
                for item in node:
                    yield from iter_conditions(item)

        for record in self.catalog['records']:
            for condition in iter_conditions(record['prerequisite']):
                for candidate_id in condition.get('candidateIds', []):
                    self.assertIn(
                        candidate_id,
                        record_ids,
                        f"{record['id']} references missing prerequisite candidateId {candidate_id}",
                    )

    def test_known_oblivion_prerequisite_aliases_are_resolved_by_id(self):
        expected = {
            "Oblivion's Sight": 'olvido_1_oblivion_sight',
            'Where the Shroud Thins': 'olvido_2_where_the_veil_thins',
        }

        def iter_conditions(node):
            if isinstance(node, dict):
                yield node
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        yield from iter_conditions(value)
            elif isinstance(node, list):
                for item in node:
                    yield from iter_conditions(item)

        for record in self.catalog['records']:
            for condition in iter_conditions(record['prerequisite']):
                raw = condition.get('raw')
                if raw in expected and 'type' in condition:
                    self.assertEqual(condition.get('type'), 'record')
                    self.assertIn(expected[raw], condition.get('candidateIds', []))

    def test_amalgam_index_is_generated_from_catalog(self):
        generated = generate_amalgam_index(self.catalog)
        self.assertEqual(self.index['entries'], generated)
        self.assertEqual(len(generated), 56)
        self.assertEqual(self.index['sourceCatalogChecksum']['value'], catalog_record_checksum(self.catalog))

    def test_amalgam_generator_imports_as_package_module(self):
        result = subprocess.run(
            [
                sys.executable,
                '-B',
                '-c',
                "import runpy; runpy.run_module('tools.generate_amalgama_index', run_name='not_main')",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_creator_predator_awards_are_structured(self):
        for predator in self.creator['predatorTypes']:
            self.assertIn('automaticAwards', predator)
            self.assertIn('pendingFlawChoice', predator)
            self.assertNotIn('grantedMerits', predator)
            self.assertNotIn('grantedFlaws', predator)
            self.assertNotIn('pendingFlaws', predator)
            for award in predator['automaticAwards']:
                self.assertIn(award['kind'], {'fixedTrait', 'choiceGroup', 'allocationGroup', 'domainGrant'})
                if award['kind'] == 'fixedTrait':
                    self.assertNotRegex(award['name'], r'/|reparte')


    def test_advantage_catalog_ids_are_unique(self):
        advantages = self.creator['advantagesCatalog']
        ids = [advantage['id'] for advantage in advantages]
        self.assertEqual(len(ids), len(set(ids)))
        for trait_id in ids:
            self.assertRegex(trait_id, r'^(merit|flaw)_[a-z0-9_]+$')

    def test_advantage_trait_references_exist(self):
        trait_ids = {advantage['id'] for advantage in self.creator['advantagesCatalog']}
        domain_ids = {trait['id'] for trait in self.creator.get('domainCatalog', [])}

        for advantage in self.creator['advantagesCatalog']:
            for requirement in advantage.get('requires', []):
                if requirement.get('type') == 'trait':
                    self.assertIn(
                        requirement.get('traitId'),
                        trait_ids,
                        f"{advantage['id']} requires missing traitId {requirement.get('traitId')}",
                    )
            for incompatible_id in advantage.get('incompatibleWith', []):
                self.assertIn(
                    incompatible_id,
                    trait_ids,
                    f"{advantage['id']} is incompatible with missing traitId {incompatible_id}",
                )

        def validate_award_node(node, inherited_type=None):
            if isinstance(node, dict):
                current_type = node.get('type') or inherited_type
                scope = node.get('scope', 'character')
                trait_id = node.get('traitId')

                if scope == 'character' and current_type in {'merit', 'flaw'} and trait_id:
                    self.assertIn(
                        trait_id,
                        trait_ids,
                        f"Predator award {node.get('name')} references missing character traitId {trait_id}",
                    )

                if scope == 'domain' and trait_id:
                    self.assertIn(
                        trait_id,
                        domain_ids,
                        f"Predator award {node.get('name')} references missing domain traitId {trait_id}",
                    )

                if current_type in {'merit', 'flaw'} and scope == 'character' and node.get('name') and not node.get('category') and node.get('kind') != 'allocationGroup':
                    self.assertIn(
                        trait_id,
                        trait_ids,
                        f"Predator award {node.get('name')} is missing a valid character traitId",
                    )

                for value in node.values():
                    if isinstance(value, (dict, list)):
                        validate_award_node(value, current_type)
            elif isinstance(node, list):
                for item in node:
                    validate_award_node(item, inherited_type)

        for predator in self.creator['predatorTypes']:
            validate_award_node(predator.get('automaticAwards', []))
            validate_award_node(predator.get('pendingFlawChoice'))


    def test_invalid_extracted_advantage_names_were_removed(self):
        serialized = json.dumps({
            'advantagesCatalog': self.creator['advantagesCatalog'],
            'predatorTypes': self.creator['predatorTypes'],
        }, ensure_ascii=False)
        self.assertNotIn('Rebaño migrante', serialized)
        self.assertNotIn('Refugio: Espeluznante', serialized)
        self.assertNotIn('Refugio: Embrujado', serialized)
        self.assertNotIn('Aspecto Bello', serialized)
        self.assertNotIn('Contactos criminales', serialized)

        advantage_names = {advantage['name'] for advantage in self.creator['advantagesCatalog']}
        self.assertNotIn('Dominio', advantage_names, 'Dominio must not be a character advantage')


    def test_haven_traits_have_structured_rules(self):
        by_id = {advantage['id']: advantage for advantage in self.creator['advantagesCatalog']}
        by_name = {advantage['name']: advantage for advantage in self.creator['advantagesCatalog']}

        self.assertEqual(by_name['Refugio']['id'], 'merit_refugio')
        self.assertEqual(by_name['Sin Refugio']['id'], 'flaw_refugio_sin_refugio')
        self.assertIn('flaw_refugio_sin_refugio', by_name['Refugio'].get('incompatibleWith', []))
        self.assertIn('merit_refugio', by_name['Sin Refugio'].get('incompatibleWith', []))

        for name in ['Espeluznante', 'Embrujado']:
            trait = by_name[name]
            self.assertTrue(
                any(req.get('type') == 'trait' and req.get('traitId') == 'merit_refugio' and req.get('minDots') == 1 for req in trait.get('requires', [])),
                f"{trait['id']} must require Haven/Refugio",
            )

        for name in ['Blindado', 'Alijo de Contrabandistas', 'Matrículas de Repuesto', 'Sobre Raíles', 'Temperamental']:
            trait = by_name[name]
            self.assertTrue(
                any(req.get('type') == 'trait' and req.get('traitId') == 'merit_refugio_movil' and req.get('minDots') == 1 for req in trait.get('requires', [])),
                f"{trait['id']} must require Mobile Haven",
            )

    def test_predator_haven_and_herd_awards_use_trait_ids(self):
        predators = {predator['name']: predator for predator in self.creator['predatorTypes']}

        road_killer = predators['Asesino de carretera']
        herd_award = next(award for award in road_killer['automaticAwards'] if award.get('traitId') == 'merit_rebano')
        self.assertEqual(herd_award['name'], 'Rebaño')
        self.assertEqual(herd_award['dots'], 2)

        trap_flaws = predators['Trampa']['pendingFlawChoice']['options']
        self.assertEqual({option['traitId'] for option in trap_flaws}, {'flaw_refugio_espeluznante', 'flaw_refugio_embrujado'})
        self.assertEqual({option['name'] for option in trap_flaws}, {'Espeluznante', 'Embrujado'})

    def test_structured_prerequisites_for_fame_merits(self):
        by_name = {advantage['name']: advantage for advantage in self.creator['advantagesCatalog']}

        self.assertTrue(
            any(req.get('type') == 'trait' and req.get('traitId') == 'merit_fama' and req.get('minDots') == 2 for req in by_name['Influencer'].get('requires', []))
        )
        self.assertTrue(
            any(req.get('type') == 'trait' and req.get('traitId') == 'merit_fama' and req.get('minDots') == 3 for req in by_name['Fama Duradera'].get('requires', []))
        )

    def test_domain_catalog_is_separate_from_character_advantages(self):
        domain_catalog = self.creator.get('domainCatalog', [])
        domain_ids = {trait['id'] for trait in domain_catalog}
        advantage_ids = {advantage['id'] for advantage in self.creator['advantagesCatalog']}

        self.assertIn('domain_dominio', domain_ids)
        self.assertIn('domain_chasse', domain_ids)
        self.assertIn('domain_lien', domain_ids)
        self.assertIn('domain_portillon', domain_ids)
        self.assertTrue(domain_ids.isdisjoint(advantage_ids))

        for trait in domain_catalog:
            self.assertEqual(trait['scope'], 'domain')
            self.assertEqual(trait['spendPool'], 'domain')
            self.assertRegex(trait['id'], r'^domain_[a-z0-9_]+$')
            self.assertTrue(set(trait['dotOptions']).issubset({1, 2, 3, 4, 5}))

    def test_incompatible_coterie_content_is_disabled_by_chronicle_style(self):
        disabled = self.creator.get('disabledCoterieContent', [])
        self.assertGreaterEqual(len(disabled), 1)

        disabled_ids = {entry['id'] for entry in disabled}
        self.assertIn('disabled_coterie_types', disabled_ids)
        self.assertIn('disabled_coterie_advantages', disabled_ids)
        self.assertIn('disabled_coterie_clan_merits', disabled_ids)

        for entry in disabled:
            self.assertEqual(entry['status'], 'disabled')
            self.assertIn('Inviable con el estilo de la crónica', entry['disabledReason'])

    def test_tithe_collector_offers_status_or_personal_domain(self):
        predators = {predator['name']: predator for predator in self.creator['predatorTypes']}
        tithe_collector = predators['Recaudador de diezmos']

        awards = tithe_collector['automaticAwards']
        self.assertEqual(awards[0]['kind'], 'allocationGroup')
        self.assertEqual(awards[0]['scope'], 'mixed')
        self.assertEqual(awards[0]['totalDots'], 3)
        self.assertEqual(awards[0]['allocationMode'], 'chooseOne')

        options_by_scope = {option['scope']: option for option in awards[0]['options']}
        self.assertEqual(options_by_scope['character']['traitId'], 'merit_estatus')
        self.assertEqual(options_by_scope['character']['dots'], 3)
        self.assertEqual(options_by_scope['domain']['traitId'], 'domain_dominio')
        self.assertEqual(options_by_scope['domain']['dots'], 3)
        self.assertEqual(options_by_scope['domain']['target'], 'character.domain.pool.grantedDots')

        self.assertEqual(awards[1], {
            'kind': 'fixedTrait',
            'type': 'flaw',
            'scope': 'character',
            'name': 'Adversario',
            'dots': 2,
            'traitId': 'flaw_mawla_adversario',
        })

    def test_character_state_schema_requires_personal_domain(self):
        schema = json.loads((ROOT / 'schemas' / 'character-state.schema.json').read_text(encoding='utf-8'))
        self.assertIn('domain', schema['required'])
        domain = schema['properties']['domain']
        self.assertIn('pool', domain['required'])
        self.assertIn('traits', domain['required'])
        self.assertIn('chasse', domain['properties']['traits']['required'])
        self.assertIn('lien', domain['properties']['traits']['required'])
        self.assertIn('portillon', domain['properties']['traits']['required'])



    def test_domain_catalog_includes_adapted_backgrounds(self):
        advantage_ids = {advantage['id'] for advantage in self.creator['advantagesCatalog']}
        by_id = {trait['id']: trait for trait in self.creator['domainCatalog']}

        expected = {
            'domain_background_rebano': 'merit_rebano',
            'domain_background_refugio': 'merit_refugio',
            'domain_background_influencia': 'merit_influencia',
            'domain_background_recursos': 'merit_recursos',
            'domain_background_criados': 'merit_criados',
            'domain_background_contactos': 'merit_contactos',
            'domain_background_aliados': 'merit_aliados',
            'domain_background_mawla': 'merit_mawla',
            'domain_background_estatus': 'merit_estatus',
        }

        for domain_trait_id, source_trait_id in expected.items():
            self.assertIn(domain_trait_id, by_id)
            trait = by_id[domain_trait_id]
            self.assertEqual(trait['scope'], 'domain')
            self.assertEqual(trait['type'], 'domainBackground')
            self.assertEqual(trait['spendPool'], 'domain')
            self.assertEqual(trait['purchaseScope'], 'domain')
            self.assertEqual(trait['sourceTraitId'], source_trait_id)
            self.assertIn(source_trait_id, advantage_ids)
            self.assertEqual(trait['storeIn'], 'character.domain.backgrounds')
            self.assertEqual(trait['notStoredIn'], 'character.advantages.merits')

    def test_domain_background_flaws_feed_domain_pool_not_individual_flaws(self):
        by_id = {trait['id']: trait for trait in self.creator['domainCatalog']}
        expected_flaws = {
            'domain_background_flaw_rebano_depredador_manifiesto': 'flaw_rebano_depredador_manifiesto',
            'domain_background_flaw_refugio_espeluznante': 'flaw_refugio_espeluznante',
            'domain_background_flaw_mawla_adversario': 'flaw_mawla_adversario',
            'domain_background_flaw_criados_acosadores': 'flaw_criados_acosadores',
        }

        for domain_trait_id, source_trait_id in expected_flaws.items():
            self.assertIn(domain_trait_id, by_id)
            trait = by_id[domain_trait_id]
            self.assertEqual(trait['type'], 'domainBackgroundFlaw')
            self.assertEqual(trait['sourceTraitId'], source_trait_id)
            self.assertEqual(trait['addsToPool'], 'character.domain.pool.flawDots')
            self.assertEqual(trait['storeIn'], 'character.domain.flaws')
            self.assertEqual(trait['notStoredIn'], 'character.advantages.flaws')

    def test_character_state_schema_tracks_domain_contributions_and_advantage_budget(self):
        schema = json.loads((ROOT / 'schemas' / 'character-state.schema.json').read_text(encoding='utf-8'))
        advantages = schema['properties']['advantages']
        self.assertIn('budget', advantages['required'])
        budget = advantages['properties']['budget']
        self.assertIn('contributedToDomainDots', budget['required'])
        self.assertIn('availableMeritDots', budget['required'])

        domain = schema['properties']['domain']
        self.assertIn('contributions', domain['required'])
        self.assertIn('backgrounds', domain['required'])
        contribution = domain['properties']['contributions']['items']
        self.assertEqual(contribution['properties']['source']['const'], 'characterAdvantages')
        self.assertEqual(contribution['properties']['sourceBudget']['const'], 'advantages.meritDots')
        background = domain['properties']['backgrounds']['items']
        self.assertEqual(background['properties']['purchaseScope']['const'], 'domain')

    def test_individual_advantage_budget_subtracts_domain_contributions(self):
        state = {
            'advantages': {
                'merits': [{'traitId': 'merit_fama', 'dots': 3}],
                'flaws': [],
                'budget': {
                    'totalMeritDots': 7,
                    'spentMeritDots': 3,
                    'contributedToDomainDots': 2,
                    'availableMeritDots': 2,
                },
            },
            'domain': {
                'pool': {
                    'baseDots': 1,
                    'contributedAdvantageDots': 2,
                    'flawDots': 0,
                    'grantedDots': 0,
                    'spentDots': 0,
                },
                'contributions': [
                    {
                        'id': 'domain_contribution_initial_01',
                        'source': 'characterAdvantages',
                        'sourceBudget': 'advantages.meritDots',
                        'dots': 2,
                        'reason': 'Aporte voluntario a Dominio personal',
                    }
                ],
                'traits': {'chasse': 0, 'lien': 0, 'portillon': 0},
                'backgrounds': [],
                'merits': [],
                'flaws': [],
            },
        }

        self.assertEqual(domain_contribution_dots(state), 2)
        self.assertEqual(advantage_available_merit_dots(state), 2)
        self.assertEqual(validate_budget_integrity(state), [])

    def test_domain_pool_spends_on_adapted_backgrounds_without_double_counting(self):
        state = {
            'advantages': {
                'merits': [{'traitId': 'merit_fama', 'dots': 1}],
                'flaws': [],
                'budget': {
                    'totalMeritDots': 7,
                    'spentMeritDots': 1,
                    'contributedToDomainDots': 2,
                    'availableMeritDots': 4,
                },
            },
            'domain': {
                'pool': {
                    'baseDots': 1,
                    'contributedAdvantageDots': 2,
                    'flawDots': 0,
                    'grantedDots': 3,
                    'spentDots': 6,
                },
                'contributions': [
                    {
                        'id': 'domain_contribution_initial_01',
                        'source': 'characterAdvantages',
                        'sourceBudget': 'advantages.meritDots',
                        'dots': 2,
                        'reason': 'Aporte voluntario a Dominio personal',
                    }
                ],
                'traits': {'chasse': 2, 'lien': 1, 'portillon': 0},
                'backgrounds': [
                    {
                        'domainTraitId': 'domain_background_rebano',
                        'sourceTraitId': 'merit_rebano',
                        'dots': 2,
                        'purchaseScope': 'domain',
                    },
                    {
                        'domainTraitId': 'domain_background_refugio',
                        'sourceTraitId': 'merit_refugio',
                        'dots': 1,
                        'purchaseScope': 'domain',
                    },
                ],
                'merits': [],
                'flaws': [],
            },
        }

        self.assertEqual(domain_pool_available(state), 6)
        self.assertEqual(domain_pool_spent(state), 6)
        self.assertEqual(advantage_available_merit_dots(state), 4)
        self.assertEqual(validate_budget_integrity(state), [])

    def test_double_spent_advantage_points_are_detected(self):
        state = {
            'advantages': {
                'merits': [{'traitId': 'merit_fama', 'dots': 6}],
                'flaws': [],
                'budget': {
                    'totalMeritDots': 7,
                    'spentMeritDots': 6,
                    'contributedToDomainDots': 2,
                    'availableMeritDots': 0,
                },
            },
            'domain': {
                'pool': {
                    'baseDots': 1,
                    'contributedAdvantageDots': 2,
                    'flawDots': 0,
                    'grantedDots': 0,
                    'spentDots': 0,
                },
                'contributions': [
                    {
                        'id': 'domain_contribution_initial_01',
                        'source': 'characterAdvantages',
                        'sourceBudget': 'advantages.meritDots',
                        'dots': 2,
                        'reason': 'Aporte voluntario a Dominio personal',
                    }
                ],
                'traits': {'chasse': 0, 'lien': 0, 'portillon': 0},
                'backgrounds': [],
                'merits': [],
                'flaws': [],
            },
        }

        errors = validate_budget_integrity(state)
        self.assertIn('advantages.budget.availableMeritDots must equal totalMeritDots - spentMeritDots - contributedToDomainDots', errors)
        self.assertIn('individual merit budget is overspent after Domain contributions', errors)


    def test_predator_fixed_trait_dots_match_advantage_catalog_dot_options(self):
        by_id = {advantage['id']: advantage for advantage in self.creator['advantagesCatalog']}
        errors = []

        def validate_node(node, predator_name):
            if isinstance(node, dict):
                scope = node.get('scope', 'character')
                trait_id = node.get('traitId')
                dots = node.get('dots')
                if scope == 'character' and trait_id in by_id and isinstance(dots, int):
                    allowed = by_id[trait_id].get('dotOptions', [])
                    if allowed and dots not in allowed:
                        errors.append(
                            f"{predator_name}: {node.get('name')} uses {dots} dots for {trait_id}, allowed {allowed}"
                        )
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        validate_node(value, predator_name)
            elif isinstance(node, list):
                for item in node:
                    validate_node(item, predator_name)

        for predator in self.creator['predatorTypes']:
            validate_node(predator.get('automaticAwards', []), predator['name'])
            validate_node(predator.get('pendingFlawChoice'), predator['name'])

        self.assertEqual(errors, [])

    def test_blood_leech_prey_exclusion_is_one_dot_with_mortals_as_detail(self):
        predators = {predator['name']: predator for predator in self.creator['predatorTypes']}
        blood_leech = predators['Sanguijuela de la Sangre']
        prey_exclusion = next(
            award for award in blood_leech['automaticAwards']
            if award.get('traitId') == 'flaw_alimentacion_exclusion_de_presa'
        )

        self.assertEqual(prey_exclusion['name'], 'Exclusión de Presa')
        self.assertEqual(prey_exclusion['dots'], 1)
        self.assertEqual(prey_exclusion['detailDefault'], 'mortales')

    def test_predator_prey_exclusion_variants_are_details_not_distinct_trait_names(self):
        for predator in self.creator['predatorTypes']:
            def iter_nodes(node):
                if isinstance(node, dict):
                    yield node
                    for value in node.values():
                        if isinstance(value, (dict, list)):
                            yield from iter_nodes(value)
                elif isinstance(node, list):
                    for item in node:
                        yield from iter_nodes(item)

            for node in iter_nodes(predator):
                if node.get('traitId') == 'flaw_alimentacion_exclusion_de_presa':
                    self.assertEqual(node.get('name'), 'Exclusión de Presa')
                    self.assertEqual(node.get('dots'), 1)
                    self.assertIn('detailDefault', node)

    def test_allies_maximum_is_normalized_to_five(self):
        by_id = {advantage['id']: advantage for advantage in self.creator['advantagesCatalog']}
        self.assertEqual(by_id['merit_aliados']['dotOptions'], [2, 3, 4, 5])


    def test_predator_award_names_match_canonical_traits(self):
        by_id = {advantage['id']: advantage for advantage in self.creator['advantagesCatalog']}

        def iter_award_nodes(node):
            if isinstance(node, dict):
                yield node
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        yield from iter_award_nodes(value)
            elif isinstance(node, list):
                for item in node:
                    yield from iter_award_nodes(item)

        for predator in self.creator['predatorTypes']:
            for node in iter_award_nodes({
                'automaticAwards': predator.get('automaticAwards', []),
                'pendingFlawChoice': predator.get('pendingFlawChoice'),
            }):
                trait_id = node.get('traitId')
                if node.get('scope', 'character') == 'character' and trait_id in by_id and node.get('name'):
                    self.assertEqual(
                        node['name'],
                        by_id[trait_id]['name'],
                        f"{predator['name']} uses non-canonical award name {node['name']!r} for {trait_id}",
                    )
                    self.assertEqual(
                        node.get('type', by_id[trait_id]['type']),
                        by_id[trait_id]['type'],
                        f"{predator['name']} uses wrong award type for {trait_id}",
                    )

    def test_predator_detail_requiring_awards_are_explicit(self):
        by_id = {advantage['id']: advantage for advantage in self.creator['advantagesCatalog']}

        def iter_award_nodes(node):
            if isinstance(node, dict):
                yield node
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        yield from iter_award_nodes(value)
            elif isinstance(node, list):
                for item in node:
                    yield from iter_award_nodes(item)

        for predator in self.creator['predatorTypes']:
            for node in iter_award_nodes({
                'automaticAwards': predator.get('automaticAwards', []),
                'pendingFlawChoice': predator.get('pendingFlawChoice'),
            }):
                trait_id = node.get('traitId')
                if node.get('scope', 'character') != 'character' or trait_id not in by_id:
                    continue

                if by_id[trait_id].get('requiresDetail'):
                    detail_default = node.get('detailDefault')
                    detail_required = node.get('detailRequired')
                    self.assertTrue(
                        isinstance(detail_default, str) and detail_default.strip() or detail_required is True,
                        f"{predator['name']} references detail-requiring trait {trait_id} without detailDefault or detailRequired",
                    )

    def test_predator_award_options_are_not_bare_categories(self):
        def iter_award_nodes(node):
            if isinstance(node, dict):
                yield node
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        yield from iter_award_nodes(value)
            elif isinstance(node, list):
                for item in node:
                    yield from iter_award_nodes(item)

        for predator in self.creator['predatorTypes']:
            for node in iter_award_nodes({
                'automaticAwards': predator.get('automaticAwards', []),
                'pendingFlawChoice': predator.get('pendingFlawChoice'),
            }):
                is_selection_filter_object = (
                    set(node.keys()).issubset({'scope', 'type', 'category'})
                    and {'scope', 'type', 'category'}.issubset(node.keys())
                )
                self.assertFalse(
                    'category' in node and 'traitId' not in node and 'selectionFilter' not in node and not is_selection_filter_object,
                    f"{predator['name']} contains a bare category option: {node}",
                )

    def test_predator_selection_filters_are_structured_and_resolvable(self):
        advantages = self.creator['advantagesCatalog']
        domain_traits = self.creator.get('domainCatalog', [])

        def iter_group_options(node, parent=None):
            if isinstance(node, dict):
                if isinstance(node.get('options'), list):
                    for option in node['options']:
                        yield option, node
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        yield from iter_group_options(value, node)
            elif isinstance(node, list):
                for item in node:
                    yield from iter_group_options(item, parent)

        for predator in self.creator['predatorTypes']:
            for option, parent in iter_group_options({
                'automaticAwards': predator.get('automaticAwards', []),
                'pendingFlawChoice': predator.get('pendingFlawChoice'),
            }):
                if 'selectionFilter' not in option:
                    continue

                selection_filter = option['selectionFilter']
                self.assertIn(selection_filter.get('scope'), {'character', 'domain'})
                self.assertIn('type', selection_filter)
                self.assertIn('category', selection_filter)

                if selection_filter['scope'] == 'character':
                    matches = [
                        trait for trait in advantages
                        if trait.get('type') == selection_filter['type']
                        and trait.get('category') == selection_filter['category']
                    ]
                else:
                    matches = [
                        trait for trait in domain_traits
                        if trait.get('type') == selection_filter['type']
                        and trait.get('category') == selection_filter['category']
                    ]

                self.assertGreaterEqual(
                    len(matches),
                    1,
                    f"{predator['name']} has unresolved selectionFilter {selection_filter}",
                )

                total_dots = parent.get('totalDots')
                if isinstance(total_dots, int):
                    self.assertTrue(
                        any(total_dots in trait.get('dotOptions', []) for trait in matches),
                        f"{predator['name']} selectionFilter {selection_filter} cannot satisfy {total_dots} dots",
                    )

    def test_predator_group_awards_have_complete_option_shapes(self):
        def iter_groups(node):
            if isinstance(node, dict):
                if node.get('kind') in {'choiceGroup', 'allocationGroup'}:
                    yield node
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        yield from iter_groups(value)
            elif isinstance(node, list):
                for item in node:
                    yield from iter_groups(item)

        for predator in self.creator['predatorTypes']:
            for group in iter_groups({
                'automaticAwards': predator.get('automaticAwards', []),
                'pendingFlawChoice': predator.get('pendingFlawChoice'),
            }):
                self.assertIsInstance(group.get('options'), list, f"{predator['name']} group has no options")
                self.assertGreaterEqual(len(group['options']), 1, f"{predator['name']} group has empty options")

                if group['kind'] == 'allocationGroup':
                    self.assertIsInstance(group.get('totalDots'), int)
                    self.assertIn(group.get('allocationMode'), {'chooseOne', 'splitBetweenOptions'})
                if group['kind'] == 'choiceGroup' and 'totalDots' in group:
                    self.assertIn(group.get('allocationMode'), {'chooseOne', 'splitBetweenOptions'})

                for option in group['options']:
                    self.assertTrue(
                        option.get('traitId') or option.get('selectionFilter'),
                        f"{predator['name']} option is neither traitId nor selectionFilter: {option}",
                    )

    def test_alias_registry_file_exists_and_has_schema(self):
        self.assertEqual(self.aliases['schemaVersion'], 'alias-registry-v1')
        self.assertTrue(self.aliases['policy']['canonicalReferencesUseIds'])
        self.assertTrue(self.aliases['policy']['aliasesAreNotCanonicalData'])
        schema = json.loads((ROOT / 'schemas' / 'aliases.schema.json').read_text(encoding='utf-8'))
        self.assertEqual(schema['properties']['schemaVersion']['const'], 'alias-registry-v1')

    def test_alias_registry_targets_exist(self):
        record_ids = {record['id'] for record in self.catalog['records']}
        advantage_ids = {advantage['id'] for advantage in self.creator['advantagesCatalog']}
        domain_ids = {trait['id'] for trait in self.creator['domainCatalog']}

        for alias in self.aliases['disciplineRecordAliases']:
            self.assertEqual(alias['scope'], 'disciplineRecord')
            self.assertIn(alias['canonicalId'], record_ids)

        for alias in self.aliases['advantageTraitAliases']:
            self.assertEqual(alias['scope'], 'advantageTrait')
            self.assertIn(alias['canonicalId'], advantage_ids)

        for alias in self.aliases['domainTraitAliases']:
            self.assertEqual(alias['scope'], 'domainTrait')
            self.assertIn(alias['canonicalId'], domain_ids)

    def test_prerequisite_raw_name_mismatches_are_registered_as_aliases(self):
        registered = {
            (alias['raw'], alias['canonicalId'])
            for alias in self.aliases['disciplineRecordAliases']
            if alias['status'] == 'active'
        }

        def iter_conditions(node):
            if isinstance(node, dict):
                if 'candidateIds' in node:
                    yield node
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        yield from iter_conditions(value)
            elif isinstance(node, list):
                for item in node:
                    yield from iter_conditions(item)

        for record in self.catalog['records']:
            for condition in iter_conditions(record['prerequisite']):
                raw = condition.get('raw')
                name = condition.get('name')
                if raw and name and raw != name:
                    for candidate_id in condition.get('candidateIds', []):
                        self.assertIn(
                            (raw, candidate_id),
                            registered,
                            f"{record['id']} uses unregistered alias {raw!r} -> {candidate_id!r}",
                        )

    def test_rejected_aliases_do_not_resolve_as_active_advantages(self):
        active_advantage_aliases = {
            alias['raw']
            for alias in self.aliases['advantageTraitAliases']
            if alias['status'] == 'active'
        }
        rejected = {
            alias['raw']
            for alias in self.aliases['rejectedAliases']
            if alias['scope'] == 'advantageTrait'
        }
        self.assertIn('Rebaño migrante', rejected)
        self.assertNotIn('Rebaño migrante', active_advantage_aliases)

    def test_domain_alias_is_not_registered_as_individual_advantage_alias(self):
        domain_aliases = {
            alias['raw']: alias['canonicalId']
            for alias in self.aliases['domainTraitAliases']
        }
        active_advantage_aliases = {
            alias['raw']
            for alias in self.aliases['advantageTraitAliases']
            if alias['status'] == 'active'
        }
        self.assertEqual(domain_aliases['Dominio'], 'domain_dominio')
        self.assertNotIn('Dominio', active_advantage_aliases)


    def test_json_is_authoritative_for_disciplines(self):
        self.assertTrue(self.catalog['policy']['jsonIsAuthoritative'])
        self.assertFalse(self.catalog['policy']['otherAmalgamsImported'])
        self.assertTrue(self.creator['disciplineCatalog']['authoritative'])

if __name__ == '__main__':
    unittest.main()
