import unittest

import pygame

from whiskerbay import art, fishart
from whiskerbay.data import FI


class FishArtTests(unittest.TestCase):
    def test_special_species_use_their_declared_body_shapes(self):
        expected = {
            'siltpuffer': 'puffer',
            'lamplighterjelly': 'jelly',
            'vaultoctopus': 'squid',
            'gorgonray': 'ray',
            'hippocampus': 'seahorse',
            'nereidjelly': 'jelly',
            'moonshardray': 'ray',
        }
        for species_id, painter in expected.items():
            with self.subTest(species=species_id):
                self.assertEqual(fishart.look(FI[species_id]).kind, painter)

    def test_signature_fish_features_are_present(self):
        self.assertEqual(fishart.look(FI['stickleback']).dorsal[0][4], 3)
        self.assertTrue(fishart.look(FI['salmonking']).crown)
        self.assertEqual(fishart.look(FI['pike']).mouth, 'fangs')
        self.assertGreater(fishart.look(FI['wels']).barbels, 0)

    def test_updated_species_render_visible_sprites(self):
        species_ids = (
            'siltpuffer', 'lamplighterjelly', 'vaultoctopus', 'gorgonray',
            'hippocampus', 'nereidjelly', 'moonshardray', 'stickleback',
            'salmonking', 'pike', 'wels',
        )
        for species_id in species_ids:
            with self.subTest(species=species_id):
                surface = pygame.Surface((320, 180), pygame.SRCALPHA)
                pen = art.Pen(surface, aa=True)
                pen.translate(160, 90)
                fishart.draw_fish(pen, FI[species_id], 150, ph=0.7)
                self.assertGreater(surface.get_bounding_rect().width, 0)
                self.assertGreater(surface.get_bounding_rect().height, 0)


if __name__ == '__main__':
    unittest.main()
