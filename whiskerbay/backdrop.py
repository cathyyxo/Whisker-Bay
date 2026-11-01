"""The world behind the fish: skies, islands, water and light, rock walls, the seabed, and the life around the bay."""
import math
import random

import pygame
from pygame import gfxdraw

from . import ui
from . import world as Wd
from .art import Pen, _blur, blit_fish
from .data import BIOME_IDS, BIOMES, CAVES, FISH, RI
from .sfx import Sfx
from .util import D, TAU, clamp, hexc, lerp, mix, rand

G = Wd.G
_cache = {}


def sy(d):
    return Wd.sy(d)


# ===================================================================================
#  Looks for each island
# ===================================================================================
THEME = {
    'shore': D(
        sky=[(0, '#2766c9'), (0.42, '#5aa8f5'), (0.8, '#ffd2a0'), (1, '#ffe6bf')],
        water=[(0, '#4cc7ea'), (0.04, '#2aa2d6'), (0.22, '#1479b2'), (0.55, '#0b4880'), (1, '#031a33')],
        surf='#7fe0ff', sheen='#ffe3b8', far='#a5c4de', mid='#6e9fbf', midhi='#94bcd6', haze='#ffe1bc',
        mid_span=(0.40, 0.95), cloud=('#ffffff', '#c4d3e8', '#ffffff', 0.95), sun='sun', birds=True, sail=True,
        jumps=True, caustic=1.0, rays=1.0, floor='#dcc290', floor2='#a88c5c', wall='#b89a66', wallhi='#dcc290',
        school='#c9d9e6', plants='seagrass', sand='#f2d9a0', sand2='#cfae74', grass='#5fae4a', rock='#8a8f99',
        hut='#d9a066', roof='#c94b3b', palm='#3f9a4a'),
    'reef': D(
        sky=[(0, '#0f86de'), (0.45, '#3ac2fb'), (0.85, '#c2f6ff'), (1, '#e4fdff')],
        water=[(0, '#69ecec'), (0.04, '#2bd0d4'), (0.2, '#139fb8'), (0.55, '#0b5a82'), (1, '#031c31')],
        surf='#a0faff', sheen='#e6fdff', far='#a9e2ea', mid='#62bfc3', midhi='#8ad6d8', haze='#e6fdff',
        mid_span=(0.42, 0.95), cloud=('#ffffff', '#cfe4f0', '#ffffff', 0.95), sun='sun', birds=True, sail=True,
        jumps=True, rainbow=True, caustic=1.3, rays=1.15, floor='#f4ddb0', floor2='#c9aa76', wall='#d98a6a',
        wallhi='#f5b494', school='#ffd23d', turtle=True, plants='coral', sand='#fbe6c2', sand2='#dcbd8a',
        grass='#4fc98a', rock='#a09080', hut='#d9a066', roof='#c94b3b', palm='#2fbf7a'),
    'volcano': D(
        sky=[(0, '#0e0509'), (0.4, '#331016'), (0.78, '#9a3420'), (1, '#ff8a3d')],
        water=[(0, '#a8482a'), (0.04, '#7a2e22'), (0.2, '#4c1a1c'), (0.5, '#260b10'), (1, '#070205')],
        surf='#d0663a', sheen='#ff9a50', far='#5c2a30', mid='#3a1a20', midhi='#6a3038', haze='#ff8a4a',
        mid_span=(0.30, 0.62), cloud=('#4a3238', '#ff7a3d', '#6e5050', 0.9), stars=0.3, ash=True,
        caustic=0.55, caus_tint=(255, 150, 70), rays=0.0, floor='#2b2224', floor2='#120d0f', wall='#2e2224', wallhi='#6a3a30',
        plants='rocks', sand='#3b2e30', sand2='#241a1c', rock='#2a2224', hut='#5a4040', roof='#7a2a20'),
    'trench': D(
        sky=[(0, '#02030a'), (0.5, '#070f28'), (0.85, '#17244e'), (1, '#2a3d70')],
        water=[(0, '#235a84'), (0.04, '#173f64'), (0.18, '#0c2645'), (0.5, '#040e1e'), (1, '#000004')],
        surf='#4f86b8', sheen='#3a5590', far='#1d2a55', mid='#121a38', midhi='#26325f', haze='#2a3d70',
        mid_span=(0.40, 0.95), cloud=('#26315c', '#121a36', '#6676b4', 0.55), sun='moon', stars=1.0,
        aurora=True, milky=True, caustic=0.45, caus_tint=(120, 190, 255), rays=0.25, floor='#151824', floor2='#07080e', wall='#0e1426',
        wallhi='#1d2a4a', school='glow', jellies=True, plants='crystals', sand='#2a3048', sand2='#181d30',
        rock='#1a1f30', hut='#3a4458', roof='#3a4a7a', specks=260, speck_cols=['#5affd8', '#5acfff', '#b48cff'],
        floorglow=True, sign='DEEP SUPPLY'),
    'pallid': D(
        sky=[(0, '#39424b'), (0.45, '#66717b'), (0.85, '#a9b2b9'), (1, '#c3c9ce')],
        water=[(0, '#5d8290'), (0.04, '#41677a'), (0.2, '#24414f'), (0.5, '#0c1922'), (1, '#02060a')],
        surf='#8fb2be', sheen='#cdd7dc', far='#76838e', mid='#525e68', midhi='#73808a', haze='#c4ccd2',
        mid_span=(0.36, 0.9), cloud=('#a7b0b8', '#6b757e', '#d2d8dc', 0.97), birds=True, sail=True,
        caustic=0.45, caus_tint=(170, 205, 220), rays=0.35, floor='#5c5d5a', floor2='#26292b', wall='#3b4046', wallhi='#68717a',
        school='#c8d4dc', jellies=True, plants='kelp', sand='#8d8e88', sand2='#5d5e5a', grass='#7a8a62', rock='#5c6166',
        hut='#6a5440', roof='#3c3436', specks=120, speck_cols=['#9fe8ff', '#dfe8f0', '#7fd0c0'], speck_k=0.7,
        jelly_cols=['#dfe8f0', '#9fe8ff', '#c8d8ff'], sign="WHALER'S REST"),
    'frost': D(
        sky=[(0, '#050d1a'), (0.45, '#0d2240'), (0.85, '#285878'), (1, '#55889e')],
        water=[(0, '#6ac8e0'), (0.04, '#3a9ec4'), (0.2, '#1a5a80'), (0.5, '#071e34'), (1, '#01060c')],
        surf='#bfefff', sheen='#e8fbff', far='#b9d4e6', mid='#87adc6', midhi='#eef8ff', haze='#8fbcd6',
        mid_span=(0.3, 0.95), cloud=('#3a5a78', '#1a2e48', '#8ab0d0', 0.55), sun='moon', stars=1.0, aurora=True,
        caustic=0.5, caus_tint=(170, 230, 255), rays=0.3, floor='#c8d8e0', floor2='#4a5a68', wall='#7d9ab2', wallhi='#e8f4ff',
        school='#e0f0ff', jellies=True, plants='ice', sand='#eef6fa', sand2='#aac0d0', rock='#7a8a98',
        hut='#7a5a48', roof='#c8322a', specks=110, speck_cols=['#9fe8ff', '#e8fbff', '#bfa0ff'], speck_k=0.75,
        jelly_cols=['#9fe8ff', '#bfa0ff', '#e8fbff'], floorglow=True, sign='ICE OUTPOST', snow=True, bergs=True),
    'mariana': D(
        sky=[(0, '#0b1a3c'), (0.42, '#3a3a7c'), (0.8, '#e07a5a'), (1, '#ffb070')],
        water=[(0, '#2a8ac8'), (0.02, '#1a6aa8'), (0.08, '#0c3a6a'), (0.2, '#04162e'), (0.6, '#010409'), (1, '#000002')],
        surf='#7fd0ff', sheen='#ffc8a0', far='#3e3a6e', mid='#2a2850', midhi='#6a4a7a', haze='#ff9a7a',
        mid_span=(0.52, 0.9), cloud=('#ffb090', '#7a4a6a', '#ffd8b8', 0.85), sun='sun', birds=True,
        caustic=0.6, caus_tint=(150, 210, 255), rays=0.6, floor='#2a2a30', floor2='#08080c', wall='#14181e', wallhi='#2a3038',
        school='glow', jellies=True, plants='vents', sand='#e0d0a8', sand2='#b09a70', grass='#4fae5a', rock='#5a5a60',
        hut='#e8e8e0', roof='#3a6aa8', palm='#2fa060', specks=700, speck_cols=['#7fbfff', '#ff9ad8', '#9fffe8'], speck_k=0.8,
        jelly_cols=['#9fffe8', '#ff9ad8', '#bfa0ff'], floorglow=True, sign='DIVE STATION', marinesnow=True, palms=True),
    'loch': D(
        sky=[(0, '#4a5560'), (0.45, '#77838a'), (0.85, '#b4bcb8'), (1, '#cfd4cc')],
        water=[(0, '#5a5a3a'), (0.03, '#4a3e22'), (0.12, '#2a2010'), (0.4, '#120c04'), (1, '#050301')],
        surf='#8a9a8a', sheen='#c8d0c4', far='#6a7a72', mid='#5a4a68', midhi='#8a6a98', haze='#c4ccc4',
        mid_span=(0.34, 1.0), cloud=('#9aa4a8', '#5e686e', '#c8d0d0', 0.97), birds=True,
        caustic=0.3, caus_tint=(200, 180, 120), rays=0.25, floor='#2a2016', floor2='#0e0a06', wall='#2a241c', wallhi='#4a4030',
        school='#a8a890', plants='kelp', sand='#7a6a4a', sand2='#4a3e2a', grass='#5a7a3a', rock='#6a6a62',
        hut='#8a8070', roof='#3a4a5a', specks=90, speck_cols=['#c8b878', '#9a8a5a', '#c8ff9a'], speck_k=0.6,
        jelly_cols=['#bfffd0', '#e8f0c8'], sign='LOCHSIDE INN', castle=True),
    'atlantis': D(
        sky=[(0, '#263c50'), (0.45, '#608b83'), (0.85, '#c5b77e'), (1, '#eee0aa')],
        water=[(0, '#79d8bb'), (0.04, '#48b89f'), (0.2, '#1d827a'), (0.55, '#124653'), (1, '#04141d')],
        surf='#a7f2d5', sheen='#e8f4bd', far='#99b8a0', mid='#547e79', midhi='#82a994', haze='#d4ce99',
        mid_span=(0.36, 0.95), cloud=('#e9e3be', '#7a9381', '#fff0bd', 0.82), sun='sun', stars=0.15,
        caustic=0.85, caus_tint=(140, 255, 205), rays=0.7, floor='#d9d0ad', floor2='#716b55',
        wall='#596b5b', wallhi='#c7b982', school='#9be8c5', plants='coral', sand='#d9d0ad', sand2='#91876a',
        grass='#59a98a', rock='#8b927d', hut='#c7b982', roof='#54786d', specks=120,
        speck_cols=['#9fffe8', '#ffe08a', '#b5f7cf'], speck_k=0.8, jelly_cols=['#9fffe8', '#d2f7c4', '#ffe08a'],
        floorglow=True, sign='THE DROWNED CITY'),
    'redhollow': D(
        sky=[(0, '#090513'), (0.45, '#30102e'), (0.82, '#9d2445'), (1, '#e34b58')],
        water=[(0, '#a63d74'), (0.04, '#74295f'), (0.2, '#491d50'), (0.55, '#21102f'), (1, '#080510')],
        surf='#ff7188', sheen='#ffb0a1', far='#55213f', mid='#361536', midhi='#6b254c', haze='#cb4a5e',
        mid_span=(0.32, 0.9), cloud=('#391533', '#160c22', '#9b2848', 0.7), sun='moon', stars=1.0,
        caustic=0.24, caus_tint=(255, 55, 100), rays=0.15, floor='#321c35', floor2='#100a18',
        wall='#25142d', wallhi='#79354b', school='glow', plants='crystals', sand='#54243b', sand2='#29132c',
        grass='#7a294e', rock='#3a203b', hut='#54243b', roof='#3a1537', specks=260,
        speck_cols=['#ff5272', '#ff9b9b', '#c875ff'], speck_k=0.82,
        jelly_cols=['#ff5272', '#e76bba', '#bb74ff'], floorglow=True, sign='THE FRACTURE'),
}


def TH():
    return THEME[Wd.P.biome]


def bidx(bid):
    return BIOME_IDS.index(bid) if bid in BIOME_IDS else 0


# ===================================================================================
#  Small helpers
# ===================================================================================
def stops_col(stops, u):
    if u <= stops[0][0]:
        return hexc(stops[0][1])
    for i in range(len(stops) - 1):
        o0, c0 = stops[i]
        o1, c1 = stops[i + 1]
        if u <= o1:
            return mix(c0, c1, 0 if o1 == o0 else (u - o0) / (o1 - o0))
    return hexc(stops[-1][1])


def vgrad(w, h, stops):
    s = pygame.Surface((max(1, w), max(1, h)))
    for y in range(h):
        pygame.draw.line(s, stops_col(stops, y / max(1, h - 1)), (0, y), (w, y))
    return s


_nrng = random.Random(9001)
_NZ = [_nrng.random() for _ in range(1024)]


def noise1(v):
    fl = math.floor(v)
    f = v - fl
    i = int(fl) & 1023
    a, b = _NZ[i], _NZ[(i + 1) & 1023]
    return a + (b - a) * f * f * (3 - 2 * f)


def fbm(v):
    return noise1(v) * 0.6 + noise1(v * 2.13 + 17.3) * 0.28 + noise1(v * 4.61 + 3.7) * 0.12


def _falloff():
    s = _cache.get('falloff')
    if s is None:
        n = 40
        s = pygame.Surface((n, n))
        for y in range(n):
            for x in range(n):
                d = math.hypot((x + 0.5) / n * 2 - 1, (y + 0.5) / n * 2 - 1)
                v = int(255 * max(0.0, 1 - d) ** 2)
                s.set_at((x, y), (v, v, v))
        _cache['falloff'] = s
    return s


def glow_add(r, col, k=1.0):
    """A soft additive glow (an RGB picture you add on top with BLEND_RGB_ADD)."""
    r = max(2, int(r))
    if r > 16:
        r = r // 4 * 4
    lv = int(clamp(round(k * 6), 1, 6))
    key = ('gadd', r, col, lv)
    s = _cache.get(key)
    if s is None:
        s = pygame.transform.smoothscale(_falloff(), (2 * r, 2 * r))
        cr, cg, cb = hexc(col)
        f = lv / 6
        s.fill((int(cr * f), int(cg * f), int(cb * f)), special_flags=pygame.BLEND_RGB_MULT)
        _cache[key] = s
    return s


def add_glow(c, x, y, r, col, k=1.0):
    if k <= 0.06:
        return
    s = glow_add(r, col, k)
    c.blit(s, (x - s.get_width() / 2, y - s.get_height() / 2), special_flags=pygame.BLEND_RGB_ADD)


def overlay_rect(c, rect, col, a):
    r = pygame.Rect(rect)
    if r.w <= 0 or r.h <= 0 or a <= 0.004:
        return
    k = ('ov', r.w, r.h, col)
    s = _cache.get(k)
    if s is None:
        s = pygame.Surface((r.w, r.h))
        s.fill(col)
        _cache[k] = s
    s.set_alpha(int(255 * clamp(a, 0, 1)))
    c.blit(s, r.topleft)


def sky_h():
    return int(G.H * 0.42) + 2


def clear_caches():
    _cache.clear()
    AMB.bid = None


# ===================================================================================
#  Pictures painted once per island
# ===================================================================================
def sky_surface(bid):
    key = ('sky', bid)
    s = _cache.get(key)
    if s is not None:
        return s
    Th = THEME[bid]
    W, h = G.W, sky_h()
    s = vgrad(W, h, Th.sky)
    rng = random.Random(bidx(bid) * 7 + 3)
    if Th.milky:
        lay = pygame.Surface((W, h), pygame.SRCALPHA)
        lay.fill((140, 150, 210, 0))
        pts = [(x, h * 0.62 - x / W * h * 0.5 + math.sin(x * 0.01) * 10) for x in range(-40, W + 41, 40)]
        pygame.draw.lines(lay, (140, 150, 210, 64), False, pts, 46)
        lay = _blur(lay, 18)
        s.blit(lay, (0, 0))
        for _ in range(1500):
            u = rng.random()
            x = u * W
            y = h * 0.62 - u * h * 0.5 + math.sin(x * 0.01) * 10 + rng.gauss(0, 16)
            if 0 <= y < h and 0 <= x < W:
                p = (int(x), int(y))
                s.set_at(p, mix(s.get_at(p)[:3], (230, 235, 255), rng.uniform(0.12, 0.45)))
    if Th.stars:
        for _ in range(int(240 * Th.stars)):
            p = (rng.randrange(W), rng.randrange(int(h * 0.9)))
            s.set_at(p, mix(s.get_at(p)[:3], (255, 255, 255), rng.random() * 0.55 * Th.stars))
    if Th.rainbow:
        lay = pygame.Surface((W, h), pygame.SRCALPHA)
        cx, cy, R = W * 0.36, h * 1.32, h * 1.0
        for i, col in enumerate(('#ff4a4a', '#ff9f3a', '#ffe14d', '#5ae070', '#3ab8ff', '#5a6cff', '#b06bff')):
            pygame.draw.circle(lay, hexc(col) + (40,), (int(cx), int(cy)), int(R - i * 6), 6)
        lay = _blur(lay, 3)
        fade = pygame.Surface((W, h), pygame.SRCALPHA)
        for y in range(h):
            pygame.draw.line(fade, (255, 255, 255, int(255 * clamp(1.45 - y / h * 1.55, 0, 1))), (0, y), (W, y))
        lay.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(lay, (0, 0))
    _cache[key] = s
    return s


def sun_sprite():
    s = _cache.get('sun')
    if s is None:
        R = int(170 * G.S)

        def fn(u, v):
            d = math.hypot(u - 0.5, v - 0.5) * 2
            if d >= 1:
                return (255, 236, 180, 0)
            if d < 0.13:
                return (255, 253, 238, 255)
            if d < 0.17:
                k = (d - 0.13) / 0.04
                return (255, int(253 - 10 * k), int(238 - 40 * k), int(255 - 70 * k))
            k = (d - 0.17) / 0.83
            return (255, 236, 186, int(185 * (1 - k) ** 2.6))
        s = _cache['sun'] = ui.radial_surface(2 * R, 2 * R, fn, (96, 96))
    return s


def moon_sprite():
    s = _cache.get('moon')
    if s is None:
        R = int(30 * G.S)
        size = R * 6
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        glow = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(glow, (170, 195, 255, 120), (size // 2, size // 2), int(R * 1.6))
        s.blit(_blur(glow, int(R * 0.8)), (0, 0))
        c = size // 2
        pygame.draw.circle(s, hexc('#eef3ff'), (c, c), R)
        spots = pygame.Surface((size, size), pygame.SRCALPHA)
        for dx, dy, r in ((-0.32, -0.18, 0.2), (0.22, 0.2, 0.16), (-0.08, 0.42, 0.11), (0.3, -0.36, 0.09), (-0.45, 0.25, 0.08)):
            pygame.draw.circle(spots, (178, 188, 214, 120), (int(c + dx * R), int(c + dy * R)), int(r * R))
        s.blit(_blur(spots, 2), (0, 0))
        shade = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(shade, (255, 255, 255, 255), (c, c), R)
        pygame.draw.circle(shade, (0, 0, 0, 0), (int(c + R * 0.45), int(c - R * 0.25)), int(R * 0.95))
        dark = pygame.Surface((size, size), pygame.SRCALPHA)
        dark.fill((20, 26, 60, 150))
        dark.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(dark, (0, 0))
        _cache['moon'] = s
    return s


def _make_cloud(rng, w, base, shade, hi, alpha):
    flat = int(w * 0.62) + 14
    W2, H2 = int(w * 1.35) + 24, flat + int(w * 0.08) + 14
    sh, bc, hc = hexc(shade), hexc(base), hexc(hi)
    lay = pygame.Surface((W2, H2), pygame.SRCALPHA)
    lay.fill(sh + (0,))
    n = rng.randint(6, 9)
    blobs = []
    for i in range(n):
        u = i / (n - 1)
        r = (0.13 + 0.17 * math.sin(u * math.pi)) * w * rng.uniform(0.85, 1.12)
        x = W2 * 0.14 + u * W2 * 0.72 + rng.uniform(-0.04, 0.04) * w
        y = flat - r * 0.62 + rng.uniform(-0.02, 0.02) * w
        blobs.append((x, y, r))
    for x, y, r in blobs:
        pygame.draw.circle(lay, sh + (255,), (x, y), r)
    for x, y, r in blobs:
        pygame.draw.circle(lay, bc + (255,), (x - r * 0.05, y - r * 0.17), r * 0.9)
    for x, y, r in blobs[1:-1]:
        if rng.random() < 0.65:
            pygame.draw.circle(lay, hc + (255,), (x - r * 0.2, y - r * 0.34), r * 0.5)
    pygame.draw.rect(lay, sh + (0,), (0, flat, W2, H2 - flat))
    lay = _blur(lay, max(2, int(w * 0.022)))
    lay.fill((255, 255, 255, int(255 * alpha)), special_flags=pygame.BLEND_RGBA_MULT)
    return lay


def cloud_sprites(bid):
    key = ('clouds', bid)
    lst = _cache.get(key)
    if lst is None:
        base, shade, hi, alpha = THEME[bid].cloud
        rng = random.Random(42 + bidx(bid))
        lst = [_make_cloud(rng, rng.uniform(120, 270) * G.S, base, shade, hi, alpha) for _ in range(9)]
        _cache[key] = lst
    return lst


def _ridge(c, rng, x0, x1, base, hmax, col, rough, rim=None):
    n = 65
    hs = [0.0] * n
    hs[0], hs[-1] = rng.random(), rng.random()
    step, amp = n - 1, 1.0
    while step > 1:
        half = step // 2
        for i in range(half, n - 1, step):
            hs[i] = (hs[i - half] + hs[i + half]) / 2 + (rng.random() - 0.5) * amp
        step, amp = half, amp * rough
    lo, hi = min(hs), max(hs)
    pts = []
    c.begin()
    c.move(x0, base)
    for i in range(n):
        u = i / (n - 1)
        env = math.sin(u * math.pi) ** 0.55
        y = base - (0.22 + 0.78 * (hs[i] - lo) / ((hi - lo) or 1)) * hmax * env
        x = lerp(x0, x1, u)
        c.line(x, y)
        pts.append((x, y))
    c.line(x1, base)
    c.close()
    c.fill(col)
    if rim:
        c.begin()
        for x, y in pts:
            c.line(x, y + 1.2)
        c.stroke(rim, 1.4)


def island_profile(t):
    """A point on the home island's outline (t from 0 at the left to 1 at the shoreline)."""
    W, Sc = G.W, G.S
    iw = island_w()
    top = 0.0
    p0, p1, p2 = (-10, top - 52 * Sc), (iw * 0.55, top - 82 * Sc), (iw * 1.05, top + 6)
    u = 1 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0], u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def island_w():
    return max(120, G.W * 0.13)


def land_layer(bid):
    """Mountains, the volcano, the home island, the dock and the shop: painted once (supersampled)."""
    key = ('land', bid)
    v = _cache.get(key)
    if v is not None:
        return v
    Th = THEME[bid]
    W, Sc = G.W, G.S
    LH, below, ss = int(300 * Sc), 18, 2
    big = pygame.Surface((W * ss, (LH + below) * ss), pygame.SRCALPHA)
    c = Pen(big)
    c.scale(ss)
    top = LH
    rng = random.Random(bidx(bid) * 31 + 5)
    _ridge(c, rng, W * 0.16, W + 30, top, 84 * Sc, Th.far, 0.62)
    if bid == 'volcano':
        vx, vh = W * 0.82, 230 * Sc
        c.begin()
        c.move(vx - 270 * Sc, top)
        c.quad(vx - 140 * Sc, top - vh * 0.55, vx - 52 * Sc, top - vh)
        c.line(vx + 42 * Sc, top - vh)
        c.quad(vx + 150 * Sc, top - vh * 0.5, vx + 290 * Sc, top)
        c.close()
        c.fill_linear(0, top - vh, 0, top, [(0, '#3a2427'), (1, '#1a1012')], bands=10)
        for _ in range(12):
            x = vx + rng.uniform(-170, 190) * Sc
            y = top - rng.uniform(10, 150) * Sc
            c.begin()
            c.move(x, y)
            c.line(x + rng.uniform(-14, 14) * Sc, y + rng.uniform(12, 30) * Sc)
            c.stroke((15, 8, 10, 140), 2)
    span = Th.mid_span or (0.4, 0.95)
    _ridge(c, rng, W * span[0], W * span[1], top, 46 * Sc, Th.mid, 0.5, rim=Th.midhi)
    if Th.castle:
        _castle(c, rng, W * 0.74, top, Sc)
    if Th.bergs:
        for bx, bw, bh in ((0.47, 70, 34), (0.66, 120, 62), (0.9, 90, 44)):
            x0 = W * bx
            pts = [(x0 - bw * Sc / 2, top)]
            n = 7
            for k in range(1, n):
                u = k / n
                pts.append((x0 - bw * Sc / 2 + bw * Sc * u, top - bh * Sc * (0.55 + 0.45 * math.sin(u * math.pi)) * rng.uniform(0.8, 1.05)))
            pts.append((x0 + bw * Sc / 2, top))
            c.begin()
            c.move(*pts[0])
            for q in pts[1:]:
                c.line(*q)
            c.close()
            c.fill_linear(x0 - bw * Sc / 2, 0, x0 + bw * Sc / 2, 0, [(0, '#ffffff'), (0.55, '#e4f2fb'), (1, '#9fc4dc')], bands=8)
            c.begin()
            c.move(x0 + bw * Sc * 0.05, top - bh * Sc * 0.9)
            c.line(x0 + bw * Sc * 0.2, top - bh * Sc * 0.3)
            c.stroke((150, 190, 215, 160), 1.2)
    haze = pygame.Surface(big.get_size(), pygame.SRCALPHA)
    hz = hexc(Th.haze)
    hh = int(70 * Sc * ss)
    for i in range(hh):
        pygame.draw.line(haze, hz + (int(120 * (1 - i / hh) ** 2),), (0, top * ss - i), (W * ss, top * ss - i))
    big.blit(haze, (0, 0))
    _island(c, big, rng, bid, Th, top, ss)
    surf = pygame.transform.smoothscale(big, (W, LH + below))
    _cache[key] = (surf, LH)
    return _cache[key]


def _castle(c, rng, x, top, Sc):
    """A ruined Highland castle on the far shore of the loch (a little like Urquhart)."""
    stone, dark, lite = '#7a766a', '#4e4a42', '#a29c8c'
    # the rocky point it stands on
    c.begin()
    c.move(x - 120 * Sc, top)
    c.quad(x - 60 * Sc, top - 22 * Sc, x + 10 * Sc, top - 20 * Sc)
    c.quad(x + 80 * Sc, top - 16 * Sc, x + 130 * Sc, top)
    c.close()
    c.fill('#4a5a3a')
    # broken curtain wall
    c.begin()
    c.move(x - 90 * Sc, top - 20 * Sc)
    for px, py in ((-90, 34), (-74, 34), (-68, 27), (-52, 30), (-46, 38), (-18, 38), (-18, 20)):
        c.line(x + px * Sc, top - py * Sc)
    c.close()
    c.fill(stone)
    # the tall tower house, missing a corner
    tx0, tx1, th = x - 18 * Sc, x + 26 * Sc, 92 * Sc
    c.begin()
    c.move(tx0, top - 18 * Sc)
    c.line(tx0, top - th)
    for k in range(5):
        xa = tx0 + k * 8.8 * Sc
        c.line(xa, top - th - 6 * Sc)
        c.line(xa + 4.4 * Sc, top - th - 6 * Sc)
        c.line(xa + 4.4 * Sc, top - th)
        c.line(xa + 8.8 * Sc, top - th)
    c.line(tx1, top - th + 14 * Sc)
    c.line(tx1 - 6 * Sc, top - th + 22 * Sc)
    c.line(tx1, top - th + 30 * Sc)
    c.line(tx1, top - 18 * Sc)
    c.close()
    c.fill_linear(tx0, 0, tx1, 0, [(0, lite), (0.6, stone), (1, dark)], bands=6)
    for k in range(4):
        for j in range(2):
            c.begin()
            c.rect(tx0 + (9 + j * 18) * Sc, top - th + (16 + k * 18) * Sc, 4 * Sc, 8 * Sc)
            c.fill('#24221e')
    # lower ruined tower
    c.begin()
    c.move(x + 40 * Sc, top - 16 * Sc)
    c.line(x + 40 * Sc, top - 44 * Sc)
    c.line(x + 50 * Sc, top - 50 * Sc)
    c.line(x + 58 * Sc, top - 42 * Sc)
    c.line(x + 64 * Sc, top - 46 * Sc)
    c.line(x + 64 * Sc, top - 16 * Sc)
    c.close()
    c.fill(stone)
    c.begin()
    c.rect(x + 48 * Sc, top - 34 * Sc, 4 * Sc, 7 * Sc)
    c.fill('#24221e')


def _island(c, big, rng, bid, Th, top, ss):
    W, Sc = G.W, G.S
    iw = island_w()
    c.begin()
    c.move(-10, top + 6)
    c.line(-10, top - 52 * Sc)
    c.quad(iw * 0.55, top - 82 * Sc, iw * 1.05, top + 6)
    c.close()
    c.fill_linear(0, top - 82 * Sc, 0, top + 6, [(0, Th.sand), (1, Th.sand2)], bands=10)
    c.begin()
    c.rect(-10, top - 4 * Sc, iw * 1.05 + 10, 10 * Sc)
    c.fill((0, 0, 0, 36))
    if bid in ('shore', 'reef', 'mariana'):
        for _ in range(14):
            x, y = island_profile(rng.uniform(0.06, 0.78))
            y += top + 2 * Sc
            c.begin()
            for k in range(-1, 2):
                c.move(x + k * 2 * Sc, y)
                c.line(x + k * 5 * Sc + rng.uniform(-1, 1), y - rng.uniform(6, 11) * Sc)
            c.stroke(mix(Th.grass, '#000000', rng.uniform(0, 0.25)), 1.6, 'round')
    for rx, rw, rh in ((iw * 0.95, 24, 15), (iw * 1.06, 14, 9), (iw * 0.2, 18, 10), (iw * 0.08, 12, 7)):
        c.begin()
        c.ellipse(rx, top + 2 * Sc, rw * Sc, rh * Sc, 0, math.pi, TAU)
        c.fill(Th.rock)
        c.begin()
        c.ellipse(rx - rw * 0.25 * Sc, top - rh * 0.45 * Sc, rw * 0.45 * Sc, rh * 0.28 * Sc)
        c.fill(mix(Th.rock, '#ffffff', 0.25))
    if bid == 'reef':
        ax, ay = iw * 0.85, top - 30 * Sc
        for px in (ax - 18 * Sc, ax + 10 * Sc):
            c.begin()
            c.rect(px, ay - 34 * Sc, 8 * Sc, 34 * Sc)
            c.fill('#c9c3b5')
            c.begin()
            c.move(px + 2 * Sc, ay - 28 * Sc)
            c.line(px + 5 * Sc, ay - 20 * Sc)
            c.line(px + 3 * Sc, ay - 12 * Sc)
            c.stroke('#9a9488', 1)
        c.begin()
        c.rect(ax - 22 * Sc, ay - 40 * Sc, 44 * Sc, 7 * Sc)
        c.fill('#d8d2c4')
    if bid == 'pallid':
        for _ in range(10):
            x, y = island_profile(rng.uniform(0.06, 0.5))
            y += top + 2 * Sc
            c.begin()
            for k in range(-1, 2):
                c.move(x + k * 2 * Sc, y)
                c.line(x + k * 4 * Sc + rng.uniform(-1, 1), y - rng.uniform(4, 8) * Sc)
            c.stroke(mix(Th.grass, '#000000', rng.uniform(0, 0.3)), 1.4, 'round')
        ax, ay = iw * 0.3, top - 44 * Sc
        for sgn in (-1, 1):
            c.begin()
            c.move(ax + sgn * 22 * Sc, ay + 18 * Sc)
            c.quad(ax + sgn * 26 * Sc, ay - 36 * Sc, ax + sgn * 2 * Sc, ay - 50 * Sc)
            c.stroke('#e8e2d2', 6 * Sc, 'round')
            c.begin()
            c.move(ax + sgn * 22 * Sc, ay + 18 * Sc)
            c.quad(ax + sgn * 26 * Sc, ay - 36 * Sc, ax + sgn * 2 * Sc, ay - 50 * Sc)
            c.stroke('#b8b2a2', 1.4)
    if bid == 'trench':
        lx, ly = iw * 0.5, top - 56 * Sc
        c.begin()
        c.move(lx - 11 * Sc, ly)
        c.line(lx - 6 * Sc, ly - 72 * Sc)
        c.line(lx + 6 * Sc, ly - 72 * Sc)
        c.line(lx + 11 * Sc, ly)
        c.fill('#e8e4da')
        for k in range(3):
            c.begin()
            yy = ly - (14 + k * 22) * Sc
            c.rect(lx - (10 - k * 1.5) * Sc, yy - 7 * Sc, (20 - k * 3) * Sc, 7 * Sc)
            c.fill('#c94b3b')
        c.begin()
        c.rect(lx - 8 * Sc, ly - 82 * Sc, 16 * Sc, 10 * Sc)
        c.fill('#2a2e3a')
    dy = top - 12 * Sc
    c.begin()
    c.rect(iw * 0.55, dy, iw * 0.78, 7 * Sc)
    c.fill('#8a6038')
    c.begin()
    for k in range(10):
        x = iw * 0.55 + k * iw * 0.078
        c.move(x, dy)
        c.line(x, dy + 7 * Sc)
    c.stroke('#5a3d22', 1)
    for k in range(4):
        c.begin()
        c.rect(iw * 0.6 + k * iw * 0.2, dy, 5 * Sc, 30 * Sc)
        c.fill('#6a4528')
        c.begin()
        c.rect(iw * 0.6 + k * iw * 0.2, dy - 2 * Sc, 5 * Sc, 3 * Sc)
        c.fill('#9a7048')
    hx, hy = iw * 0.6, dy
    c.begin()
    c.rect(hx - 2 * Sc, hy - 42 * Sc, 50 * Sc, 42 * Sc)
    c.fill(Th.hut)
    c.begin()
    for k in range(1, 6):
        c.move(hx - 2 * Sc, hy - k * 7 * Sc)
        c.line(hx + 48 * Sc, hy - k * 7 * Sc)
    c.stroke(mix(Th.hut, '#000000', 0.22), 1)
    c.begin()
    c.move(hx - 10 * Sc, hy - 40 * Sc)
    c.line(hx + 23 * Sc, hy - 68 * Sc)
    c.line(hx + 56 * Sc, hy - 40 * Sc)
    c.close()
    c.fill(Th.roof)
    c.begin()
    c.move(hx - 10 * Sc, hy - 40 * Sc)
    c.line(hx + 56 * Sc, hy - 40 * Sc)
    c.stroke(mix(Th.roof, '#000000', 0.35), 3)
    c.begin()
    c.rect(hx + 5 * Sc, hy - 27 * Sc, 12 * Sc, 27 * Sc)
    c.fill('#6a4528')
    c.begin()
    c.circle(hx + 14.5 * Sc, hy - 13 * Sc, 1.3 * Sc)
    c.fill('#ffd27a')
    c.begin()
    c.rect(hx + 26 * Sc, hy - 31 * Sc, 15 * Sc, 12 * Sc)
    c.fill('#ffe08a')
    c.begin()
    c.move(hx + 33.5 * Sc, hy - 31 * Sc)
    c.line(hx + 33.5 * Sc, hy - 19 * Sc)
    c.move(hx + 26 * Sc, hy - 25 * Sc)
    c.line(hx + 41 * Sc, hy - 25 * Sc)
    c.stroke('#7a5532', 1.4)
    if bid == 'mariana':
        cx_ = iw * 1.25
        for dx in (-9, 9):
            c.begin()
            c.move(cx_ + dx * Sc, dy)
            c.line(cx_ + 22 * Sc, dy - 64 * Sc)
            c.stroke('#ffb43a', 4)
        c.begin()
        c.move(cx_ + 22 * Sc, dy - 64 * Sc)
        c.line(cx_ + 22 * Sc, dy - 20 * Sc)
        c.stroke((40, 40, 46, 220), 1.4)
        c.begin()
        c.arc(cx_ + 22 * Sc, dy - 17 * Sc, 3 * Sc, 0, math.pi)
        c.stroke((40, 40, 46, 220), 1.6)
    if bid == 'frost':
        c.begin()
        c.move(hx - 4 * Sc, hy - 44 * Sc)
        c.line(hx + 23 * Sc, hy - 70 * Sc)
        c.line(hx + 50 * Sc, hy - 44 * Sc)
        for k in range(6):
            c.line(hx + 50 * Sc - k * 9 * Sc, hy - (41 if k % 2 else 46) * Sc)
        c.close()
        c.fill('#f4fbff')
        for k in range(8):
            ix = hx - 6 * Sc + k * 8.5 * Sc
            c.begin()
            c.move(ix - 1.6 * Sc, hy - 40 * Sc)
            c.line(ix, hy - (31 + (k % 3) * 3) * Sc)
            c.line(ix + 1.6 * Sc, hy - 40 * Sc)
            c.close()
            c.fill((220, 240, 255, 230))
    sx, sw, sh = hx + 4 * Sc, 40 * Sc, 11 * Sc
    c.begin()
    c.rect(sx, hy - 54 * Sc, sw, sh)
    c.fill('#e8c27a')
    f = ui.font('k', max(8, int(8.5 * Sc * ss)))
    t = f.render(Th.sign or 'BAIT & TACKLE', True, (70, 40, 15))
    t = pygame.transform.smoothscale(t, (int(min(t.get_width(), sw * ss * 0.9)), t.get_height()))
    big.blit(t, ((sx + sw / 2) * ss - t.get_width() / 2, (hy - 54 * Sc + sh / 2) * ss - t.get_height() / 2))


def lava_layer():
    s = _cache.get('lava')
    if s is not None:
        return s
    W, Sc = G.W, G.S
    LH = int(300 * Sc)
    vx, vh, top = W * 0.82, 230 * Sc, LH
    x0 = int(vx - 200 * Sc)
    w = int(360 * Sc)
    ss = 2
    big = pygame.Surface((w * ss, (LH + 10) * ss), pygame.SRCALPHA)
    c = Pen(big)
    c.scale(ss)
    c.translate(-x0, 0)
    for (a, b, cc, d, e, f) in ((vx - 20 * Sc, top - vh + 4, vx - 70 * Sc, top - vh * 0.5, vx - 130 * Sc, top - 6),
                                (vx + 10 * Sc, top - vh + 4, vx + 40 * Sc, top - vh * 0.45, vx + 110 * Sc, top - 4),
                                (vx - 5 * Sc, top - vh + 4, vx - 10 * Sc, top - vh * 0.6, vx - 30 * Sc, top - vh * 0.3)):
        c.begin()
        c.move(a, b)
        c.quad(cc, d, e, f)
        pts = c.subs[0][0]
        for i in range(len(pts) - 1):
            u = i / (len(pts) - 1)
            col = mix('#ffe08a', '#ff6a1a', u / 0.4) if u < 0.4 else mix('#ff6a1a', '#a01e05', (u - 0.4) / 0.6)
            for p in c._stroke_polys([pts[i], pts[i + 1]], False, 7 * Sc * ss, 'round'):
                pygame.draw.polygon(big, col, p)
    c.begin()
    c.ellipse(vx - 5 * Sc, top - vh, 47 * Sc, 9 * Sc)
    c.fill('#ffb03a')
    core = pygame.transform.smoothscale(big, (w, LH + 10))
    glow = _blur(core, 10)
    glow.fill((255, 120, 40, 255), special_flags=pygame.BLEND_RGBA_MULT)
    _cache['lava'] = (core, glow, x0)
    return _cache['lava']


def sheen_band(bid):
    """The sky's colour reflected just under the water surface."""
    key = ('sheen', bid)
    s = _cache.get(key)
    if s is None:
        h = int(46 * G.S)
        s = pygame.Surface((G.W, h), pygame.SRCALPHA)
        col = hexc(THEME[bid].sheen)
        for y in range(h):
            pygame.draw.line(s, col + (int(95 * (1 - y / h) ** 2),), (0, y), (G.W, y))
        _cache[key] = s
    return s


def floor_layer(bid):
    """The sea floor with its rocks, shells and corals (the swaying bits are drawn live)."""
    key = ('floor', bid)
    v = _cache.get(key)
    if v is not None:
        return v
    Th = THEME[bid]
    W, Sc = G.W, G.S
    FH, ss = int(150 * Sc), 2
    top = int(26 * Sc)
    big = pygame.Surface((W * ss, FH * ss), pygame.SRCALPHA)
    c = Pen(big)
    c.scale(ss)
    rng = random.Random(bidx(bid) * 13 + 7)
    edge = []
    c.begin()
    c.move(0, FH)
    for k in range(41):
        x = k / 40 * W
        y = top + math.sin(k * 0.9) * 6 * Sc + (fbm(k * 0.37 + 5) - 0.5) * 18 * Sc
        c.line(x, y)
        edge.append((x, y))
    c.line(W, FH)
    c.close()
    c.fill_linear(0, top - 10 * Sc, 0, FH, [(0, Th.floor), (1, Th.floor2)], bands=12)

    def ground(x):
        i = clamp(int(x / W * 40), 0, 39)
        (x0, y0), (x1, y1) = edge[i], edge[i + 1]
        return lerp(y0, y1, (x - x0) / ((x1 - x0) or 1))
    if bid in ('shore', 'reef'):
        for _ in range(34):
            x = rng.uniform(0, W)
            y = ground(x) + rng.uniform(12, 90) * Sc
            w = rng.uniform(20, 48) * Sc
            c.begin()
            c.move(x - w / 2, y)
            c.quad(x, y - 4 * Sc, x + w / 2, y)
            c.stroke(mix(Th.floor, '#ffffff', 0.3), 1.4)
    for _ in range(36):
        x = rng.uniform(0, W)
        y = ground(x) + rng.uniform(4, 100) * Sc
        r = rng.uniform(1.5, 4.5) * Sc
        c.begin()
        c.ellipse(x, y, r * 1.3, r)
        c.fill(mix(Th.floor2, '#000000', rng.uniform(0.05, 0.3)) if rng.random() < 0.6 else mix(Th.floor, '#ffffff', 0.2))
    glows, plants = [], []
    if bid == 'shore':
        for _ in range(4):
            x = rng.uniform(40, W - 40)
            y = ground(x) + rng.uniform(6, 30) * Sc
            col = rng.choice(['#ff7a45', '#ff5a6a', '#ffb050'])
            c.begin()
            for k in range(10):
                a = -math.pi / 2 + k * math.pi / 5
                r = (9 if k % 2 == 0 else 3.6) * Sc
                c.line(x + math.cos(a) * r, y + math.sin(a) * r * 0.75)
            c.fill(col)
        for _ in range(6):
            x = rng.uniform(30, W - 30)
            y = ground(x) + rng.uniform(4, 40) * Sc
            c.begin()
            c.arc(x, y, 6 * Sc, math.pi, TAU)
            c.fill(rng.choice(['#f6e2d0', '#f2c9b0', '#e8d8f0']))
            c.begin()
            for k in range(4):
                a = math.pi + (k + 0.5) * math.pi / 4
                c.move(x, y)
                c.line(x + math.cos(a) * 6 * Sc, y + math.sin(a) * 6 * Sc)
            c.stroke((150, 110, 90, 150), 1)
        ax = W * 0.68
        ay = ground(ax) + 4 * Sc
        c.begin()
        c.move(ax, ay - 46 * Sc)
        c.line(ax, ay - 4 * Sc)
        c.stroke('#6a5040', 4)
        c.begin()
        c.arc(ax, ay - 16 * Sc, 14 * Sc, 0.2, math.pi - 0.2)
        c.stroke('#6a5040', 4, 'round')
        c.begin()
        c.circle(ax, ay - 49 * Sc, 4 * Sc)
        c.stroke('#6a5040', 2.5)
        for k in range(9):
            plants.append((W * (0.05 + k * 0.11) + rng.uniform(-20, 20), rng.randint(3, 5)))
    elif bid == 'reef':
        for k in range(6):
            x = W * (0.1 + k * 0.16) + rng.uniform(-30, 30)
            y = ground(x) + 6 * Sc
            r = rng.uniform(14, 26) * Sc
            col = rng.choice(['#ff8fb0', '#ffb070', '#c9a0ff', '#7ae0c0', '#ffd27a'])
            c.begin()
            c.ellipse(x, y, r * 1.2, r, 0, math.pi, TAU)
            c.fill(col)
            c.begin()
            for j in range(4):
                c.move(x - r * 0.9 + j * r * 0.5, y - r * 0.2)
                c.quad(x - r * 0.7 + j * r * 0.5, y - r * 0.9, x - r * 0.5 + j * r * 0.5, y - r * 0.25)
            c.stroke(mix(col, '#000000', 0.25), 1.5)
        for _ in range(4):
            x = rng.uniform(40, W - 40)
            y = ground(x) + rng.uniform(4, 30) * Sc
            c.begin()
            c.circle(x, y - 5 * Sc, 5 * Sc)
            c.fill('#3a2050')
            c.begin()
            for k in range(12):
                a = k / 12 * TAU
                c.move(x, y - 5 * Sc)
                c.line(x + math.cos(a) * 10 * Sc, y - 5 * Sc + math.sin(a) * 10 * Sc)
            c.stroke('#5a3080', 1)
        for k in range(10):
            plants.append((W * (0.05 + k * 0.1) + rng.uniform(-25, 25), rng.randint(0, 3)))
    elif bid == 'volcano':
        for k in range(8):
            x = (k * 0.13 + 0.05) * W + rng.uniform(-20, 20)
            y = ground(x) + 4 * Sc
            h = rng.uniform(30, 52) * Sc
            c.begin()
            c.move(x - 32 * Sc, y)
            c.line(x - 6 * Sc, y - h)
            c.line(x + 8 * Sc, y - h * 0.9)
            c.line(x + 32 * Sc, y)
            c.fill('#1a1416')
            c.begin()
            c.move(x - 10 * Sc, y - h * 0.25)
            c.line(x, y - h * 0.7)
            c.line(x + 8 * Sc, y - h * 0.3)
            c.stroke('#ff6a1a', 1.6)
            glows.append((x, y - h * 0.5, 16 * Sc, '#ff6a1a'))
        for k in range(3):
            x = W * (0.2 + k * 0.3) + rng.uniform(-40, 40)
            y = ground(x) + 2 * Sc
            c.begin()
            c.move(x - 14 * Sc, y)
            c.line(x - 6 * Sc, y - 34 * Sc)
            c.line(x + 6 * Sc, y - 34 * Sc)
            c.line(x + 14 * Sc, y)
            c.fill('#241a1c')
            plants.append((x, y - 34 * Sc))
    elif bid == 'pallid':
        bone, bone2 = '#d8d2c0', '#a8a290'
        sx0, sx1 = W * 0.2, W * 0.6
        gy0 = ground(sx0) + 14 * Sc
        gy1 = ground(sx1) + 12 * Sc

        def spine(u):
            return lerp(sx0, sx1, u), lerp(gy0, gy1, u) - (34 + 10 * math.sin(u * 3.0)) * Sc * (0.4 + 0.6 * u)
        c.begin()
        x, y = spine(0)
        c.move(x, y)
        for i in range(1, 25):
            x, y = spine(i / 24)
            c.line(x, y)
        c.stroke(bone, 7, 'round')
        for k in range(12):
            u = 0.3 + k * 0.055
            x, y = spine(u)
            g = lerp(gy0, gy1, u)
            c.begin()
            c.move(x, y)
            c.quad(x - 30 * Sc, y + 10 * Sc, x - 16 * Sc, g)
            c.stroke(bone, 4.2, 'round')
            c.begin()
            c.move(x, y)
            c.quad(x - 30 * Sc, y + 10 * Sc, x - 16 * Sc, g)
            c.stroke(bone2, 1)
        for k in range(10):
            x, y = spine(k * 0.028)
            c.begin()
            c.circle(x, y - 3 * Sc, (5 - k * 0.3) * Sc)
            c.fill(bone)
        hx, hy = spine(1.0)
        c.begin()
        c.move(hx - 6 * Sc, hy - 8 * Sc)
        c.line(hx + 70 * Sc, hy - 12 * Sc)
        c.quad(hx + 86 * Sc, hy + 10 * Sc, hx + 70 * Sc, gy1)
        c.line(hx - 2 * Sc, gy1)
        c.close()
        c.fill(bone)
        c.begin()
        c.ellipse(hx + 22 * Sc, hy + 12 * Sc, 9 * Sc, 6 * Sc)
        c.fill('#3a3a38')
        c.begin()
        c.move(hx + 4 * Sc, gy1 - 6 * Sc)
        c.line(hx + 70 * Sc, gy1 - 8 * Sc)
        c.stroke(bone2, 2)
        for _ in range(12):
            x = rng.uniform(20, W - 20)
            y = ground(x) + rng.uniform(8, 60) * Sc
            a = rng.uniform(0, math.pi)
            ln = rng.uniform(10, 24) * Sc
            c.begin()
            c.move(x - math.cos(a) * ln / 2, y - math.sin(a) * ln / 2 * 0.3)
            c.line(x + math.cos(a) * ln / 2, y + math.sin(a) * ln / 2 * 0.3)
            c.stroke(bone, 3, 'round')
        ax = W * 0.8
        ay = ground(ax) + 6 * Sc
        c.begin()
        c.move(ax, ay - 40 * Sc)
        c.line(ax + 4 * Sc, ay - 4 * Sc)
        c.stroke('#5a4a40', 4)
        c.begin()
        c.arc(ax + 2 * Sc, ay - 14 * Sc, 13 * Sc, 0.2, math.pi - 0.2)
        c.stroke('#5a4a40', 4, 'round')
        for k in range(11):
            plants.append((W * (0.03 + k * 0.095) + rng.uniform(-18, 18), rng.randint(2, 4)))
    elif bid == 'mariana':
        for k in range(5):
            x = (k * 0.2 + 0.1) * W + rng.uniform(-30, 30)
            y = ground(x) + 4 * Sc
            h = rng.uniform(50, 90) * Sc
            c.begin()
            c.move(x - 20 * Sc, y)
            c.line(x - 7 * Sc, y - h)
            c.line(x + 7 * Sc, y - h * 0.94)
            c.line(x + 20 * Sc, y)
            c.close()
            c.fill_linear(x - 20 * Sc, 0, x + 20 * Sc, 0, [(0, '#1a1614'), (0.5, '#3a302a'), (1, '#141210')], bands=6)
            for j in range(3):
                yy = y - h * (0.25 + j * 0.25)
                c.begin()
                c.ellipse(x + rng.uniform(-4, 4) * Sc, yy, 9 * Sc, 3 * Sc)
                c.fill((70, 56, 46, 200))
            c.begin()
            c.move(x - 5 * Sc, y - h * 0.4)
            c.line(x, y - h * 0.8)
            c.stroke('#ff7a3a', 1.2)
            glows.append((x, y - h, 20 * Sc, '#ff8a4a'))
            plants.append((x, y - h))
        for _ in range(9):
            x = rng.uniform(30, W - 30)
            y = ground(x) + rng.uniform(10, 60) * Sc
            c.begin()
            c.ellipse(x, y, 12 * Sc, 5 * Sc)
            c.fill((210, 130, 150, 220))
            c.begin()
            for k in range(4):
                c.move(x - 8 * Sc + k * 5 * Sc, y - 4 * Sc)
                c.line(x - 9 * Sc + k * 5 * Sc, y - 9 * Sc)
            c.stroke((230, 160, 180, 220), 1.4, 'round')
    elif bid == 'frost':
        for k in range(8):
            x = (k * 0.125 + 0.05) * W + rng.uniform(-20, 20)
            y = ground(x) + 5 * Sc
            for j in range(rng.randint(3, 5)):
                a = -math.pi / 2 + rng.uniform(-0.55, 0.55)
                ln = rng.uniform(18, 46) * Sc
                wd = rng.uniform(4, 7) * Sc
                ca, sa = math.cos(a), math.sin(a)
                px, py = -sa * wd, ca * wd
                tx, ty = x + ca * ln, y + sa * ln
                c.begin()
                c.move(x - px, y - py)
                c.line(tx - px * 0.8, ty - py * 0.8)
                c.line(tx + ca * wd * 1.2, ty + sa * wd * 1.2)
                c.line(tx + px * 0.8, ty + py * 0.8)
                c.line(x + px, y + py)
                c.close()
                c.fill((200, 236, 255, 220))
                c.begin()
                c.move(x - px * 0.3, y - py * 0.3)
                c.line(tx - px * 0.3, ty - py * 0.3)
                c.stroke((255, 255, 255, 200), 1.2)
            glows.append((x, y - 22 * Sc, 26 * Sc, '#7fd8ff'))
        for _ in range(14):
            x = rng.uniform(20, W - 20)
            y = ground(x) + rng.uniform(6, 50) * Sc
            r = rng.uniform(6, 14) * Sc
            c.begin()
            c.ellipse(x, y, r * 1.4, r, 0, math.pi, TAU)
            c.fill(Th.rock)
            c.begin()
            c.ellipse(x - r * 0.3, y - r * 0.55, r * 0.7, r * 0.22)
            c.fill((240, 250, 255, 200))
        for k in range(9):
            plants.append((W * (0.06 + k * 0.105) + rng.uniform(-20, 20), rng.randint(0, 1)))
    elif bid == 'trench':
        for k in range(9):
            x = (k * 0.12 + 0.03) * W + rng.uniform(-14, 14)
            y = ground(x) + 4 * Sc
            h = rng.uniform(46, 76) * Sc
            c.begin()
            c.move(x - 24 * Sc, y)
            c.line(x - 6 * Sc, y - h)
            c.line(x + 26 * Sc, y)
            c.fill('#0d0f18')
            cx = x + 5 * Sc
            c.begin()
            c.move(cx - 4 * Sc, y - 18 * Sc)
            c.line(cx, y - 36 * Sc)
            c.line(cx + 5 * Sc, y - 18 * Sc)
            c.fill('#5ac8e8')
            glows.append((cx, y - 26 * Sc, 22 * Sc, '#5acfff'))
        for k in range(4):
            x = rng.uniform(60, W - 60)
            y = ground(x) + 3 * Sc
            for j in range(6):
                tx = x + (j - 2.5) * 5 * Sc
                th = rng.uniform(14, 30) * Sc
                c.begin()
                c.move(tx, y)
                c.line(tx + rng.uniform(-2, 2), y - th)
                c.stroke('#e8e0d0', 2.4, 'round')
                plants.append((tx, y - th))
    elif bid == 'atlantis':
        for k in range(5):
            x = W * (0.1 + k * 0.19) + rng.uniform(-22, 22)
            y = ground(x) + 5 * Sc
            h = rng.uniform(48, 84) * Sc
            wid = rng.uniform(12, 19) * Sc
            c.begin()
            c.move(x - wid, y)
            c.line(x - wid * 0.72, y - h)
            c.line(x + wid * 0.72, y - h)
            c.line(x + wid, y)
            c.close()
            c.fill_linear(x - wid, 0, x + wid, 0, [(0, '#7c806d'), (0.45, '#e3d8ad'), (1, '#847c5d')], bands=7)
            for j in range(4):
                yy = y - h * (0.18 + j * 0.17)
                c.begin()
                c.rect(x - wid * 0.52, yy, wid * 1.04, 2.2 * Sc)
                c.fill('#a7a078')
            c.begin()
            c.rect(x - wid * 1.35, y - h - 5 * Sc, wid * 2.7, 7 * Sc)
            c.fill('#d8cca0')
            glows.append((x, y - h * 0.5, 23 * Sc, '#a0ffd4'))
            plants.append((x, y - h))
        for k in range(8):
            x = W * (0.06 + k * 0.125) + rng.uniform(-12, 12)
            plants.append((x, ground(x) - rng.uniform(3, 10) * Sc))
    elif bid == 'redhollow':
        for k in range(8):
            x = W * (0.05 + k * 0.125) + rng.uniform(-16, 16)
            y = ground(x) + 5 * Sc
            h = rng.uniform(34, 72) * Sc
            c.begin()
            c.move(x - 18 * Sc, y)
            c.line(x - rng.uniform(2, 8) * Sc, y - h)
            c.line(x + rng.uniform(2, 8) * Sc, y - h * 0.8)
            c.line(x + 24 * Sc, y)
            c.close()
            c.fill_linear(x - 18 * Sc, 0, x + 24 * Sc, 0, [(0, '#21162d'), (0.55, '#633047'), (1, '#24112e')], bands=7)
            c.begin()
            c.move(x, y - h * 0.82)
            c.line(x + rng.uniform(-10, 10) * Sc, y - h * 0.38)
            c.line(x - rng.uniform(-8, 8) * Sc, y - h * 0.12)
            c.stroke('#ff405d', 1.5 * Sc)
            glows.append((x, y - h * 0.55, 24 * Sc, '#ff315c'))
            plants.append((x, y - h))
    surf = pygame.transform.smoothscale(big, (W, FH))
    _cache[key] = (surf, top, glows, plants, edge)
    return _cache[key]


def caustic_tiles(k, tint=(150, 220, 255)):
    """Two tileable textures of the bright wavy lines sunlight makes underwater."""
    key = ('caus', round(k, 2), tint)
    v = _cache.get(key)
    if v is not None:
        return v
    base = _cache.get('caus_base')
    if base is None:
        base = []
        for waves in (((2, 1, 0.0, 1.0), (-1, 3, 1.3, 0.9), (3, -1, 2.1, 0.8), (5, 4, 0.7, 0.45)),
                      ((1, 2, 0.5, 1.0), (3, 1, 2.4, 0.85), (-2, 3, 1.1, 0.8), (4, -3, 0.2, 0.4))):
            w, h = 256, 64
            s = pygame.Surface((w, h))
            px = pygame.PixelArray(s)
            for y in range(h):
                for x in range(w):
                    val = 0.0
                    for kx, ky, ph, amp in waves:
                        val += amp * math.sin(TAU * (kx * x / w + ky * y / h) + ph)
                    i = 1 - abs(val) / 0.36
                    if i > 0:
                        v = int(255 * i * i)
                        px[x, y] = (v, v, v)
            del px
            base.append(pygame.transform.smoothscale(s, (512, 128)))
        _cache['caus_base'] = base
    out = []
    f = clamp(0.36 * k, 0, 1)
    for tile in base:
        tt = tile.copy()
        tt.fill((int(tint[0] * f), int(tint[1] * f), int(tint[2] * f)), special_flags=pygame.BLEND_RGB_MULT)
        out.append(tt)
    _cache[key] = out
    return out


def caustic_fade(w, band):
    key = ('causfade', w, band)
    s = _cache.get(key)
    if s is None:
        s = pygame.Surface((w, band))
        for y in range(band):
            u = y / band
            v = int(255 * min(1.0, y / 10.0) * (1 - u) ** 1.5)
            pygame.draw.line(s, (v, v, v), (0, y), (w, y))
        _cache[key] = s
    return s


def ray_sprites():
    v = _cache.get('rays')
    if v is not None:
        return v
    Sc, PPM = G.S, G.PPM
    h = int(95 * PPM)
    out = []
    for variant in range(3):
        w_top, w_bot, slant = (34 + 14 * variant) * Sc, (100 + 34 * variant) * Sc, -70 * Sc
        width = int(w_bot + abs(slant) + 60)
        s = pygame.Surface((width, h))
        xc0 = width * 0.68
        for y in range(0, h, 2):
            u = y / h
            cx = xc0 + slant * u
            half = lerp(w_top, w_bot, u) / 2
            inten = (1 - u) ** 1.7
            for layer in range(4):
                fr = (4 - layer) / 4
                val = inten * (24 + 22 * layer)
                col = (int(val), int(val), int(val * 0.9))
                pygame.draw.line(s, col, (cx - half * fr, y), (cx + half * fr, y), 2)
        s = _blur(s, 7)
        levels = []
        for f in (0.55, 0.78, 1.0):
            t = s.copy()
            g = int(255 * f)
            t.fill((g, g, g), special_flags=pygame.BLEND_RGB_MULT)
            levels.append(t)
        out.append(levels)
    _cache['rays'] = out
    return out


def vignette_corner():
    v = _cache.get('vig')
    if v is None:
        w, h = 460, 300

        def fn(u, vv):
            d = math.hypot(u, vv)
            return (2, 6, 14, int(255 * clamp(1 - d / 1.05, 0, 1) ** 2.2))
        tl = ui.radial_surface(w, h, fn, (46, 30))
        v = _cache['vig'] = (tl, pygame.transform.flip(tl, True, False), pygame.transform.flip(tl, False, True),
                             pygame.transform.flip(tl, True, True))
    return v


def tiny_fish(col):
    key = ('tiny', col)
    s = _cache.get(key)
    if s is None:
        big = pygame.Surface((36, 18), pygame.SRCALPHA)
        c = Pen(big)
        c.scale(2)
        c.begin()
        c.ellipse(9, 4.5, 6, 2.6)
        c.fill(col)
        c.begin()
        c.move(4, 4.5)
        c.line(0.5, 1.5)
        c.line(0.5, 7.5)
        c.fill(mix(col, '#000000', 0.2))
        c.begin()
        c.circle(12.5, 4, 0.9)
        c.fill((20, 20, 30))
        s = pygame.transform.smoothscale(big, (18, 9))
        _cache[key] = (s, pygame.transform.flip(s, True, False))
        s = _cache[key]
    return s


def turtle_frames():
    v = _cache.get('turtle')
    if v is not None:
        return v
    frames = []
    for i in range(8):
        ph = TAU * i / 8
        ss = 2
        big = pygame.Surface((110 * ss, 70 * ss), pygame.SRCALPHA)
        c = Pen(big)
        c.scale(ss)
        c.translate(55, 35)
        flap = math.sin(ph)
        skin = '#7fb07a'
        for sgn, L, base_a in ((1, 30, 0.55), (-1, 30, -0.55)):
            c.save()
            c.translate(12, sgn * 6)
            c.rotate(base_a + flap * 0.5 * sgn)
            c.begin()
            c.ellipse(16, 0, 18, 5.5)
            c.fill(skin)
            c.restore()
        for sgn in (1, -1):
            c.save()
            c.translate(-20, sgn * 8)
            c.rotate(sgn * (2.4 + flap * 0.25))
            c.begin()
            c.ellipse(8, 0, 9, 4)
            c.fill(skin)
            c.restore()
        c.begin()
        c.ellipse(30, 0, 9, 7)
        c.fill(skin)
        c.begin()
        c.circle(34, -2.5, 1.6)
        c.fill((20, 25, 20))
        c.begin()
        c.ellipse(0, 0, 30, 19)
        c.fill_linear(0, -19, 0, 19, [(0, '#5a8a50'), (0.5, '#3f6e40'), (1, '#2c4e30')])
        c.begin()
        for (px, py) in ((0, 0), (-12, -7), (12, -7), (-12, 7), (12, 7), (-22, 0), (22, 0)):
            c.circle(px, py, 6.2)
        c.stroke((30, 50, 30, 170), 1.2)
        c.begin()
        c.ellipse(0, 0, 30, 19)
        c.stroke('#a8c890', 1.6)
        frames.append(pygame.transform.smoothscale(big, (110, 70)))
    _cache['turtle'] = frames
    return frames


def jelly_sprite(col):
    key = ('jelly', col)
    v = _cache.get(key)
    if v is None:
        frames = []
        for i in range(6):
            ph = TAU * i / 6
            ss = 2
            big = pygame.Surface((44 * ss, 60 * ss), pygame.SRCALPHA)
            c = Pen(big)
            c.scale(ss)
            c.translate(22, 18)
            pulse = 1 + math.sin(ph) * 0.12
            c.begin()
            for k in range(5):
                x = -9 + k * 4.5
                c.move(x, 2)
                for s in range(1, 7):
                    c.line(x + math.sin(ph + s * 0.9 + k) * 2.2, 2 + s * 5.5)
            c.stroke(hexc(col) + (150,), 1.2)
            c.begin()
            c.ellipse(0, 2, 13 * pulse, 13 / pulse, 0, math.pi, TAU)
            c.fill(hexc(col) + (150,))
            c.begin()
            c.ellipse(0, -2, 6 * pulse, 5 / pulse, 0, math.pi, TAU)
            c.fill((255, 255, 255, 120))
            frames.append(pygame.transform.smoothscale(big, (44, 60)))
        v = _cache[key] = frames
    return v


# ===================================================================================
#  Life around the bay (birds, boats, jumping fish, schools, turtles, jellies...)
# ===================================================================================
class Amb:
    def __init__(self):
        self.bid = None

    def reset(self, bid):
        self.bid = bid
        Th = THEME[bid]
        rng = random.Random(bidx(bid) * 101 + 17)
        W = G.W
        # paint this island's big pictures now (while the screen is dark from sailing), not mid-dive
        sky_surface(bid)
        land_layer(bid)
        floor_layer(bid)
        sheen_band(bid)
        if bid == 'volcano':
            lava_layer()
        if Th.caustic:
            caustic_tiles(Th.caustic, Th.caus_tint or (150, 220, 255))
        if Th.rays:
            ray_sprites()
        sprites = cloud_sprites(bid)
        self.clouds = []
        for i in range(10):
            near = i >= 5
            self.clouds.append(D(x=rng.uniform(-0.2, 1.2), y=rng.uniform(0.04, 0.42) if near else rng.uniform(0.45, 0.75),
                                 spr=sprites[i % len(sprites)], near=near, v=rng.uniform(0.006, 0.011) if near else rng.uniform(0.002, 0.004),
                                 k=1.0 if near else 0.55))
        self.clouds.sort(key=lambda c: c.near)
        self.birds = []
        self.birdT = rand(3, 9)
        self.sail = D(x=rng.uniform(0.3, 1.0), v=-rng.uniform(0.0025, 0.004))
        self.jumps = []
        self.jumpT = rand(6, 14)
        self.schools = []
        if Th.school:
            for _ in range(3):
                self.schools.append(self._school(rng, bid, initial=True))
        self.turtle = None
        self.turtleT = rand(8, 20)
        self.jellies = []
        if Th.jellies:
            dmin = (BIOMES[bid].dark or 150) + 20
            for _ in range(max(7, BIOMES[bid].depth // 900)):
                self.jellies.append(D(x=rng.uniform(0, W), d=rng.uniform(dmin, BIOMES[bid].depth - 60), vx=rng.uniform(-6, 6),
                                      ph=rng.uniform(0, 6), col=rng.choice(Th.jelly_cols or ['#8fdcff', '#c8a0ff', '#ff9ad8', '#9fffd8'])))
        self.specks = []
        if bid == 'volcano':
            Th.specks, Th.speck_cols, Th.speck_k = 90, ['#ff6a1a'], 0.6
        if Th.specks:
            for _ in range(Th.specks):
                self.specks.append(D(side=rng.randint(0, 1), d=rng.uniform(30, BIOMES[bid].depth), off=rng.uniform(4, 70),
                                     ph=rng.uniform(0, 6), col=rng.choice(Th.speck_cols), r=rng.uniform(5, 11)))
        self.plankton = []
        self.msnow = [D(x=rng.uniform(0, W), y=rng.uniform(0, G.H), v=rng.uniform(5, 14), r=rng.choice((1, 1, 2)), ph=rng.uniform(0, 6))
                      for _ in range(80)] if Th.marinesnow else []
        self.ash = [D(x=rng.uniform(0, W), y=rng.uniform(0, G.H), v=rng.uniform(10, 26), ph=rng.uniform(0, 6))
                    for _ in range(90 if Th.snow else 50)] if (Th.ash or Th.snow) else []
        self.twinkle = [D(x=rng.uniform(0, W), y=rng.uniform(0, 0.8), ph=rng.uniform(0, 6), f=rng.uniform(0.6, 1.8))
                        for _ in range(40)] if Th.stars else []
        self.glitter = [D(dx=(rng.random() ** 1.7) * (1 if rng.random() < 0.5 else -1), dy=rng.random(),
                          f=rng.uniform(2.0, 5.0), ph=rng.uniform(0, 6)) for _ in range(70)]

    def _school(self, rng, bid, initial=False):
        Th = THEME[bid]
        depth = BIOMES[bid].depth
        dmax = min(depth - 10, 260 if Th.school != 'glow' else 1400)
        dmin = 12 if Th.school != 'glow' else 200
        vx = rng.uniform(10, 22) * G.S * (1 if rng.random() < 0.5 else -1)
        n = rng.randint(10, 18)
        return D(d=rng.uniform(dmin, dmax), x=rng.uniform(0, G.W) if initial else (-120 if vx > 0 else G.W + 120), vx=vx,
                 members=[(rng.uniform(-50, 50) * G.S, rng.uniform(-14, 14) * G.S, rng.uniform(0, 6)) for _ in range(n)])


AMB = Amb()


def amb_tick(dt):
    P = Wd.P
    if AMB.bid != P.biome:
        AMB.reset(P.biome)
    Th = TH()
    W = G.W
    for cl in AMB.clouds:
        cl.x += cl.v * dt * (4 if G.storm > 0.3 else 1)
        if cl.x > 1.25:
            cl.x = -0.25
    if Th.birds:
        AMB.birdT -= dt
        if AMB.birdT <= 0 and not AMB.birds:
            AMB.birdT = rand(18, 35)
            d = 1 if random.random() < 0.5 else -1
            n = random.randint(3, 6)
            AMB.birds = [D(x=(-60 if d > 0 else W + 60) - i * 22 * G.S * d, y=rand(0.12, 0.32), oy=(i % 2 * 2 - 1) * (i + 1) // 2 * 9 * G.S,
                           vx=d * rand(55, 75) * G.S, ph=random.random() * 6) for i in range(n)]
            if random.random() < 0.5 and G.cam < 30:
                Sfx.play('gull', 0.6)
        for b in AMB.birds:
            b.x += b.vx * dt
        if AMB.birds and all((b.x > W + 100 if b.vx > 0 else b.x < -100) for b in AMB.birds):
            AMB.birds = []
    if Th.sail:
        AMB.sail.x += AMB.sail.v * dt
        if AMB.sail.x < -0.1:
            AMB.sail.x = 1.1
    if Th.jumps:
        AMB.jumpT -= dt
        if AMB.jumpT <= 0:
            AMB.jumpT = rand(12, 24)
            if G.cam < 40 and G.mode not in ('reel', 'bite'):
                lst = [f for f in FISH if f.b == P.biome and RI[f.r] <= 1 and f.shape in ('fish', 'koi')]
                if lst:
                    x0 = rand(G.W * 0.38, G.W * 0.92)
                    AMB.jumps.append(D(sp=random.choice(lst), x0=x0, dir=1 if random.random() < 0.5 else -1, t=0.0, dur=1.05,
                                       h=rand(42, 70) * G.S, splashed=False))
                    _splash(x0)
        for j in AMB.jumps[:]:
            j.t += dt
            if j.t >= j.dur and not j.splashed:
                j.splashed = True
                _splash(j.x0 + j.dir * 90 * G.S)
            if j.t > j.dur + 0.1:
                AMB.jumps.remove(j)
    for s in AMB.schools:
        s.x += s.vx * dt
        if (s.vx > 0 and s.x > W + 160) or (s.vx < 0 and s.x < -160):
            AMB.schools[AMB.schools.index(s)] = AMB._school(random, P.biome)
    if Th.turtle:
        if AMB.turtle is None:
            AMB.turtleT -= dt
            if AMB.turtleT <= 0:
                d = 1 if random.random() < 0.5 else -1
                AMB.turtle = D(x=-90 if d > 0 else W + 90, d=rand(18, 150), vx=d * 20 * G.S, ph=random.random() * 6)
        else:
            t = AMB.turtle
            t.x += t.vx * dt
            if t.x < -140 or t.x > W + 140:
                AMB.turtle = None
                AMB.turtleT = rand(35, 70)
    for j in AMB.jellies:
        j.x += j.vx * dt
        if j.x < -40:
            j.x = W + 40
        elif j.x > W + 40:
            j.x = -40
    if BIOMES[P.biome].dark is not None and G.hook.d > BIOMES[P.biome].dark - 20 and G.hook.speed > 15 and len(AMB.plankton) < 80:
        for _ in range(int(min(4, G.hook.speed / 40)) + (1 if random.random() < 0.5 else 0)):
            AMB.plankton.append(D(x=G.hook.x + rand(-26, 26), d=G.hook.d + rand(-5, 5), life=rand(0.6, 1.4), max=1.4))
    for m in AMB.msnow:
        m.y += m.v * dt
        m.x += math.sin(G.t * 0.4 + m.ph) * 4 * dt
        if m.y > G.H + 4:
            m.y = -4
            m.x = random.uniform(0, W)
    for p in AMB.plankton[:]:
        p.life -= dt
        if p.life <= 0:
            AMB.plankton.remove(p)
    for a in AMB.ash:
        a.y += a.v * dt
        a.x += math.sin(G.t * 0.7 + a.ph) * 8 * dt - 6 * dt
        if a.y > G.H:
            a.y = -5
            a.x = random.uniform(0, W)


def _splash(x):
    Wd.burst(x, -0.3, '#e6f7ff', 10, 0.7, 'drop')
    Wd.ripple(x, 0.7)
    if G.cam < 25:
        Sfx.play('plop', 0.5)


# ===================================================================================
#  Sky and land
# ===================================================================================
def draw_sky(c, dt):
    P = Wd.P
    Th = TH()
    W, H, Sc, t, b = G.W, G.H, G.S, G.t, P.biome
    top = sy(0)
    if top <= 0:
        return
    skytop = top - H * 0.42
    c.blit(sky_surface(b), (0, skytop))
    old = c.get_clip()
    c.set_clip(pygame.Rect(0, 0, W, int(top) + 1))
    for s in AMB.twinkle:
        a = 0.5 + 0.5 * math.sin(t * s.f + s.ph)
        if a > 0.6:
            x, y = s.x, skytop + s.y * H * 0.42
            k = (a - 0.6) / 0.4 * (Th.stars or 1)
            col = (255, 255, 255, int(220 * k))
            gfxdraw.pixel(c, int(x), int(y), col)
            if k > 0.6:
                gfxdraw.hline(c, int(x - 3), int(x + 3), int(y), (255, 255, 255, int(110 * k)))
                gfxdraw.vline(c, int(x), int(y - 3), int(y + 3), (255, 255, 255, int(110 * k)))
    if Th.aurora:
        draw_aurora(c, skytop, top)
    sunX, sunY = W * 0.78, top - H * 0.26
    if Th.sun == 'sun':
        rays_a = 9
        for k in range(10):
            a = t * 0.02 + k * TAU / 10
            pts = [(sunX, sunY), (sunX + math.cos(a - 0.035) * 420 * Sc, sunY + math.sin(a - 0.035) * 420 * Sc),
                   (sunX + math.cos(a + 0.035) * 420 * Sc, sunY + math.sin(a + 0.035) * 420 * Sc)]
            gfxdraw.filled_polygon(c, [(int(x), int(y)) for x, y in pts], (255, 246, 210, rays_a))
        s = sun_sprite()
        c.blit(s, (sunX - s.get_width() / 2, sunY - s.get_height() / 2))
    elif Th.sun == 'moon':
        m = moon_sprite()
        c.blit(m, (sunX - m.get_width() / 2, sunY - m.get_height() / 2))
    for cl in AMB.clouds:
        if cl.near:
            continue
        _blit_cloud(c, cl.spr, cl.x * W, skytop + cl.y * H * 0.42, 0.6)
    c.set_clip(old)
    draw_land(c, top)
    if Th.sail:
        x, y = AMB.sail.x * W, top - 1
        gfxdraw.filled_polygon(c, [(int(x - 11 * Sc), int(y - 3 * Sc)), (int(x + 11 * Sc), int(y - 3 * Sc)), (int(x + 8 * Sc), int(y)), (int(x - 8 * Sc), int(y))], (40, 60, 80, 170))
        gfxdraw.filled_trigon(c, int(x), int(y - 17 * Sc), int(x), int(y - 4 * Sc), int(x + 9 * Sc), int(y - 4 * Sc), (255, 255, 255, 190))
        gfxdraw.filled_trigon(c, int(x - 1), int(y - 13 * Sc), int(x - 1), int(y - 4 * Sc), int(x - 7 * Sc), int(y - 4 * Sc), (240, 240, 250, 150))
    c.set_clip(pygame.Rect(0, 0, W, int(top) + 1))
    for b_ in AMB.birds:
        bx, by = b_.x, skytop + b_.y * H * 0.42 + b_.oy + math.sin(t * 2 + b_.ph) * 3
        f = math.sin(t * 9 + b_.ph)
        pts = [(bx - 8 * Sc, by - 3.5 * Sc * f), (bx - 3 * Sc, by + 0.5), (bx, by + 1.8 * Sc), (bx + 3 * Sc, by + 0.5), (bx + 8 * Sc, by - 3.5 * Sc * f)]
        col = (40, 52, 66) if b != 'trench' else (200, 210, 230)
        pygame.draw.aalines(c, col, False, pts)
        pygame.draw.aalines(c, col, False, [(x, y + 1) for x, y in pts])
    for cl in AMB.clouds:
        if not cl.near:
            continue
        _blit_cloud(c, cl.spr, cl.x * W, skytop + cl.y * H * 0.42, 1.0)
    if Th.sun == 'sun' and sunY > -100:
        cx, cy = W * 0.5, H * 0.62
        for f, r, a in ((0.32, 16, 26), (0.52, 8, 34), (0.78, 30, 16), (1.05, 12, 22)):
            x, y = lerp(sunX, cx, f), lerp(sunY, cy, f)
            if y < top:
                gfxdraw.filled_circle(c, int(x), int(y), int(r * Sc), (255, 240, 200, a))
    if Th.ash or Th.snow:
        col = (235, 245, 255, 210) if Th.snow else (90, 80, 80, 160)
        for a in AMB.ash:
            if a.y < top:
                sz = 3 if (Th.snow and a.v > 18) else 2
                gfxdraw.box(c, (int(a.x), int(a.y), sz, sz), col)
    c.set_clip(old)


def _blit_cloud(c, spr, x, y, scale):
    if scale != 1.0:
        key = ('cloudsc', id(spr), scale)
        s = _cache.get(key)
        if s is None:
            s = _cache[key] = pygame.transform.smoothscale(spr, (int(spr.get_width() * scale), int(spr.get_height() * scale)))
        spr = s
    c.blit(spr, (x - spr.get_width() / 2, y - spr.get_height() / 2))


def draw_aurora(c, skytop, top):
    W, Sc, t = G.W, G.S, G.t
    sh = G.H * 0.42
    for k, (col, base, amp) in enumerate((((90, 255, 170), 0.18, 1.0), ((80, 220, 255), 0.26, 0.8), ((190, 120, 255), 0.12, 0.6))):
        xs = list(range(-40, W + 41, 32))
        tops, hs = [], []
        for x in xs:
            y = skytop + sh * base + 22 * Sc * math.sin(x * 0.004 + t * 0.22 + k * 2) + 10 * Sc * math.sin(x * 0.011 - t * 0.37 + k)
            h = (46 + 26 * math.sin(x * 0.006 + t * 0.3 + k * 1.7)) * Sc * amp
            tops.append(y)
            hs.append(h)
        for band, a in enumerate((10, 18, 30, 46)):
            u0, u1 = band / 4, (band + 1) / 4
            upper = [(x, ty + h * u0) for x, ty, h in zip(xs, tops, hs)]
            lower = [(x, ty + h * u1) for x, ty, h in zip(xs, tops, hs)]
            poly = upper + lower[::-1]
            shimmer = int(a * (0.75 + 0.25 * math.sin(t * 0.8 + k)))
            gfxdraw.filled_polygon(c, [(int(px), int(py)) for px, py in poly], col + (shimmer,))


def draw_land(c, top):
    P = Wd.P
    Th = TH()
    W, Sc, b, t = G.W, G.S, P.biome, G.t
    layer, LH = land_layer(b)
    c.blit(layer, (0, top - LH))
    pen = Pen(c, aa=True)
    if b == 'volcano':
        vx, vh = W * 0.82, 230 * Sc
        core, glow, x0 = lava_layer()
        g = 0.7 + 0.3 * math.sin(t * 2)
        glow.set_alpha(int(255 * g))
        c.blit(glow, (x0, top - LH))
        glow.set_alpha(255)
        c.blit(core, (x0, top - LH))
        add_glow(c, vx - 5 * Sc, top - vh, 80 * Sc, '#ff6a1a', 0.55 + 0.25 * math.sin(t * 1.7))
        for kk in range(5):
            ph = ((t * 0.35 + kk * 0.2) % 1.0)
            yy = top - vh - ph * 170 * Sc
            r = (14 + ph * 46) * Sc
            pen.begin()
            pen.circle(vx + math.sin(t * 0.6 + kk) * 18 * Sc - ph * 30 * Sc, yy, r)
            pen.fill((70, 52, 56, int(150 * (1 - ph) + 30)))
        if G.erupt > 0:
            overlay_rect(c, (0, 0, W, max(0, int(top))), (255, 120, 40), 0.22 * min(1, G.erupt))
    if b in ('shore', 'reef') or Th.palms:
        for pt, ph_, scale in ((0.24, 1.0, 1.0), (0.5, 0.82, 0.85)):
            bx, by = island_profile(pt)
            draw_palm(pen, bx, top + by + 3 * Sc, scale * Sc, math.sin(t * 1.1 + pt * 5) * 4, Th.palm)
    iw = island_w()
    hx, hy = iw * 0.6, top - 12 * Sc
    fx, fy = hx + 23 * Sc, hy - 68 * Sc
    pen.begin()
    pen.move(fx, fy)
    pen.line(fx, fy - 16 * Sc)
    pen.stroke('#5a3d22', 1.6)
    wave = math.sin(t * 5)
    pen.begin()
    pen.move(fx, fy - 16 * Sc)
    pen.quad(fx + 6 * Sc, fy - 16 * Sc + wave * 2, fx + 12 * Sc, fy - 13 * Sc + wave * 1.5)
    pen.line(fx, fy - 10 * Sc)
    pen.close()
    pen.fill('#ff5a6a' if b != 'trench' else '#5ccfff')
    add_glow(c, hx + 33 * Sc, hy - 25 * Sc, 16 * Sc, '#ffcf6a', 0.5 + 0.1 * math.sin(t * 7))
    if b == 'reef':
        ax, ay = iw * 0.85, top - 30 * Sc
        a = 0.6 + 0.4 * math.sin(t * 3)
        add_glow(c, ax, ay - 20 * Sc, 26 * Sc, '#be78ff', a)
        gfxdraw.filled_circle(c, int(ax), int(ay - 20 * Sc), int(6 * Sc), (215, 170, 255, int(200 + 55 * a)))
    if b == 'trench':
        lx, ly = iw * 0.5, top - 56 * Sc
        beam = (t * 0.8) % TAU
        L = W * 1.1
        pen.begin()
        pen.move(lx, ly - 77 * Sc)
        pen.line(lx + math.cos(beam) * L, ly - 77 * Sc + math.sin(beam) * 70 * Sc - 46 * Sc)
        pen.line(lx + math.cos(beam) * L, ly - 77 * Sc + math.sin(beam) * 70 * Sc + 46 * Sc)
        pen.fill((255, 240, 180, 26))
        add_glow(c, lx, ly - 77 * Sc, 30 * Sc, '#fff3c4', 0.9)


def draw_palm(pen, bx, by, sc, sway, col):
    lean = 12 * sc
    tx, ty = bx + lean + sway, by - 92 * sc
    pen.begin()
    pen.move(bx, by)
    pen.quad(bx + 12 * sc, by - 48 * sc, tx, ty)
    pen.stroke('#8a5a2b', 7 * sc, 'round')
    pen.begin()
    for k in range(6):
        u = (k + 1) / 7
        u2 = 1 - u
        x = u2 * u2 * bx + 2 * u2 * u * (bx + 12 * sc) + u * u * tx
        y = u2 * u2 * by + 2 * u2 * u * (by - 48 * sc) + u * u * ty
        pen.move(x - 3.2 * sc, y)
        pen.line(x + 3.2 * sc, y - 1)
    pen.stroke('#6a4220', 1.4)
    dark = mix(col, '#000000', 0.3)
    for k in range(7):
        a = -math.pi / 2 + (k - 3) * 0.52 + sway * 0.01
        L = (40 + 8 * math.cos(k)) * sc
        ex = tx + math.cos(a) * L * 1.1
        ey = ty + math.sin(a) * L * 0.5 + 22 * sc
        mx_, my_ = tx + math.cos(a) * L * 0.55, ty + math.sin(a) * L * 0.55 - 6 * sc
        nx, ny = -math.sin(a) * 6 * sc, math.cos(a) * 6 * sc
        pen.begin()
        pen.move(tx, ty)
        pen.quad(mx_ + nx, my_ + ny, ex, ey)
        pen.quad(mx_ - nx * 0.4, my_ - ny * 0.4, tx, ty)
        pen.fill(col if k % 2 else mix(col, '#ffffff', 0.08))
        pen.begin()
        pen.move(tx, ty)
        pen.quad(mx_, my_, ex, ey)
        pen.stroke(dark, 1.1)
    pen.begin()
    for dx in (-3, 2, 6):
        pen.circle(tx + dx * sc, ty + 4 * sc, 3.2 * sc)
    pen.fill('#6a4a2a')


# ===================================================================================
#  Water
# ===================================================================================
def water_col(B, d):
    k = ('wtab', B.id)
    tab = _cache.get(k)
    if tab is None:
        stops = THEME[B.id].water
        end = min(B.depth, 900)
        tab = _cache[k] = [stops_col(stops, i / end) for i in range(int(end) + 2)]
    i = int(d)
    return tab[0 if i < 0 else i if i < len(tab) else -1]


def draw_water(c, dt):
    P = Wd.P
    Th = TH()
    B = Wd.BIO()
    W, H, Sc, t = G.W, G.H, G.S, G.t
    top = sy(0)
    y = max(0, int(top) + 2)
    base, ppm, cam = Wd.surfBase(), G.PPM, G.cam
    while y < H:
        c.fill(water_col(B, (y - base) / ppm + cam), (0, y, W, 4))
        y += 4
    if G.erupt > 0 and P.biome == 'volcano':
        overlay_rect(c, (0, max(0, int(top)), W, H - max(0, int(top))), (255, 90, 20), 0.1 * min(1, G.erupt))
    if -60 < top < H:
        c.blit(sheen_band(P.biome), (0, top))
    draw_walls(c, B)
    if Th.caustic:
        draw_caustics(c, top, Th.caustic, Th.caus_tint or (150, 220, 255))
    if Th.rays and G.cam < 140:
        rs = ray_sprites()
        for k in range(5):
            x = W * (0.02 + k * 0.21) + math.sin(t * 0.13 + k * 1.7) * 30 * Sc
            lv = int(clamp((0.5 + 0.5 * math.sin(t * 0.31 + k * 2.1)) * 2.99, 0, 2))
            spr = rs[k % 3][lv]
            if Th.rays < 0.5:
                spr = rs[0][0]
            c.blit(spr, (x, top), special_flags=pygame.BLEND_RGB_ADD)
    draw_schools(c, Th)
    if AMB.turtle is not None:
        tu = AMB.turtle
        y = sy(tu.d) + math.sin(t * 0.8 + tu.ph) * 6
        if -60 < y < H + 60:
            fr = turtle_frames()[int((t * 3 + tu.ph) % 8)]
            if tu.vx < 0:
                fr = pygame.transform.flip(fr, True, False)
            c.blit(fr, (tu.x - fr.get_width() / 2, y - fr.get_height() / 2))
    mcol = (255, 140, 70) if P.biome == 'volcano' else (220, 240, 255)
    rise = 22 if P.biome == 'volcano' else 0
    for (mx, my, ms, mv, mp) in MOTES:
        yy = ((my * H - G.cam * G.PPM * 0.6 - t * rise * (0.5 + mv)) % H + H) % H
        if yy < top + 4:
            continue
        a = 0.25 + 0.25 * math.sin(t * 2 + mp)
        gfxdraw.box(c, (int(mx * W + math.sin(t * mv + mp) * 10), int(yy), max(1, int(ms)), max(1, int(ms))), mcol + (int(90 * a),))
    if P.biome == 'volcano':
        for v in G.vents:
            x = v.fx * W
            y0, y1 = sy(v.d0), sy(v.d1)
            if y1 < 0 or y0 > H:
                continue
            strip = vent_strip(y1 - y0)
            strip.set_alpha(int(255 * (0.32 + 0.12 * math.sin(t * 5 + v.ph))))
            c.blit(strip, (x - 20 * Sc, y0))
            strip.set_alpha(255)
            span = max(1, y1 - y0)
            for kk in range(10):
                yy = y1 - ((t * 60 * Sc + kk * 47) % span)
                if -5 < yy < H + 5:
                    gfxdraw.filled_circle(c, int(x + math.sin(t * 3 + kk) * 8 * Sc), int(yy), max(1, int(2.5 * Sc)), (255, 200, 120, 153))
    fy = sy(B.depth)
    if fy < H + 40:
        draw_floor(c, fy)


MOTES = [(random.random(), random.random(), random.random() * 2 + 0.6, random.random() * 0.3 + 0.1, random.random() * 6) for _ in range(80)]


def vent_strip(height):
    k = ('vent', int(height))
    s = _cache.get(k)
    if s is None:
        w = int(40 * G.S)
        row = pygame.Surface((w, 1), pygame.SRCALPHA)
        for x in range(w):
            u = 1 - abs(x / (w - 1) * 2 - 1)
            row.set_at((x, 0), (255, int(90 + 30 * u), int(20 + 20 * u), int(255 * u)))
        s = pygame.transform.scale(row, (w, max(1, int(height))))
        _cache[k] = s
    return s


def draw_caustics(c, top, k, tint):
    """Dancing light lines under the surface, fading out with depth (built in a buffer, then added)."""
    H, W = G.H, G.W
    band = int(72 * G.PPM) + 4
    itop = int(top)
    v0 = max(0, -itop)                 # first buffer row that is on screen
    v1 = min(band, H - itop)           # one past the last one
    if v1 - v0 <= 0:
        return
    tiles = caustic_tiles(k, tint)
    buf = _cache.get(('causbuf', W, band))
    if buf is None:
        buf = _cache[('causbuf', W, band)] = pygame.Surface((W, band))
    area = pygame.Rect(0, v0, W, v1 - v0)
    buf.fill((0, 0, 0), area)
    old = buf.get_clip()
    buf.set_clip(area)
    t = G.t
    for layer, (vx, vy) in enumerate(((13, 5), (-10, 8))):
        tile = tiles[layer]
        yy = -128 + int((t * vy) % 128)
        while yy < v1:
            if yy + 128 > v0:
                x = -512 + int((t * vx) % 512)
                while x < W:
                    buf.blit(tile, (x, yy), special_flags=pygame.BLEND_RGB_ADD)
                    x += 512
            yy += 128
    buf.set_clip(old)
    buf.blit(caustic_fade(W, band), area.topleft, area, special_flags=pygame.BLEND_RGB_MULT)
    c.blit(buf, (0, itop + v0), area, special_flags=pygame.BLEND_RGB_ADD)


def wall_thickness(bid, side, d):
    Sc = G.S
    iw = island_w()
    if bid == 'shore':
        if side == 1:
            return None
        slope = iw * 1.05 * max(0.0, 1 - d / 55) ** 1.3
        return max(slope, (22 + 46 * fbm(d * 0.045 + 3)) * Sc)
    if bid == 'reef':
        if side == 0:
            slope = iw * 1.05 * max(0.0, 1 - d / 35) ** 1.2
            return max(slope, (40 + 70 * fbm(d * 0.03 + 1)) * Sc)
        k = clamp((d - 60) / 90, 0, 1)
        return (20 + 70 * fbm(d * 0.025 + 9)) * Sc * k if k > 0 else None
    if bid == 'volcano':
        th = (56 + 74 * fbm(d * 0.02 + side * 11)) * Sc
        if side == 0:
            th = max(th, iw * 1.05 * max(0.0, 1 - d / 40))
        return th
    th = (70 + 95 * fbm(d * 0.012 + side * 7)) * Sc * (0.55 + 0.45 * clamp(d / 300, 0, 1))
    if side == 0:
        th = max(th, iw * 1.05 * max(0.0, 1 - d / 40))
    return th


def _hash(k):
    return _NZ[k & 1023]


CORAL_COLS = ['#ff7ab0', '#ffb070', '#c9a0ff', '#7ae0c0', '#ffd27a', '#ff6a6a']


def wall_cols(B, Th, dm, end):
    key = ('wcol', B.id, int(dm))
    v = _cache.get(key)
    if v is None:
        wc = water_col(B, dm)
        fog = clamp(dm / end, 0, 1) * 0.72
        v = _cache[key] = (mix(Th.wall, wc, fog), mix(mix(Th.wall, '#000000', 0.38), wc, fog), wc, fog)
    return v


def draw_walls(c, B):
    """Rock walls down the sides: a lit rim, a shadowed inside, rocks, corals, all fading into the deep."""
    P = Wd.P
    Th = TH()
    W, H, Sc = G.W, G.H, G.S
    base, ppm, cam = Wd.surfBase(), G.PPM, G.cam
    d_top = max(0.0, cam + (0 - base) / ppm)
    d_bot = min(B.depth, cam + (H - base) / ppm)
    if d_bot <= d_top:
        return
    end = min(B.depth, 900)
    step = 4.0
    inset = 18 * Sc
    for side in (0, 1):
        sgn = 1 if side == 0 else -1
        edge = 0 if side == 0 else W
        pts = []
        d = math.floor(d_top / step) * step - step
        while d <= d_bot + step:
            dd = clamp(d, 0, B.depth)
            th = wall_thickness(P.biome, side, dd)
            if th is not None:
                pts.append((th if side == 0 else W - th, sy(dd), dd, th))
            d += step
        if len(pts) < 2:
            continue
        for i in range(len(pts) - 1):
            (x0, y0, d0, t0), (x1, y1, _, _) = pts[i], pts[i + 1]
            dm = d0 + step / 2
            col, dark, wc, fog = wall_cols(B, Th, dm, end)
            yy0, yy1 = int(y0), int(y1) + 1
            gfxdraw.filled_polygon(c, [(edge, yy0), (int(x0), yy0), (int(x1), yy1), (edge, yy1)], col)
            ix0, ix1 = x0 - sgn * inset, x1 - sgn * inset
            if (ix0 - edge) * sgn > 2 and (ix1 - edge) * sgn > 2:
                gfxdraw.filled_polygon(c, [(edge, yy0), (int(ix0), yy0), (int(ix1), yy1), (edge, yy1)], dark)
            k = int(d0 / step) * 7 + side * 131
            if _hash(k) < 0.55 and t0 > 26 * Sc:
                rx = edge + sgn * t0 * (0.15 + 0.55 * _hash(k + 3))
                rr = (3 + 7 * _hash(k + 5)) * Sc
                gfxdraw.filled_ellipse(c, int(rx), int(y0 + (y1 - y0) * _hash(k + 9)), int(rr * 1.4), int(rr), mix(dark, '#000000', 0.25))
            if P.biome == 'reef' and _hash(k + 11) < 0.32 and dm < 300:
                cc = mix(CORAL_COLS[int(_hash(k + 13) * 6) % 6], wc, fog * 1.1)
                cx = x0 + sgn * 2
                for j in range(3):
                    rr = (5 + 5 * _hash(k + 17 + j)) * Sc
                    gfxdraw.filled_circle(c, int(cx + sgn * (j - 1) * 5 * Sc), int(y0 - j * 4 * Sc), int(rr), cc)
        rim_pts = [(x + sgn * 1.5, y) for x, y, _, _ in pts]
        for i in range(0, len(rim_pts) - 1, 4):
            seg = rim_pts[i:i + 5]
            dm = pts[min(len(pts) - 1, i + 2)][2]
            rim = mix(Th.wallhi, water_col(B, dm), clamp(dm / end, 0, 1) * 0.72)
            pygame.draw.aalines(c, rim, False, seg)
            pygame.draw.aalines(c, rim, False, [(x + sgn, y) for x, y in seg])
    cave = CAVES.get(P.biome)
    if cave:
        depth = sum(cave.d) / 2
        cy = int(sy(depth))
        if -120 * Sc < cy < H + 120 * Sc:
            cx = int(sum(cave.x) * 0.5 * W)
            cw, ch = int(150 * Sc), int(104 * Sc)
            mouth = pygame.Rect(cx - cw // 2, cy - ch // 2, cw, ch)
            rock = pygame.Rect(mouth.x - int(14 * Sc), mouth.y - int(12 * Sc), mouth.w + int(28 * Sc), mouth.h + int(24 * Sc))
            gfxdraw.filled_ellipse(c, rock.centerx, rock.centery, rock.w // 2, rock.h // 2, hexc(Th.wall))
            gfxdraw.filled_ellipse(c, mouth.centerx, mouth.centery, mouth.w // 2, mouth.h // 2, hexc(mix(water_col(B, depth), '#000000', 0.72)))
            pygame.draw.arc(c, hexc(Th.wallhi), rock, math.pi, TAU, max(2, int(5 * Sc)))
            pygame.draw.arc(c, hexc(Th.wallhi), mouth, math.pi, TAU, max(1, int(2 * Sc)))


def draw_floor(c, fy):
    P = Wd.P
    Th = TH()
    W, H, Sc, t = G.W, G.H, G.S, G.t
    layer, top, glows, plants, edge = floor_layer(P.biome)
    c.blit(layer, (0, fy - top))
    yb = int(fy - top + layer.get_height())
    if yb < H:
        c.fill(hexc(Th.floor2), (0, yb, W, H - yb))
    pen = Pen(c, aa=True)
    off = fy - top
    if P.biome == 'shore':
        for (x, n) in plants:
            gy = _edge_y(edge, x) + off
            for j in range(n):
                bx = x + (j - n / 2) * 5 * Sc
                h = (36 + 12 * math.sin(j * 2.3 + x)) * Sc
                pen.begin()
                pen.move(bx, gy + 4)
                for s in range(1, 6):
                    u = s / 5
                    pen.line(bx + math.sin(t * 1.4 + s * 0.8 + x * 0.1 + j) * 7 * Sc * u, gy - h * u)
                pen.stroke('#3f8a46' if j % 2 else '#2f7a3a', 4 * Sc, 'round')
    elif P.biome == 'reef':
        for (x, kind) in plants:
            gy = _edge_y(edge, x) + off
            if kind == 0:
                for j in range(7):
                    a = -math.pi / 2 + (j - 3) * 0.22 + math.sin(t * 1.2 + j + x) * 0.08
                    pen.begin()
                    pen.move(x, gy)
                    pen.quad(x + math.cos(a) * 14 * Sc, gy + math.sin(a) * 14 * Sc, x + math.cos(a) * 26 * Sc, gy + math.sin(a) * 26 * Sc)
                    pen.stroke('#ff7ab0', 2.2 * Sc, 'round')
                    gfxdraw.filled_circle(c, int(x + math.cos(a) * 26 * Sc), int(gy + math.sin(a) * 26 * Sc), max(1, int(2.2 * Sc)), (255, 200, 225))
            elif kind == 1:
                pen.begin()
                pen.move(x, gy)
                for s in range(1, 8):
                    u = s / 7
                    pen.line(x + math.sin(t * 1.1 + s + x) * 6 * Sc * u, gy - 60 * Sc * u)
                pen.stroke('#2fbf7a', 3.5 * Sc, 'round')
            else:
                sw = math.sin(t * 0.9 + x) * 0.05
                pen.save()
                pen.translate(x, gy)
                pen.rotate(sw)
                pen.begin()
                pen.ellipse(0, -22 * Sc, 18 * Sc, 22 * Sc, 0, math.pi, TAU)
                pen.fill((180, 110, 255, 150))
                pen.begin()
                for j in range(6):
                    a = math.pi + (j + 0.5) * math.pi / 6
                    pen.move(0, 0)
                    pen.line(math.cos(a) * 18 * Sc, -22 * Sc + math.sin(a) * 22 * Sc + 22 * Sc)
                pen.stroke((120, 60, 200, 160), 1.2)
                pen.restore()
    elif P.biome == 'volcano':
        for (x, y, r, col) in glows:
            add_glow(c, x, y + off, r, col, 0.45 + 0.35 * math.sin(t * 2 + x))
        for (x, y) in plants:
            for kk in range(4):
                ph = (t * 0.6 + kk * 0.25 + x * 0.01) % 1.0
                gfxdraw.filled_circle(c, int(x + math.sin(t * 3 + kk) * 5), int(y + off - ph * 120 * Sc), max(1, int((2 + ph * 3) * Sc)), (255, 200, 140, int(170 * (1 - ph))))
    elif P.biome == 'trench':
        for (x, y) in plants:
            gfxdraw.filled_circle(c, int(x), int(y + off), max(1, int(2.6 * Sc)), (230, 60, 70))
    elif P.biome == 'mariana':
        for (x, y, r, col) in glows:
            add_glow(c, x, y + off, r, col, 0.4 + 0.3 * math.sin(t * 2.2 + x))
        for (x, y) in plants:
            for kk in range(6):
                ph = (t * 0.35 + kk / 6 + x * 0.01) % 1.0
                rr = int((4 + ph * 16) * Sc)
                gfxdraw.filled_circle(c, int(x + math.sin(t * 0.8 + kk) * 6 * ph * 4), int(y + off - ph * 150 * Sc), max(1, rr),
                                      (30, 26, 24, int(170 * (1 - ph))))
    elif P.biome == 'frost':
        for (x, y, r, col) in glows:
            add_glow(c, x, y + off, r, col, 0.3 + 0.2 * math.sin(t * 1.4 + x))
        for (x, kind) in plants:
            gy = _edge_y(edge, x) + off
            colp = (255, 214, 232) if kind else (240, 248, 255)
            for j in range(6):
                a = -math.pi / 2 + (j - 2.5) * 0.25 + math.sin(t * 1.1 + j + x) * 0.07
                tx_, ty_ = x + math.cos(a) * 24 * Sc, gy + math.sin(a) * 24 * Sc
                pen.begin()
                pen.move(x, gy)
                pen.quad(x + math.cos(a) * 12 * Sc, gy + math.sin(a) * 12 * Sc, tx_, ty_)
                pen.stroke(colp, 2.4 * Sc, 'round')
                gfxdraw.filled_circle(c, int(tx_), int(ty_), max(1, int(3 * Sc)), colp + (230,))
    elif P.biome == 'pallid':
        for (x, n) in plants:
            gy = _edge_y(edge, x) + off
            for j in range(n):
                bx = x + (j - n / 2) * 7 * Sc
                h = (70 + 30 * math.sin(j * 2.1 + x)) * Sc
                pen.begin()
                pen.move(bx, gy + 4)
                pts = []
                for s_ in range(1, 9):
                    u = s_ / 8
                    px = bx + math.sin(t * 0.9 + s_ * 0.6 + x * 0.1 + j) * 10 * Sc * u
                    pen.line(px, gy - h * u)
                    pts.append((px, gy - h * u))
                pen.stroke('#5a5a2a' if j % 2 else '#4a4a22', 3.2 * Sc, 'round')
                for k_, (px, py) in enumerate(pts[1:-1]):
                    if k_ % 2 == 0:
                        gfxdraw.filled_circle(c, int(px + 3 * Sc), int(py), max(1, int(2.2 * Sc)), (110, 104, 52))
    elif P.biome == 'atlantis':
        for (x, gy) in plants:
            pen.begin()
            pen.move(x, gy + off)
            for k in range(1, 7):
                u = k / 6
                pen.line(x + math.sin(t * 1.3 + k + x * 0.02) * 5 * Sc * u, gy + off - 26 * Sc * u)
            pen.stroke('#74c9a7', 2 * Sc, 'round')
        for (x, gy, r, col) in glows:
            add_glow(c, x, gy + off, r, col, 0.48 + 0.3 * math.sin(t * 1.8 + x))
    elif P.biome == 'redhollow':
        pulse = 0.45 + 0.4 * math.sin(t * 1.7)
        for (x, gy, r, col) in glows:
            add_glow(c, x, gy + off, r * (0.9 + pulse * 0.3), col, pulse)
        for x, gy in plants:
            gfxdraw.filled_circle(c, int(x), int(gy + off), max(1, int(2.2 * Sc)), (255, 75, 110, int(170 * pulse)))


def _edge_y(edge, x):
    W = G.W
    i = clamp(int(x / W * 40), 0, 39)
    (x0, y0), (x1, y1) = edge[i], edge[i + 1]
    return lerp(y0, y1, (x - x0) / ((x1 - x0) or 1))


def floor_glows(c):
    """Crystals on the trench floor glow through the dark."""
    P = Wd.P
    if not TH().floorglow:
        return
    fy = sy(Wd.BIO().depth)
    if fy > G.H + 60:
        return
    layer, top, glows, plants, edge = floor_layer(P.biome)
    for (x, y, r, col) in glows:
        add_glow(c, x, y + fy - top, r * 1.6, col, 0.55 + 0.4 * math.sin(G.t * 1.5 + x))


def draw_schools(c, Th):
    if not AMB.schools or Th.school == 'glow':
        return
    t, H = G.t, G.H
    spr = tiny_fish(Th.school)
    for s in AMB.schools:
        y0 = sy(s.d)
        if y0 < sy(0) + 10 or y0 > H + 40:
            continue
        img = spr[0] if s.vx > 0 else spr[1]
        for (ox, oy, ph) in s.members:
            x = s.x + ox + math.sin(t * 1.3 + ph) * 5
            y = y0 + oy + math.sin(t * 1.9 + ph) * 3
            if y > sy(0) + 6:
                c.blit(img, (x, y))


def draw_glowers(c):
    """Things that glow in the dark, drawn after the trench darkness so they shine through it."""
    P = Wd.P
    Th = TH()
    t, H, W, Sc = G.t, G.H, G.W, G.S
    if not AMB.specks and BIOMES[P.biome].dark is None:
        return
    d_top = G.cam + (0 - Wd.surfBase()) / G.PPM - 10
    d_bot = G.cam + (H - Wd.surfBase()) / G.PPM + 10
    for s in AMB.specks:
        if not d_top < s.d < d_bot:
            continue
        th = wall_thickness(P.biome, s.side, s.d)
        if th is None:
            continue
        x = (th - s.off * Sc) if s.side == 0 else (W - th + s.off * Sc)
        k = 0.35 + 0.35 * math.sin(t * 1.3 + s.ph)
        add_glow(c, x, sy(s.d), s.r * Sc, s.col, k * (Th.speck_k or 1))
    if BIOMES[P.biome].dark is None:
        return
    floor_glows(c)
    for j in AMB.jellies:
        y = sy(j.d) + math.sin(t * 0.5 + j.ph) * 12
        if -60 < y < H + 60:
            add_glow(c, j.x, y, 34 * Sc, j.col, 0.35 + 0.15 * math.sin(t * 2 + j.ph))
            fr = jelly_sprite(j.col)[int((t * 3 + j.ph) % 6)]
            c.blit(fr, (j.x - fr.get_width() / 2, y - 18))
    for s in (AMB.schools if Th.school == 'glow' else ()):
        y0 = sy(s.d)
        if -40 < y0 < H + 40:
            for (ox, oy, ph) in s.members:
                x = s.x + ox + math.sin(t * 1.3 + ph) * 5
                y = y0 + oy + math.sin(t * 1.9 + ph) * 3
                add_glow(c, x, y, 5 * Sc, '#7ffcff', 0.8)
    for p in AMB.plankton:
        add_glow(c, p.x, sy(p.d), 6 * Sc, '#7ffcff', p.life / p.max)
    if AMB.msnow and G.cam > 150:
        k = clamp((G.cam - 150) / 500, 0, 1)
        for m in AMB.msnow:
            gfxdraw.filled_circle(c, int(m.x), int(m.y), m.r, (215, 225, 235, int(110 * k)))


# ===================================================================================
#  The water surface
# ===================================================================================
def wave_y(x, t, Sc):
    return math.sin(x * 0.018 + t * 1.8) * 3.2 * Sc + math.sin(x * 0.047 - t * 2.6) * 1.6 * Sc + math.sin(x * 0.11 + t * 1.1) * 0.8 * Sc


def draw_surface(c):
    y0 = sy(0)
    if y0 < -30 or y0 > G.H + 30:
        return
    Th = TH()
    W, Sc, t = G.W, G.S, G.t
    B = Wd.BIO()
    pts = [(x, y0 + wave_y(x, t, Sc)) for x in range(0, W + 17, 16)]
    poly = pts + [(W, y0 + 9), (0, y0 + 9)]
    surf = hexc(Th.surf)
    body = mix(surf, water_col(B, 0), 0.35)
    gfxdraw.filled_polygon(c, [(int(x), int(y)) for x, y in poly], body + (225,))
    hi = mix(surf, '#ffffff', 0.55)
    pygame.draw.aalines(c, hi, False, pts)
    pygame.draw.aalines(c, hi, False, [(x, y + 1) for x, y in pts])
    gfxdraw.box(c, (0, int(y0 + 9), W, int(12 * Sc)), (255, 255, 255, 16))
    for i in range(1, len(pts) - 1):
        if pts[i][1] < pts[i - 1][1] and pts[i][1] <= pts[i + 1][1]:
            x, y = pts[i]
            a = int(150 + 80 * math.sin(t * 3 + x))
            gfxdraw.hline(c, int(x - 5 * Sc), int(x + 5 * Sc), int(y - 1), (255, 255, 255, max(0, min(255, a))))
    if Th.sun:
        cx = W * 0.78
        k = 1.0 if Th.sun == 'sun' else 0.55
        for g in AMB.glitter:
            v = math.sin(t * g.f + g.ph)
            if v <= 0.55:
                continue
            a = ((v - 0.55) / 0.45) ** 2 * k
            x = cx + g.dx * 240 * Sc
            y = y0 + wave_y(x, t, Sc) + 3 + g.dy * 22 * Sc * (1 - abs(g.dx) * 0.6)
            col = (255, 255, 240) if Th.sun == 'sun' else (220, 230, 255)
            gfxdraw.hline(c, int(x - 3 * Sc), int(x + 3 * Sc), int(y), col + (int(230 * a),))
            if a > 0.5:
                gfxdraw.vline(c, int(x), int(y - 2 * Sc), int(y + 2 * Sc), col + (int(160 * a),))
    for rp in G.ripples:
        u = rp.t / rp.life
        rx = (8 + 80 * u) * rp.size * Sc
        a = int(180 * (1 - u) ** 1.5)
        if a > 4 and rx > 1:
            gfxdraw.aaellipse(c, int(rp.x), int(y0 + 2), int(rx), max(1, int(rx * 0.2)), (255, 255, 255, a))
            if rx > 12:
                gfxdraw.aaellipse(c, int(rp.x), int(y0 + 2), int(rx * 0.6), max(1, int(rx * 0.12)), (255, 255, 255, a // 2))


def draw_reflection(c, x, w, col):
    """A wobbly reflection of a boat just under the water surface."""
    y0 = sy(0)
    if y0 < -30 or y0 > G.H + 30:
        return
    t, Sc = G.t, G.S
    cr, cg, cb = hexc(col)
    for i in range(6):
        ww = w * (1 - i * 0.12)
        ox = math.sin(t * 2.2 + i * 1.3) * 4 * Sc
        gfxdraw.box(c, (int(x - ww / 2 + ox), int(y0 + 10 + i * 5 * Sc), int(ww), max(1, int(3 * Sc))), (cr, cg, cb, 70 - i * 10))


def draw_jumps(c):
    for j in AMB.jumps:
        u = clamp(j.t / j.dur, 0, 1)
        if u >= 1:
            continue
        Sc = G.S
        x = j.x0 + j.dir * 90 * Sc * u
        y = sy(0) - math.sin(u * math.pi) * j.h + 4
        dx = j.dir * 90 * Sc
        dy = -j.h * math.pi * math.cos(u * math.pi)
        rot = math.atan2(dy, abs(dx))
        L = j.sp.len * Sc
        blit_fish(c, j.sp, None, False, L * 1.23, L, int(G.t * 8) % 16, x, y, j.dir < 0, rot * j.dir)


def draw_vignette(c):
    k = clamp((G.cam - 8) / 140, 0, 0.8)
    if BIOMES[Wd.P.biome].dark is not None:
        k = min(1.0, k + 0.2)
    if k <= 0.03:
        return
    W, H = G.W, G.H
    tl, tr, bl, br = vignette_corner()
    a = int(255 * k)
    w, h = tl.get_size()
    for spr, pos in ((tl, (0, 0)), (tr, (W - w, 0)), (bl, (0, H - h)), (br, (W - w, H - h))):
        spr.set_alpha(a)
        c.blit(spr, pos)
        spr.set_alpha(255)
