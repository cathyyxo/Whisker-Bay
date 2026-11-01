"""Everything you click: the HUD, menus, chat, and the title / login screens."""
import base64
import json
import math
import random
import time
import zlib

import pygame
from pygame import gfxdraw

from . import admin as AD
from . import online, settings, ui
from . import pets as PT
from . import world as Wd
from .art import Pen, draw_ability_icon, draw_portrait, portrait
from .data import (ABILITIES, ACTION_NAMES, BAIT, BAITS, BIOMES, BIOME_IDS, BOAT, BOATS, DEFAULT_KEYS, EGGS, EMOTES, ENCH,
                   ENCHANTS, FI, FISH, FURS, GEAR, GEARI, GIMMICKS, ISLE, KEEPER_LOGS, MUT, MUTS, PATCH_NOTES, PET, PET_DUPE_MIN,
                   PET_LEVEL_MIN, MATS, PET_MAX, PETS, QI, QUESTS, RAR, REEL, RELIC_PRICE, RI, ROD, RODS)
from .settings import SET, save_settings
from .sfx import Sfx
from .ui import (CORAL, DANGER, FOAM, LINE, MIST, NIGHT, PANEL, SAND, SEA, UI, Scroll, Slider, TextField,
                 box, button, para, text, text_w, wrap)
from .util import D, TAU, clamp, fmt, fmtW, hexc, mix, pick

G = Wd.G


def P():
    return Wd.P


def _name_ok(ch):
    return ch.isalnum() or ch == '_'


class _State:
    def __init__(self):
        self.panel = None
        self.chat_open = False
        self.chat_field = TextField('', 140, placeholder='Say something nice... (Enter to send, Esc to close)')
        self.rebind = None
        self.title_tab = 'local'
        self.name_field = TextField('', 16, placeholder="Your cat's name")
        self.new_fur = FURS[0]
        self.srv_field = TextField(SET.get('server') or 'localhost:7777', 80, placeholder='192.168.1.20:7777')
        self.user_field = TextField(SET.get('user') or '', 16, placeholder='Pick a name (letters, numbers, _)', allowed=_name_ok)
        self.pw_field = TextField('', 64, password=True, placeholder='Password')
        self.code_field = TextField('', 40, placeholder='Invite code (only if your host set one)')
        self.import_field = TextField('', 100000, placeholder='Paste a save code here (Ctrl+V)')
        self.remember = True
        self.reset_arm = 0.0
        self.del_arm = 0.0
        self.rolling = None
        self.altar_target = None
        self.patch_notes = False
        self.patch_scroll = Scroll()
        self.slider = Slider()
        self.title_scroll = Scroll()
        self.fps = 0.0
        self.code_cache = None
        self.lb_tab = 'coins'
        self.hatch = None         # the egg-hatching moment: D(t, res)
        self.tmp = None           # an off-screen layer so menus can fade in


S = _State()


def keyLabel(k):
    if not k:
        return '-'
    names = {'left': 'Left', 'right': 'Right', 'up': 'Up', 'down': 'Down', 'space': 'Space', 'return': 'Enter', 'tab': 'Tab',
             'left shift': 'L-Shift', 'right shift': 'R-Shift', 'left ctrl': 'L-Ctrl', 'right ctrl': 'R-Ctrl',
             'escape': 'Esc', 'backspace': 'Bksp', 'left alt': 'L-Alt', 'right alt': 'R-Alt'}
    return names.get(k, k.upper() if len(k) == 1 else k.title())


def K(action):
    b = SET['binds'].get(action) or []
    return keyLabel(b[0] if b else None)


def actionOf(keyname):
    for a, keys in SET['binds'].items():
        if keyname in keys:
            return a
    return None


# ===================================================================================
#  Little icons, painted with shapes
# ===================================================================================
_icons = {}


def icon(c, name, cx, cy, s=1.0, col=None):
    """A small picture (drawn once with smooth edges, then reused)."""
    col = col or FOAM
    key = (name, round(s, 3), col if isinstance(col, str) else tuple(col))
    spr = _icons.get(key)
    if spr is None:
        ss = 3
        size = int(30 * s) + 6
        big = pygame.Surface((size * ss, size * ss), pygame.SRCALPHA)
        p = Pen(big, aa=False)
        p.translate(size * ss / 2, size * ss / 2)
        p.scale(s * ss)
        _icon_body(p, name, col)
        spr = _icons[key] = pygame.transform.smoothscale(big, (size, size))
    c.blit(spr, (cx - spr.get_width() / 2, cy - spr.get_height() / 2))


def _icon_body(p, name, col):
    p.save()
    if name == 'bag':
        p.begin()
        p.arc(0, -6, 6, math.pi, 0)
        p.stroke(col, 2)
        p.begin()
        p.rect(-9, -6, 18, 15)
        p.fill(CORAL)
    elif name == 'shop':
        p.begin()
        p.move(-11, -2)
        p.line(0, -11)
        p.line(11, -2)
        p.fill('#c94b3b')
        p.begin()
        p.rect(-8, -2, 16, 11)
        p.fill('#d9a066')
        p.begin()
        p.rect(-3, 2, 6, 7)
        p.fill('#ffe08a')
    elif name == 'altar':
        p.begin()
        p.circle(0, 0, 8)
        p.fill('#b678ff')
        p.begin()
        p.circle(-2.5, -2.5, 3)
        p.fill((255, 255, 255, 170))
    elif name == 'map':
        p.begin()
        p.circle(0, 0, 9)
        p.stroke(col, 2)
        p.begin()
        p.move(0, -7)
        p.line(3, 0)
        p.line(-3, 0)
        p.fill(DANGER)
        p.begin()
        p.move(0, 7)
        p.line(3, 0)
        p.line(-3, 0)
        p.fill(col)
    elif name == 'dex':
        p.begin()
        p.rect(-10, -8, 9, 16)
        p.rect(1, -8, 9, 16)
        p.fill('#2fd3c0')
        p.begin()
        p.move(0, -8)
        p.line(0, 8)
        p.stroke(NIGHT, 1.5)
    elif name == 'me':
        p.begin()
        p.ellipse(0, 3, 6, 5)
        for x, y in ((-6, -3), (-2, -7), (2, -7), (6, -3)):
            p.circle(x, y, 2.4)
        p.fill(SAND)
    elif name == 'players':
        p.begin()
        p.circle(-4, -4, 4)
        p.circle(5, -3, 3.5)
        p.fill(col)
        p.begin()
        p.arc(-4, 8, 7, math.pi, 0)
        p.arc(5, 8, 6, math.pi, 0)
        p.fill(col)
    elif name == 'settings':
        p.begin()
        for k in range(8):
            a = k / 8 * TAU
            p.ellipse(math.cos(a) * 7, math.sin(a) * 7, 2.6, 2.6)
        p.circle(0, 0, 7)
        p.fill(MIST)
        p.begin()
        p.circle(0, 0, 3)
        p.fill(NIGHT)
    elif name in ('sound', 'mute'):
        p.begin()
        p.move(-9, -3)
        p.line(-5, -3)
        p.line(0, -8)
        p.line(0, 8)
        p.line(-5, 3)
        p.line(-9, 3)
        p.fill(col)
        p.begin()
        if name == 'sound':
            p.arc(1, 0, 5, -0.9, 0.9)
            p.stroke(col, 1.6)
            p.begin()
            p.arc(1, 0, 9, -0.9, 0.9)
            p.stroke(col, 1.6)
        else:
            p.move(3, -4)
            p.line(10, 4)
            p.move(10, -4)
            p.line(3, 4)
            p.stroke(DANGER, 2)
    elif name == 'rod':
        p.begin()
        p.move(-12, 12)
        p.quad(0, -2, 12, -13)
        p.stroke(col, 3, 'round')
        p.begin()
        p.move(12, -13)
        p.line(12, 4)
        p.stroke((220, 230, 240), 1)
        p.begin()
        p.circle(-6, 6, 3.5)
        p.fill('#9aa7b4')
    elif name == 'boat':
        p.begin()
        p.move(-14, 0)
        p.line(14, -1)
        p.quad(12, 9, 6, 10)
        p.line(-8, 10)
        p.quad(-13, 8, -14, 0)
        p.fill(col)
        p.begin()
        p.move(-2, -1)
        p.line(-2, -16)
        p.line(8, -3)
        p.fill('#f4efe2')
    elif name == 'sonar':
        p.begin()
        p.arc(0, -2, 10, 0.2, math.pi - 0.2)
        p.stroke(col, 2.5)
        p.begin()
        p.move(0, -2)
        p.line(0, 10)
        p.stroke(col, 2)
        p.begin()
        p.circle(0, -2, 2.5)
        p.fill(SEA)
    elif name == 'radar':
        p.begin()
        p.circle(0, 0, 11)
        p.fill((20, 80, 70))
        p.begin()
        p.circle(0, 0, 11)
        p.stroke(SEA, 1.5)
        p.begin()
        p.move(0, 0)
        p.line(8, -8)
        p.stroke(SEA, 2)
        p.begin()
        p.circle(4, 5, 2)
        p.fill(SAND)
    elif name == 'shield':
        p.begin()
        p.move(0, -12)
        p.line(10, -7)
        p.quad(9, 7, 0, 12)
        p.quad(-9, 7, -10, -7)
        p.fill('#ff7a2a')
        p.begin()
        p.move(0, -6)
        p.line(0, 7)
        p.stroke((255, 220, 160), 2)
    elif name == 'lamp':
        p.begin()
        p.move(-2, -4)
        p.line(12, -10)
        p.line(12, 10)
        p.line(-2, 4)
        p.fill((255, 240, 180, 120))
        p.begin()
        p.rect(-12, -4, 11, 8)
        p.fill('#5a6470')
    elif name == 'reel':
        p.begin()
        p.circle(0, 0, 10)
        p.fill('#f2c14e')
        p.begin()
        for k in range(4):
            a = k / 4 * math.pi
            p.move(math.cos(a) * 9, math.sin(a) * 9)
            p.line(-math.cos(a) * 9, -math.sin(a) * 9)
        p.stroke('#b8862a', 2)
        p.begin()
        p.circle(0, 0, 3)
        p.fill('#fff2c2')
    elif name == 'relic':
        p.begin()
        p.circle(0, 0, 10)
        p.fill('#8a4dff')
        p.begin()
        p.circle(-3, -3, 3.5)
        p.fill((255, 255, 255, 180))
    elif name == 'hook':
        p.begin()
        p.move(3, -11)
        p.line(3, 4)
        p.arc(-2, 4, 5, 0, math.pi)
        p.line(-7, 0)
        p.stroke('#d9e2ea', 2.4, 'round')
    elif name == 'star':
        p.begin()
        for k in range(8):
            a = k / 8 * TAU - math.pi / 2
            r = 11 if k % 2 == 0 else 4
            p.line(math.cos(a) * r, math.sin(a) * r)
        p.fill(col)
    elif name == 'bait':
        p.begin()
        p.circle(0, 0, 7)
        p.fill(col)
        p.begin()
        p.circle(-2, -2, 2.5)
        p.fill((255, 255, 255, 150))
    elif name == 'fish':
        p.begin()
        p.ellipse(0, 0, 9, 5)
        p.fill(col)
        p.begin()
        p.move(-7, 0)
        p.line(-12, -5)
        p.line(-12, 5)
        p.fill(col)
    elif name == 'quest':
        p.begin()
        p.rect(-7, -8, 13, 16)
        p.fill('#f3e2b8')
        p.begin()
        p.ellipse(-7, -8, 2.2, 2.2)
        p.ellipse(6, 8, 2.2, 2.2)
        p.fill('#d9b878')
        p.begin()
        for k in range(3):
            p.move(-4, -4 + k * 4)
            p.line(3, -4 + k * 4)
        p.stroke('#8a6a3a', 1.3)
        p.begin()
        p.move(1, 5)
        p.line(3, 7)
        p.line(8, 1)
        p.stroke(SEA, 2, 'round')
    elif name == 'charm':
        p.begin()
        p.move(-6, -11)
        p.quad(0, -4, 6, -11)
        p.stroke('#e8c27a', 1.6)
        p.begin()
        p.circle(0, 2, 8.5)
        p.fill('#2fd3c0')
        p.stroke('#e8c27a', 2)
        p.begin()
        p.move(1.5, -4)
        p.line(-3, 3)
        p.line(1, 3)
        p.line(-1.5, 8.5)
        p.line(4, 0.5)
        p.line(0, 0.5)
        p.close()
        p.fill('#fff2a8')
    p.restore()


def gear_icon(g):
    return g.icon


# ===================================================================================
#  Panels
# ===================================================================================
def open_panel(kind, tab=None):
    if not Wd.LIVE or G.mode in ('reel', 'bite') or G.sail:
        return
    if kind == 'players' and not online.active():
        Wd.toast('Players and leaderboards need online play. Log in from the title screen.', '')
        return
    if S.panel and S.panel.kind == kind and tab is None:
        close_panel()
        return
    S.panel = D(kind=kind, tab=tab, scroll=Scroll(), t=0.0)
    S.rebind = None
    if G.act:
        Wd.actUp()
    G.keys = {}
    if kind in ('players', 'admin'):
        online.request_boards()
    Wd.refreshStats()


def close_panel():
    S.panel = None
    S.rebind = None
    UI.focus = None
    if Wd.LIVE:
        Wd.saveProfile()
        Wd.refreshStats()


def spend(n):
    p = P()
    if p.coins < n:
        Sfx.play('nope')
        Wd.toast(f'You need {fmt(n - p.coins)} more coins.', 'bad')
        return False
    p.coins -= n
    Sfx.play('buy')
    return True


def pills(c, x, y, items, clip):
    """Little outlined tags. items: [(text, colour)]."""
    for t, col in items:
        w = text_w(t, 'k', 11) + 14
        box(c, (x, y, w, 19), None, col, 10, 1)
        text(c, t, x + w / 2, y + 9.5, 'k', 11, col, 'center', 'middle')
        x += w + 5
    return x


def card(c, rect, ic, title, desc='', stats=None, buttons=(), equip=False, locked=False, clip=None, tag_items=None):
    """A shop / bag card. ic: (icon name, colour) or a Surface. buttons: [(label, style, disabled, fn)]."""
    r = pygame.Rect(rect)
    a = 0.55 if locked else 1.0
    box(c, r, (20, 58, 95, 140), SEA if equip else (43, 90, 132, 204), 14, 2 if equip else 1, alpha=a)
    pygame.draw.line(c, (96, 174, 208) if equip else (50, 91, 125),
                     (r.x + 16, r.y + 2), (r.right - 16, r.y + 2), 1)
    ib = pygame.Rect(r.x + 12, r.y + 12, 56, 56)
    box(c, ib, (7, 26, 46, 166), None, 12, alpha=a)
    if isinstance(ic, pygame.Surface):
        c.blit(ic, ic.get_rect(center=ib.center))
    elif ic:
        icon(c, ic[0], ib.centerx, ib.centery, 1.35, hexc(ic[1]) if isinstance(ic[1], str) else ic[1])
    x0 = r.x + 80
    w = r.right - 12 - x0
    y = r.y + 10
    text(c, title, x0, y, 'k', 16, FOAM, alpha=a)
    y += 23
    if tag_items:
        pills(c, x0, y, tag_items, clip)
        y += 24
    if desc:
        for ln in wrap(desc, 'b', 13, w)[:3]:
            text(c, ln, x0, y, 'b', 13, MIST, alpha=a)
            y += 17
    if stats:
        sx = x0
        room = r.right - 10 - x0
        for t, col in stats:
            tw = text_w(t, 'x', 12)
            if sx + tw > r.right - 10 and sx > x0:
                sx = x0
                y += 16
            if tw > room:
                for ln in wrap(t, 'x', 12, room):
                    text(c, ln, x0, y + 2, 'x', 12, col or FOAM, alpha=a)
                    y += 16
                sx = x0
                y -= 16
                continue
            text(c, t, sx, y + 2, 'x', 12, col or FOAM, alpha=a)
            sx += tw + 12
        y += 18
    bx = x0
    by = r.bottom - 44
    for label, style, dis, fn in buttons:
        bw = text_w(label, 'k', 14) + 28
        if button(c, (bx, by, bw, 34), label, style, dis, clip=clip):
            fn()
        bx += bw + 8


def grid(c, body, y0, items, draw_item, colmin=260, card_h=124, gap=10):
    cols = max(1, (body.w + gap) // (colmin + gap))
    cw = (body.w - gap * (cols - 1)) / cols
    rows = (len(items) + cols - 1) // cols
    for i, it in enumerate(items):
        rr, k = divmod(i, cols)
        rect = pygame.Rect(int(body.x + k * (cw + gap)), int(y0 + rr * (card_h + gap)), int(cw), card_h)
        if rect.bottom >= body.y and rect.y <= body.bottom:
            draw_item(c, rect, it)
    return rows * (card_h + gap)


def panel_title(kind):
    p = P()
    return {'bag': 'Your bag', 'shop': f'{Wd.BIO().name} shop', 'altar': 'The Altar', 'map': 'Sea chart',
            'dex': 'Fishpedia', 'me': p.name, 'settings': 'Settings', 'players': 'Players', 'quests': 'Quests',
            'portal': 'Poseidon’s Statue', 'admin': 'Admin panel'}.get(kind, '')


def draw_panel(c, dt):
    pn = S.panel
    pn.t = (pn.t or 0.0) + dt
    if pn.t < 0.2:
        # fade the menu in gently: draw it on a see-through layer first
        if S.tmp is None or S.tmp.get_size() != c.get_size():
            S.tmp = pygame.Surface(c.get_size(), pygame.SRCALPHA)
        S.tmp.fill((0, 0, 0, 0))
        _draw_panel(S.tmp, dt)
        e = 1 - (1 - min(1.0, pn.t / 0.2)) ** 3
        S.tmp.set_alpha(int(255 * e))
        c.blit(S.tmp, (0, int((1 - e) * 14)))
        S.tmp.set_alpha(255)
        return
    _draw_panel(c, dt)


def _draw_panel(c, dt):
    pn = S.panel
    W, H = G.W, G.H
    hatch_click = None
    if S.hatch:                       # while an egg hatches, clicks belong to the hatching
        hatch_click, UI.click = UI.click, None
    ui.overlay(c, (2, 8, 16), 0.62)
    PW, PH = min(940, W - 20), min(660, H - 20)
    px, py = (W - PW) // 2, (H - PH) // 2
    pr = pygame.Rect(px, py, PW, PH)
    box(c, pr, None, LINE, 20, 1, grad=(PANEL, NIGHT))
    if UI.click and not pr.collidepoint(UI.click) and not UI.consumed:
        UI.consumed = True
        close_panel()
        return
    Wd.refreshStats()
    sub = panel_sub(pn)
    tr = text(c, panel_title(pn.kind), px + 18, py + 14, 'd', 26, SAND)
    if sub:
        text(c, sub, tr.right + 14, py + 24, 'k', 13, MIST)
    if button(c, (pr.right - 52, py + 12, 38, 38), '', '', radius=12):
        close_panel()
        return
    pygame.draw.aaline(c, FOAM, (pr.right - 39, py + 25), (pr.right - 27, py + 37))
    pygame.draw.aaline(c, FOAM, (pr.right - 27, py + 25), (pr.right - 39, py + 37))
    tabs = panel_tabs(pn)
    top = py + 62
    if tabs:
        if pn.tab is None:
            pn.tab = tabs[0][0]
        t = ui.tabs(c, px + 18, top, tabs, pn.tab, maxw=PW - 36)
        if t and t != pn.tab:
            pn.tab = t
            pn.scroll = Scroll()
            S.rebind = None
        top += 44
    body = pygame.Rect(px + 18, top, PW - 36, pr.bottom - top - 14)
    off = pn.scroll.update(body)
    old = c.get_clip()
    c.set_clip(body)
    y = body.y - off
    fn = {'bag': panel_bag, 'shop': panel_shop, 'altar': panel_altar, 'map': panel_map, 'dex': panel_dex, 'me': panel_me,
          'settings': panel_settings, 'players': panel_players, 'quests': panel_quests, 'portal': panel_portal,
          'admin': AD.panel}[pn.kind]
    h = fn(c, body, y, dt)
    c.set_clip(old)
    if S.panel is pn:
        pn.scroll.content = h or 0
        pn.scroll.bar(c, pygame.Rect(body.right + 6, body.y, 10, body.h))
    if S.hatch:
        UI.click = hatch_click
        draw_hatch(c, pr, dt)
    UI.block(pr)


def panel_sub(pn):
    p = P()
    k = pn.kind
    if k == 'bag':
        if pn.tab == 'pets':
            return f'{len(p.pets)} of {len(PETS)} pets · pet boat {len(p.petOn)}/{Wd.petSlots()} seats'
        return 'Pick the bait on your hook' if pn.tab == 'bait' else f'{len(p.bag)} of {Wd.holdSize()} slots'
    if k == 'shop':
        return f'{fmt(p.coins)} coins'
    if k == 'altar':
        return f'{p.relics} relic{"" if p.relics == 1 else "s"}'
    if k == 'map':
        return f'Boat: {BOAT[p.boat].name}'
    if k == 'dex':
        return f'{sum(1 for f in FISH if f.id in p.dex)} of {len(FISH)} species'
    if k == 'me':
        return f'Level {p.level}'
    if k == 'quests':
        return f'{sum(1 for q in QUESTS if q.id in p.qc or Wd.questSkipped(q))} of {len(QUESTS)} done'
    if k == 'players':
        return f'{len(online.who)} online on {online.st.srvname or online.st.server}'
    if k == 'admin':
        return AD.panel_sub()
    return ''


def panel_tabs(pn):
    p = P()
    k = pn.kind
    if k == 'bag':
        return [('fish', 'Fish'), ('bait', 'Bait'), ('pets', 'Pets')]
    if k == 'shop':
        t = [('rods', 'Rods'), ('boats', 'Boats'), ('gear', 'Gear'), ('bait', 'Bait')]
        if p.unlocked.get('reef'):
            t.append(('eggs', 'Eggs'))
        if p.biome == 'reef':
            t.append(('relic', 'Relics'))
        return t
    if k == 'dex':
        islands = [(b, BIOMES[b].short) for b in BIOME_IDS if not BIOMES[b].portal or p.unlocked.get(b)]
        return islands + [('odds', 'Odds'), ('logs', 'Keeper’s Logs')]
    if k == 'settings':
        return [('saves', 'Saves'), ('controls', 'Controls'), ('sound', 'Sound & display'), ('updates', 'What’s New')]
    if k == 'players':
        return [('online', 'Online now'), ('boards', 'Leaderboards')]
    return None


# ---------------- bag ----------------
def panel_bag(c, body, y, dt):
    p = P()
    if S.panel.tab == 'pets':
        return panel_pets(c, body, y, dt)
    if S.panel.tab == 'bait':
        items = [None] + [b for b in BAITS if p.baits.get(b.id)]

        def item(c, r, b):
            if b is None:
                def use_none():
                    p.bait = None
                card(c, r, ('hook', FOAM), 'Bare hook', 'No bonuses, but never runs out.',
                     buttons=[('Use no bait' if p.bait else 'In use', '', not p.bait, use_none)], equip=not p.bait, clip=body)
            else:
                def use(b=b):
                    p.bait = b.id
                inuse = p.bait == b.id
                card(c, r, ('bait', b.dot), f'{b.name} x{p.baits.get(b.id, 0)}', b.desc,
                     buttons=[('In use' if inuse else 'Use', 'go', inuse, use)], equip=inuse, clip=body)
        return grid(c, body, y, items, item, card_h=124)
    fish = sorted(p.bag, key=lambda f: -f.val)
    total = sum(f.val for f in fish if not f.lock)
    fish_bait = FI.get(p.fish_bait) if p.fish_bait in FI else None

    def sell_all():
        keep = [f for f in p.bag if f.lock]
        if len(keep) == len(p.bag):
            return
        p.bag = keep
        Wd.onSold(total)
        Sfx.play('coin')
        Wd.toast(f'Sold for {fmt(total)} coins.', 'gold')
        Wd.saveProfile()
    label = f'Sell all unlocked ({fmt(total)} coins)'
    if button(c, (body.x, y, text_w(label, 'k', 14) + 30, 38), label, 'go', not total, clip=body):
        sell_all()
    if fish_bait:
        bait_text = f'Saved fish-bait: {fish_bait.name} · +{max(0, round((1.12 + (RI[fish_bait.r] * 0.08) - 1) * 100))}% luck and bite'
        text(c, bait_text, body.x + 12, y + 46, 'x', 12, (164, 232, 255), alpha=0.92)
        if button(c, (body.right - 196, y + 42, 180, 30), 'Clear saved fish bait', '', False, clip=body):
            Wd.useFishBait()
    y0 = y + 50 if not fish_bait else y + 82
    if not fish:
        para(c, f'Nothing yet. Close this and cast your line: hold {K("act")} or the mouse button, then let go.', body.x, y0, body.w)
        return 100

    def item(c, r, f):
        sp = FI[f.sp]
        rr = RAR[RI[sp.r]]
        m = MUT.get(f.mut) if f.mut else None
        tags = [(rr.name, hexc(rr.col))]
        if m:
            tags.append((f'{m.name} x{m.mult}', hexc(m.col)))
        if f.perfect:
            tags.append(('Perfect', SAND))
        if f.pet:
            tags.append(('by Mittens', (255, 217, 160)))

        def sell(f=f):
            if f in p.bag:
                p.bag.remove(f)
                Wd.onSold(f.val)
            Sfx.play('coin')

        def lock(f=f):
            f.lock = not f.lock
        card(c, r, portrait(sp, f.mut, 56, 56), sp.name, '', [(fmtW(f.kg), FOAM), (f'{fmt(f.val)} coins', SAND)],
             [('Sell', '', f.lock, sell), ('Locked' if f.lock else 'Lock', '', False, lock)], clip=body, tag_items=tags)
    return 50 + grid(c, body, y0, fish, item, card_h=128)


# ---------------- pets ----------------
def panel_pets(c, body, y, dt):
    p = P()
    yy = y
    if not p.unlocked.get('reef') and not p.pets:
        para(c, 'Pets hatch from eggs. The hatchery opens once you reach the Coral Reef: buy eggs in the shop (Eggs tab), and your pets '
                'ride in a little boat behind yours. They grow (levels 1 to 10) while you play with them aboard, and help a little with fishing.',
             body.x, yy, body.w)
        return 120
    slots = Wd.petSlots()
    yy += para(c, f'Your pet boat has {slots} seat{"s" if slots > 1 else ""}' + ('' if slots > 1 else ' (a second one opens when you reach the Volcanic Biome)') +
               '. Pets aboard grow while you play and lend a paw; pets at home rest. Buy eggs in the shop (Eggs tab).', body.x, yy, body.w) + 8

    def item(c, r, pt):
        own = pt.id in p.pets
        col = hexc(PT.rarity_col(pt.id))
        aboard = pt.id in p.petOn
        box(c, r, (20, 58, 95, 140), SEA if aboard else (43, 90, 132, 204), 14, 2 if aboard else 1, alpha=1 if own else 0.6)
        ib = pygame.Rect(r.x + 12, r.y + 12, 72, 72)
        box(c, ib, (7, 26, 46, 166), None, 12)
        lvl, frac = Wd.petProgress(pt.id) if own else (1, 0)
        ic = PT.pet_icon(pt.id, 64, lvl)
        if not own:
            ic = ic.copy()
            ic.fill((10, 30, 50, 255), special_flags=pygame.BLEND_RGBA_MIN)
        c.blit(ic, ic.get_rect(center=ib.center))
        x0 = r.x + 96
        w = r.right - 14 - x0
        text(c, f'{pt.name} the {pt.kind}' if own else f'??? ({pt.kind})', x0, r.y + 10, 'k', 16, FOAM)
        pills(c, x0, r.y + 33, [(RAR[RI[pt.r]].name, col)] + ([(f'Level {lvl}' + (' MAX' if lvl >= PET_MAX else ''), SAND)] if own else []), body)
        yq = r.y + 58
        txt = Wd.petEffectText(pt.id, lvl) if own else pt.desc
        for ln in wrap(txt, 'b', 13, w)[:3]:
            text(c, ln, x0, yq, 'b', 13, MIST)
            yq += 17
        if own:
            if lvl < PET_MAX:
                need = PET_LEVEL_MIN[lvl] - PET_LEVEL_MIN[lvl - 1]
                box(c, (x0, r.bottom - 58, w - 10, 8), (255, 255, 255, 30), None, 4)
                box(c, (x0, r.bottom - 58, max(8, (w - 10) * frac), 8), col, None, 4)
                left = max(0, PET_LEVEL_MIN[lvl] - (p.pets[pt.id].t or 0) / 60)
                text(c, f'{left:.0f} min aboard to level {lvl + 1}' if left >= 1 else f'almost level {lvl + 1}!', x0, r.bottom - 46, 'x', 11, MIST)
            else:
                text(c, 'Fully grown!', x0, r.bottom - 50, 'k', 12, SAND)
            full = len(p.petOn) >= slots and not aboard
            lab = 'Aboard  (send home)' if aboard else ('Seats full' if full else 'Bring aboard')
            if button(c, (x0, r.bottom - 34, text_w(lab, 'k', 13) + 28, 28), lab, '' if aboard else 'go', full, size=13, clip=body):
                if Wd.togglePet(pt.id):
                    Sfx.play('buy')
        else:
            text(c, 'Hatch it from an egg', x0, r.bottom - 26, 'x', 12, MIST)
    return yy - y + grid(c, body, yy, PETS, item, colmin=410, card_h=172)


def draw_hatch(c, pr, dt):
    """The egg wobbles, cracks and pops: here's your pet."""
    H_ = S.hatch
    H_.t += dt
    res = H_.res
    t = H_.t
    ui.overlay(c, (2, 8, 16), min(0.85, t * 3))
    cx, cy = pr.centerx, pr.centery - 30
    p_ = Pen(c, aa=True)
    if t < 1.9:
        wob = min(1.0, t / 0.5)
        crack = max(0.0, (t - 0.9) / 0.9)
        if int(t * 6) != int((t - dt) * 6) and t > 0.9:
            Sfx.play('crack')
        PT.draw_egg(p_, res.egg, cx, cy, 70, t * (1 + t), wob, crack)
        text(c, 'Hatching...', cx, cy + 120, 'd', 22, SAND, 'center', 'middle')
        return
    if not H_.done:
        H_.done = True
        Sfx.play('hatch')
        Wd.flash(0.5, PT.rarity_col(res.pid))
    pt = PET[res.pid]
    col = hexc(PT.rarity_col(res.pid))
    k = min(1.0, (t - 1.9) / 0.35)
    for i in range(14):
        a = G.t * 0.6 + i * TAU / 14
        gfxdraw.filled_trigon(c, int(cx), int(cy), int(cx + math.cos(a) * 260 * k - math.sin(a) * 18), int(cy + math.sin(a) * 260 * k + math.cos(a) * 18),
                              int(cx + math.cos(a) * 260 * k + math.sin(a) * 18), int(cy + math.sin(a) * 260 * k - math.cos(a) * 18), col + (40,))
    ic = PT.pet_icon(res.pid, int(150 * (0.6 + 0.4 * k)), Wd.petLevel(res.pid))
    c.blit(ic, ic.get_rect(center=(cx, cy)))
    text(c, ('NEW PET!' if res.new else 'Again!'), cx, cy - 110, 'd', 30, col, 'center', 'middle', outline=3, ocol=(0, 0, 0, 160))
    text(c, f'{pt.name} the {pt.kind}', cx, cy + 96, 'd', 24, FOAM, 'center', 'middle')
    text(c, RAR[RI[pt.r]].name.upper(), cx, cy + 122, 'k', 13, col, 'center', 'middle')
    if res.new:
        sub = 'Hopped into your pet boat!' if res.pid in P().petOn else 'Your pet boat is full: swap pets in Bag > Pets.'
    elif res.refund:
        sub = f'Already fully grown, so you get {fmt(res.refund)} coins back.'
    else:
        sub = f'You already have {pt.name}: +{PET_DUPE_MIN} minutes of growth instead.'
    text(c, sub, cx, cy + 146, 'x', 14, MIST, 'center', 'middle')
    if t > 2.5:
        text(c, 'Click to continue', cx, cy + 176, 'x', 12, (234, 246, 255, 150), 'center', 'middle')
        if UI.click:
            UI.consumed = True
            S.hatch = None


# ---------------- shop ----------------
def panel_shop(c, body, y, dt):
    p = P()
    t = S.panel.tab or 'rods'
    if t == 'rods':
        def item(c, r, rod):
            own = rod.id in p.rods
            if rod.quest:
                return quest_rod_card(c, r, rod, body)
            here = rod.at == p.biome
            recipeOk = not rod.need or p.recipes.get(rod.id)
            materialOk = not rod.need or (p.mats.get(rod.need) or 0) > 0
            needOk = recipeOk and materialOk
            reach = p.unlocked.get(rod.at)
            stats = [(f'{rod.depth} m', FOAM), (f'luck x{rod.luck}', FOAM), (f'reel x{rod.reel}', FOAM), (f'strength x{rod.str}', FOAM)]
            if rod.need:
                stats.append((f'Crafting material: {MATS[rod.need].name}', hexc(MATS[rod.need].col)))
            e = (p.rods.get(rod.id) or {}).get('ench') if own else None
            if e:
                stats.append((f'+ {ENCH[e].name}', hexc(ENCH[e].col)))
            A = ABILITIES.get(rod.ab)
            if A:
                stats.append((f'Ability: {A.name}', hexc(A.col)))
                stats.append((A.desc, MIST))
            if own:
                def equip(rod=rod):
                    p.rod = rod.id
                btn = ('Equipped' if p.rod == rod.id else 'Equip', '', p.rod == rod.id, equip)
            else:
                def buy(rod=rod):
                    if spend(rod.price):
                        if rod.need:
                            p.mats[rod.need] -= 1
                        p.rods[rod.id] = D(ench=None)
                        p.rod = rod.id
                        Wd.toast(f'{rod.name} {"crafted and equipped" if rod.need else "equipped"}.', 'good')
                        Wd.saveProfile()
                if not recipeOk:
                    requirement = f'Find the {BIOMES[rod.at].name} ruins blueprint'
                elif not materialOk:
                    requirement = f'Needs 1 {MATS[rod.need].name}'
                else:
                    requirement = f'{"Craft" if rod.need else "Buy"} {fmt(rod.price)}'
                label = requirement if here else (f'Sold at {BIOMES[rod.at].name}' if reach else f'Reach {BIOMES[rod.at].name} first')
                btn = (label, 'go', not here or not needOk, buy)
            card(c, r, ('rod', rod.col), rod.name, rod.desc, stats, [btn], equip=p.rod == rod.id, locked=not own and not here, clip=body)
            A = ABILITIES.get(rod.ab)
            if A:
                draw_ability_icon(c, rod.ab, r.right - 22, r.y + 22, 12, hexc(A.col))
        yy = y
        order = [p.biome] + [b for b in BIOME_IDS if b != p.biome]
        for bid in order:
            tr = text(c, f'{BIOMES[bid].name} rods', body.x, yy + 6, 'd', 20, SAND if bid == p.biome else MIST)
            note = 'sold here' if bid == p.biome else ('sold on that island' if p.unlocked.get(bid) else 'not reached yet')
            text(c, f'{note} · quest rods come from that island\'s quests ({K("quests")})', tr.right + 12, yy + 12, 'x', 12, MIST)
            yy += 36
            yy += grid(c, body, yy, [rod for rod in RODS if rod.at == bid], item, card_h=212) + 6
        return yy - y
    if t == 'boats':
        def item(c, r, b):
            own = b.id in p.boats
            far = [BIOMES[i].short for i in BIOME_IDS if BIOMES[i].boat == max(BIOMES[j].boat for j in BIOME_IDS if BIOMES[j].boat <= b.tier)]
            reach = ' and '.join(far)
            if own:
                def use(b=b):
                    p.boat = b.id
                btn = ('In use' if p.boat == b.id else 'Use', '', p.boat == b.id, use)
            else:
                def buy(b=b):
                    if spend(b.price):
                        p.boats.append(b.id)
                        p.boat = b.id
                        Wd.saveProfile()
                btn = (f'Buy {fmt(b.price)}', 'go', False, buy)
            card(c, r, ('boat', b.col), b.name, b.desc, [(f'holds {b.hold} fish', FOAM), (f'sails as far as: {reach}', MIST)], [btn], equip=p.boat == b.id, clip=body)
        return grid(c, body, y, BOATS, item, card_h=150)
    if t == 'gear':
        def item(c, r, g):
            own = bool(p.gear.get(g.id))
            needOk = not g.need or p.gear.get(g.need)
            atOk = not g.get('at') or p.unlocked.get(g.at)
            if own:
                btn = ('Equipped' if g.get('accessory') else 'Owned', '', True, lambda: None)
            else:
                def buy(g=g):
                    if spend(g.price):
                        p.gear[g.id] = True
                        Wd.saveProfile()
                label = (f'Opens at {BIOMES[g.at].name}' if not atOk else
                         f'Needs {GEARI[g.need].name}' if not needOk else f'Buy {fmt(g.price)}')
                btn = (label, 'go', not (needOk and atOk), buy)
            tags = [('CAT ACCESSORY', SAND)] if g.get('accessory') else None
            card(c, r, (g.icon, FOAM), g.name, g.desc, None, [btn], equip=own, locked=not atOk, clip=body,
                 tag_items=tags)
        return grid(c, body, y, GEAR, item, card_h=130)
    if t == 'bait':
        def item(c, r, b):
            here = not b.at or b.at == p.biome

            def buy(b=b):
                if spend(b.price * b.per):
                    p.baits[b.id] = (p.baits.get(b.id) or 0) + b.per
                    if not p.bait:
                        p.bait = b.id
            card(c, r, ('bait', b.dot), f'{b.name} (you have {p.baits.get(b.id) or 0})', b.desc, None,
                 [(f'Buy {b.per} for {fmt(b.price * b.per)}' if here else f'Sold at {BIOMES[b.at].name}', 'go', not here, buy)], clip=body)
        return grid(c, body, y, BAITS, item, card_h=130)
    if t == 'eggs':
        hdr = para(c, 'Eggs hatch into pets that ride in a little boat behind yours. Each egg is sold once you reach its island; '
                      f'a pet you already have becomes {PET_DUPE_MIN} minutes of extra growth for it instead.', body.x, y, body.w) + 8

        def item(c, r, e):
            ok = p.unlocked.get(e.at)
            tot = sum(e.odds.values())
            tags = [(f'{PET[k].kind} {v * 100 / tot:.0f}%', hexc(PT.rarity_col(k))) for k, v in e.odds.items() if v]

            def buy(e=e):
                if p.coins < e.price:
                    spend(e.price)
                    return
                res = Wd.hatchEgg(e.id)
                if res:
                    Sfx.play('buy')
                    S.hatch = D(t=0.0, res=res, done=False)
            card(c, r, PT.egg_icon(e, 56), e.name, e.desc, None,
                 [(f'Hatch for {fmt(e.price)}' if ok else f'Opens at {BIOMES[e.at].name}', 'go', not ok, buy)], locked=not ok, clip=body)
            pills(c, r.x + 80, r.y + 76, tags[:3], body)
            if len(tags) > 3:
                pills(c, r.x + 80, r.y + 99, tags[3:], body)
        return hdr + grid(c, body, y + hdr, EGGS, item, colmin=420, card_h=176)
    if t == 'relic':
        def item(c, r, _):
            def buy():
                if spend(RELIC_PRICE):
                    p.relics += 1
            card(c, r, ('relic', FOAM), f'Enchant Relic (you have {p.relics})', 'Spend one at the Altar to enchant your rod. Rare catches sometimes drop them too.',
                 None, [(f'Buy {fmt(RELIC_PRICE)}', 'go', False, buy)], clip=body)
        return grid(c, body, y, [0], item, card_h=130)
    return 0


def quest_rod_stats(rod):
    stats = [(f'{rod.depth} m', FOAM), (f'luck x{rod.luck}', FOAM), (f'reel x{rod.reel}', FOAM), (f'strength x{rod.str}', FOAM)]
    A = ABILITIES.get(rod.ab)
    if A:
        stats.append((f'Ability: {A.name}', hexc(A.col)))
        stats.append((A.desc, MIST))
    return stats


def quest_rod_card(c, r, rod, clip):
    p = P()
    q = QI[rod.quest]
    own = rod.id in p.rods
    done = Wd.questOpen(q) and Wd.questDone(q)
    if own:
        def equip(rod=rod):
            p.rod = rod.id
        btn = ('Equipped' if p.rod == rod.id else 'Equip', '', p.rod == rod.id, equip)
    elif done and q.id not in p.qc:
        btn = ('Claim', 'go', False, lambda q=q: Wd.claimQuest(q.id))
    elif not Wd.questOpen(q):
        btn = (f'Quest on {BIOMES[q.isle].name}', '', True, lambda: None)
    else:
        have, need = Wd.questProgress(q)
        btn = (f'Quest: {round(have / need * 100)}%', '', True, lambda: None)
    card(c, r, ('rod', rod.col), rod.name, f'Quest "{q.name}": {q.desc}', quest_rod_stats(rod), [btn], equip=p.rod == rod.id,
         locked=not own and not done, clip=clip)
    A = ABILITIES.get(rod.ab)
    if A:
        draw_ability_icon(c, rod.ab, r.right - 22, r.y + 22, 12, hexc(A.col))


def _goal_rows(c, q, x0, y, w, opened):
    """One row per goal: what to do, a bar and the count (the bar goes underneath on narrow cards)."""
    narrow = w < 520
    for i, g in enumerate(q.goals):
        have, need = Wd.goalProgress(q, i) if opened else (0, g.n)
        if Wd.questSkipped(q):
            have = need
        done = have >= need
        gfxdraw.filled_circle(c, int(x0 + 4), int(y + 8), 4, SEA if done else (98, 160, 255, 160))
        text(c, Wd.goalText(g), x0 + 14, y, 'b', 13, SEA if done else FOAM)
        if narrow:
            y += 18
            bx, bw = x0 + 14, w - 14 - 70
        else:
            bw = 150
            bx = x0 + w - bw - 74
        box(c, (bx, y + 4, bw, 9), (255, 255, 255, 30), None, 5)
        if have > 0:
            box(c, (bx, y + 4, max(9, bw * have / need), 9), SEA if done else (98, 160, 255), None, 5)
        text(c, f'{fmt(have)} / {fmt(need)}', x0 + w, y, 'k', 12, SEA if done else MIST, 'right')
        y += 22
    return y


def panel_quests(c, body, y, dt):
    p = P()
    yy = y + para(c, 'Every island has an island quest (finish it to be allowed to sail on to the next island) and two rod quests, '
                     'whose rods are made for that island. Progress counts from the moment you reach an island.', body.x, y, body.w) + 4
    glow = 0.5 + 0.5 * math.sin(G.t * 4)
    for bid in BIOME_IDS:
        b = BIOMES[bid]
        opened = bool(p.unlocked.get(bid))
        tr = text(c, b.name, body.x, yy + 8, 'd', 21, SAND if opened else MIST)
        if not opened:
            ok, why = Wd.sailCheck(bid)
            text(c, ('Ready to sail there!' if ok else f'Locked: {why}') + ' Quests start when you arrive.', tr.right + 14, yy + 15, 'x', 13, MIST)
        yy += 42
        qs = [q for q in QUESTS if q.isle == bid and (not q.hidden or Wd.questOpen(q))]
        if not qs:
            continue
        iq = next(q for q in qs if q.island)
        hgt = 76 + 22 * len(iq.goals)
        r = pygame.Rect(body.x, yy, body.w, hgt)
        if r.bottom >= body.y and r.y <= body.bottom:
            skipped = Wd.questSkipped(iq)
            done = opened and Wd.questDone(iq)
            claimed = iq.id in p.qc or skipped
            ready = done and not claimed
            box(c, r, (24, 52, 70, 170), (47, 211, 192, int(150 + 100 * glow)) if ready else (255, 217, 138, 110) if opened else (43, 90, 132, 160), 14, 2,
                alpha=1 if opened else 0.6)
            icon(c, 'map', r.x + 30, r.y + 30, 1.3, SAND)
            x0 = r.x + 58
            text(c, f'Island quest: {iq.name}', x0, r.y + 10, 'k', 17, SAND if opened else MIST)
            text(c, iq.desc, x0, r.y + 33, 'b', 13, MIST)
            _goal_rows(c, iq, x0, r.y + 56, r.right - 16 - x0, opened)
            nxt = BIOMES[iq.unlock].name if iq.unlock else 'the next update'
            rw = f'Reward: {fmt(iq.coins)} coins · opens the way to {nxt}'
            text(c, rw, x0, r.bottom - 22, 'x', 12, SAND)
            if skipped:
                text(c, f'Done (you already reached {nxt})', r.right - 16, r.y + 12, 'k', 13, SEA, 'right')
            elif claimed:
                text(c, 'Complete!', r.right - 16, r.y + 12, 'k', 14, SEA, 'right')
            elif ready:
                if button(c, (r.right - 112, r.y + 10, 98, 32), 'Claim!', 'go', clip=body):
                    Wd.claimQuest(iq.id)
        yy += hgt + 10

        def item(c, r, q, opened=opened):
            rod = ROD[q.rod]
            A = ABILITIES[rod.ab]
            done = opened and Wd.questDone(q)
            claimed = q.id in p.qc
            ready = done and not claimed
            box(c, r, (20, 58, 95, 150), (47, 211, 192, int(150 + 100 * glow)) if ready else (43, 90, 132, 204), 14, 2 if ready else 1,
                alpha=1 if opened else 0.6)
            ib = pygame.Rect(r.x + 12, r.y + 12, 58, 58)
            box(c, ib, (7, 26, 46, 166), None, 12)
            icon(c, 'rod', ib.centerx, ib.centery, 1.4, hexc(rod.col))
            draw_ability_icon(c, rod.ab, ib.right - 6, ib.bottom - 6, 11, hexc(A.col))
            x0 = r.x + 82
            w = r.right - 14 - x0
            text(c, q.name, x0, r.y + 10, 'k', 16, SAND if ready else FOAM)
            yr = _goal_rows(c, q, x0, r.y + 36, w, opened) + 4
            if q.rod in p.rods and not claimed:
                tr2 = text(c, f'Reward: {fmt(q.coins)} coins (you own the {rod.name})', x0, yr, 'x', 12, MIST)
            else:
                tr = text(c, 'Reward: ', x0, yr, 'x', 12, MIST)
                tr2 = text(c, rod.name, tr.right, yr, 'k', 12, hexc(rod.tip or rod.col))
                text(c, f' + {fmt(q.coins)} coins  ·  {A.name}', tr2.right, yr, 'x', 12, hexc(A.col))
            if claimed:
                text(c, 'Claimed', r.right - 14, r.y + 12, 'k', 13, SEA, 'right')
            elif ready:
                if button(c, (r.right - 100, r.bottom - 40, 86, 30), 'Claim!', 'go', size=13, clip=body):
                    Wd.claimQuest(q.id)
        yy += grid(c, body, yy, [q for q in qs if not q.island], item, colmin=400, card_h=136) + 10
    return yy - y


def panel_portal(c, body, y, dt):
    p = P()
    yy = y + para(c, 'The statue’s trident-shaped socket is the lock on the drowned city’s oldest gate.',
                  body.x, y, body.w) + 18
    if p.biome == 'atlantis':
        if not p.portal.started:
            para(c, 'The statue is silent. Something in Atlantis must know how to wake it.',
                 body.x, yy, body.w)
            return yy - y + 52
        q = QI['q_trident']
        if not p.qc.get(q.id):
            text(c, 'The Broken Trident', body.x, yy, 'd', 21, SAND)
            yy += 36
            yy += _goal_rows(c, q, body.x, yy, body.w, True) + 14
            para(c, 'The Oracle Eel’s riddle points to three shards carried by fish across the bay. Recover them, then claim the quest reward.',
                 body.x, yy, body.w)
            return yy - y + 54
        text(c, 'The Red Hollow gate is open.', body.x, yy, 'd', 21, SEA)
        yy += 44
        if button(c, (body.x, yy, 230, 42), 'Enter Red Hollow', 'go', clip=body):
            close_panel()
            Wd.sailTo('redhollow')
            return yy - y + 52
        return yy - y + 62
    if p.biome == 'redhollow':
        if p.portal.ending:
            ending = 'The gate was repaired. The worlds remain joined.' if p.portal.ending == 'repair' else 'The gate was sealed. The worlds are safe, apart.'
            para(c, ending + ' The Keeper’s coat is yours.', body.x, yy, body.w)
            yy += 70
        elif p.qc.get('p_hollow'):
            text(c, 'Choose the fate of the gate', body.x, yy, 'd', 21, SAND)
            yy += 38
            para(c, 'The Watcher has fallen. Repairing the gate reunites the bay; sealing it protects both worlds from what lies beyond.',
                 body.x, yy, body.w)
            yy += 66
            if button(c, (body.x, yy, 210, 42), 'Repair the gate', 'go', clip=body):
                Wd.choosePortalEnding('repair')
            if button(c, (body.x + 226, yy, 210, 42), 'Seal the gate', '', clip=body):
                Wd.choosePortalEnding('seal')
            yy += 54
        else:
            q = QI['p_hollow']
            text(c, q.name, body.x, yy, 'd', 21, SAND)
            yy += 36
            yy += _goal_rows(c, q, body.x, yy, body.w, True) + 16
        if button(c, (body.x, yy, 230, 42), 'Return to Atlantis', '', clip=body):
            close_panel()
            Wd.sailTo('atlantis')
            return yy - y + 52
        return yy - y + 58
    para(c, 'The statue is not part of this island.', body.x, yy, body.w)
    return yy - y + 50


# ---------------- altar ----------------
def roll_enchant(target=None):
    p = P()
    if S.rolling or p.relics < 1:
        return
    target = target or None
    if target and target not in ENCH:
        target = None
    if target is None:
        p.relics -= 1
        Sfx.play('enchant')
        tot = sum(e.w for e in ENCHANTS)
        x = random.random() * tot
        choice = ENCHANTS[0]
        for e in ENCHANTS:
            x -= e.w
            if x <= 0:
                choice = e
                break
        S.rolling = D(t=0.0, n=0, pick=choice, shown=pick(ENCHANTS), rod=p.rod)
        return
    goal = ENCH[target]
    spins = 0
    while p.relics > 0:
        p.relics -= 1
        spins += 1
        Sfx.play('enchant')
        tot = sum(e.w for e in ENCHANTS)
        x = random.random() * tot
        choice = ENCHANTS[0]
        for e in ENCHANTS:
            x -= e.w
            if x <= 0:
                choice = e
                break
        if choice.id == target:
            rid = p.rod if p.rod in p.rods else next(iter(p.rods))
            p.rods[rid]['ench'] = choice.id
            p.stats.enchants += 1
            Sfx.play('level')
            Wd.toast(f'{ROD[rid].name} is now {choice.name}! It took {spins} relics.', 'gold' if choice.id == 'mythical' else 'good')
            S.rolling = None
            Wd.refreshStats()
            Wd.saveProfile()
            return
    Wd.toast(f'No more relics. You were hunting {goal.name} and the altar kept the luck for a while.', 'bad')
    S.rolling = None


def tick_rolling(dt):
    """The altar's spin keeps going even if you close the menu, so a relic is never lost."""
    R = S.rolling
    p = P()
    if not R or p is None:
        return
    R.t += dt
    while R.t > 0.09:
        R.t -= 0.09
        R.n += 1
        R.shown = pick(ENCHANTS) if R.n < 14 else R.pick
        if R.n > 14:
            rid = R.rod if R.rod in p.rods else p.rod
            p.rods[rid]['ench'] = R.pick.id
            p.stats.enchants += 1
            Sfx.play('level')
            Wd.toast(f'{ROD[rid].name} is now {R.pick.name}!', 'gold' if R.pick.id == 'mythical' else 'good')
            S.rolling = None
            Wd.refreshStats()
            Wd.saveProfile()
            return


def panel_altar(c, body, y, dt):
    p = P()
    rod = ROD[p.rod]
    cur = (p.rods.get(p.rod) or {}).get('ench')
    top = pygame.Rect(body.x, y, body.w, 150)
    box(c, top, (20, 58, 95, 140), (43, 90, 132, 204), 14)
    ib = pygame.Rect(top.x + 12, top.y + 12, 56, 56)
    box(c, ib, (7, 26, 46, 166), None, 12)
    icon(c, 'relic', ib.centerx, ib.centery, 1.6)
    text(c, rod.name, top.x + 80, top.y + 12, 'k', 16)
    if S.rolling:
        e = S.rolling.shown
        text(c, e.name, top.x + 80, top.y + 38, 'd', 22, hexc(e.col))
    elif cur:
        e = ENCH[cur]
        tr = text(c, 'Enchanted with ', top.x + 80, top.y + 38, 'b', 14, MIST)
        tr2 = text(c, e.name, tr.right, top.y + 38, 'k', 14, hexc(e.col))
        text(c, ': ' + e.desc, tr2.right, top.y + 38, 'b', 14, MIST)
    else:
        text(c, 'No enchantment yet. Offer a relic to roll one. A new roll replaces the old one.', top.x + 80, top.y + 38, 'b', 14, MIST)
    if S.altar_target is None:
        S.altar_target = 'mythical'
    target = ENCH.get(S.altar_target) or ENCHANTS[0]
    expected = sum(e.w for e in ENCHANTS) / target.w
    label = f'Roll until {target.name}'
    text(c, f'Target: {target.name} · expected {expected:.1f} relics', top.x + 80, top.y + 76, 'x', 12, MIST)
    if button(c, (top.x + 80, top.y + 98, 200, 36), 'The altar hums...' if S.rolling else label, 'go', bool(S.rolling) or p.relics < 1, clip=body):
        roll_enchant(S.altar_target)
    if button(c, (top.x + 290, top.y + 98, 120, 36), 'Random roll', '', bool(S.rolling), clip=body):
        roll_enchant()
    tot = sum(e.w for e in ENCHANTS)

    def item(c, r, e):
        q = (e.w / tot * 100)
        selected = S.altar_target == e.id
        if button(c, (r.x, r.y, r.w, r.h), '', 'tabon' if selected else '', clip=None):
            S.altar_target = e.id
        card(c, r, ('star', e.col), e.name, e.desc, [(f'{q:.1f}% chance', FOAM)], clip=body)
    return 166 + grid(c, body, y + 166, ENCHANTS, item, card_h=110)


# ---------------- sea chart ----------------
def chart_surface(w, h):
    k = ('chart', w, h)
    s = _cache.get(k)
    if s is None:
        s = pygame.Surface((w, h))
        for yy in range(h):
            pygame.draw.line(s, mix('#1c6aa0', '#0a2a4a', yy / h), (0, yy), (w, yy))
        grid_col = mix('#1c6aa0', '#ffffff', 0.08)
        for kk in range(0, max(w, h), 40):
            pygame.draw.line(s, grid_col, (kk, 0), (kk, h))
            pygame.draw.line(s, grid_col, (0, kk), (w, kk))
        segs = [((BIOMES[BIOMES[b].link].x * w, BIOMES[BIOMES[b].link].y * h), (BIOMES[b].x * w, BIOMES[b].y * h))
                for b in BIOME_IDS if BIOMES[b].link]
        for (x0, y0), (x1, y1) in segs:
            L = math.hypot(x1 - x0, y1 - y0)
            n = int(L / 14)
            for j in range(n):
                a, b = j / n, (j + 0.45) / n
                pygame.draw.line(s, (200, 180, 120), (x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b), 3)
        _cache[k] = s
    return s


_cache = {}


def panel_map(c, body, y, dt):
    p = P()
    w = body.w
    h = int(w * 9 / 16)
    if h > body.h - 40:
        h = body.h - 40
        w = int(h * 16 / 9)
    x = body.x + (body.w - w) // 2
    ch = pygame.Rect(x, y, w, h)
    c.blit(chart_surface(w, h), ch)
    pygame.draw.rect(c, LINE, ch, 1, border_radius=4)
    peers = online.peers.values() if online.active() else []
    for bid in BIOME_IDS:
        b = BIOMES[bid]
        if b.portal and not p.unlocked.get(bid):
            continue
        here = bid == p.biome
        ok, need = Wd.sailCheck(bid)
        why = 'You are here' if here else (need if not ok else f'Sail · {b.depth} m deep')
        bw = max(150, text_w(why, 'x', 12) + 26)
        cx, cy = x + b.x * w, y + b.y * h
        r = pygame.Rect(int(cx - bw / 2), int(cy - 28), bw, 56)
        lock = not ok
        hover = UI.over(r, body)
        box(c, r, (20, 58, 95, 235) if hover else (7, 26, 46, 210), SEA if here else (255, 255, 255, 120 if lock else 180), 14, 2, alpha=0.75 if lock else 1)
        text(c, b.name, r.centerx, r.y + 8, 'd', 17, FOAM, 'center', alpha=0.75 if lock else 1)
        text(c, why, r.centerx, r.y + 32, 'x', 12, MIST, 'center')
        friends = [q.name for q in peers if q.biome == bid]
        if friends:
            tag = ', '.join(friends[:3]) + (f' +{len(friends) - 3}' if len(friends) > 3 else '')
            text(c, tag, r.centerx, r.bottom + 4, 'k', 12, SEA, 'center', outline=2, ocol=(0, 0, 0, 140))
        if UI.take(r, body):
            if here:
                pass
            elif lock:
                Sfx.play('nope')
                Wd.toast(why + ' to sail there.', 'bad')
            else:
                close_panel()
                Wd.sailTo(bid)
                return h
    para(c, 'Each island has its own fish, depths and shop, and boats are sold at every dock. The first trip to a new island also needs '
            f'its level and the previous island\'s island quest (press {K("quests")}).' + (' Friends\' names show under the island they are on.' if online.active() else ''),
         body.x, y + h + 12, body.w)
    return h + 70


# ---------------- Fishpedia ----------------
def panel_dex(c, body, y, dt):
    p = P()
    tab = S.panel.tab or 'shore'
    if tab == 'logs':
        yy = y + para(c, 'Keeper’s Logs preserve the clues left along the Line. Catch a fish on an island or complete its island quest to recover its entry.',
                      body.x, y, body.w) + 10
        for entry in KEEPER_LOGS:
            found = entry.id in p.logs
            r = pygame.Rect(body.x, yy, body.w, 92)
            if r.bottom >= body.y and r.y <= body.bottom:
                box(c, r, (24, 52, 70, 170), (47, 211, 192, 125) if found else (43, 90, 132, 125), 13, 1)
                title = entry.title if found else 'Unrecovered entry'
                text(c, title, r.x + 14, r.y + 10, 'k', 16, SAND if found else MIST)
                text(c, BIOMES.get(entry.id, D(name='The Gate')).name, r.right - 14, r.y + 13, 'x', 12, MIST, 'right')
                para(c, entry.text if found else 'The ink is still hidden. Explore its waters and listen for the Keeper’s signal.',
                     r.x + 14, r.y + 38, r.w - 28, size=13, col=FOAM if found else MIST)
            yy += 102
        return yy - y
    if tab == 'odds':
        hgt = para(c, 'Base spawn odds. Luck from rods, bait, enchants and pets raises the rare ones. Every species lives around its own '
                      'favourite depth (see each fish\'s card): within its range it is at home, and every 50 m further away it gets about 35% less likely, '
                      'so you have to fish at the right depth. A few deep-island species only appear inside the marked cave mouths. The Firstlight Koi is '
                      'limited to three catches per server. Rare fish are also shy: they notice your hook less often than small fry, and bolt if '
                      'your hook dives fast. The first fish to touch your bait takes it. Mythics live only from the Deep Trench on, and they and the '
                      'bosses go quiet for a while after one shows up.', body.x, y, body.w)
        yy = y + hgt + 8
        for r in RAR:
            text(c, r.name, body.x + 4, yy + 7, 'k', 14, hexc(r.col))
            text(c, f'{r.w}%', body.right - 8, yy + 7, 'k', 14, FOAM, 'right')
            pygame.draw.line(c, (43, 90, 132), (body.x, yy + 32), (body.right, yy + 32))
            yy += 34
        text(c, 'Mutations', body.x, yy + 14, 'd', 18, MIST)
        yy += 46
        for m in MUTS:
            text(c, m.name, body.x + 4, yy + 7, 'k', 14, hexc(m.col))
            text(c, f'{m.chance * 100:.1f}% · value x{m.mult}', body.right - 8, yy + 7, 'k', 14, FOAM, 'right')
            pygame.draw.line(c, (43, 90, 132), (body.x, yy + 32), (body.right, yy + 32))
            yy += 34
        return yy - y + 10
    lst = [f for f in FISH if f.b == tab]

    def item(c, r, sp):
        d = p.dex.get(sp.id)
        rr = RAR[RI[sp.r]]
        box(c, r, (20, 58, 95, 115), (43, 90, 132, 180), 12)
        draw_portrait(c, sp, None, (r.centerx - 60, r.y + 8, 120, 60), not d, G.t + RI[sp.r] * 0.37)
        nm = sp.name if d else '???'
        while text_w(nm, 'k', 13) > r.w - 12 and len(nm) > 3:
            nm = nm[:-2] + '…'
        text(c, nm, r.centerx, r.y + 72, 'k', 13, FOAM, 'center')
        yy = r.y + 92
        lab = REEL[RI[sp.r]].label
        text(c, f'{max(0, sp.dz - sp.dr)}-{min(BIOMES[sp.b].depth, sp.dz + sp.dr)} m', r.centerx, r.bottom - (50 if sp.gim else 34), 'x', 11, (150, 210, 240), 'center')
        text(c, f'Reel: {lab}', r.centerx, r.bottom - 34 if sp.gim else r.bottom - 18, 'x', 11, hexc(rr.col), 'center')
        if sp.gim:
            names = ' · '.join(GIMMICKS[g].name for g in sp.gim) if d else 'Tricks: ???'
            for ln in wrap(names, 'x', 11, r.w - 12)[:1]:
                text(c, ln, r.centerx, r.bottom - 18, 'x', 11, (255, 200, 140) if d else MIST, 'center')
        if d:
            line = f'caught {d.n} · best {fmtW(d.kg)}'
            rw = text_w(rr.name + ' · ', 'b', 11)
            lw = text_w(line, 'b', 11)
            sx = r.centerx - (rw + lw) / 2
            text(c, rr.name + ' · ', sx, yy, 'b', 11, hexc(rr.col))
            text(c, line, sx + rw, yy, 'b', 11, MIST)
            yy += 15
            if d.muts:
                ms = [m for m in MUTS if m.id in d.muts]
                tot = sum(text_w(m.name, 'b', 11) + 6 for m in ms)
                sx = r.centerx - tot / 2
                for m in ms:
                    text(c, m.name, sx, yy, 'b', 11, hexc(m.col))
                    sx += text_w(m.name, 'b', 11) + 6
                yy += 15
            for ln in wrap(sp.desc, 'b', 11, r.w - 14)[:2 if sp.gim else 3]:
                text(c, ln, r.centerx, yy, 'b', 11, MIST, 'center')
                yy += 14
        else:
            text(c, rr.name, r.centerx, yy, 'b', 11, hexc(rr.col), 'center')
    return grid(c, body, y, lst, item, colmin=160, card_h=212, gap=8)


# ---------------- you ----------------
def panel_me(c, body, y, dt):
    p = P()
    s = p.stats
    rows = [('Casts', s.casts), ('Fish caught', s.catches), ('Got away', s.lost), ('Lines snapped', s.snapped), ('Lines burned', s.burned),
            ('Coins earned', fmt(s.earned)), ('Best single catch', fmt(s.bestCatch) + ' coins'), ('Mythics', s.mythics),
            ('Bosses defeated', s.bosses), ('Enchant rolls', s.enchants),
            ('Boss trophies', ', '.join(f'{v} {MATS[k].name}' for k, v in p.mats.items() if v) or 'None yet'), ('Fish caught by pets', s.petCatches or 0),
            ('Eggs hatched', s.hatched or 0), ('Time fishing', f'{round(s.play / 60)} min')]
    yy = y
    for k, v in rows:
        text(c, k, body.x + 4, yy + 7, 'b', 15, FOAM)
        text(c, str(v), body.right - 8, yy + 7, 'k', 15, FOAM, 'right')
        pygame.draw.line(c, (43, 90, 132), (body.x, yy + 33), (body.right, yy + 33))
        yy += 35
    text(c, 'How to fish', body.x, yy + 14, 'd', 18, MIST)
    yy += 46
    yy += para(c, f'Hold {K("act")} or the mouse button to charge a cast, let go to throw. Steer the sinking hook with {K("left")}/{K("right")}, '
                  f'{K("down")} dives faster, {K("up")} reels up, {K("act")} stops the hook at its depth. Fish that notice your bait race for it, and '
                  'the first one to touch it is hooked straight away, so steer the bait toward the fish you want (rare fish are shy and bolt if you '
                  f'dive fast). On the reel bar, hold to push your white bar right and let go to slide left; keep the fish inside it until the catch '
                  f'bar fills, before line tension hits the top. {K("recall")} pulls the line in.', body.x, yy, body.w)
    yy += 8
    yy += para(c, 'Rarer fish fight harder: they swim faster, your bar gets narrower and the catch bar drains quicker when they slip out. '
                  'Many fish also have tricks (Dash, Ink, Decoy, Warp and more). A warning bubble pops up just before a trick goes off, '
                  'and the Fishpedia lists the tricks of every fish you have caught.', body.x, yy, body.w)
    yy += 8
    yy += para(c, f'Every rod has an ability. Keep the fish inside your bar to charge it, then press {K("ability")} or right-click: '
                  'Tug, Quick Reel, Freeze, Slice, Inferno, Gravity Well, Tidal Slash and more. The Ability Charm (Gear) charges it faster.', body.x, yy, body.w)
    yy += 8
    yy += para(c, f'Quests ({K("quests")}): each island has an island quest you must finish (with the right level and boat) before you can sail '
                  'on, and two rod quests whose rods are made for that island. Every fish gives XP; the bar at the top shows how much you need '
                  'for the next level.', body.x, yy, body.w)
    yy += 8
    yy += para(c, 'Pets: from the Coral Reef on, the shop sells eggs. Pets ride in a little boat behind yours, grow while you play with them '
                  'aboard (Bag > Pets) and help a little: the seagull, otter and parrot give small boosts, the puppy speeds up your hook, and '
                  'Mittens the kitten catches fish on her own.', body.x, yy, body.w)
    yy += 8
    yy += para(c, 'Saves, controls and sound are in Settings. Playing online? Press T to chat, 1-5 for emotes (5 cheers on a friend fighting a boss), '
                  'and fishing near friends gives everyone a crew luck bonus. Saved Common fish act as a second bait bonus; press V to clear that bait when you want a fresh one.', body.x, yy, body.w)
    if button(c, (body.x + 260, yy + 8, 150, 34), 'Patch notes', 'go', clip=body):
        S.patch_notes = True
    return yy - y + 10


# ---------------- settings ----------------
def encode_save(p):
    raw = json.dumps(p, separators=(',', ':')).encode('utf-8')
    return 'WB1:' + base64.b64encode(zlib.compress(raw, 9)).decode('ascii')


def decode_save(s):
    s = ''.join(s.split())
    if s.startswith('WB1:'):
        raw = zlib.decompress(base64.b64decode(s[4:]))
        return json.loads(raw.decode('utf-8'))
    # also accept codes from the browser version (plain base64 JSON)
    return json.loads(base64.b64decode(s).decode('utf-8'))


def quit_to_title():
    close_panel()
    if online.active():
        Wd.saveProfile()
        online.leave()
    Wd.stopPlaying()
    S.chat_open = False
    UI.focus = None


def panel_settings(c, body, y, dt):
    p = P()
    tab = S.panel.tab or 'saves'
    now = time.time()
    if tab == 'saves':
        where = 'on the server you logged in to (and a backup on this computer)' if Wd.MODE == 'online' else 'on this computer'
        when = time.strftime('%H:%M:%S', time.localtime((p.last or 0) / 1000)) if p.last else 'never'
        yy = y + para(c, f'Playing as {p.name}. Progress saves {where} every 10 seconds and whenever you buy, sell or catch something. Last saved at {when}.', body.x, y, body.w)
        yy += 8
        bx = body.x
        if button(c, (bx, yy, 130, 38), 'Save now', 'go', clip=body):
            Wd.saveProfile()
            if online.active():
                online.flush_save(force=True)
            Wd.toast('Saved.', 'good')
        bx += 140
        label = 'Log out to title' if Wd.MODE == 'online' else 'Switch angler'
        if button(c, (bx, yy, text_w(label, 'k', 14) + 30, 38), label, '', clip=body):
            quit_to_title()
            return 0
        yy += 54
        text(c, 'Back up or move your save', body.x, yy, 'd', 18, MIST)
        yy += 30
        yy += para(c, f'Your saves are files in this folder: {settings.SAVE_DIR}. You can also copy a save code and paste it into Whisker Bay on another computer to bring this angler along.', body.x, yy, body.w)
        yy += 6
        if button(c, (body.x, yy, 180, 36), 'Copy save code', '', clip=body):
            code = encode_save(p)
            if ui.clipboard_put(code):
                Wd.toast('Save code copied. Paste it somewhere safe.', 'good')
            else:
                path = settings.SAVE_DIR + '/save_code.txt'
                try:
                    with open(path, 'w') as f:
                        f.write(code)
                    Wd.toast(f'Copying is not available here, so the code was written to {path}.', '')
                except OSError:
                    Wd.toast('Could not copy the save code.', 'bad')
        yy += 48
        submit = S.import_field.draw(c, (body.x, yy, body.w - 240, 40), clip=body, size=13)
        if button(c, (body.right - 228, yy, 228, 40), 'Load as a new angler', 'go', clip=body) or submit:
            try:
                raw = decode_save(S.import_field.text)
                np_ = Wd.sanitize(raw)
            except Exception:
                np_ = None
            if np_ is None:
                Sfx.play('nope')
                Wd.toast('That code is not a Whisker Bay save. Check you copied all of it.', 'bad')
            else:
                Wd.saveProfile()
                np_.id = Wd.new_id()
                Wd.saveLocal(np_)
                S.import_field.text = ''
                Wd.toast(f"Loaded {np_.name}'s save as an angler on this computer. Find it on the title screen.", 'good')
        yy += 56
        text(c, 'Danger zone', body.x, yy, 'd', 18, MIST)
        yy += 32
        armed = S.reset_arm > now
        if button(c, (body.x, yy, 260, 38), 'Click again: erase progress' if armed else 'Start this angler over', 'warn', clip=body):
            if armed:
                fresh = Wd.freshProfile(p.name, p.fur)
                fresh.id = p.id
                fresh.rev = (p.rev or 0) + 1
                S.reset_arm = 0
                close_panel()
                Wd.startPlaying(fresh, Wd.MODE)
                Wd.saveProfile()
                Wd.toast('Fresh start. Good luck out there.')
                return 0
            S.reset_arm = now + 3
        if Wd.MODE == 'local':
            armed = S.del_arm > now
            if button(c, (body.x + 272, yy, 250, 38), 'Click again to delete forever' if armed else 'Delete this angler', 'warn', clip=body):
                if armed:
                    pid = p.id
                    S.del_arm = 0
                    close_panel()
                    Wd.LIVE = False
                    Wd.deleteLocal(pid)
                    Wd.stopPlaying()
                    return 0
                S.del_arm = now + 3
        return yy + 50 - y
    if tab == 'controls':
        yy = y + para(c, 'Click a key to change it, then press the new key (Esc cancels). Each action can have two keys. The mouse button also casts, strikes and reels. F11 switches fullscreen.', body.x, y, body.w)
        yy += 6
        for a in DEFAULT_KEYS:
            text(c, ACTION_NAMES[a], body.x + 4, yy + 9, 'k', 14, FOAM)
            for slot in (0, 1):
                keys = SET['binds'].get(a) or []
                waiting = S.rebind == (a, slot)
                lab = 'Press a key...' if waiting else keyLabel(keys[slot] if slot < len(keys) else None)
                if button(c, (body.right - 230 + slot * 116, yy + 2, 108, 32), lab, 'tabon' if waiting else '', size=13, kind='x', clip=body):
                    S.rebind = (a, slot)
            pygame.draw.line(c, (43, 90, 132), (body.x, yy + 40), (body.right, yy + 40))
            yy += 42
        yy += 10
        if button(c, (body.x, yy, 210, 36), 'Reset keys to default', '', clip=body):
            SET['binds'] = json.loads(json.dumps(DEFAULT_KEYS))
            save_settings()
            Wd.toast('Keys reset.', 'good')
        yy += 50
        text(c, 'Emotes (online): ' + '   '.join(f'{i + 1} = {e.text}' for i, e in enumerate(EMOTES)), body.x, yy, 'x', 13, MIST)
        return yy + 30 - y
    if tab == 'updates':
        yy = y + para(c, 'These are the current release notes. They also appear once automatically after each game update.', body.x, y, body.w)
        yy += 10
        for note in PATCH_NOTES:
            lines = wrap(note, 'b', 14, body.w - 24)
            text(c, '•', body.x + 2, yy, 'k', 15, SAND)
            for line in lines:
                text(c, line, body.x + 22, yy, 'b', 14, FOAM)
                yy += 19
            yy += 9
        return yy - y
    # sound & display
    yy = y
    text(c, 'Volume', body.x + 4, yy + 10, 'k', 15)
    v = S.slider.draw(c, (body.x + 160, yy + 4, body.w - 260, 24), SET.get('vol', 0.8), 0, 1, clip=body)
    if abs(v - SET.get('vol', 0.8)) > 0.001:
        SET['vol'] = round(v, 2)
        save_settings()
        Sfx.refresh_volume()
    if not S.slider.drag and getattr(S, '_was_drag', False):
        Sfx.play('coin')
    S._was_drag = S.slider.drag
    text(c, f'{round(SET.get("vol", 0.8) * 100)}%', body.right - 10, yy + 10, 'k', 15, FOAM, 'right')
    yy += 48
    opts = [('Sound', not SET.get('muted'), lambda v: Sfx.set_muted(not v)),
            ('Screen shake', SET.get('shake', True), lambda v: SET.__setitem__('shake', v)),
            ('Fish names on sonar', SET.get('sonarNames', True), lambda v: SET.__setitem__('sonarNames', v)),
            ('Fullscreen (F11)', SET.get('fullscreen', False), lambda v: toggle_fullscreen(v)),
            ('Show frames per second', SET.get('showFps', False), lambda v: SET.__setitem__('showFps', v)),
            ('Fade old chat messages', SET.get('chatFade', True), lambda v: SET.__setitem__('chatFade', v))]
    for label, on, setter in opts:
        text(c, label, body.x + 4, yy + 8, 'k', 15)
        if ui.toggle(c, (body.right - 70, yy + 2, 56, 30), on, clip=body):
            setter(not on)
            save_settings()
        pygame.draw.line(c, (43, 90, 132), (body.x, yy + 40), (body.right, yy + 40))
        yy += 44
    return yy - y + 10


def toggle_fullscreen(v=None):
    want = (not SET.get('fullscreen')) if v is None else bool(v)
    try:
        cur = bool(pygame.display.is_fullscreen())
    except (AttributeError, pygame.error):
        cur = bool(SET.get('fullscreen'))
    if cur != want:
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass
    SET['fullscreen'] = want
    save_settings()


# ---------------- players & leaderboards ----------------
LB_TABS = [('coins', 'Richest'), ('level', 'Highest level'), ('best', 'Best catch'), ('dex', 'Fishpedia'), ('bosses', 'Bosses'), ('catches', 'Most fish')]


def panel_players(c, body, y, dt):
    tab = S.panel.tab or 'online'
    if tab == 'online':
        yy = y
        if not online.who:
            text(c, 'Asking the server...', body.x, yy, 'b', 14, MIST)
            return 40
        for w in online.who:
            r = pygame.Rect(body.x, yy, body.w, 50)
            box(c, r, (20, 58, 95, 120), (43, 90, 132, 160), 12)
            gfxdraw.filled_circle(c, r.x + 26, r.centery, 14, hexc(w.get('fur') or '#f4a53c'))
            gfxdraw.aacircle(c, r.x + 26, r.centery, 14, (255, 255, 255))
            me = w.get('n') == online.st.user
            text(c, w.get('n', '?') + ('  (you)' if me else ''), r.x + 52, r.centery, 'k', 16, SAND if me else FOAM, 'left', 'middle')
            text(c, f"Lv {w.get('lvl', 1)}  ·  {BIOMES.get(w.get('b'), BIOMES['shore']).name}", r.right - 14, r.centery, 'x', 13, MIST, 'right', 'middle')
            yy += 56
        yy += 6
        yy += para(c, 'Tip: sail to the same island as friends for a crew luck bonus (+5% per friend, up to +15%). Press 5 to cheer when someone fights a boss: it speeds up their reel.', body.x, yy, body.w)
        if button(c, (body.x, yy + 8, 120, 34), 'Refresh', '', clip=body):
            online.request_boards()
        return yy + 50 - y
    t = ui.tabs(c, body.x, y, LB_TABS, S.lb_tab, size=13, maxw=body.w)
    if t:
        S.lb_tab = t
    yy = y + 46
    lbd = online.lb
    if not lbd:
        text(c, 'Asking the server...', body.x, yy, 'b', 14, MIST)
        return 90
    rows = (lbd.get('boards') or {}).get(S.lb_tab) or []
    fmtv = {'coins': lambda v: f'{fmt(v)} coins', 'level': lambda v: f'Level {v}', 'best': lambda v: f'{fmt(v)} coins',
            'dex': lambda v: f'{v} / {len(FISH)} species', 'bosses': lambda v: f'{v} slain', 'catches': lambda v: f'{fmt(v)} fish'}[S.lb_tab]
    for i, row in enumerate(rows):
        r = pygame.Rect(body.x, yy, body.w, 44)
        me = row.get('n') == online.st.user
        box(c, r, (255, 217, 138, 40) if me else (20, 58, 95, 110), SAND if me else (43, 90, 132, 150), 10)
        medal = [(255, 210, 60), (200, 210, 225), (205, 127, 50)]
        text(c, f'#{i + 1}', r.x + 14, r.centery, 'd', 18, medal[i] if i < 3 else MIST, 'left', 'middle')
        gfxdraw.filled_circle(c, r.x + 70, r.centery, 11, hexc(row.get('fur') or '#f4a53c'))
        text(c, row.get('n', '?'), r.x + 90, r.centery, 'k', 15, FOAM, 'left', 'middle')
        text(c, fmtv(row.get('v', 0)), r.right - 14, r.centery, 'k', 14, SAND, 'right', 'middle')
        yy += 50
    if not rows:
        text(c, 'Nobody on this board yet. Go fish!', body.x, yy, 'b', 14, MIST)
        yy += 30
    text(c, f"{lbd.get('players', 0)} anglers have played on this server.", body.x, yy + 6, 'b', 13, MIST)
    return yy + 40 - y


# ===================================================================================
#  HUD
# ===================================================================================
def chip(c, x, y, label, col=FOAM, w=None):
    w = w or text_w(label, 'x', 14) + 26
    box(c, (x, y, w, 32), (7, 26, 46, 184), (234, 246, 255, 41), 16)
    text(c, label, x + w / 2, y + 16, 'x', 14, col, 'center', 'middle')
    UI.block((x, y, w, 32))
    return x + w + 8


def draw_hud(c, dt):
    p = P()
    W, H = G.W, G.H
    x, y = 12, 10
    x = chip(c, x, y, f'{fmt(p.coins)} coins', SAND)
    need = Wd.xpNeed(p.level)
    xpl = f'{fmt(p.xp)} / {fmt(need)} XP'
    lw = text_w(f'Lv {p.level}', 'x', 14)
    bwid = max(84, text_w(xpl, 'x', 11) + 6)
    w = lw + 26 + bwid + 8
    box(c, (x, y, w, 32), (7, 26, 46, 184), (234, 246, 255, 41), 16)
    text(c, f'Lv {p.level}', x + 13, y + 16, 'x', 14, FOAM, 'left', 'middle')
    bx = x + 13 + lw + 8
    box(c, (bx, y + 7, bwid, 6), (255, 255, 255, 36), None, 3)
    frac = clamp(p.xp / need, 0, 1)
    if frac > 0.02:
        box(c, (bx, y + 7, max(4, int(bwid * frac)), 6), SEA, None, 3)
    text(c, xpl, bx + bwid / 2, y + 22, 'x', 11, MIST, 'center', 'middle')
    x += w + 8
    x = chip(c, x, y, Wd.BIO().name)
    left_end = x
    if online.active():
        x, y = 12, 48          # online status goes on a second row so it never hits the buttons
        st = online.st
        if st.phase == 'in':
            n = len(online.visible_peers())
            lab = f'Online · {n} here' if n else 'Online'
            xw = text_w(lab, 'x', 14) + 40
            box(c, (x, y, xw, 32), (7, 26, 46, 184), (47, 211, 192, 120), 16)
            gfxdraw.filled_circle(c, x + 16, y + 16, 5, SEA)
            text(c, lab, x + 27, y + 16, 'x', 14, FOAM, 'left', 'middle')
            x += xw + 8
        else:
            x = chip(c, x, y, 'Reconnecting...', DANGER)
        if G.crew:
            chip(c, x, y, f'Crew +{min(15, 5 * G.crew)}% luck', SEA)
    y = 10
    # right-hand buttons
    items = [('bag', f'Bag {len(p.bag)}/{Wd.holdSize()}', 'bag'), ('shop', 'Shop', 'shop')]
    if p.biome == 'reef':
        items.append(('altar', 'Altar', 'altar'))
    short = p.name if len(p.name) <= 10 else p.name[:9] + '…'
    if p.biome in ('atlantis', 'redhollow') and p.portal.started:
        items.append(('charm', 'Statue', 'portal'))
    items += [('map', 'Sail', 'map'), ('dex', 'Fishpedia', 'dex'), ('quest', 'Quests', 'quests'), ('me', short, 'me')]
    if online.active():
        items.append(('players', 'Players', 'players'))
        if online.st.admin:
            items.append(('star', 'Admin', 'admin'))
    items.append(('settings', 'Settings', 'settings'))
    widths = [text_w(lab, 'x', 14) + 46 for _, lab, _ in items]
    room = W - 12 - 48 - left_end - 12
    for kind in ('settings', 'admin', 'me', 'players', 'map', 'quests', 'dex', 'shop', 'altar', 'portal'):
        if sum(widths) + 6 * len(widths) <= room:
            break
        for i, (_, _, k) in enumerate(items):
            if k == kind:
                widths[i] = 40
    waiting = bool(Wd.questsWaiting())
    rx = W - 12 - 40
    sound_r = pygame.Rect(rx, y, 40, 36)
    if button(c, sound_r, '', 'hud', radius=14):
        Sfx.set_muted(not Sfx.muted)
        save_settings()
    icon(c, 'mute' if Sfx.muted else 'sound', sound_r.centerx, sound_r.centery, 1.0)
    rx -= 8
    for (ic, lab, kind), bw in reversed(list(zip(items, widths))):
        rx -= bw
        r = pygame.Rect(rx, y, bw, 36)
        hot = kind == 'bag' and len(p.bag) >= Wd.holdSize() or (kind == 'shop' and G.nearDock) or (kind == 'quests' and waiting)
        if button(c, r, '', 'hot' if hot else 'hud', radius=14):
            open_panel(kind)
        if bw > 40:
            icon(c, ic, r.x + 19, r.centery, 0.95)
            text(c, lab, r.x + 33, r.centery, 'x', 14, FOAM, 'left', 'middle')
        else:
            icon(c, ic, r.centerx, r.centery, 0.95)
        if kind == 'quests' and waiting:
            gfxdraw.filled_circle(c, r.right - 4, r.y + 4, 6, DANGER)
            gfxdraw.aacircle(c, r.right - 4, r.y + 4, 6, (255, 255, 255))
        rx -= 6
    # bait chip
    b = BAIT.get(p.bait) if p.bait else None
    n = (p.baits.get(p.bait) or 0) if b else 0
    lab = f'{b.name} x{n}' if b and n else 'No bait'
    bw = text_w(lab, 'x', 14) + 46
    r = pygame.Rect(12, H - 48, bw, 36)
    if button(c, r, '', 'hud', radius=14):
        open_panel('bag', 'bait')
    icon(c, 'bait' if b and n else 'hook', r.x + 19, r.centery, 0.9, hexc(b.dot) if b and n else FOAM)
    text(c, lab, r.x + 33, r.centery, 'x', 14, FOAM, 'left', 'middle')


def hint_text():
    if not Wd.LIVE:
        return ''
    p = P()
    m = G.mode
    if m == 'idle':
        if len(p.bag) >= Wd.holdSize():
            return 'Your bag is full. Open the Bag to sell.'
        if G.nearDock:
            return f"You're at the dock: press {K('shop')} for the shop · hold {K('act')} to cast"
        return f"{K('left')}/{K('right')} to sail · hold {K('act')} or click to cast, then let go"
    if m == 'charge':
        return 'Let go to cast. A fuller meter throws further.'
    if m == 'sinking':
        return (f"Steer the bait to the fish you want with {K('left')}/{K('right')} · {K('down')} dives · {K('up')} reels up · {K('act')} "
                f"{'lets it sink again' if G.hook.hold else 'holds this depth'} · {K('recall')} pulls in")
    if m == 'bite':
        return 'Fish on! Get ready to reel...'
    if m == 'reel':
        return f"Hold {K('act')} to push your bar right, let go to slide left · {K('ability')} or right-click: rod ability"
    return ''


def draw_hint(c):
    h = hint_text()
    if h and not S.panel:
        text(c, h, G.W / 2, G.H - 30, 'x', 14, FOAM, 'center', 'middle', outline=2, ocol=(0, 0, 0, 170))


def draw_toasts(c):
    y = 56
    for ts in G.toasts:
        a = 1.0 if ts.t < ts.dur else max(0.0, 1 - (ts.t - ts.dur) / 0.45)
        a *= min(1.0, ts.t / 0.2)
        lines = wrap(ts.msg, 'x', 14, 520)
        w = max(text_w(ln, 'x', 14) for ln in lines) + 28
        h = len(lines) * 19 + 14
        border = {'good': SEA, 'bad': DANGER, 'gold': SAND}.get(ts.kind, LINE)
        col = {'bad': (255, 208, 216), 'gold': SAND}.get(ts.kind, FOAM)
        yy = y - (1 - min(1.0, ts.t / 0.25)) * 8
        box(c, (G.W / 2 - w / 2, yy, w, h), (7, 26, 46, 235), border, 12, alpha=a)
        for i, ln in enumerate(lines):
            text(c, ln, G.W / 2, yy + 7 + i * 19, 'x', 14, col, 'center', alpha=a)
        y += h + 6


def name_col(name):
    h = 0
    for ch in name:
        h = (h * 31 + ord(ch)) & 0xffffff
    cols = ['#ffd98a', '#7cf0ff', '#9dffb0', '#ff9ec7', '#ffb070', '#c9b0ff', '#8fd3ff', '#ffe14d']
    return hexc(cols[h % len(cols)])


def draw_chat(c):
    if not online.active():
        S.chat_open = False
        return
    now = time.time()
    W, H = G.W, G.H
    x, w = 12, 470
    bottom = H - 60
    lines = []
    show = online.chat[-12:] if S.chat_open else online.chat[-7:]
    for m in show:
        age = now - m.t
        a = 1.0 if S.chat_open or not SET.get('chatFade', True) else clamp((14 - age) / 2, 0, 1)
        if a <= 0:
            continue
        lines.append((m, a))
    rows = []
    for m, a in lines:
        if m.kind == 'chat':
            prefix = m.who + ': '
            pw = text_w(prefix, 'k', 14)
            wl = wrap(m.text, 'b', 14, w - 20 - pw)
            for i, ln in enumerate(wl):
                rows.append((m, a, prefix if i == 0 else None, ln, pw))
        else:
            for ln in wrap(m.text, 'x', 13, w - 20):
                rows.append((m, a, None, ln, 0))
    rows = rows[-14:]
    lh = 19
    if S.chat_open:
        hgt = len(rows) * lh + 56
        box(c, (x, bottom - hgt, w, hgt), (7, 26, 46, 200), (234, 246, 255, 40), 12)
        UI.block((x, bottom - hgt, w, hgt))
    yy = bottom - (44 if S.chat_open else 0) - len(rows) * lh
    for m, a, prefix, ln, pw in rows:
        if m.kind == 'chat':
            if prefix:
                text(c, prefix, x + 10, yy, 'k', 14, name_col(m.who), alpha=a, outline=1, ocol=(0, 0, 0, 160))
            text(c, ln, x + 10 + pw, yy, 'b', 14, FOAM, alpha=a, outline=1, ocol=(0, 0, 0, 160))
        else:
            col = hexc(m.col) if m.col else (MIST if m.kind == 'sys' else (255, 200, 240))
            text(c, ln, x + 10, yy, 'x', 13, col, alpha=a, outline=1, ocol=(0, 0, 0, 160))
        yy += lh
    if S.chat_open:
        UI.focus = S.chat_field
        if S.chat_field.draw(c, (x + 6, bottom - 42, w - 12, 36), size=14):
            online.send_chat(S.chat_field.text)
            S.chat_field.text = ''
            S.chat_open = False
            UI.focus = None
    elif online.st.phase == 'in':
        text(c, f"{K('chat')} to chat", x + 2, bottom + 0, 'x', 12, (159, 194, 227, 150))


def open_chat():
    if online.active():
        S.chat_open = True
        UI.focus = S.chat_field
        if G.act:
            Wd.actUp()
        G.keys = {}


def close_chat():
    S.chat_open = False
    if UI.focus is S.chat_field:
        UI.focus = None


# ===================================================================================
#  Title, profiles and login
# ===================================================================================
def title_veil():
    v = _cache.get('veil')
    if v is None:
        def fn(u, vv):
            d = math.hypot((u - 0.5) * 1.2, (vv - 0.3))
            k = clamp(d / 0.8, 0, 1)
            a = 0.16 + (0.62 - 0.16) * k
            col = mix((14, 42, 70), (2, 8, 16), k)
            return col + (int(255 * a),)
        v = _cache['veil'] = ui.radial_surface(G.W, G.H, fn, (128, 72))
    return v


def draw_patch_notes(c):
    W, H = G.W, G.H
    overlay = pygame.Rect(W * 0.12, H * 0.12, W * 0.76, H * 0.76)
    ui.overlay(c, (2, 8, 16), 0.72)
    box(c, overlay, (13, 36, 67, 210), (18, 46, 80, 220), 18)
    text(c, 'Patch notes', overlay.centerx, overlay.y + 28, 'd', 28, SAND, 'center')
    text(c, 'Scroll to read every update', overlay.centerx, overlay.y + 50, 'x', 12, MIST, 'center')
    inner = pygame.Rect(overlay.x + 18, overlay.y + 72, overlay.w - 42, overlay.h - 128)
    content_h = 0
    for note in PATCH_NOTES:
        content_h += len(wrap(note, 'b', 13, inner.w - 28)) * 18 + 8
    S.patch_scroll.content = content_h
    off = S.patch_scroll.update(inner)
    old_clip = c.get_clip()
    c.set_clip(inner)
    y = inner.y - off
    for note in PATCH_NOTES:
        text(c, '•', inner.x + 2, y + 4, 'k', 14, SAND)
        for ln in wrap(note, 'b', 13, inner.w - 28):
            text(c, ln, inner.x + 22, y, 'b', 13, FOAM)
            y += 18
        y += 8
    c.set_clip(old_clip)
    S.patch_scroll.bar(c, inner)
    if button(c, (overlay.right - 132, overlay.bottom - 44, 116, 36), 'Close', 'go', clip=overlay):
        S.patch_notes = False


def draw_title(c, dt):
    W, H = G.W, G.H
    c.blit(title_veil(), (0, 0))
    ts = _cache.get('title')
    if ts is None:
        f = ui.font('d', 92)
        t1 = f.render('Whisker Bay', True, SAND)
        sh = f.render('Whisker Bay', True, hexc('#a3561c'))
        from .art import _blur
        ts = pygame.Surface((t1.get_width() + 60, t1.get_height() + 60), pygame.SRCALPHA)
        dark = pygame.Surface(ts.get_size(), pygame.SRCALPHA)
        dark.blit(f.render('Whisker Bay', True, (0, 0, 0)), (30, 34))
        dark = _blur(dark, 12)
        dark.fill((255, 255, 255, 140), special_flags=pygame.BLEND_RGBA_MULT)
        ts.blit(dark, (0, 0))
        ts.blit(sh, (30, 26))
        ts.blit(t1, (30, 20))
        _cache['title'] = ts
    c.blit(ts, (W / 2 - ts.get_width() / 2, 2))
    text(c, "A cat, a boat, and four islands of fish that really don't want to be caught.", W / 2, 140, 'x', 16, FOAM, 'center', outline=2, ocol=(0, 0, 0, 140))
    from . import __version__
    if not S.patch_notes and SET.get('seenPatchNotes') != __version__:
        S.patch_notes = True
        SET['seenPatchNotes'] = __version__
        save_settings()
    if button(c, (W - 146, 20, 120, 28), 'Patch notes', 'tabon'):
        S.patch_notes = True
    text(c, f'v{__version__}', W - 12, H - 10, 'x', 12, (234, 246, 255, 150), 'right', 'bottom', outline=2, ocol=(0, 0, 0, 120))
    if S.patch_notes:
        draw_patch_notes(c)
        UI.block((0, 0, W, H))
        return
    tabs = [('local', 'Play on this computer'), ('online', 'Play online with friends')]
    tw = sum(text_w(l, 'k', 15) + 28 for _, l in tabs) + 6
    t = ui.tabs(c, W / 2 - tw / 2, 178, tabs, S.title_tab, size=15)
    if t and t != S.title_tab:
        S.title_tab = t
        UI.focus = None
    pw = 620
    area = pygame.Rect(W / 2 - pw / 2, 224, pw, H - 240)
    if S.title_tab == 'local' and online.st.phase in ('off',):
        title_local(c, area)
    else:
        if S.title_tab != 'online':
            S.title_tab = 'online'
        title_online(c, area, dt)
    UI.block((0, 0, W, H))


def title_local(c, area):
    lst = Wd.readIndex()
    newh = 176
    lh = min(len(lst) * 72, area.h - newh - 14)
    y = area.y
    if lst:
        clip = pygame.Rect(area.x, y, area.w, lh)
        off = S.title_scroll.update(clip)
        S.title_scroll.content = len(lst) * 72
        old = c.get_clip()
        c.set_clip(clip)
        yy = y - off
        for e in lst:
            r = pygame.Rect(area.x, yy, area.w - 14, 64)
            if r.bottom >= clip.y and r.y <= clip.bottom:
                box(c, r, (14, 42, 70, 217), LINE, 16)
                gfxdraw.filled_circle(c, r.x + 33, r.centery, 21, hexc(e.fur or FURS[0]))
                gfxdraw.aacircle(c, r.x + 33, r.centery, 21, (200, 210, 220))
                text(c, e.name, r.x + 66, r.y + 11, 'k', 17)
                text(c, f'Level {e.level} · {fmt(e.coins or 0)} coins · {e.dex or 0} species', r.x + 66, r.y + 36, 'x', 13, MIST)
                if button(c, (r.right - 100, r.y + 14, 86, 36), 'Play', 'go', clip=clip):
                    p = Wd.loadLocal(e.id)
                    if p is None:
                        Wd.toast('That save could not be read.', 'bad')
                    else:
                        Wd.startPlaying(p, 'local')
                        Wd.toast(f'Welcome back, {p.name}!', 'good')
                        c.set_clip(old)
                        return
            yy += 72
        c.set_clip(old)
        S.title_scroll.bar(c, clip)
        y += lh + 14
    r = pygame.Rect(area.x, y, area.w - 14, newh)
    box(c, r, (14, 42, 70, 217), LINE, 16)
    text(c, 'New angler', r.x + 16, r.y + 12, 'k', 16)
    sub = S.name_field.draw(c, (r.x + 16, r.y + 40, r.w - 32, 44), size=16)
    fx = r.x + 16
    for f in FURS[:-1]:
        rr = pygame.Rect(fx, r.y + 96, 38, 38)
        sel = f == S.new_fur
        gfxdraw.filled_circle(c, rr.centerx, rr.centery, 17, hexc(f))
        gfxdraw.aacircle(c, rr.centerx, rr.centery, 17, hexc(f))
        if sel:
            pygame.draw.circle(c, SAND, rr.center, 20, 3)
        if UI.over(rr):
            UI.hot = True
        if UI.take(rr):
            S.new_fur = f
        fx += 46
    if button(c, (r.right - 180, r.y + 96, 164, 40), 'Start fishing', 'go') or sub:
        name = S.name_field.text.strip()[:16] or 'Whiskers'
        p = Wd.freshProfile(name, S.new_fur)
        Wd.startPlaying(p, 'local')
        Wd.saveProfile()
        S.name_field.text = ''
        UI.focus = None
        Wd.toast(f'Welcome to Whisker Bay, {name}! Hold {K("act")} or click to cast.', 'good')


def title_online(c, area, dt):
    st = online.st
    r = pygame.Rect(area.x, area.y, area.w - 14, min(area.h, 470))
    box(c, r, (14, 42, 70, 225), LINE, 16)
    x, y, w = r.x + 18, r.y + 14, r.w - 36
    if st.phase == 'connecting':
        text(c, st.status or 'Connecting...', r.centerx, r.y + 60, 'k', 18, FOAM, 'center')
        dots = int(time.time() * 3) % 4
        text(c, '.' * dots, r.centerx, r.y + 88, 'd', 26, SAND, 'center')
        if button(c, (r.centerx - 60, r.y + 140, 120, 38), 'Cancel', ''):
            online.cancel()
        return
    if st.phase == 'newangler':
        text(c, f'Welcome, {st.user}!', x, y, 'd', 24, SAND)
        y += 40
        y += para(c, 'Your account is ready. Pick a fur colour and start fresh, or bring one of the anglers saved on this computer along.', x, y, w)
        y += 10
        fx = x
        for f in FURS[:-1]:
            rr = pygame.Rect(fx, y, 38, 38)
            gfxdraw.filled_circle(c, rr.centerx, rr.centery, 17, hexc(f))
            gfxdraw.aacircle(c, rr.centerx, rr.centery, 17, hexc(f))
            if f == S.new_fur:
                pygame.draw.circle(c, SAND, rr.center, 20, 3)
            if UI.take(rr):
                S.new_fur = f
            fx += 46
        if button(c, (r.right - 200, y, 182, 40), 'Start fishing', 'go'):
            online.new_online_angler(S.new_fur)
            return
        y += 58
        lst = Wd.readIndex()[:5]
        if lst:
            text(c, 'Or bring an angler from this computer:', x, y, 'k', 14, MIST)
            y += 26
            for e in lst:
                rr = pygame.Rect(x, y, w, 44)
                box(c, rr, (20, 58, 95, 150), (43, 90, 132, 180), 12)
                gfxdraw.filled_circle(c, rr.x + 22, rr.centery, 13, hexc(e.fur or FURS[0]))
                text(c, f'{e.name}  ·  Level {e.level}  ·  {fmt(e.coins or 0)} coins', rr.x + 44, rr.centery, 'x', 14, FOAM, 'left', 'middle')
                if button(c, (rr.right - 92, rr.y + 5, 84, 34), 'Bring', 'go', size=13):
                    online.new_online_angler(S.new_fur, bring=e.id)
                    return
                y += 50
        if button(c, (x, r.bottom - 52, 110, 36), 'Cancel', ''):
            online.close()
        return
    # logged out: show the login form
    rem = SET.get('remember')
    if rem and rem.get('token'):
        text(c, f"Continue as {rem.get('user')}", x, y, 'd', 22, SAND)
        text(c, f"on {rem.get('server')}", x, y + 32, 'x', 14, MIST)
        if button(c, (r.right - 300, y + 4, 160, 40), 'Continue', 'go'):
            online.start('resume', rem.get('server'), rem.get('user'), token=rem.get('token'), remember=True)
            return
        if button(c, (r.right - 130, y + 4, 112, 40), 'Log out', ''):
            SET['remember'] = None
            save_settings()
        y += 64
        pygame.draw.line(c, (43, 90, 132), (x, y), (x + w, y))
        y += 12
        text(c, 'Or use another account:', x, y, 'k', 13, MIST)
        y += 24
    fields = [('Server address', S.srv_field), ('Username', S.user_field), ('Password', S.pw_field)]
    if st.needCode:
        fields.append(('Invite code', S.code_field))
    submit = False
    lw = 140
    for label, fld in fields:
        text(c, label, x, y + 20, 'k', 14, FOAM, 'left', 'middle')
        if fld.draw(c, (x + lw, y, w - lw, 40), size=15):
            submit = True
        y += 48
    if UI.focus in [f for _, f in fields]:
        for key, mod in UI.keys:
            if key == pygame.K_TAB:
                fl = [f for _, f in fields]
                i = fl.index(UI.focus)
                UI.focus = fl[(i + (-1 if mod & pygame.KMOD_SHIFT else 1)) % len(fl)]
    on = S.remember
    if ui.toggle(c, (x + lw, y + 2, 50, 28), on):
        S.remember = not on
    text(c, 'Keep me logged in on this computer', x + lw + 62, y + 16, 'x', 14, FOAM, 'left', 'middle')
    y += 44
    bl = button(c, (x + lw, y, 150, 42), 'Log in', 'go')
    br = button(c, (x + lw + 160, y, 190, 42), 'Create account', '')
    y += 50
    if not st.needCode:
        if button(c, (x + lw - 6, y - 4, 210, 28), 'I have an invite code', 'ghost', size=13, kind='x', col=MIST):
            st.needCode = True
        y += 28
    if bl or br or submit:
        srv, user, pw = S.srv_field.text, S.user_field.text, S.pw_field.text
        if not user or not pw:
            st.error = 'Type a username and password first.'
        else:
            UI.focus = None
            online.start('register' if br else 'login', srv, user, pw, S.code_field.text, S.remember)
            return
    if st.error:
        for ln in wrap(st.error, 'k', 14, w):
            text(c, ln, x, y, 'k', 14, (255, 160, 175))
            y += 19
        y += 4
    para(c, "No server yet? One friend runs \"Start Server\" (see READ ME FIRST.txt) and shares the address it shows. "
            "Passwords travel unencrypted to the host's computer, so use one you don't use anywhere else.", x, y, w, 'b', 13, MIST)


# ===================================================================================
#  The frame
# ===================================================================================
def draw(c, dt):
    if Wd.LIVE:
        tick_rolling(dt)
        click = UI.click
        if S.panel:            # the menu is on top: the HUD underneath must not take its clicks
            UI.click = None
        draw_hud(c, dt)
        draw_chat(c)
        draw_hint(c)
        UI.click = click
        if S.panel:
            draw_panel(c, dt)
        draw_toasts(c)
    else:
        S.panel = None
        draw_title(c, dt)
        draw_toasts(c)
    if SET.get('showFps'):
        S.fps = S.fps * 0.9 + (1 / max(dt, 1e-3)) * 0.1
        text(c, f'{S.fps:.0f} fps', G.W - 8, G.H - 8, 'x', 12, MIST, 'right', 'bottom')
