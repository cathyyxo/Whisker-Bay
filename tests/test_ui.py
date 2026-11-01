import os
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame

from whiskerbay import scene, ui


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.surface = pygame.Surface((640, 360), pygame.SRCALPHA)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        ui.UI.frame()
        ui.UI.mouse = (60, 40)
        ui.UI.focus = None

    def test_button_styles_render_and_receive_clicks(self):
        styles = ('', 'go', 'warn', 'tab', 'tabon', 'hud', 'hot', 'ghost')
        for index, style in enumerate(styles):
            rect = pygame.Rect(10 + index * 75, 12, 68, 42)
            self.surface.fill((0, 0, 0, 0))
            self.assertFalse(ui.button(self.surface, rect, 'Test', style))
            self.assertFalse(self.surface.get_bounding_rect().size == (0, 0))

        ui.UI.click = (60, 40)
        self.assertTrue(ui.button(self.surface, (10, 12, 100, 50), 'Go', 'go'))

    def test_disabled_button_consumes_click_without_activating(self):
        ui.UI.click = (40, 30)
        self.assertFalse(ui.button(self.surface, (10, 10, 80, 40), 'Locked', 'go', disabled=True))
        self.assertTrue(ui.UI.consumed)

    def test_clipped_button_rejects_click_outside_clip(self):
        ui.UI.click = (40, 30)
        self.assertFalse(ui.button(
            self.surface, (10, 10, 80, 40), 'Hidden', clip=(100, 100, 20, 20)
        ))
        self.assertFalse(ui.UI.consumed)

    def test_fish_sonar_labels_are_positioned_without_overlap(self):
        labels = [
            (320, 180, 'Moonshard Ray', '#ffffff', 5, False),
            (320, 180, 'Gorgon Ray', '#ffffff', 4, False),
            (320, 180, 'Stickleback', '#ffffff', 3, True),
        ]

        placed = scene._layout_fish_names(labels, 14, 640, 360)

        self.assertEqual(len(placed), len(labels))
        bounds = []
        for x, y, label, _ in placed:
            half_width = ui.text_w(label, 'x', 14) / 2
            bounds.append((x - half_width, y - 14, x + half_width, y + 2))
        for index, (left, top, right, bottom) in enumerate(bounds):
            for other_left, other_top, other_right, other_bottom in bounds[index + 1:]:
                overlaps = (left < other_right and right > other_left
                            and top < other_bottom and bottom > other_top)
                self.assertFalse(overlaps)

if __name__ == '__main__':
    unittest.main()
