import time
import unittest

import server
from whiskerbay.data import (
    BAITS, BIOMES, BOSSES, ENCHANTS, FI, ISLAND_QUEST, PETS, PET_LEVEL_MIN, PET_MAX,
    QI, RAR, ROD_SKILL, RODS, SKILLS, generateCaves,
)


class Peer:
    def __init__(self, ident, name, biome):
        self.id = ident
        self.name = name
        self.acc = None
        self.state = {'b': biome, 'm': 'bite', 'boss': True, 'hx': 0.5, 'hd': 0}
        self.boss_search_times = []
        self.shared_claim_times = []
        self.st_times = []
        self.population_chunk = None
        self.sent = []

    def send(self, message):
        self.sent.append(message)

    def close(self):
        pass


class SharedWorldTests(unittest.TestCase):
    def make_server(self, biome='trench'):
        instance = server.Server.__new__(server.Server)
        instance.clients = set()
        instance.by_name = {}
        instance.shared_population = {}
        instance.shared_fish = {}
        instance.shared_respawn = {}
        instance.shared_bosses = {}
        instance.shared_boss_targets = {}
        instance.shared_boss_respawn = {}
        instance.limited_remaining = {}
        instance.caves = generateCaves(1234)
        instance.players = lambda: list(instance.clients)
        instance.broadcast = lambda *args, **kwargs: None
        instance.sys = lambda *args, **kwargs: None
        first = Peer('first', 'AnglerOne', biome)
        second = Peer('second', 'AnglerTwo', biome)
        instance.clients.update((first, second))
        instance.by_name = {peer.name.lower(): peer for peer in (first, second)}
        return instance, first, second

    def test_cave_layouts_are_seeded_and_connected(self):
        first = generateCaves(101)
        same = generateCaves(101)
        other = generateCaves(202)
        self.assertEqual(set(first), set(same))
        for biome, cave in first.items():
            self.assertEqual(len(cave.rooms), len(cave.corridors))
            self.assertEqual(
                [(room.x, room.d) for room in cave.rooms],
                [(room.x, room.d) for room in same[biome].rooms],
            )
            self.assertNotEqual(
                [(room.x, room.d) for room in cave.rooms],
                [(room.x, room.d) for room in other[biome].rooms],
            )

    def test_cave_population_fish_stays_inside_its_generated_room(self):
        instance, _, _ = self.make_server('trench')
        original_choices = server.random.choices
        server.random.choices = lambda population, weights, k: [
            next(fish for fish in population if fish.id == 'lanternlurker')
        ]
        try:
            fish = instance._new_population_fish('trench', 5)
        finally:
            server.random.choices = original_choices

        self.assertIsNotNone(fish)
        room = instance.caves['trench'].rooms[fish['room']]
        self.assertGreaterEqual(fish['x'], room.x[0])
        self.assertLessEqual(fish['x'], room.x[1])
        self.assertGreaterEqual(fish['d'], room.d[0])
        self.assertLessEqual(fish['d'], room.d[1])
        for elapsed in range(0, 3600, 7):
            x, depth = instance.population_position(fish, fish['born'] + elapsed)
            self.assertGreaterEqual(x, room.x[0])
            self.assertLessEqual(x, room.x[1])
            self.assertGreaterEqual(depth, room.d[0])
            self.assertLessEqual(depth, room.d[1])

    def test_progression_and_fishing_catalog_links_resolve(self):
        rod_ids = {rod.id for rod in RODS}
        self.assertTrue(set(ISLAND_QUEST).issubset(BIOMES))
        self.assertTrue(all(biome.quest is None or biome.quest in QI for biome in BIOMES.values()))
        self.assertTrue(all(rod in rod_ids and skill in SKILLS for rod, skill in ROD_SKILL.items()))
        self.assertTrue(all(rod.at in BIOMES and 0 < rod.depth <= BIOMES[rod.at].depth for rod in RODS))
        self.assertTrue(all(bait.at is None or bait.at in BIOMES for bait in BAITS))
        self.assertTrue(all(enchant.w > 0 for enchant in ENCHANTS))
        self.assertAlmostEqual(sum(rarity.w for rarity in RAR), 100.0)
        self.assertEqual([rarity.diff for rarity in RAR], sorted(rarity.diff for rarity in RAR))
        self.assertEqual(len(PET_LEVEL_MIN), PET_MAX)
        self.assertTrue(PETS)
        for quest in QI.values():
            for goal in quest.goals:
                self.assertTrue(goal.get('sp') is None or goal.sp in FI, quest.id)

    def test_shared_population_claim_is_first_wins(self):
        instance, first, second = self.make_server('shore')
        fish = instance._new_population_fish('shore', 0)
        fish['chunk'] = 0
        instance.shared_population['shore'] = {fish['id']: fish}
        x, depth = instance.population_position(fish)
        for peer in (first, second):
            peer.state.update(hx=x, hd=depth)

        instance.on_shared_claim(first, {'b': 'shore', 'id': fish['id']})
        instance.on_shared_claim(second, {'b': 'shore', 'id': fish['id']})

        self.assertEqual(fish['owner'], first.id)
        self.assertTrue(first.sent[-1]['ok'])
        self.assertFalse(second.sent[-1]['ok'])

    def test_boss_target_is_shared_and_released_after_fight(self):
        instance, first, second = self.make_server()
        first.state['m'] = 'idle'
        instance.on_boss_search(first, {'b': 'trench'})
        target = instance.shared_boss_targets['trench']
        self.assertEqual(target['sp'], BOSSES['trench'].fish)

        for peer in (first, second):
            peer.state.update(m='bite', hx=target['x'], hd=target['d'])
        instance.on_shared_claim(first, {'b': 'trench', 'id': target['id']})
        instance.on_shared_claim(second, {'b': 'trench', 'id': target['id']})
        self.assertTrue(first.sent[-1]['ok'])
        self.assertFalse(second.sent[-1]['ok'])

        instance.on_shared_release(first, {'b': 'trench', 'id': target['id']})
        self.assertIsNone(target['owner'])
        self.assertNotIn('trench', instance.shared_bosses)

    def test_caught_boss_is_removed_for_global_cooldown(self):
        instance, first, _ = self.make_server()
        first.state['m'] = 'idle'
        instance.on_boss_search(first, {'b': 'trench'})
        target = instance.shared_boss_targets['trench']
        target['owner'] = first.id

        original_log = server.log
        server.log = lambda *args: None
        try:
            instance.on_catch(first, {
                'sp': target['sp'], 'tier': 6, 'mut': target['mut'], 'val': 100,
                'shared_id': target['id'],
            })
        finally:
            server.log = original_log

        self.assertNotIn('trench', instance.shared_boss_targets)
        self.assertGreater(instance.shared_boss_respawn['trench'], time.time())
        self.assertIsNone(instance.shared_boss_snapshot('trench'))

    def test_disconnect_releases_shared_boss(self):
        instance, first, second = self.make_server()
        first.state['m'] = 'idle'
        instance.by_name = {first.name.lower(): first, second.name.lower(): second}
        instance.on_boss_search(first, {'b': 'trench'})
        target = instance.shared_boss_targets['trench']
        target['owner'] = first.id
        instance.shared_bosses['trench'] = {'owner': first.id, 'name': first.name, 'expires': time.time() + 60}

        original_log = server.log
        server.log = lambda *args: None
        try:
            instance.drop(first)
        finally:
            server.log = original_log

        self.assertIsNone(target['owner'])
        self.assertNotIn('trench', instance.shared_bosses)
        self.assertTrue(any(message.get('t') == 'shared_boss' for message in second.sent))

    def test_disconnect_releases_shared_population_fish(self):
        instance, first, _ = self.make_server('shore')
        fish = instance._new_population_fish('shore', 0)
        fish['chunk'] = 0
        instance.shared_population['shore'] = {fish['id']: fish}
        x, depth = instance.population_position(fish)
        first.state.update(m='bite', hx=x, hd=depth)
        instance.on_shared_claim(first, {'b': 'shore', 'id': fish['id']})
        self.assertEqual(fish['owner'], first.id)

        original_log = server.log
        server.log = lambda *args: None
        try:
            instance.drop(first)
        finally:
            server.log = original_log

        self.assertIsNone(fish['owner'])


if __name__ == '__main__':
    unittest.main()
