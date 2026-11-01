"""Pets, the little pet boat they ride in, and the eggs they hatch from. All painted in code, like the fish."""
import math

import pygame

from .art import Pen, draw_cat
from .data import PET, RAR, RI
from .util import D, TAU, hexc, mix

_icons = {}


# ===================================================================================
#  Pets (drawn facing right, sitting on the origin, about 40 units tall)
# ===================================================================================
def _eye(c, x, y, r, blink):
    if blink:
        c.begin()
        c.move(x - r, y)
        c.line(x + r, y)
        c.stroke((40, 26, 20), r * 0.7, 'round')
        return
    c.begin()
    c.ellipse(x, y, r, r * 1.15)
    c.fill((30, 20, 18))
    c.begin()
    c.circle(x + r * 0.35, y - r * 0.4, r * 0.38)
    c.fill((255, 255, 255))


def pup(c, t, lvl=1, pull=0.0):
    fur, dk_, cr = hexc('#d9a25a'), hexc('#a8733a'), hexc('#f6e2c0')
    wag = math.sin(t * 9) * 0.5
    c.begin()
    c.move(-14, -10)
    c.quad(-24, -18 + wag * 6, -22 - wag * 4, -28)
    c.stroke(fur, 5, 'round')
    c.begin()
    c.ellipse(-4, -12, 14, 12)
    c.fill(fur)
    c.begin()
    c.ellipse(0, -9, 7, 8)
    c.fill(cr)
    for k, px in enumerate((-10, 4)):
        c.begin()
        c.ellipse(px, -1, 5, 3)
        c.fill(dk_ if k == 0 else fur)
    hx, hy = 8, -28 - abs(math.sin(t * 2)) * 1.2 + pull * 2
    c.begin()
    c.ellipse(hx, hy, 12, 11)
    c.fill(fur)
    flop = math.sin(t * 3) * 0.15
    for s, ex in ((-1, hx - 9), (1, hx + 7)):
        c.begin()
        c.ellipse(ex, hy + 4, 4.5, 9, rot=0.25 * s + flop)
        c.fill(dk_)
    c.begin()
    c.ellipse(hx + 8, hy + 4, 7, 5.5)
    c.fill(cr)
    c.begin()
    c.ellipse(hx + 13, hy + 1.5, 3, 2.4)
    c.fill((40, 26, 20))
    blink = (t % 3.7) < 0.12
    _eye(c, hx + 3, hy - 3, 2.2, blink)
    c.begin()
    c.ellipse(hx + 9, hy + 9 + abs(math.sin(t * 6)) * 1.2, 2.4, 3.2)
    c.fill('#ff7a8a')
    if lvl >= 10:
        c.begin()
        c.ellipse(hx - 2, hy + 10, 9, 2.5)
        c.fill('#ffd23d')
        c.begin()
        c.circle(hx + 2, hy + 13, 2.2)
        c.fill('#ffe98a')


def gull(c, t, lvl=1):
    flap = math.sin(t * 7)
    body, wing, tip = (244, 246, 248), (200, 208, 216), (60, 64, 72)
    c.begin()
    c.ellipse(0, 0, 13, 7)
    c.fill(body)
    for s in (1, 0.85):
        c.begin()
        c.move(-4, -2)
        c.quad(-6, -14 * flap * s - 4, -20, -16 * flap * s - 2)
        c.line(-24, -14 * flap * s)
        c.quad(-10, -4 * flap, 4, -1)
        c.close()
        c.fill(wing if s == 1 else mix(wing, '#000000', 0.12))
        c.begin()
        c.move(-20, -16 * flap * s - 2)
        c.line(-24, -14 * flap * s)
        c.line(-18, -13 * flap * s)
        c.close()
        c.fill(tip)
    c.begin()
    c.move(-12, 0)
    c.line(-20, -3)
    c.line(-20, 3)
    c.close()
    c.fill(body)
    c.begin()
    c.circle(10, -4, 6)
    c.fill(body)
    c.begin()
    c.move(15, -4)
    c.line(23, -2.5)
    c.line(15, -1)
    c.close()
    c.fill('#ffc23d')
    c.begin()
    c.circle(21.5, -2.5, 0.9)
    c.fill('#e0402a')
    _eye(c, 12, -6, 1.3, (t % 4.3) < 0.1)


def otter(c, t, lvl=1):
    fur, dk_, cr = hexc('#8a5a3a'), hexc('#5e3b24'), hexc('#d8b894')
    bob = math.sin(t * 1.8) * 1.5
    c.save()
    c.translate(0, bob)
    c.begin()
    c.ellipse(0, 0, 18, 7.5)
    c.fill(fur)
    c.begin()
    c.ellipse(1, -2, 12, 4.5)
    c.fill(cr)
    c.begin()
    c.move(-16, 0)
    c.quad(-26, -2, -30, 2 + math.sin(t * 2) * 2)
    c.stroke(dk_, 4.5, 'round')
    c.begin()
    c.circle(17, -5, 7.5)
    c.fill(fur)
    c.begin()
    c.ellipse(21, -3, 4.2, 3.4)
    c.fill(cr)
    c.begin()
    c.circle(24, -4, 1.4)
    c.fill((30, 20, 18))
    for ex in (13, 17):
        c.begin()
        c.circle(ex, -12, 2.2)
        c.fill(dk_)
    _eye(c, 19, -7.5, 1.4, (t % 3.3) < 0.12)
    c.begin()
    c.circle(2, -8 - abs(math.sin(t * 1.5)) * 2, 3.4)
    c.fill('#a8b0b8')
    c.begin()
    c.circle(1.2, -9 - abs(math.sin(t * 1.5)) * 2, 1.1)
    c.fill((230, 236, 240))
    for px in (-1, 5):
        c.begin()
        c.ellipse(px, -6.5, 2.4, 1.8)
        c.fill(dk_)
    c.restore()


def parrot(c, t, lvl=1):
    sway = math.sin(t * 1.4) * 0.06
    c.save()
    c.rotate(sway)
    c.begin()
    c.move(-3, -6)
    c.line(-9, 12)
    c.line(-1, 9)
    c.close()
    c.fill('#2a6ad0')
    c.begin()
    c.ellipse(0, -16, 9, 13)
    c.fill('#2fbf4a')
    c.begin()
    c.ellipse(-2, -14, 6, 10)
    c.fill('#1f9a38')
    c.begin()
    c.ellipse(-3, -10, 4, 7)
    c.fill('#ffd23d')
    c.begin()
    c.circle(3, -30, 7.5)
    c.fill('#e83a3a')
    c.begin()
    c.move(8, -32)
    c.quad(15, -31, 12, -24)
    c.line(9, -26)
    c.close()
    c.fill('#3a3a40')
    c.begin()
    c.circle(5, -32, 3)
    c.fill((255, 255, 255))
    _eye(c, 5.5, -32, 1.5, (t % 2.9) < 0.1)
    c.begin()
    c.move(-4, -36)
    c.line(12, -36)
    c.line(10, -40)
    c.line(4, -43)
    c.line(-2, -40)
    c.close()
    c.fill((30, 30, 36))
    c.begin()
    c.circle(4, -39, 1.4)
    c.fill((240, 240, 240))
    for px in (-2, 3):
        c.begin()
        c.move(px, -3)
        c.line(px + 1, 1)
        c.stroke('#8a8a8a', 1.6, 'round')
    c.restore()


def kitten(c, t, lvl=1, mode='idle'):
    c.save()
    c.scale(0.48)
    draw_cat(c, 0, 0, D(fur='#f2ede4', rod='starter', mode=mode, t=t + 1.7, biome='shore', ten=0.2))
    c.restore()


PAINT = {'pup': pup, 'gull': gull, 'otter': otter, 'parrot': parrot, 'kitten': kitten}
KITTEN_TIP = (90 * 0.48, -104 * 0.48)     # where the kitten's little rod ends


def pet_icon(pid, size=56, lvl=1):
    """A pet's portrait for cards (cached)."""
    key = (pid, size, lvl >= 10)
    s = _icons.get(key)
    if s is None:
        ss = 3
        big = pygame.Surface((size * ss, size * ss), pygame.SRCALPHA)
        c = Pen(big, aa=False)
        c.scale(ss * size / 56)
        if pid == 'kitten':
            c.translate(27, 50)
            c.scale(0.92)
        elif pid == 'gull':
            c.translate(30, 32)
            c.scale(1.4)
        elif pid == 'otter':
            c.translate(24, 36)
            c.scale(1.25)
        elif pid == 'parrot':
            c.translate(26, 52)
            c.scale(1.05)
        else:
            c.translate(27, 47)
            c.scale(1.12)
        PAINT[pid](c, 0.6, lvl)
        s = _icons[key] = pygame.transform.smoothscale(big, (size, size))
    return s


# ===================================================================================
#  The pet boat
# ===================================================================================
def draw_pet_boat(surf, x, y, S, t, pets, levels=None, kit=None):
    """A little boat with your pets in it. kit: the kitten's catch animation (D(t, sp, tier)) or None."""
    levels = levels or {}
    c = Pen(surf, aa=True)
    roll = math.sin(t * 1.5 + 1) * 0.045
    by = y + math.sin(t * 1.9 + 0.7) * 2 * S
    c.save()
    c.translate(x, by)
    c.rotate(roll)
    c.scale(S)
    hl = 46
    # seats are filled from the back
    seat = {}
    order = [p for p in pets if p in PAINT and p not in ('gull', 'otter')]
    spots = [(-14, -6), (16, -6)]
    for i, p in enumerate(order[:2]):
        seat[p] = spots[i] if len(order) > 1 else (2, -6)
    if 'parrot' in seat:
        px, py = seat['parrot']
        c.begin()
        c.move(px, py + 4)
        c.line(px, py - 40)
        c.stroke('#7a5232', 3)
        c.begin()
        c.move(px - 10, py - 38)
        c.line(px + 10, py - 38)
        c.stroke('#7a5232', 3, 'round')
    for p, (px, py) in seat.items():
        c.save()
        if p == 'parrot':
            c.translate(px, py - 38)
            c.scale(0.8)
            parrot(c, t, levels.get(p, 1))
        elif p == 'kitten':
            c.translate(px, py + 2)
            kitten(c, t, levels.get(p, 1), 'reel' if kit and kit.t < 1.0 else 'card' if kit and kit.t < 2.2 else 'idle')
        else:
            c.translate(px, py + 2)
            c.scale(0.9)
            PAINT[p](c, t, levels.get(p, 1))
        c.restore()
    # hull
    c.begin()
    c.move(-hl, -8)
    c.line(hl + 8, -11)
    c.quad(hl - 2, 16, hl - 26, 18)
    c.line(-hl + 22, 18)
    c.quad(-hl + 3, 15, -hl, -8)
    c.fill_linear(0, -8, 0, 20, [(0, '#e8c48a'), (1, '#9a7448')], bands=10)
    c.begin()
    c.rect(-hl, -10, 2 * hl + 8, 3.5)
    c.fill((255, 255, 255, 100))
    # a paw print on the side
    c.begin()
    c.ellipse(-2, 6, 4.2, 3.4)
    for dx, dy in ((-5, 1), (-2, -1.8), (2, -1.8), (5, 1)):
        c.circle(-2 + dx * 0.9, 6 + dy - 3, 1.6)
    c.fill((255, 255, 255, 150))
    c.restore()
    out = D(tip=None)
    if 'kitten' in seat:
        px, py = seat['kitten']
        cs, sn = math.cos(roll), math.sin(roll)
        tx, ty = px + KITTEN_TIP[0], py + 2 + KITTEN_TIP[1]
        out.tip = (x + (tx * cs - ty * sn) * S, by + (tx * sn + ty * cs) * S)
    if 'otter' in pets:
        c.save()
        c.translate(x - (hl + 30) * S, y + 6 * S)
        c.scale(S * 0.95)
        otter(c, t, levels.get('otter', 1))
        c.restore()
    if 'gull' in pets:
        gx = x + math.sin(t * 0.5) * 70 * S
        gy = y - (95 + math.sin(t * 1.1) * 14) * S
        c.save()
        c.translate(gx, gy)
        c.scale(S * 0.9 * (1 if math.cos(t * 0.5) > 0 else -1), S * 0.9)
        gull(c, t, levels.get('gull', 1))
        c.restore()
    return out


# ===================================================================================
#  Eggs
# ===================================================================================
def draw_egg(c, egg, x, y, r, t=0.0, wobble=0.0, crack=0.0):
    """An egg of radius r (it is 1.3 r tall), wobbling and cracking while it hatches."""
    c.save()
    c.translate(x, y)
    c.rotate(math.sin(t * 18) * 0.12 * wobble)
    c.begin()
    c.ellipse(0, r * 1.25, r * 0.8, r * 0.18)
    c.fill((0, 0, 0, 50))
    c.begin()
    c.ellipse(0, 0, r, r * 1.3)
    c.fill_radial(-r * 0.3, -r * 0.5, 0, 0, 0, r * 1.3, [(0, mix(egg.col, '#ffffff', 0.55)), (0.55, egg.col), (1, mix(egg.col, '#000000', 0.35))], rings=12)
    c.begin()
    for k in range(6):
        a = k * 1.7 + 0.4
        c.circle(math.cos(a) * r * 0.5, math.sin(a * 1.3) * r * 0.7, r * (0.12 + 0.04 * (k % 3)))
    c.fill(hexc(egg.spot) + (220,))
    c.begin()
    c.ellipse(-r * 0.35, -r * 0.6, r * 0.22, r * 0.34)
    c.fill((255, 255, 255, 110))
    if crack > 0:
        c.begin()
        pts = [(-r * 0.95, -r * 0.1), (-r * 0.6, -r * 0.3), (-r * 0.35, 0.05 * r), (-r * 0.05, -r * 0.3), (r * 0.25, 0), (r * 0.55, -r * 0.28), (r * 0.95, -r * 0.05)]
        n = max(2, int(len(pts) * min(1.0, crack)))
        c.move(*pts[0])
        for p in pts[1:n]:
            c.line(*p)
        c.stroke((40, 30, 30, 220), max(1.5, r * 0.06), 'round')
    c.restore()


def egg_icon(egg, size=56):
    key = ('egg', egg.id, size)
    s = _icons.get(key)
    if s is None:
        ss = 3
        big = pygame.Surface((size * ss, size * ss), pygame.SRCALPHA)
        c = Pen(big, aa=False)
        c.scale(ss)
        draw_egg(c, egg, size / 2, size / 2 + 1, size * 0.32)
        s = _icons[key] = pygame.transform.smoothscale(big, (size, size))
    return s


def rarity_col(pid):
    return RAR[RI[PET[pid].r]].col
