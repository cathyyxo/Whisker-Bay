"""The main loop: window, input, and calling everything else once per frame."""
import os
import sys

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
os.environ.setdefault('SDL_RENDER_SCALE_QUALITY', 'linear')

import pygame  # noqa: E402

from . import admin, online, scene, screens  # noqa: E402
from . import world as Wd  # noqa: E402
from .data import ACTION_NAMES, FI  # noqa: E402
from .settings import SET, save_settings  # noqa: E402
from .sfx import Sfx  # noqa: E402
from .ui import UI  # noqa: E402

G = Wd.G


class Loop:
    def __init__(self):
        self.held = set()
        self.up_pending = False
        self.text_on = False
        self.cursor_hand = False
        self.running = True

    def keydown(self, ev):
        key, mod = ev.key, ev.mod
        name = pygame.key.name(key)
        S = screens.S
        if key == pygame.K_F11:
            screens.toggle_fullscreen()
            return
        if key == pygame.K_F9 and Wd.LIVE and UI.focus is None and not S.rebind:
            if S.panel and S.panel.kind == 'admin':
                screens.close_panel()
            else:
                admin.open_panel()
            return
        if S.rebind:
            a, slot = S.rebind
            if key != pygame.K_ESCAPE and name:
                for act in SET['binds']:
                    SET['binds'][act] = [k for k in SET['binds'][act] if k != name]
                lst = list(SET['binds'].get(a) or [])
                if slot < len(lst):
                    lst[slot] = name
                else:
                    lst.append(name)
                SET['binds'][a] = lst[:2]
                save_settings()
                Wd.toast(f'{ACTION_NAMES[a]} is now {screens.keyLabel(name)}.', 'good')
            S.rebind = None
            return
        UI.keys.append((key, mod))
        if UI.focus is not None:
            if key == pygame.K_ESCAPE:
                if UI.focus is S.chat_field:
                    screens.close_chat()
                UI.focus = None
            return
        if name in self.held:
            return
        self.held.add(name)
        if key == pygame.K_ESCAPE:
            if S.panel:
                screens.close_panel()
            elif Wd.LIVE:
                screens.open_panel('settings')
            return
        if not Wd.LIVE:
            return
        a = screens.actionOf(name)
        if S.panel:
            if a in ('bag', 'shop', 'map', 'dex', 'players', 'quests') and S.panel.kind == a:
                screens.close_panel()
            return
        if a is None:
            if online.active() and pygame.K_1 <= key <= pygame.K_5:
                online.send_emote(key - pygame.K_1)
            return
        if a in ('left', 'right', 'up', 'down'):
            G.keys[a] = True
        elif a == 'act':
            Wd.actDown()
        elif a == 'ability':
            Wd.useAbility()
        elif a == 'skill':
            Wd.useSkill()
        elif a == 'bait':
            Wd.useFishBait()
        elif a == 'recall':
            Wd.recall()
        elif a == 'chat':
            screens.open_chat()
        elif a in ('bag', 'shop', 'map', 'dex', 'players', 'quests'):
            screens.open_panel(a)

    def keyup(self, ev):
        name = pygame.key.name(ev.key)
        self.held.discard(name)
        a = screens.actionOf(name)
        if a == 'act':
            if G.act and not pygame.mouse.get_pressed()[0]:
                Wd.actUp()
        elif a in ('left', 'right', 'up', 'down'):
            G.keys[a] = False

    def events(self):
        for ev in pygame.event.get():
            t = ev.type
            if t == pygame.QUIT:
                self.running = False
            elif t == pygame.KEYDOWN:
                self.keydown(ev)
            elif t == pygame.KEYUP:
                self.keyup(ev)
            elif t == pygame.TEXTINPUT:
                if UI.focus is not None:
                    UI.typed.append(ev.text)
            elif t == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:
                    UI.click = ev.pos
                    UI.mouse = ev.pos
                elif ev.button == 3:
                    UI.rclick = ev.pos
                    if Wd.LIVE and G.mode == 'reel' and not screens.S.panel:
                        Wd.useAbility()
            elif t == pygame.MOUSEBUTTONUP:
                if ev.button == 1:
                    self.up_pending = True
            elif t == pygame.MOUSEWHEEL:
                UI.wheel += ev.y
            elif t in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMINIMIZED):
                G.keys = {}
                self.held.clear()
                if G.act:
                    Wd.actUp()

    def frame(self, screen, real):
        UI.frame()
        UI.mouse = pygame.mouse.get_pos()
        self.events()
        online.pump(real)
        Wd.tick(real)
        admin.tick(real)
        Sfx.start_ambient()
        scene.draw(screen, real)
        screens.draw(screen, real)
        admin.draw(screen)
        S = screens.S
        if UI.click is not None and not UI.consumed:
            if S.chat_open:
                screens.close_chat()
            elif Wd.LIVE and not S.panel:
                Wd.actDown()
            if UI.focus is not None and UI.focus is not S.chat_field:
                UI.focus = None
        if self.up_pending:
            self.up_pending = False
            if G.act and not any(screens.actionOf(k) == 'act' for k in self.held):
                Wd.actUp()
        want = UI.focus is not None
        if want != self.text_on:
            self.text_on = want
            if want:
                pygame.key.start_text_input()
            else:
                pygame.key.stop_text_input()
        if UI.hot != self.cursor_hand:
            self.cursor_hand = UI.hot
            try:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if UI.hot else pygame.SYSTEM_CURSOR_ARROW)
            except (pygame.error, AttributeError):
                pass


def window_icon():
    from .art import portrait
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.circle(s, (14, 42, 70), (32, 32), 31)
    pygame.draw.circle(s, (255, 217, 138), (32, 32), 31, 3)
    p = portrait(FI['goldtuna'], None, 56, 40)
    s.blit(p, (4, 12))
    return s


def run():
    pygame.mixer.pre_init(22050, -16, 2, 512)
    pygame.init()
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(22050, -16, 2, 512)
        except pygame.error:
            pass
    pygame.display.set_caption('Whisker Bay')
    flags = pygame.SCALED | pygame.RESIZABLE
    try:
        screen = pygame.display.set_mode((1280, 720), flags, vsync=1)
    except pygame.error:
        screen = pygame.display.set_mode((1280, 720), flags)
    try:
        pygame.display.set_icon(window_icon())
    except pygame.error:
        pass
    if not hasattr(pygame.scrap, 'put_text'):
        try:
            pygame.scrap.init()
        except pygame.error:
            pass
    if SET.get('fullscreen'):
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            SET['fullscreen'] = False
    pygame.key.stop_text_input()
    pygame.key.set_repeat(400, 35)
    Sfx.start()
    Wd.guestBackdrop()
    loop = Loop()
    clock = pygame.time.Clock()
    try:
        while loop.running:
            real = min(0.05, clock.tick(60) / 1000)
            loop.frame(screen, real)
            admin.present(screen)
            pygame.display.flip()
    finally:
        try:
            online.shutdown()
            if Wd.LIVE:
                Wd.saveProfile()
            save_settings()
        finally:
            pygame.quit()


if __name__ == '__main__':
    run()
    sys.exit(0)
