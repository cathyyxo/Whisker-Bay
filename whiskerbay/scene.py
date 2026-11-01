"""Painting everything in front of the backdrop: fish, particles, boats, the line, the reel bar and the big overlays.
The sky, islands, water, light and sea floor live in backdrop.py."""
import math
import random

import pygame
from pygame import gfxdraw

from . import backdrop as BD
from . import online, ui
from . import world as Wd
from . import pets as PT
from .art import FRAMES, RATE, Pen, _blur, _col, blit_fish, draw_ability_icon, draw_boat_cat, portrait, pump
from .data import ABILITIES, BIOMES, BOAT, BOSSES, GIMMICKS, MUT, RAR, REEL
from .settings import SET
from .util import D, TAU, clamp, fmt, fmtW, hexc, lerp, mix, rand, rgba

G = Wd.G
_cache = {}


def sy(d):
    return Wd.sy(d)


def nframes(sp):
    return 24 if sp.r == 'leviathan' else FRAMES


def frame_of(sp, t):
    n = nframes(sp)
    return int(t * RATE.get(sp.shape, 6) / TAU * n) % n


def base_len(sp):
    if sp.r == 'leviathan':
        return min(640.0, sp.len * G.S * 1.23 * 0.86)
    return sp.len * G.S * 1.23 * Wd.FISH_K


def clear_caches():
    _cache.clear()
    BD.clear_caches()


def ring_sprite(w, h, col):
    k = ('ring', int(w), int(h), col)
    s = _cache.get(k)
    if s is None:
        s = pygame.Surface((int(w) + 4, int(h) + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(s, hexc(col), (2, 2, int(w), int(h)), 2)
        _cache[k] = s
    return s


def hole_sprite(r, s):
    r = max(4, int(r))
    lvl = int(s * 20)
    k = ('hole', r, lvl)
    sp = _cache.get(k)
    if sp is None:
        sp = pygame.Surface((2 * r, 2 * r), pygame.SRCALPHA)
        steps = 24
        for i in range(steps):
            rr = r * (1 - i / steps)
            pygame.draw.circle(sp, (0, 0, 0, int(255 * (lvl / 20) * (i + 1) / steps)), (r, r), max(1, int(rr)))
        _cache[k] = sp
        if len(_cache) > 900:
            for kk in [x for x in list(_cache.keys()) if isinstance(x, tuple) and x[0] == 'hole'][:300]:
                del _cache[kk]
    return sp


def soft_blob(w, h, col, a):
    """A soft cloudy blob (used for ink and frost)."""
    key = ('blob', int(w), int(h), col, a)
    s = _cache.get(key)
    if s is None:
        w, h = max(8, int(w)), max(8, int(h))
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        rng = random.Random(w * 31 + h)
        cc = hexc(col)
        for _ in range(9):
            rx, ry = rng.uniform(0.18, 0.3) * w, rng.uniform(0.25, 0.4) * h
            cx, cy = rng.uniform(0.3, 0.7) * w, rng.uniform(0.35, 0.65) * h
            pygame.draw.ellipse(s, cc + (a,), (cx - rx, cy - ry, 2 * rx, 2 * ry))
        s = _blur(s, max(2, int(min(w, h) * 0.08)))
        _cache[key] = s
    return s


# ===================================================================================
#  Fish
# ===================================================================================
def _reel_for(f):
    R = G.reel
    return R if (R is not None and G.mode == 'reel' and R.f is f) else None


def draw_fishes(c):
    P = Wd.P
    sonar = G.stats.sonar
    W, H, t = G.W, G.H, G.t
    surf_y = sy(0)
    names = []
    for f in G.fish:
        x, y = f.x, sy(f.d)
        if y < surf_y - 20 or y > H + f.size * 1.5 or x < -f.size * 1.2 or x > W + f.size * 1.2:
            continue
        hooked = f.state == 'hooked'
        clear = f.d < 26 or (P.biome == 'reef' and f.d < 60)
        sil = not (sonar >= 1 or clear or hooked) and f.tier != 6
        sp = f.sp
        size, alpha, sx = f.size, f.alpha, 1.0
        R = _reel_for(f) if hooked else None
        if hooked:
            frozen = R is not None and R.abT.get('freeze', 0) > 0
            rot = 0.0 if frozen else math.sin(t * 14) * 0.35
            face = f.dir
            frame = 3 if frozen else frame_of(sp, t * 2.2)
            if R is not None:
                if R.eff.get('puff'):
                    size *= 1.4
                if R.eff.get('camo'):
                    alpha *= 0.22
        else:
            rot = clamp(f.vd * G.PPM / max(30, abs(f.vx) + 30), -0.5, 0.5)
            k = (f.turn or 0.0) / 0.32
            if k > 0:
                sx = abs(2 * k - 1)
                face = -f.dir if k > 0.5 else f.dir
            else:
                face = f.dir
            frame = frame_of(sp, f.anim)
        # sonar: a soft light along the fish's own outline, in its rarity colour (brighter for the big ones on Mk III)
        glow, oa = None, 0.0
        if sonar >= 1 and f.tier >= 1 and not sil and not hooked:
            glow = RAR[f.tier].col
            big = sonar >= 3 and f.tier >= 4
            oa = (0.52 + 0.22 * math.sin(t * 2.4 + f.seed)) if big else (0.26 + 0.1 * math.sin(t * 2.0 + f.seed))
        blit_fish(c, sp, None if sil else f.mut, sil, base_len(sp), size, frame, x, y, face < 0, rot * face, alpha, nframes(sp), sx,
                  outline=glow, oa=oa)
        if R is not None:
            hooked_fx(c, R, x, y, size)
        if sonar >= 2 and not sil and SET.get('sonarNames', True) and not (sonar >= 3 and f.tier >= 4 and not hooked):
            names.append((x, y - f.size * 0.42 - 6, (MUT[f.mut].name + ' ' if f.mut else '') + sp.name, RAR[f.tier].col))
    for x, y, txt, col in names:
        ui.text(c, txt, x, y, 'x', max(10, int(11 * max(0.85, G.S))), col, 'center', 'baseline', outline=2, ocol=(0, 0, 0, 120))


def _eff_alpha(R, g, fade_in=0.25, fade_out=0.45):
    rem = R.eff.get(g, 0)
    if rem <= 0:
        return 0.0
    dur = GIMMICKS[g].dur or 1.0
    return clamp(min((dur - rem) / fade_in, rem / fade_out), 0, 1)


def hooked_fx(c, R, x, y, size):
    """The fish's tricks and your abilities also show in the water, around the fish on your line."""
    t, Sc = G.t, G.S
    a = _eff_alpha(R, 'ink')
    if a > 0:
        b = soft_blob(size * 2.4, size * 1.6, '#1a0f33', 215)
        b.set_alpha(int(255 * a))
        c.blit(b, (x - b.get_width() / 2, y - b.get_height() / 2))
        b.set_alpha(255)
    if R.eff.get('zap'):
        for k in range(3):
            ang = random.random() * TAU
            r0, r1 = size * 0.3, size * 0.75
            pts = [(x + math.cos(ang) * r0, y + math.sin(ang) * r0 * 0.6)]
            for s in range(1, 4):
                rr = lerp(r0, r1, s / 3)
                aa = ang + rand(-0.4, 0.4)
                pts.append((x + math.cos(aa) * rr, y + math.sin(aa) * rr * 0.6))
            pygame.draw.aalines(c, (160, 250, 255), False, pts)
    if R.abT.get('freeze', 0) > 0:
        w, h = size * 1.35, size * 0.85
        rect = (x - w / 2, y - h / 2, w, h)
        ui.box(c, rect, (190, 238, 255, 95), (230, 250, 255, 220), int(8 * Sc), 2)
        p = Pen(c, aa=True)
        p.begin()
        p.move(x - w * 0.36, y - h * 0.3)
        p.line(x - w * 0.12, y - h * 0.38)
        p.move(x - w * 0.38, y - h * 0.12)
        p.line(x - w * 0.3, y - h * 0.2)
        p.stroke((255, 255, 255, 200), 1.4)
    if R.slashT > 0:
        u = R.slashT / 0.55
        p = Pen(c, aa=True)
        L = size * (0.9 + 0.3 * (1 - u))
        p.begin()
        p.move(x - L * 0.6, y + L * 0.32)
        p.line(x + L * 0.6, y - L * 0.32)
        p.stroke((255, 120, 180, int(150 * u)), 9 * u + 2, 'round')
        p.stroke((255, 255, 255, int(255 * u)), 3 * u + 1, 'round')
    if R.abT.get('gravity', 0) > 0:
        for k in range(3):
            ph = (t * 1.4 + k / 3) % 1.0
            rr = size * (1.2 - ph * 0.9)
            gfxdraw.aaellipse(c, int(x), int(y), max(2, int(rr)), max(2, int(rr * 0.55)), (92, 207, 255, int(200 * ph)))
    if R.abT.get('inferno', 0) > 0:
        BD.add_glow(c, x, y, size * 0.9, '#ff7a2a', 0.6 + 0.2 * math.sin(t * 12))
    if R.abT.get('phoenix', 0) > 0:
        BD.add_glow(c, x, y, size * 0.8, '#ffb03a', 0.4 + 0.2 * math.sin(t * 9))
    if R.abT.get('gold', 0) > 0:
        BD.add_glow(c, x, y, size * 0.8, '#ffd23d', 0.45)
    if R.zapT > 0:
        u = R.zapT / 0.6
        bolt = Pen(c, aa=True)
        bolt.begin()
        bolt.move(x + size * 0.1, y - size * 1.4)
        for k in range(1, 6):
            bolt.line(x + (size * 0.18 if k % 2 else -size * 0.12), y - size * 1.4 + size * 1.4 * k / 5)
        bolt.stroke((98, 243, 255, int(140 * u)), 9, 'round')
        bolt.stroke((255, 255, 255, int(255 * u)), 3, 'round')
    if R.warn:
        gm = GIMMICKS[R.warn[0]]
        pulse = 0.5 + 0.5 * math.sin(t * 20)
        yy = y - size * 0.55 - 14 * Sc
        gfxdraw.filled_circle(c, int(x), int(yy), int(10 * Sc), hexc(gm.col) + (int(150 + 100 * pulse),))
        ui.text(c, '!', x, yy + 1, 'd', int(16 * Sc), (20, 20, 30), 'center', 'middle')


def draw_landing(c):
    L = G.land
    if not L or G.mode != 'landing':
        return
    f = L.f
    ang = -math.pi / 2 + math.sin(G.t * 14) * 0.3
    blit_fish(c, f.sp, f.mut, False, base_len(f.sp), f.size, frame_of(f.sp, G.t * 2.5), G.hook.x, sy(G.hook.d) + f.size * 0.3, False, ang, 1.0, nframes(f.sp))


# ===================================================================================
#  Particles and floating text
# ===================================================================================
def draw_parts(c):
    H = G.H
    t = G.t
    for p in G.parts:
        y = sy(p.d)
        if y < -20 or y > H + 20:
            continue
        a = p.life / p.max
        x = p.x
        col = _col(p.col)
        k = p.kind
        if k == 'bubble':
            r = max(1, int(p.size))
            xx = x + math.sin(t * 3 + p.max * 7) * 1.5
            gfxdraw.aacircle(c, int(xx), int(y), r, (col[0], col[1], col[2], int(200 * a)))
            if r >= 2:
                gfxdraw.pixel(c, int(xx - r * 0.4), int(y - r * 0.4), (255, 255, 255, int(230 * a)))
        elif k == 'star':
            ang = t * 3
            ca, sa = math.cos(ang) * p.size, math.sin(ang) * p.size
            cc = (col[0], col[1], col[2], int(255 * a))
            gfxdraw.line(c, int(x - ca), int(y - sa), int(x + ca), int(y + sa), cc)
            gfxdraw.line(c, int(x + sa), int(y - ca), int(x - sa), int(y + ca), cc)
        elif k == 'zap':
            cc = (col[0], col[1], col[2], int(255 * a))
            x1, y1 = x + rand(-6, 6), y + rand(-6, 6)
            gfxdraw.line(c, int(x), int(y), int(x1), int(y1), cc)
            gfxdraw.line(c, int(x1), int(y1), int(x + rand(-8, 8)), int(y + rand(-8, 8)), cc)
        else:
            if k == 'smoke':
                r = p.size * (2 - a)
                aa = a * 0.35
            else:
                r = p.size
                aa = a
            ri = max(1, int(r))
            gfxdraw.filled_circle(c, int(x), int(y), ri, (col[0], col[1], col[2], int(255 * aa)))
            if k == 'drop' and ri >= 2:
                gfxdraw.pixel(c, int(x - ri * 0.3), int(y - ri * 0.3), (255, 255, 255, int(255 * aa)))


def draw_screen_parts(c):
    rain = (168, 200, 255, int(255 * 0.5 * G.storm))
    for p in G.sparts:
        if p.kind == 'rain':
            gfxdraw.line(c, int(p.x), int(p.y), int(p.x - 4), int(p.y + 14), rain)
            continue
        a = min(1, p.life / p.max * 2)
        col = _col(p.col)
        r = max(1, int(p.size))
        if p.kind == 'ember':
            gfxdraw.filled_circle(c, int(p.x), int(p.y), r * 3, (col[0], col[1], col[2], int(60 * a)))
        gfxdraw.filled_circle(c, int(p.x), int(p.y), r, (col[0], col[1], col[2], int(255 * a)))


def draw_floats(c):
    for f in G.floats:
        a = min(1, (f.dur - f.t) * 2.5)
        pop = 1 + 0.35 * max(0, 1 - f.t * 6)
        y = sy(f.d) - f.t * 30
        ui.text(c, f.text, f.x, y, 'd', int(f.size * max(0.85, G.S) * pop), f.col, 'center', 'baseline', alpha=a, outline=3, ocol=(0, 0, 0, 153))


# ===================================================================================
#  The line and the hook
# ===================================================================================
def draw_line_for(c, tip, mode, hx, hd, hold, bait_col):
    """Draw a fishing line from a rod tip. Used for you and for other anglers."""
    Sc = G.S
    if mode in ('idle', 'charge', 'card', 'sail') or hd < 0:
        swing = math.sin(G.t * 2) * 6 * Sc
        x, y = tip[0] + swing, tip[1] + 42 * Sc
        pygame.draw.aaline(c, (225, 235, 245), tip, (x, y))
        draw_hook_icon(c, x, y, bait_col)
        return
    hy, wy = sy(hd), sy(0)
    taut = mode in ('reel', 'landing', 'bite')
    col = (250, 252, 255) if taut else (215, 228, 240)
    pts = []
    if hd <= 0:
        cx, cy = (tip[0] + hx) / 2, max(tip[1], hy) + 20
        p0, p1, p2 = tip, (cx, cy), (hx, hy)
    else:
        p0, p1, p2 = tip, (lerp(tip[0], hx, 0.6), lerp(tip[1], wy, 0.7) if taut else wy + 8), (hx, wy)
    for i in range(17):
        tt = i / 16
        u = 1 - tt
        pts.append((u * u * p0[0] + 2 * u * tt * p1[0] + tt * tt * p2[0], u * u * p0[1] + 2 * u * tt * p1[1] + tt * tt * p2[1]))
    if hd > 0:
        if taut and mode == 'reel':
            vib = math.sin(G.t * 60) * 1.2
            mx, my = (hx + pts[-1][0]) / 2 + vib, (hy + wy) / 2
            pts.append((mx, my))
        pts.append((hx, hy))
    pygame.draw.aalines(c, col, False, pts)
    if taut:
        pygame.draw.aalines(c, col, False, [(px + 0.6, py) for px, py in pts])
    if hd > 0:
        by = wy + math.sin(G.t * 3) * 2 + (math.sin(G.t * 30) * 4 if mode == 'bite' else 0)
        pen = Pen(c, aa=True)
        pen.begin()
        pen.arc(hx, by - 3, 6 * Sc, math.pi, TAU)
        pen.fill('#ff4f6d')
        pen.begin()
        pen.arc(hx, by - 3, 6 * Sc, 0, math.pi)
        pen.fill('#ffffff')
        gfxdraw.filled_circle(c, int(hx - 2 * Sc), int(by - 6 * Sc), max(1, int(1.6 * Sc)), (255, 255, 255, 200))
    draw_hook_icon(c, hx, hy, bait_col)
    if hold and mode == 'sinking':
        r = 14 * Sc
        for i in range(0, 16, 2):
            a0, a1 = TAU * i / 16 + G.t, TAU * (i + 1) / 16 + G.t
            pygame.draw.aaline(c, (255, 217, 138), (hx + math.cos(a0) * r, hy + math.sin(a0) * r), (hx + math.cos(a1) * r, hy + math.sin(a1) * r))


def draw_hook_icon(c, x, y, bait_col):
    pen = Pen(c, aa=True)
    pen.begin()
    pen.move(x, y - 6)
    pen.line(x, y + 4)
    pen.arc(x - 4, y + 4, 4, 0, math.pi)
    pen.stroke('#d9e2ea', 2)
    if bait_col:
        gfxdraw.filled_circle(c, int(x - 4), int(y + 7), 3, _col(bait_col))
        gfxdraw.aacircle(c, int(x - 4), int(y + 7), 3, _col(bait_col))


def draw_line(c):
    b = G.stats.bait if G.stats else None
    draw_line_for(c, Wd.rodTip(), G.mode, G.hook.x, G.hook.d, G.hook.hold, b.dot if b else None)


# ===================================================================================
#  The dark of the trench, radar, depth gauge, bite, cast meter, storm
# ===================================================================================
def draw_darkness(c, peers):
    P = Wd.P
    dark = BIOMES[P.biome].dark
    if dark is None:
        return
    camDepth = G.cam + (G.H * 0.5) / G.PPM
    a = clamp((camDepth - dark) / 260, 0, BIOMES[P.biome].darkmax or 0.95)
    if a <= 0.01:
        return
    w, h = G.W // 2, G.H // 2
    dk = _cache.get('dark')
    if dk is None:
        dk = _cache['dark'] = pygame.Surface((w, h), pygame.SRCALPHA)
    dk.fill((0, 0, 6, int(a * 255)))

    def hole(x, y, r, s):
        if r <= 0:
            return
        sp = hole_sprite(r * 0.5, s)
        R = sp.get_width() / 2
        dk.blit(sp, (x * 0.5 - R, y * 0.5 - R), special_flags=pygame.BLEND_RGBA_SUB)
    L = G.stats.light
    if G.hook.d > 0:
        hole(G.hook.x, sy(G.hook.d), (100 + 70 * L) * G.S, 1)
    for f in G.fish:
        if f.sp.glow or f.mut:
            y = sy(f.d)
            if -200 < y < G.H + 200:
                hole(f.x, y, f.size * 0.9 + 20, 0.75)
    hole(Wd.boatX(), sy(0), 240 * G.S, 1)
    for p in peers:
        hole(p.x, sy(0), 200 * G.S, 0.9)
        if p.hd > 0:
            hole(p.hx * G.W, sy(p.hd), 140 * G.S, 0.8)
    c.blit(pygame.transform.scale(dk, (G.W, G.H)), (0, 0))
    if G.hook.d > 0:
        BD.add_glow(c, G.hook.x, sy(G.hook.d), (36 + 18 * L) * G.S, '#9fdcff', 0.35)


def _sonar_origin():
    if G.hook.d > 0 and G.mode in ('sinking', 'bite', 'reel', 'recall'):
        return G.hook.x, G.hook.d
    return Wd.boatX(), 0.0


def draw_radar(c):
    """Sonar Mk III: Legendary-and-better fish get a target frame on screen, a marker at the edge of the
    screen when they are out of sight, and a dot on the sonar screen, each showing how far away they are."""
    if G.stats.sonar < 3 or G.mode in ('reel', 'card', 'landing') or G.sail:
        return
    W, H, t = G.W, G.H, G.t
    ox, od = _sonar_origin()
    big = [f for f in G.fish if f.tier >= 4 and f.state != 'hooked']
    # --- the sonar screen ---
    R = 58
    cx, cy = 84, H - 140
    RANGE = 220.0
    scr = _cache.get(('sonar', R))
    if scr is None:
        scr = pygame.Surface((2 * R + 8, 2 * R + 8), pygame.SRCALPHA)
        pygame.draw.circle(scr, (4, 30, 34, 205), (R + 4, R + 4), R)
        for k in (1, 2, 3):
            gfxdraw.aacircle(scr, R + 4, R + 4, int(R * k / 3), (90, 255, 200, 70))
        gfxdraw.hline(scr, 4, 2 * R + 4, R + 4, (90, 255, 200, 45))
        gfxdraw.vline(scr, R + 4, 4, 2 * R + 4, (90, 255, 200, 45))
        gfxdraw.aacircle(scr, R + 4, R + 4, R, (120, 255, 210, 160))
        _cache[('sonar', R)] = scr
    c.blit(scr, (cx - R - 4, cy - R - 4))
    sw = (t * 1.6) % TAU
    for k in range(10):
        a = sw - k * 0.06
        gfxdraw.line(c, int(cx), int(cy), int(cx + math.cos(a) * R), int(cy + math.sin(a) * R), (120, 255, 200, max(0, 110 - k * 11)))
    gfxdraw.filled_circle(c, int(cx), int(cy), 3, (255, 217, 138))
    near = None
    for f in big:
        dxm = (f.x - ox) / G.PPM
        ddm = f.d - od
        dist = math.hypot(dxm, ddm)
        if near is None or dist < near[1]:
            near = (f, dist)
        k = min(1.0, dist / RANGE)
        ang = math.atan2(ddm, dxm)
        bx, by = cx + math.cos(ang) * R * k * 0.95, cy + math.sin(ang) * R * k * 0.95
        diff = (sw - ang) % TAU
        lit = max(0.0, 1 - diff / 2.2)
        col = _col(RAR[f.tier].col)
        gfxdraw.filled_circle(c, int(bx), int(by), 4 if f.tier < 5 else 5, col[:3] + (int(140 + 115 * lit),))
        if lit > 0.6:
            gfxdraw.aacircle(c, int(bx), int(by), int(6 + 6 * (1 - lit)), col[:3] + (int(200 * lit),))
    if near:
        f, dist = near
        ui.text(c, f'{RAR[f.tier].name} · {round(dist)} m', cx, cy + R + 16, 'k', 12, _col(RAR[f.tier].col)[:3], 'center', 'baseline',
                outline=2, ocol=(0, 0, 0, 160))
    else:
        ui.text(c, 'SONAR · no big fish', cx, cy + R + 16, 'x', 11, (150, 230, 210), 'center', 'baseline', outline=2, ocol=(0, 0, 0, 140))
    # --- target frames and edge markers ---
    placed = []
    for f in big:
        x, y = f.x, sy(f.d)
        dxm = (f.x - ox) / G.PPM
        ddm = f.d - od
        dist = round(math.hypot(dxm, ddm))
        col = _col(RAR[f.tier].col)
        pulse = 0.55 + 0.45 * math.sin(t * 5 + f.seed)
        star = ''
        name = (MUT[f.mut].name + ' ' if f.mut else '') + f.sp.name
        if 50 < y < H - 40 and -f.size * 0.4 < x < W + f.size * 0.4:
            # a quiet two-line label above the fish; the glowing outline does the rest
            lx = clamp(x, 90, W - 90)
            ly = y - max(22, f.size * 0.3) - 16
            ui.text(c, name, lx, ly, 'k', 13, mix(col[:3], (255, 255, 255), 0.15), 'center', 'baseline', alpha=0.92, outline=2, ocol=(0, 0, 0, 110))
            ui.text(c, f'{RAR[f.tier].name} · {dist} m', lx, ly + 15, 'x', 11, mix(col[:3], (255, 255, 255), 0.45), 'center', 'baseline',
                    alpha=0.7 + 0.15 * pulse, outline=2, ocol=(0, 0, 0, 90))
        else:
            below = y >= H - 40
            pw = 196
            mx = clamp(x, 160 + pw / 2, W - 60 - pw / 2)
            my = H - 118 if below else 76
            for _ in range(6):
                if any(abs(mx - qx) < pw + 6 and abs(my - qy) < 42 for qx, qy in placed):
                    my += -44 if below else 44
            placed.append((mx, my))
            ui.box(c, (mx - pw / 2, my - 19, pw, 38), (7, 20, 34, 170), col[:3] + (int(70 + 50 * pulse),), 14, 1)
            ps = portrait(f.sp, f.mut, 44, 26)
            c.blit(ps, (mx - pw / 2 + 6, my - 13))
            ui.text(c, f'{star}{f.sp.name}', mx - pw / 2 + 56, my - 6, 'k', 12, col[:3], 'left', 'middle')
            ui.text(c, f'{"below" if below else "above"} you · {dist} m', mx - pw / 2 + 56, my + 9, 'x', 11, ui.MIST, 'left', 'middle')
            ax = mx + pw / 2 - 16
            if below:
                gfxdraw.filled_trigon(c, int(ax - 7), int(my - 3 + pulse * 3), int(ax + 7), int(my - 3 + pulse * 3), int(ax), int(my + 7 + pulse * 3), col[:3] + (230,))
            else:
                gfxdraw.filled_trigon(c, int(ax - 7), int(my + 3 - pulse * 3), int(ax + 7), int(my + 3 - pulse * 3), int(ax), int(my - 7 - pulse * 3), col[:3] + (230,))


def draw_dread(c):
    """When the Leviathan is close, the water goes cold and dark, and two lights watch you from below."""
    d = G.dread or 0.0
    if d <= 0.01:
        return
    W, H = G.W, G.H
    v = _cache.get('dreadvig')
    if v is None:
        w2, h2 = W // 4, H // 4
        v = pygame.Surface((w2, h2), pygame.SRCALPHA)
        for yy in range(h2):
            for xx in range(0, w2, 2):
                u = math.hypot((xx - w2 / 2) / (w2 / 2), (yy - h2 * 0.4) / (h2 * 0.6))
                a = int(255 * min(1.0, max(0.0, (u - 0.35) / 0.8)) ** 1.4)
                v.fill((0, 10, 18, a), (xx, yy, 2, 1))
        v = _cache['dreadvig'] = pygame.transform.smoothscale(v, (W, H))
    v.set_alpha(int(200 * d))
    c.blit(v, (0, 0))
    lev = next((f for f in G.fish if f.tier == 6 and f.state != 'hooked'), None)
    if lev is not None and sy(lev.d) > H + 40:
        k = clamp((sy(lev.d) - H) / 600, 0, 1)
        ex = lev.x + lev.dir * 80 * G.S
        ey = H - 40 + k * 30
        blink = 0.6 + 0.4 * math.sin(G.t * 0.9)
        eyes = (BOSSES.get(lev.sp.b) or BOSSES['trench']).eyes
        for dx in (-26, 26):
            BD.add_glow(c, ex + dx * G.S, ey, 26 * G.S, eyes, 0.45 * d * blink * (1 - k * 0.6))


def draw_depth_gauge(c):
    if G.hook.d <= 0 or G.mode not in ('sinking', 'bite', 'reel'):
        return
    x, y0, y1 = G.W - 34, 70, G.H - 70
    if G.mode == 'reel':
        y1 = G.H - 290
    mx = G.stats.depth
    B = Wd.BIO()
    ui.box(c, (x - 6, y0 - 6, 12, y1 - y0 + 12), (7, 26, 46, 153), None, 6)

    def yOf(d):
        return lerp(y0, y1, d / B.depth)
    ym = yOf(mx)
    if y1 - ym > 0:
        BD.overlay_rect(c, (x - 4, int(ym), 8, int(y1 - ym)), (255, 79, 109), 0.35)
    yh = yOf(G.hook.d)
    gfxdraw.filled_circle(c, int(x), int(yh), 6, (255, 217, 138))
    gfxdraw.aacircle(c, int(x), int(yh), 6, (255, 217, 138))
    ui.text(c, f'{round(G.hook.d)} m', x - 12, yh + 4, 'x', 13, ui.FOAM, 'right', 'baseline', outline=2, ocol=(0, 0, 0, 153))
    ui.text(c, f'rod {mx} m', x - 12, ym + 4, 'x', 13, (255, 154, 169), 'right', 'baseline', outline=2, ocol=(0, 0, 0, 153))


def draw_bite(c):
    if G.mode != 'bite' or not G.bite:
        return
    Sc = G.S
    x, y = G.hook.x, sy(G.hook.d) - 34 * Sc
    u = 1 - G.bite.t / G.bite.win
    r = (16 + 26 * u) * Sc
    pen = Pen(c, aa=True)
    pen.begin()
    pen.circle(x, y, r)
    pen.stroke('#ffd98a', 4)
    BD.add_glow(c, x, y, 34 * Sc, '#ff4f6d', 0.5)
    pen.begin()
    pen.circle(x, y, 15 * Sc)
    pen.fill('#ff4f6d')
    ui.text(c, '!', x, y + 8 * Sc, 'd', int(24 * Sc), (255, 255, 255), 'center', 'baseline')


def draw_charge(c):
    if G.mode != 'charge':
        return
    tx, ty = Wd.rodTip()
    Sc = G.S
    x, y, w, h = tx + 40 * Sc, ty - 30 * Sc, 110 * Sc, 14 * Sc
    ui.box(c, (x - 4, y - 4, w + 8, h + 8), (7, 26, 46, 204), None, 8)
    gw = int(max(2, w * G.charge))
    bar = _cache.get(('charge', int(w), int(h)))
    if bar is None:
        bar = pygame.Surface((int(w), int(h)), pygame.SRCALPHA)
        for i in range(int(w)):
            u = i / max(1, w - 1)
            col = mix('#2fd3c0', '#ffd98a', u / 0.7) if u < 0.7 else mix('#ffd98a', '#ff4f6d', (u - 0.7) / 0.3)
            pygame.draw.line(bar, col, (i, 0), (i, h))
        mask = pygame.Surface(bar.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, int(w), int(h)), border_radius=5)
        bar.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        _cache[('charge', int(w), int(h))] = bar
    c.blit(bar, (x, y), (0, 0, gw, int(h)))
    ui.text(c, 'Release to cast', x, y - 10, 'x', 12, ui.FOAM, 'left', 'baseline')


def draw_storm(c):
    if G.storm <= 0.01:
        return
    ui.overlay(c, (4, 8, 20), 0.55 * G.storm)
    if G.bolt > 0.05:
        top = max(0, sy(0))
        x, y = G.boltX * G.W, 0.0
        pts = [(x, y)]
        while y < top:
            x += rand(-30, 30)
            y += rand(20, 50)
            pts.append((x, min(y, top)))
        if len(pts) > 1:
            pen = Pen(c, aa=True)
            pen.begin()
            for px, py in pts:
                pen.line(px, py)
            pen.stroke((207, 232, 255, int(90 * G.bolt)), 9, 'round')
            pen.stroke((230, 245, 255, int(255 * G.bolt)), 3, 'round')


# ===================================================================================
#  Boats: yours and other anglers'
# ===================================================================================
def boat_reflection(x, boat_id, S):
    b = BOAT.get(boat_id) or BOAT['dinghy']
    hl = 95 + b.tier * 16
    return x + 6 * S, (2 * hl + 12) * S * 0.92, b.col


def draw_peer_boats(c, peers):
    Sc = G.S
    for p in peers:
        x, y = p.x, sy(0) - 8 * Sc
        if x < -200 or x > G.W + 200:
            p.tip = None
            continue
        rx, rw, rc = boat_reflection(x, p.boat, Sc)
        BD.draw_reflection(c, rx, rw, rc)
        lk = D(fur=p.fur, boat=p.boat, rod=p.rod, ench=p.ench, biome=Wd.P.biome, mode=p.mode, ten=p.ten, t=G.t + p.seed, S=Sc)
        draw_boat_cat(Pen(c, aa=True), x, y, lk)
        tip = (x + 112 * Sc, sy(0) - 126 * Sc + (22 * Sc * (0.4 + p.ten) if p.mode == 'reel' else 9 * Sc if p.mode == 'bite' else 0) + math.sin((G.t + p.seed) * 1.6) * 2.5 * Sc)
        p.tip = tip


def draw_peer_lines(c, peers):
    for p in peers:
        if p.tip is None:
            continue
        draw_line_for(c, p.tip, p.mode, p.hx * G.W, p.hd, False, None)


def draw_name_tags(c, peers):
    Sc = G.S
    for p in peers:
        if p.x < -200 or p.x > G.W + 200:
            continue
        y = sy(0) - 150 * Sc
        tag = f'{p.name}  Lv {p.lvl}'
        w = ui.text_w(tag, 'k', 13) + 18
        ui.box(c, (p.x + 20 * Sc - w / 2, y - 12, w, 24), (7, 26, 46, 190), (234, 246, 255, 60), 12)
        ui.text(c, tag, p.x + 20 * Sc, y, 'k', 13, ui.FOAM, 'center', 'middle')
        draw_bubble(c, p.emote, p.x + 30 * Sc, y - 16)
    if G.emote:
        draw_bubble(c, G.emote, Wd.boatX() + 30 * Sc, sy(0) - 150 * Sc)


def draw_bubble(c, em, x, y):
    if not em:
        return
    txt, col, t0 = em
    age = G.t - t0
    if age > 3:
        return
    a = min(1, age * 5, (3 - age) * 2)
    pop = 1 + 0.25 * max(0, 1 - age * 6)
    size = int(18 * pop)
    w = ui.text_w(txt, 'd', size) + 24
    h = size + 14
    yy = y - h - age * 6
    ui.box(c, (x - w / 2, yy, w, h), (255, 255, 255, 235), None, 12, alpha=a)
    gfxdraw.filled_trigon(c, int(x - 7), int(yy + h - 1), int(x + 7), int(yy + h - 1), int(x), int(yy + h + 8), (255, 255, 255, int(235 * a)))
    ui.text(c, txt, x, yy + h / 2, 'd', size, mix(col, '#000000', 0.45), 'center', 'middle', alpha=a)


_petpos = {}


def _pet_x(key, bx, boat_id, dt):
    hl = 95 + (BOAT.get(boat_id) or BOAT['dinghy']).tier * 16
    S = G.S
    want = bx - (hl + 70) * S
    if want < 46 * S:
        want = bx + (hl + 74) * S
    cur = _petpos.get(key)
    cur = want if cur is None or abs(cur - want) > G.W else cur + (want - cur) * min(1.0, dt * 2.2)
    _petpos[key] = cur
    return cur


def draw_pet_boats(c, peers):
    """Your pets' little boat (and your friends' ones), with the kitten fishing off the side."""
    P = Wd.P
    dt = G.dt or 0.016
    Sc = G.S * 0.95
    for p in peers:
        pl = [x for x in (p.pets or []) if x in PT.PAINT]
        if pl and -200 < p.x < G.W + 200:
            px = _pet_x(('peer', p.name), p.x, p.boat, dt)
            out = PT.draw_pet_boat(c, px, sy(0) - 6 * G.S, Sc, G.t + p.seed, pl)
            if out.tip:
                _kitten_line(c, out.tip, None)
    if not P.petOn:
        return
    bx = Wd.boatX()
    if G.sail:
        st = G.sail.t
        bx = bx + (st / 1.2) ** 2 * G.W if st < 1.2 else bx - (1 - min(1, (st - 1.2) / 1.2)) * G.W * 0.6
    px = _pet_x('me', bx, P.boat, dt)
    lv = {pid: Wd.petLevel(pid) for pid in P.petOn}
    out = PT.draw_pet_boat(c, px, sy(0) - 6 * G.S, Sc, G.t, P.petOn, lv, G.petFx)
    if out.tip:
        _kitten_line(c, out.tip, G.petFx)


def _kitten_line(c, tip, fx):
    """The kitten's little line and bobber, and the fish she lands."""
    S = G.S
    wx = tip[0] + 26 * S
    wy = sy(0) + 3
    dip = 0.0
    if fx is not None and fx.t < 1.0:
        dip = 5 * S * abs(math.sin(fx.t * 14))
    pen = Pen(c, aa=True)
    pen.begin()
    pen.move(*tip)
    pen.quad(tip[0] + 18 * S, tip[1] + 10 * S, wx, wy + dip)
    pen.stroke((230, 240, 250, 150), 1)
    gfxdraw.filled_circle(c, int(wx), int(wy + dip), max(2, int(3 * S)), (255, 79, 109))
    gfxdraw.filled_circle(c, int(wx), int(wy + dip - 2 * S), max(1, int(2 * S)), (255, 255, 255))
    if fx is not None and 1.0 <= fx.t < 2.2:
        u = (fx.t - 1.0) / 1.2
        fx_ = wx + (tip[0] - 10 * S - wx) * u
        fy_ = wy - math.sin(u * math.pi) * 60 * S + (tip[1] + 18 * S - wy) * u
        L = 34 * S
        blit_fish(c, fx.sp, None, False, L, L, frame_of(fx.sp, G.t * 3), fx_, fy_, True, math.sin(G.t * 20) * 0.4, 1.0, nframes(fx.sp))
        if u < 0.12:
            BD.add_glow(c, wx, wy, 18 * S, RAR[fx.tier].col, 0.5)


def draw_my_boat(c):
    P = Wd.P
    Sc = G.S
    bx = Wd.boatX()
    if G.sail:
        t = G.sail.t
        bx = bx + (t / 1.2) ** 2 * G.W if t < 1.2 else bx - (1 - min(1, (t - 1.2) / 1.2)) * G.W * 0.6
    rx, rw, rc = boat_reflection(bx, P.boat, Sc)
    BD.draw_reflection(c, rx, rw, rc)
    st = G.stats
    hop = abs(math.sin(G.happy * math.pi * 2)) * 10 * G.happy
    lk = D(fur=P.fur, boat=P.boat, rod=P.rod, ench=st.ench if st else None, biome=P.biome, mode=G.mode,
           ten=G.reel.ten if G.reel else 0, t=G.t, S=Sc, hop=hop)
    draw_boat_cat(Pen(c, aa=True), bx, sy(0) - 8 * Sc, lk)


# ===================================================================================
#  The reel panel: catch bar, fish tricks, difficulty and your rod ability
# ===================================================================================
def _grad_bar(key, w, h, c0, c1, radius):
    s = _cache.get(key)
    if s is None:
        w, h = max(2, int(w)), max(2, int(h))
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(w):
            pygame.draw.line(s, mix(c0, c1, i / max(1, w - 1)), (i, 0), (i, h))
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
        s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        _cache[key] = s
    return s


def _track(w, h):
    key = ('track2', int(w), int(h))
    tr = _cache.get(key)
    if tr is None:
        w, h = int(w), int(h)
        tr = pygame.Surface((w, h), pygame.SRCALPHA)
        for i in range(h):
            u = i / max(1, h - 1)
            pygame.draw.line(tr, mix('#14507e', '#0a2744', u ** 0.8), (0, i), (w, i))
        pygame.draw.line(tr, (120, 200, 255), (8, 2), (w - 8, 2))
        for k in range(1, 10):
            x = int(w * k / 10)
            pygame.draw.line(tr, (255, 255, 255, 26), (x, h - 7), (x, h - 2))
        wave = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in range(0, w, 3):
            y = h * 0.62 + math.sin(x * 0.045) * 3
            pygame.draw.circle(wave, (120, 200, 255, 22), (x, int(y)), 2)
        tr.blit(wave, (0, 0))
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=14)
        tr.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        _cache[key] = tr
    return tr


def _chip(c, x, y, label, col, active, warn, passive):
    w = ui.text_w(label, 'k', 11) + 18
    h = 20
    cc = hexc(col)
    if active:
        ui.box(c, (x, y, w, h), cc + (235,), (255, 255, 255, 200), 10, 1)
        ui.text(c, label, x + w / 2, y + h / 2, 'k', 11, (20, 20, 30), 'center', 'middle')
    elif warn:
        pulse = 0.5 + 0.5 * math.sin(G.t * 22)
        ui.box(c, (x, y, w, h), cc + (int(60 + 120 * pulse),), cc + (255,), 10, 2)
        ui.text(c, label, x + w / 2, y + h / 2, 'k', 11, (255, 255, 255), 'center', 'middle')
    else:
        ui.box(c, (x, y, w, h), cc + (34 if passive else 22,), cc + (170 if passive else 110,), 10, 1)
        ui.text(c, label, x + w / 2, y + h / 2, 'k', 11, mix(cc, '#ffffff', 0.35), 'center', 'middle')
    return w


def _key_label(action):
    from . import screens
    return screens.K(action)


def draw_reel(c):
    R = G.reel
    if not R or G.mode != 'reel':
        return
    P = Wd.P
    W, H, t = G.W, G.H, G.t
    w = min(W - 80, 700)
    x = (W - w) / 2
    ph = 214
    top = H - 52 - ph
    tier = R.f.tier
    col = RAR[tier].col
    edge = '#00ffd5' if R.boss else col
    gl = _cache.get(('reelglow', int(w), edge))
    if gl is None:
        gl = pygame.Surface((int(w) + 96, ph + 60), pygame.SRCALPHA)
        pygame.draw.rect(gl, hexc(edge) + (120,), (48, 30, int(w), ph), border_radius=20)
        gl = _blur(gl, 14)
        _cache[('reelglow', int(w), edge)] = gl
    gl.set_alpha(int(150 + 60 * math.sin(t * 3)) if tier >= 4 else 110)
    c.blit(gl, (x - 48, top - 30))
    gl.set_alpha(255)
    ui.box(c, (x - 18, top, w + 36, ph), (7, 24, 42, 238), rgba(edge, 0.9), 18, 2)

    # --- header: name, difficulty ---
    named = G.stats.sonar >= 2 or R.sp.id in P.dex or R.boss
    title = ((MUT[R.f.mut].name + ' ' if R.f.mut else '') + R.sp.name) if named else f'??? {RAR[tier].name}'
    ui.text(c, title, x, top + 30, 'd', 21, col, 'left', 'baseline', outline=2, ocol=(0, 0, 0, 120))
    tx = x + ui.text_w(title, 'd', 21) + 12
    if R.boss:
        ui.text(c, f'STAGE {R.stage} / {R.stages}', tx, top + 28, 'k', 12, '#00ffd5', 'left', 'baseline')
    elif R.perfect and R.t > R.grace:
        ui.text(c, 'PERFECT', tx, top + 28, 'k', 12, ui.SAND, 'left', 'baseline')
    lab = REEL[tier].label
    px = x + w - 7 * 13 + 4
    for i in range(7):
        on = i <= tier
        cc = hexc(RAR[min(i, tier)].col) if on else (40, 70, 100)
        gfxdraw.filled_circle(c, int(px + i * 13), int(top + 23), 5, cc)
        gfxdraw.aacircle(c, int(px + i * 13), int(top + 23), 5, cc)
    ui.text(c, lab.upper(), px - 12, top + 28, 'k', 12, col, 'right', 'baseline')
    ui.text(c, 'DIFFICULTY', px - 16 - ui.text_w(lab.upper(), 'k', 12), top + 28, 'x', 11, ui.MIST, 'right', 'baseline')

    # --- the fish's tricks ---
    cy = top + 42
    cx = x
    if R.gims:
        for g in R.gims:
            gm = GIMMICKS[g]
            active = bool(R.eff.get(g)) or (g == 'thrash' and R.prog > 0.6)
            warn = bool(R.warn and R.warn[0] == g)
            cx += _chip(c, cx, cy, gm.name, gm.col, active, warn, gm.kind == 'passive') + 6
    else:
        ui.text(c, 'No tricks. Just a fish.', cx, cy + 10, 'x', 12, ui.MIST, 'left', 'middle')
    if G.cheer > 0:
        ui.text(c, 'CREW CHEERING +25%', x + w, cy + 10, 'k', 12, '#00ffd5', 'right', 'middle')

    # --- the track ---
    th = 50
    ty = top + 70
    old = c.get_clip()
    c.blit(_track(w, th), (x, ty))
    eff, abT = R.eff, R.abT
    frozen = abT.get('freeze', 0) > 0
    a = _eff_alpha(R, 'warp')
    if a > 0:
        BD.overlay_rect(c, (int(x), int(ty), int(w), th), (150, 60, 220), 0.32 * a)
        ui.text(c, 'CONTROLS REVERSED', x + w / 2, ty + 9, 'k', 10, (230, 200, 255, int(255 * a)), 'center', 'middle')
    inside = abs(R.fx - (R.pos + R.zw / 2)) < R.zw / 2
    mirror = abT.get('mirror', 0) > 0
    if mirror and not inside:
        inside = abs(R.fx - (1 - R.pos - R.zw / 2)) < R.zw / 2
    zx, zw = x + R.pos * w, R.zw * w
    stun = bool(eff.get('stun'))
    if inside:
        BD.add_glow(c, zx + zw / 2, ty + th / 2, max(zw * 0.7, 30), '#5affb4', 0.35)
    zfill = (130, 255, 200, 95) if inside else (255, 255, 255, 60)
    zedge = '#ff4f6d' if stun else '#c26bff' if a > 0 else '#8dffc8' if inside else '#ffffff'
    if abT.get('shield', 0) > 0:
        zedge = '#2fd0a0'
    elif abT.get('anchor', 0) > 0:
        zedge = '#c8d8e8'
    elif abT.get('magnet', 0) > 0:
        zedge = '#ff6a8a'
    elif abT.get('gold', 0) > 0:
        zfill, zedge = (255, 210, 61, 110), '#ffe27a'
    if abT.get('frenzy', 0) > 0 or abT.get('bloodmoon', 0) > 0:
        BD.overlay_rect(c, (int(x), int(ty), int(w), th), (255, 50, 50), 0.12 + 0.05 * math.sin(t * 12))
    if mirror:
        mx_ = x + (1 - R.pos - R.zw) * w
        ui.box(c, (mx_, ty + 3, zw, th - 6), (232, 244, 255, 70), '#e8f4ff', 11, 2)
    ui.box(c, (zx, ty + 3, zw, th - 6), zfill, zedge, 11, 3 if (stun or abT.get('shield', 0) > 0) else 2)
    if abT.get('riptide', 0) > 0:
        for k in range(4):
            u = (t * 1.6 + k / 4) % 1.0
            gfxdraw.aacircle(c, int(zx + zw / 2), int(ty + th / 2), int(8 + u * zw * 0.5), (90, 184, 232, int(150 * (1 - u))))
    if R.barb or R.chill:
        tag = ' · '.join(([('BARBED')] if R.barb else []) + (['CHILLED'] if R.chill else []))
        ui.text(c, tag, x + w - 8, ty + th - 9, 'k', 10, '#cfe8ff', 'right', 'middle')
    if stun:
        ui.text(c, 'LOCKED', zx + zw / 2, ty + th - 10, 'k', 10, '#ff8fa0', 'center', 'middle')
    c.set_clip(pygame.Rect(int(x), int(ty), int(w), th))
    if abT.get('net', 0) > 0:
        net = Pen(c, aa=True)
        net.begin()
        step = 10
        for k in range(int(zw / step) + 2):
            nx_ = zx + k * step
            net.move(nx_, ty + 3)
            net.line(nx_ - 12, ty + th - 3)
            net.move(nx_ - 12, ty + 3)
            net.line(nx_, ty + th - 3)
        net.stroke((157, 255, 176, 110), 1)
    if abT.get('slowmo', 0) > 0:
        BD.overlay_rect(c, (int(x), int(ty), int(w), th), (127, 252, 255), 0.13)
        for k in range(3):
            rr = th * (0.3 + 0.25 * k) + (t * 6) % 8
            gfxdraw.aacircle(c, int(x + R.fx * w), int(ty + th / 2), int(rr), (127, 252, 255, 90 - 25 * k))
    if abT.get('shield', 0) > 0:
        for k in range(0, int(zw), 14):
            hx_ = zx + k + 7
            gfxdraw.aacircle(c, int(hx_), int(ty + th / 2 + math.sin(t * 6 + k) * 6), 5, (47, 208, 160, 140))
    if abT.get('magnet', 0) > 0:
        mx_ = zx + zw / 2
        fxm = x + R.fx * w
        for k in range(3):
            off = (k + 1) * 6
            pen = Pen(c, aa=True)
            pen.begin()
            pen.move(mx_, ty + th / 2 - off)
            pen.quad((mx_ + fxm) / 2, ty + th / 2 - off * 2.2, fxm, ty + th / 2 - 2)
            pen.stroke((255, 106, 138, 120 - 30 * k), 1)
    if abT.get('gold', 0) > 0:
        for k in range(7):
            gx = zx + (k * 37 + t * 40) % max(10, zw)
            gy = ty + 6 + (k * 13 + t * 25) % (th - 12)
            gfxdraw.filled_circle(c, int(gx), int(gy), 2, (255, 240, 160, 220))
    if abT.get('stars', 0) > 0:
        for k in range(8):
            u = ((t * 1.3 + k * 0.137) % 1.0)
            sx0 = x + ((k * 97) % 100) / 100 * w + u * 40
            sy0 = ty - 6 + u * (th + 12)
            pen = Pen(c, aa=True)
            pen.begin()
            pen.move(sx0 - 10, sy0 - 10)
            pen.line(sx0, sy0)
            pen.stroke((224, 200, 255, int(200 * (1 - u))), 1.6)
            gfxdraw.filled_circle(c, int(sx0), int(sy0), 2, (255, 255, 255, int(255 * (1 - u * 0.5))))
    if abT.get('quick', 0) > 0:
        for k in range(6):
            lx = zx + ((t * 260 + k * 47) % max(10, zw))
            ly = ty + 10 + (k * 7) % (th - 18)
            gfxdraw.hline(c, int(lx - 14), int(lx), int(ly), (124, 240, 255, 200))
    if abT.get('gravity', 0) > 0:
        gx = zx + zw / 2
        for k in range(3):
            ph_ = (t * 1.6 + k / 3) % 1.0
            rr = (1 - ph_) * th * 1.1
            gfxdraw.aaellipse(c, int(gx), int(ty + th / 2), max(2, int(rr * 1.4)), max(2, int(rr * 0.6)), (92, 207, 255, int(220 * ph_)))
    if abT.get('anchor', 0) > 0:
        ax_, ay_ = zx + zw / 2, ty + th / 2
        pen = Pen(c, aa=True)
        pen.begin()
        pen.move(ax_, ay_ - 13)
        pen.line(ax_, ay_ + 11)
        pen.stroke((200, 216, 232, 200), 2.2, 'round')
        pen.begin()
        pen.move(ax_ - 10, ay_ + 2)
        pen.quad(ax_ - 8, ay_ + 13, ax_, ay_ + 12)
        pen.quad(ax_ + 8, ay_ + 13, ax_ + 10, ay_ + 2)
        pen.stroke((200, 216, 232, 200), 2.2, 'round')
        gfxdraw.aacircle(c, int(ax_), int(ay_ - 15), 3, (200, 216, 232, 220))
        for k in range(3):
            gfxdraw.hline(c, int(zx + 4), int(zx + zw - 4), int(ty + 6 + k * 3), (200, 216, 232, 50))
    if abT.get('whirl', 0) > 0:
        wx_, wy_ = zx + zw / 2, ty + th / 2
        pen = Pen(c, aa=True)
        for k in range(3):
            pen.begin()
            a0 = t * 5 + k * TAU / 3
            for i in range(14):
                u = i / 13
                r_ = 6 + u * th * 0.7
                px_, py_ = wx_ + math.cos(a0 + u * 4) * r_ * 1.6, wy_ + math.sin(a0 + u * 4) * r_ * 0.5
                if i:
                    pen.line(px_, py_)
                else:
                    pen.move(px_, py_)
            pen.stroke((106, 216, 255, 150), 1.6, 'round')
    if abT.get('echo', 0) > 0 or R.pingT > 0:
        tx_ = x + R.ft * w
        if abT.get('echo', 0) > 0:
            for k in range(0, th, 6):
                gfxdraw.vline(c, int(tx_), int(ty + k), int(ty + min(th, k + 3)), (127, 255, 212, 200))
            gfxdraw.aacircle(c, int(tx_), int(ty + th / 2), 9, (127, 255, 212, 220))
            gfxdraw.aacircle(c, int(tx_), int(ty + th / 2), 4, (127, 255, 212, 220))
        if R.pingT > 0:
            u = 1 - R.pingT
            gfxdraw.aacircle(c, int(x + R.fx * w), int(ty + th / 2), int(10 + u * 90), (127, 255, 212, int(220 * (1 - u))))
    if abT.get('inferno', 0) > 0:
        for k in range(0, int(w), 12):
            fh = th * 0.42 * (0.55 + 0.45 * math.sin(t * 13 + k * 0.7))
            gfxdraw.filled_trigon(c, int(x + k), int(ty + th), int(x + k + 12), int(ty + th), int(x + k + 6), int(ty + th - fh), (255, 122, 42, 150))
            gfxdraw.filled_trigon(c, int(x + k + 3), int(ty + th), int(x + k + 9), int(ty + th), int(x + k + 6), int(ty + th - fh * 0.55), (255, 224, 138, 180))
    if eff.get('burn'):
        BD.overlay_rect(c, (int(x), int(ty), int(w), th), (255, 106, 26), 0.12 + 0.06 * math.sin(t * 9))
    # fish (and its decoys)
    sp = R.sp
    L = 64 if R.boss else 46
    if eff.get('puff'):
        L *= 1.45
    fa = 1 - R.blink * 0.7
    if eff.get('camo'):
        fa *= 0.1 + 0.05 * math.sin(t * 9)
    fr = 3 if frozen else frame_of(sp, t * 2.5)
    for i, dc in enumerate(R.decoys):
        da = 0.86 + 0.1 * math.sin(t * 7 + i * 2)
        blit_fish(c, sp, None if R.boss else R.f.mut, False, L, L, (fr + 3 + i * 5) % nframes(sp), x + dc.x * w, ty + th / 2,
                  dc.ft < dc.x, 0.0, da, nframes(sp))
    fy = ty + th / 2 + (math.sin(t * 30) * 2 if eff.get('zap') else 0)
    blit_fish(c, sp, None if R.boss else R.f.mut, False, L, L, fr, x + R.fx * w, fy, R.ft < R.fx, 0.0, fa, nframes(sp))
    fxp = x + R.fx * w
    a = _eff_alpha(R, 'ink')
    if a > 0:
        b = soft_blob(w * 0.3, th * 1.5, '#1a0f33', 235)
        b.set_alpha(int(255 * a))
        c.blit(b, (fxp - b.get_width() / 2, ty + th / 2 - b.get_height() / 2))
        b.set_alpha(255)
    if frozen:
        BD.overlay_rect(c, (int(x), int(ty), int(w), th), (190, 238, 255), 0.16)
        ui.box(c, (fxp - L * 0.7, ty + 5, L * 1.4, th - 10), (200, 240, 255, 90), (235, 250, 255, 230), 8, 2)
        for k in range(5):
            ang = t * 0.8 + k * TAU / 5
            sx_, sy_ = fxp + math.cos(ang) * L * 0.85, ty + th / 2 + math.sin(ang) * th * 0.42
            gfxdraw.hline(c, int(sx_ - 3), int(sx_ + 3), int(sy_), (255, 255, 255, 220))
            gfxdraw.vline(c, int(sx_), int(sy_ - 3), int(sy_ + 3), (255, 255, 255, 220))
    if R.slashT > 0:
        u = R.slashT / 0.55
        pen = Pen(c, aa=True)
        pen.begin()
        pen.move(fxp - 30, ty + th - 4)
        pen.line(fxp + 30, ty + 4)
        pen.stroke((255, 111, 168, int(170 * u)), 8 * u + 2, 'round')
        pen.stroke((255, 255, 255, int(255 * u)), 3 * u + 1, 'round')
    if R.zapT > 0:
        u = R.zapT / 0.6
        bolt = Pen(c, aa=True)
        bolt.begin()
        bx_, by_ = fxp + 6, ty - 4
        bolt.move(bx_, by_)
        for k in range(1, 6):
            bolt.line(fxp + (8 if k % 2 else -8) * (1 - k / 6), ty + th * k / 5)
        bolt.stroke((98, 243, 255, int(140 * u)), 7, 'round')
        bolt.stroke((255, 255, 255, int(255 * u)), 2.5, 'round')
    if R.harpT > 0:
        u = R.harpT / 0.45
        hp = Pen(c, aa=True)
        hp.begin()
        hp.move(x, ty + th / 2)
        hp.line(fxp - 6, ty + th / 2)
        hp.stroke((200, 210, 220, int(220 * u)), 2.5)
        hp.begin()
        hp.move(fxp + 4, ty + th / 2)
        hp.line(fxp - 8, ty + th / 2 - 6)
        hp.line(fxp - 8, ty + th / 2 + 6)
        hp.close()
        hp.fill((230, 236, 245, int(255 * u)))
    if R.pawT > 0:
        u = R.pawT / 0.7
        px_, py_ = zx + zw / 2, ty + th / 2
        sc_ = 1 + (1 - u) * 0.6
        col_ = (255, 217, 160, int(230 * u))
        gfxdraw.filled_ellipse(c, int(px_), int(py_ + 4 * sc_), int(8 * sc_), int(6 * sc_), col_)
        for tx_, ty_ in ((-9, -4), (-3.5, -10), (3.5, -10), (9, -4)):
            gfxdraw.filled_circle(c, int(px_ + tx_ * sc_), int(py_ + ty_ * sc_), int(3.4 * sc_), col_)
    if R.flashT > 0:
        BD.overlay_rect(c, (int(x), int(ty), int(w), th), (255, 255, 255), clamp(R.flashT / (GIMMICKS['flash'].dur or 0.8), 0, 1) * 0.95)
    c.set_clip(old)
    if R.warn:
        g = R.warn[0]
        gm = GIMMICKS[g]
        pulse = 0.5 + 0.5 * math.sin(t * 24)
        lab = '! ' + gm.name.upper()
        bw = ui.text_w(lab, 'k', 12) + 18
        bx = clamp(fxp - bw / 2, x - 10, x + w - bw + 10)
        ui.box(c, (bx, ty - 26, bw, 22), hexc(gm.col) + (int(200 + 55 * pulse),), (255, 255, 255, 230), 11, 2)
        gfxdraw.filled_trigon(c, int(clamp(fxp, bx + 8, bx + bw - 8) - 6), int(ty - 5), int(clamp(fxp, bx + 8, bx + bw - 8) + 6), int(ty - 5),
                              int(clamp(fxp, bx + 8, bx + bw - 8)), int(ty + 3), hexc(gm.col) + (230,))
        ui.text(c, lab, bx + bw / 2, ty - 15, 'k', 12, (20, 20, 30), 'center', 'middle')

    # --- catch progress and line tension ---
    py = ty + th + 10
    ui.box(c, (x, py, w, 12), (255, 255, 255, 30), None, 6)
    pb = _grad_bar(('prog2', int(w)), w, 12, '#2fd3c0', '#ffd98a', 6)
    pw = int(max(12, w * clamp(R.prog, 0, 1)))
    c.blit(pb, (x, py), (0, 0, pw, 12))
    if eff.get('regen'):
        BD.overlay_rect(c, (int(x), int(py), pw, 12), (255, 143, 207), 0.35 + 0.2 * math.sin(t * 14))
    if abT.get('gold', 0) > 0:
        BD.overlay_rect(c, (int(x), int(py), pw, 12), (255, 210, 61), 0.45)
    if abT.get('shield', 0) > 0:
        ui.box(c, (x - 2, py - 2, w + 4, 16), None, '#2fd0a0', 8, 2)
    if abT.get('phoenix', 0) > 0:
        for k in range(0, int(w), 16):
            fh = 9 * (0.6 + 0.4 * math.sin(t * 12 + k))
            gfxdraw.filled_trigon(c, int(x + k), int(py), int(x + k + 10), int(py), int(x + k + 5), int(py - fh), (255, 140, 40, 170))
    if 'rebirth' in R.gims and not R.reborn:
        gfxdraw.filled_circle(c, int(x + w - 2), int(py + 6), 8, hexc('#ffb03a'))
        gfxdraw.aacircle(c, int(x + w - 2), int(py + 6), 8, (255, 255, 255))
        ui.text(c, '2', x + w - 2, py + 6, 'k', 10, (60, 30, 0), 'center', 'middle')
    ty2 = py + 20
    tcol = ui.DANGER if R.ten > 0.7 else ui.MIST
    ui.text(c, f'Catch {round(clamp(R.prog, 0, 1) * 100)}%', x, ty2 + 10, 'k', 13, ui.FOAM, 'left', 'baseline')
    tw = w * 0.42
    ui.text(c, 'Line tension', x + w - tw - 10, ty2 + 10, 'x', 12, tcol, 'right', 'baseline')
    ui.box(c, (x + w - tw, ty2, tw, 12), (255, 255, 255, 30), None, 6)
    tcolb = '#ff4f6d' if R.ten > 0.7 else '#ffb020' if R.ten > 0.4 else '#62d672'
    if abT.get('inferno', 0) > 0:
        tcolb = '#ff7a2a'
    ui.box(c, (x + w - tw, ty2, max(10, tw * clamp(R.ten, 0, 1)), 12), tcolb, None, 6)
    if R.ten > 0.75:
        BD.add_glow(c, x + w - tw + tw * clamp(R.ten, 0, 1), ty2 + 6, 22, '#ff4f6d', 0.4 + 0.3 * math.sin(t * 16))

    # --- your rod ability ---
    ab = R.ab
    if ab:
        A = ABILITIES[ab]
        ay = ty2 + 26
        ready = R.charge >= 1
        act = abT.get(ab if ab not in ('tidal',) else 'freeze', 0)
        if ready:
            BD.add_glow(c, x + 13, ay + 12, 26, A.col, 0.5 + 0.3 * math.sin(t * 8))
        draw_ability_icon(c, ab, x + 13, ay + 12, 13, A.col, '#ffffff' if ready else None)
        ui.text(c, A.name, x + 34, ay + 12, 'k', 14, ui.FOAM, 'left', 'middle')
        bx0 = x + 34 + ui.text_w(A.name, 'k', 14) + 12
        bw = max(60, w * 0.36 - (bx0 - x) + 120)
        ui.box(c, (bx0, ay + 7, bw, 10), (255, 255, 255, 30), None, 5)
        if act > 0 and A.dur:
            fillw = bw * clamp(act / A.dur, 0, 1)
            ui.box(c, (bx0, ay + 7, max(10, fillw), 10), A.col, None, 5)
            msg = f'{A.name} active  {act:.1f}s'
            ui.text(c, msg, x + w, ay + 12, 'k', 13, A.col, 'right', 'middle')
        else:
            ui.box(c, (bx0, ay + 7, max(10, bw * R.charge), 10), A.col if ready else mix(A.col, '#0a2440', 0.35), None, 5)
            if ready:
                pulse = 0.65 + 0.35 * math.sin(t * 9)
                kl = _key_label('ability')
                ui.text(c, 'READY!  Right-click' if kl == '-' else f'READY!  Press {kl} or right-click', x + w, ay + 12, 'k', 13,
                        mix('#ffd98a', '#ffffff', pulse * 0.5), 'right', 'middle', outline=2, ocol=(0, 0, 0, 120))
            else:
                ui.text(c, 'Charges while the fish is in your bar', x + w, ay + 12, 'x', 12, ui.MIST, 'right', 'middle')

    # --- big moment labels above the panel ---
    if R.labelT > 0 and R.label:
        age = max(0.0, 1.2 - R.labelT)
        pop = 1 + 0.4 * max(0, 1 - age * 7)
        al = clamp(R.labelT / 0.3, 0, 1)
        ui.text(c, R.label, W / 2, top - 20, 'd', int(30 * pop), R.labelCol, 'center', 'baseline', alpha=al, outline=3, ocol=(0, 0, 0, 170))
    elif R.t < R.grace:
        msg = "IT'S BACK!" if (R.stage > 1 or R.reborn) else f'HOOKED!  Hold {_key_label("act")} to push right'
        if R.boss and R.stage == 1 and not R.reborn:
            msg = (BOSSES.get(R.sp.b) or BOSSES['trench']).short + '  Hold on tight'
        ui.text(c, msg, W / 2, top - 20, 'd', 24, ui.SAND, 'center', 'baseline', outline=3, ocol=(0, 0, 0, 150))


# ===================================================================================
#  The catch card and the big-moment overlays
# ===================================================================================
def draw_card(c):
    K = G.card
    if not K or G.mode != 'card':
        return
    W, H = G.W, G.H
    u = min(1, K.t / 0.35)
    e = 1 - (1 - u) ** 3
    w, h = min(W - 32, 440), 336
    x, y = (W - w) / 2, H * 0.5 - h / 2 + (1 - e) * 40
    col = RAR[K.tier].col
    mut = K.rec.mut
    ui.overlay(c, (2, 8, 16), 0.45 * e)
    gk = ('cardglow', K.tier)
    gl = _cache.get(gk)
    if gl is None:
        gl = pygame.Surface((w + 80, h + 80), pygame.SRCALPHA)
        pygame.draw.rect(gl, hexc(col) + (200,), (40, 40, w, h), border_radius=22)
        gl = _blur(gl, 16)
        _cache[gk] = gl
    gl.set_alpha(int(255 * e))
    c.blit(gl, (x - 40, y - 40))
    ui.box(c, (x, y, w, h), '#0e2a46', col, 22, 3, alpha=e)
    if K.tier >= 3:
        cx, cy = x + w / 2, y + 100
        rc = _col(col)[:3] + (int(33 * e),)
        for kk in range(12):
            a = G.t * 0.5 + TAU / 12 * (kk + 1)
            ca, sa = math.cos(a), math.sin(a)
            pts = [(cx, cy), (cx + ca * 160 + sa * 18, cy + sa * 160 - ca * 18), (cx + ca * 160 - sa * 18, cy + sa * 160 + ca * 18)]
            gfxdraw.filled_polygon(c, [(int(px), int(py)) for px, py in pts], rc)
    old = c.get_clip()
    c.set_clip(pygame.Rect(int(x) + 3, int(y) + 3, int(w) - 6, h - 6))
    sp = K.sp
    L = w * 0.95 if sp.shape == 'leviathan' else min(w * 0.6, 60 + sp.len * 1.1)
    fx = x + w / 2 - (w * 0.12 if sp.shape == 'leviathan' else 0)
    blit_fish(c, sp, mut, False, L, L, frame_of(sp, G.t * 1.2), fx, y + 100 + math.sin(G.t * 2) * 4, False, 0.0, e, nframes(sp))
    c.set_clip(old)
    ui.text(c, sp.name, x + w / 2, y + 186, 'd', 26, (255, 255, 255), 'center', 'baseline', alpha=e)
    tags = [RAR[K.tier].name.upper()]
    if mut:
        tags.append(f'{MUT[mut].name.upper()} x{MUT[mut].mult}')
    if K.size:
        tags.append(K.size.upper())
    if K.rec.perfect:
        tags.append('PERFECT x1.2')
    ui.text(c, '  ·  '.join(tags), x + w / 2, y + 208, 'k', 13, col, 'center', 'baseline', alpha=e)
    ui.text(c, f'{fmtW(K.rec.kg)}   ·   worth {fmt(K.rec.val)} coins', x + w / 2, y + 236, 'x', 15, ui.MIST, 'center', 'baseline', alpha=e)
    if K.extra:
        ui.text(c, K.extra.strip(), x + w / 2, y + 258, 'x', 15, ui.SAND, 'center', 'baseline', alpha=e)
    if K.xp:
        # XP: what this fish gave, and how far you are toward the next level
        yb = y + h - 58
        bw = w - 80
        bx = x + 40
        u2 = clamp((K.t - 0.35) / 0.8, 0, 1)
        need = max(1, K.xpNeed or 1)
        now = K.xpNow or 0
        prev = max(0, now - K.xp) if not K.up else 0
        frac = clamp((prev + (now - prev) * u2) / need, 0, 1)
        ui.text(c, f'+{K.xp} XP', bx, yb - 6, 'k', 15, '#9dffb0', 'left', 'baseline', alpha=e)
        lab = f'Level {K.lvl}' + ('  LEVEL UP!' if K.up else '') + f'   {fmt(now)} / {fmt(need)} XP'
        ui.text(c, lab, bx + bw, yb - 6, 'x', 12, ui.SAND if K.up else ui.MIST, 'right', 'baseline', alpha=e)
        ui.box(c, (bx, yb, bw, 9), (255, 255, 255, 30), None, 5, alpha=e)
        if frac > 0.01:
            c.blit(_grad_bar(('xpbar', int(bw)), bw, 9, '#62d672', '#9dffb0', 5), (bx, yb), (0, 0, max(6, int(bw * frac)), 9))
        ui.text(c, f'{fmt(max(0, need - now))} XP to level {K.lvl + 1}', x + w / 2, yb + 24, 'x', 12, ui.MIST, 'center', 'baseline', alpha=e)
    if K.t > 0.6:
        ui.text(c, 'Click or press Space to keep fishing', x + w / 2, y + h - 10, 'x', 12, (234, 246, 255, 153), 'center', 'baseline')
    if K.isNew:
        nb = _cache.get('newbadge')
        if nb is None:
            s = pygame.Surface((72, 26), pygame.SRCALPHA)
            pygame.draw.rect(s, hexc('#ff4f6d'), (0, 0, 72, 26), border_radius=8)
            ui.text(s, 'NEW!', 36, 13, 'd', 16, (255, 255, 255), 'center', 'middle')
            nb = _cache['newbadge'] = pygame.transform.rotozoom(s, -math.degrees(0.25), 1)
        nb.set_alpha(int(255 * e))
        c.blit(nb, (x + w - 46 - nb.get_width() / 2, y + 26 - nb.get_height() / 2))


def draw_hype(c):
    Hy = G.hype
    if not Hy:
        return
    W, H = G.W, G.H
    a = min(1, Hy.t * 3, (Hy.dur - Hy.t) * 1.5)
    if a <= 0:
        return
    cxp, cyp = W / 2, H * 0.36
    lay = _cache.get('hypelayer')
    if lay is None:
        lay = _cache['hypelayer'] = pygame.Surface((W // 2, H // 2), pygame.SRCALPHA)
    lay.fill((0, 0, 0, 0))
    col = hexc(Hy.col)
    R = max(W, H) / 2
    hx, hy = cxp / 2, cyp / 2
    for kk in range(16):
        ang = G.t * 0.25 + TAU / 16 * (kk + 1)
        ca, sa = math.cos(ang), math.sin(ang)
        for seg in range(3):
            r0, r1 = R * seg / 3, R * (seg + 1) / 3
            w0, w1 = 30 * seg / 3, 30 * (seg + 1) / 3
            al = int(255 * 0.9 * (1 - (seg + 0.5) / 3))
            pts = [(hx + ca * r0 - sa * w0, hy + sa * r0 + ca * w0), (hx + ca * r1 - sa * w1, hy + sa * r1 + ca * w1),
                   (hx + ca * r1 + sa * w1, hy + sa * r1 - ca * w1), (hx + ca * r0 + sa * w0, hy + sa * r0 - ca * w0)]
            pygame.draw.polygon(lay, col + (al,), pts)
    big = pygame.transform.scale(lay, (W, H))
    big.set_alpha(int(255 * a * 0.55))
    c.blit(big, (0, 0))
    tk = ('hypetext', Hy.text, Hy.col)
    ts = _cache.get(tk)
    if ts is None:
        size = int((64 if Hy.big else 48) * max(0.7, G.S))
        f = ui.font('d', size)
        base = f.render(Hy.text, True, (255, 255, 255))
        tw, th = base.get_size()
        grad = pygame.Surface((tw, th), pygame.SRCALPHA)
        for yy in range(th):
            u = yy / max(1, th - 1)
            gc = mix('#fff8d6', Hy.col, u / 0.5) if u < 0.5 else mix(Hy.col, '#b8741a', (u - 0.5) / 0.5)
            pygame.draw.line(grad, gc + (255,), (0, yy), (tw, yy))
        grad.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        o = f.render(Hy.text, True, (60, 30, 0))
        pad = 6
        ts = pygame.Surface((tw + 2 * pad, th + 2 * pad), pygame.SRCALPHA)
        for i in range(16):
            an = TAU * i / 16
            ts.blit(o, (pad + round(math.cos(an) * 5), pad + round(math.sin(an) * 5)))
        ts.fill((255, 255, 255, 191), special_flags=pygame.BLEND_RGBA_MULT)
        ts.blit(grad, (pad, pad))
        _cache[tk] = ts
    pop = 1 + 0.15 * max(0, 1 - Hy.t * 3)
    s = ts if pop < 1.01 else pygame.transform.smoothscale(ts, (int(ts.get_width() * pop), int(ts.get_height() * pop)))
    s.set_alpha(int(255 * a))
    yy = cyp - Hy.t * 14
    c.blit(s, (cxp - s.get_width() / 2, yy - s.get_height() * 0.75))
    s.set_alpha(255)


# ===================================================================================
#  Everything, in order
# ===================================================================================
def draw(c, dt):
    P = Wd.P
    if P is None:
        return
    BD.amb_tick(G.dt or 0.0)
    peers = online.visible_peers() if online.active() else []
    B = Wd.BIO()
    c.fill(BD.water_col(B, max(0.0, G.cam)))
    BD.draw_sky(c, dt)
    BD.draw_water(c, dt)
    draw_fishes(c)
    draw_landing(c)
    draw_parts(c)
    draw_darkness(c, peers)
    BD.draw_glowers(c)
    draw_peer_boats(c, peers)
    draw_pet_boats(c, peers)
    draw_my_boat(c)
    BD.draw_surface(c)
    BD.draw_jumps(c)
    draw_peer_lines(c, peers)
    draw_line(c)
    draw_name_tags(c, peers)
    draw_bite(c)
    draw_floats(c)
    BD.draw_vignette(c)
    draw_dread(c)
    draw_storm(c)
    draw_radar(c)
    draw_depth_gauge(c)
    draw_charge(c)
    if G.shake > 0.3:
        c.scroll(int(rand(-G.shake, G.shake)), int(rand(-G.shake, G.shake)))
    draw_reel(c)
    draw_screen_parts(c)
    draw_card(c)
    draw_hype(c)
    if G.sail:
        t = G.sail.t
        a = clamp((t - 0.8) / 0.4, 0, 1) if t < 1.2 else clamp(1 - (t - 1.2) / 0.4, 0, 1)
        ui.overlay(c, (2, 8, 16), a)
    if G.flash > 0.01:
        ui.overlay(c, hexc(G.flashCol), min(1, G.flash))
    pump()
