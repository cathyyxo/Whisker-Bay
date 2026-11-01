import unittest
from types import SimpleNamespace
from unittest.mock import patch

from whiskerbay import world


class FishingBehaviorTests(unittest.TestCase):
    def test_rare_fish_can_notice_bait_at_normal_sink_speed(self):
        stats = SimpleNamespace(hookV=1.0)
        with patch.object(world.G, 'PPM', 5.0):
            for tier, biome_depth in ((4, 180), (5, 850)):
                with patch.object(world, 'BIO', return_value=SimpleNamespace(depth=biome_depth)):
                    sink_speed = 22 * (1 + biome_depth / 1500) * stats.hookV * world.G.PPM
                    hook = SimpleNamespace(speed=sink_speed)

                    self.assertGreater(sink_speed, world.spookSpeed(stats) * 0.5)
                    self.assertTrue(world.canNoticeHook(SimpleNamespace(tier=tier), hook, stats))

    def test_rare_fish_still_ignore_a_hook_moving_too_fast(self):
        stats = SimpleNamespace(hookV=1.0)
        with patch.object(world.G, 'PPM', 5.0):
            with patch.object(world, 'BIO', return_value=SimpleNamespace(depth=180)):
                hook = SimpleNamespace(speed=1000)

                self.assertFalse(world.canNoticeHook(SimpleNamespace(tier=4), hook, stats))
                self.assertFalse(world.canNoticeHook(SimpleNamespace(tier=5), hook, stats))

    def test_common_fish_are_not_blocked_by_hook_speed(self):
        stats = SimpleNamespace(hookV=1.0)
        hook = SimpleNamespace(speed=1000)

        self.assertTrue(world.canNoticeHook(SimpleNamespace(tier=0), hook, stats))


if __name__ == '__main__':
    unittest.main()
