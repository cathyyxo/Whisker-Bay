"""Fish sprites, painted in code.

Every fish is drawn facing right, centred on the pen's origin and L pixels long. A bony fish is built
from a side profile (how deep it is along its length); fins, a tail and a face are added, and the whole
fish is bent by a swimming wave that runs from the head to the tail. Eels, rays, squid, jellyfish,
puffers, the seahorse, the anglerfish and the Leviathan have painters of their own.
Every movement repeats exactly once per animation cycle, so the cached frames loop seamlessly."""
import math
import random

import pygame

from .util import D, TAU, clamp, hexc, lerp

SIL = (4, 14, 26)


# ===================================================================================
#  Colour helpers
# ===================================================================================
def _c(c):
    return hexc(c) if isinstance(c, str) else (int(c[0]), int(c[1]), int(c[2]))


def mixc(a, b, t):
    A, B = _c(a), _c(b)
    t = clamp(t, 0.0, 1.0)
    return (int(A[0] + (B[0] - A[0]) * t), int(A[1] + (B[1] - A[1]) * t), int(A[2] + (B[2] - A[2]) * t))


def lt(c, k):
    return mixc(c, (255, 255, 255), k)


def dk(c, k):
    return mixc(c, (0, 0, 0), k)


def al(c, a):
    r, g, b = _c(c)
    return (r, g, b, int(clamp(a, 0.0, 1.0) * 255))


# ===================================================================================
#  The swimming wave and paths in "straight fish" coordinates
# ===================================================================================
class Wave:
    """Bends the straight fish: a wave runs from head to tail, small at the head, big at the tail."""

    def __init__(self, L, ph, amp, wl=0.85, head=0.2, pw=1.7):
        self.L, self.ph, self.A, self.wl, self.head, self.pw = L, ph, amp * L, wl, head, pw
        self.xn = 0.5 * L
        self.e = max(0.5, L * 0.01)

    def dy(self, x):
        s = (self.xn - x) / self.L
        if s <= self.head:
            env = 0.04 * max(0.0, s) / self.head
        else:
            u = min(1.5, (s - self.head) / (1 - self.head))
            env = 0.04 + 0.96 * u ** self.pw
        return self.A * env * math.sin(self.ph - TAU * self.wl * s)

    def __call__(self, x, y):
        d = self.dy(x)
        e = self.e
        a = math.atan((self.dy(x + e) - self.dy(x - e)) / (2 * e))
        return x - y * math.sin(a), d + y * math.cos(a)


def _flat(x, y):
    return x, y


class Path:
    """A path in fish coordinates. .to(pen, warp) bends it and hands it to the pen."""
    __slots__ = ('subs',)

    def __init__(self):
        self.subs = []

    def move(self, x, y):
        self.subs.append([[(x, y)], False])
        return self

    def line(self, x, y):
        self.subs[-1][0].append((x, y))
        return self

    def pts(self, seq):
        self.subs[-1][0].extend(seq)
        return self

    def quad(self, cx, cy, x, y, n=10):
        p = self.subs[-1][0]
        x0, y0 = p[-1]
        for i in range(1, n + 1):
            t = i / n
            u = 1 - t
            p.append((u * u * x0 + 2 * u * t * cx + t * t * x, u * u * y0 + 2 * u * t * cy + t * t * y))
        return self

    def bez(self, ax, ay, bx, by, x, y, n=14):
        p = self.subs[-1][0]
        x0, y0 = p[-1]
        for i in range(1, n + 1):
            t = i / n
            u = 1 - t
            a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
            p.append((a * x0 + b * ax + c * bx + d * x, a * y0 + b * ay + c * by + d * y))
        return self

    def close(self):
        self.subs[-1][1] = True
        return self

    def oval(self, x, y, rx, ry, rot=0.0, n=22):
        cs, sn = math.cos(rot), math.sin(rot)
        pts = []
        for i in range(n):
            a = TAU * i / n
            px, py = math.cos(a) * rx, math.sin(a) * ry
            pts.append((x + px * cs - py * sn, y + px * sn + py * cs))
        self.subs.append([pts, True])
        return self

    def to(self, pen, W=None):
        pen.begin()
        for pts, closed in self.subs:
            first = True
            for x, y in pts:
                if W is not None:
                    x, y = W(x, y)
                if first:
                    pen.move(x, y)
                    first = False
                else:
                    pen.line(x, y)
            if closed:
                pen.close()
        return pen


def fill(c, path, W, col):
    path.to(c, W).fill(col)


def _stop(stops, t):
    t = clamp(t, 0.0, 1.0)
    for i in range(len(stops) - 1):
        o0, c0 = stops[i]
        o1, c1 = stops[i + 1]
        if t <= o1:
            u = 0.0 if o1 == o0 else (t - o0) / (o1 - o0)
            a0 = c0[3] if len(c0) > 3 else 255
            a1 = c1[3] if len(c1) > 3 else 255
            return (int(c0[0] + (c1[0] - c0[0]) * u), int(c0[1] + (c1[1] - c0[1]) * u),
                    int(c0[2] + (c1[2] - c0[2]) * u), int(a0 + (a1 - a0) * u))
    c1 = stops[-1][1]
    return (c1[0], c1[1], c1[2], c1[3] if len(c1) > 3 else 255)


def vgrad(c, path, W, y0, y1, stops, bands=None):
    """Fill a path with a smooth top-to-bottom gradient (y0 -> y1 in fish coordinates)."""
    polys = []
    for pts, _closed in path.subs:
        poly = []
        for x, y in pts:
            if W is not None:
                x, y = W(x, y)
            poly.append(c.tp(x, y))
        if len(poly) >= 3:
            polys.append(poly)
    if not polys:
        return
    sw, sh = c.surf.get_size()
    xs = [q[0] for poly in polys for q in poly]
    ys = [q[1] for poly in polys for q in poly]
    bx0, by0 = max(0, int(min(xs)) - 1), max(0, int(min(ys)) - 1)
    bx1, by1 = min(sw, int(max(xs)) + 2), min(sh, int(max(ys)) + 2)
    w, h = bx1 - bx0, by1 - by0
    if w <= 0 or h <= 0:
        return
    stops = [(o, _c(col) + ((col[3],) if len(col) > 3 else (255,)) if not isinstance(col, str) else _c(col) + (255,)) for o, col in stops]
    g0, g1 = c.tp(0, y0)[1], c.tp(0, y1)[1]
    span = (g1 - g0) or 1.0
    strip = pygame.Surface((1, h), pygame.SRCALPHA)
    for r in range(h):
        strip.set_at((0, r), _stop(stops, (by0 + r + 0.5 - g0) / span))
    g = pygame.transform.scale(strip, (w, h))
    m = pygame.Surface((w, h), pygame.SRCALPHA)
    for poly in polys:
        pygame.draw.polygon(m, (255, 255, 255, 255), [(qx - bx0, qy - by0) for qx, qy in poly])
    g.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    c.surf.blit(g, (bx0, by0))


def stroke(c, path, W, col, w, cap='butt'):
    path.to(c, W).stroke(col, w, cap)


def dot(c, W, x, y, r, col, n=14):
    x, y = W(x, y)
    Path().oval(x, y, r, r, n=n).to(c).fill(col)


# ===================================================================================
#  Colours of a fish (with mutations)
# ===================================================================================
def palette(sp, mut, lk=None):
    lk = lk or look(sp)
    fin = _c(sp.fin)
    p = D(col=_c(sp.col), belly=_c(sp.belly), fin=fin,
          tail=_c(lk.tc) if lk.tc else fin, dors=_c(lk.dc) if lk.dc else fin, pect=_c(lk.pc) if lk.pc else fin,
          patc=_c(lk.patc or sp.patc) if (lk.patc or sp.patc) else dk(sp.col, 0.35), glow=_c(sp.glow) if sp.glow else None,
          iris=_c(lk.iris) if lk.iris else (226, 196, 110), edge=_c(lk.edge) if lk.edge else None,
          acc=_c(lk.acc) if lk.acc else None, mut=mut)
    if mut == 'albino':
        for k in ('col', 'fin', 'tail', 'dors', 'pect'):
            p[k] = mixc(p[k], (255, 255, 255), 0.82)
        p.belly = (255, 255, 255)
        p.patc = mixc(p.patc, (255, 255, 255), 0.7)
        p.iris = (255, 96, 128)
        if p.edge:
            p.edge = mixc(p.edge, (255, 255, 255), 0.6)
        if p.acc:
            p.acc = mixc(p.acc, (255, 255, 255), 0.6)
    elif mut == 'electric':
        p.col = mixc(p.col, (42, 214, 255), 0.55)
        p.belly = mixc(p.belly, (210, 250, 255), 0.5)
        for k in ('fin', 'tail', 'dors', 'pect'):
            p[k] = mixc(p[k], (233, 255, 255), 0.7)
        p.patc = (255, 255, 255)
        p.glow = (98, 243, 255)
        p.iris = (200, 255, 255)
    elif mut == 'gilded':
        p.col = mixc(p.col, (255, 204, 51), 0.75)
        p.belly = (255, 241, 176)
        for k in ('fin', 'tail', 'dors', 'pect'):
            p[k] = mixc(p[k], (255, 226, 122), 0.8)
        p.patc = (255, 246, 201)
        p.glow = (255, 210, 61)
        p.iris = (255, 240, 180)
    elif mut == 'corrupted':
        p.col = mixc(p.col, (42, 6, 56), 0.75)
        p.belly = mixc(p.belly, (106, 26, 138), 0.7)
        for k in ('fin', 'tail', 'dors', 'pect'):
            p[k] = mixc(p[k], (176, 43, 255), 0.75)
        p.patc = (255, 61, 213)
        p.glow = (176, 43, 255)
        p.iris = (255, 61, 213)
    return p


# ===================================================================================
#  Eyes and little face parts
# ===================================================================================
def eye(c, x, y, r, iris, pupil=(8, 8, 16), big=False, glow=None):
    """A cartoon fish eye: a dark socket, a coloured iris, a big pupil and two sparkles."""
    k = c.k()
    if r * k < 2.2:                       # too small for details: a dark dot with a sparkle
        Path().oval(x, y, r, r, n=10).to(c).fill(pupil)
        if r * k > 1.2:
            Path().oval(x + r * 0.3, y - r * 0.3, r * 0.35, r * 0.35, n=8).to(c).fill((255, 255, 255))
        return
    Path().oval(x, y, r * 1.16, r * 1.12).to(c).fill((0, 0, 0, 70))
    Path().oval(x, y, r, r).to(c).fill(dk(iris, 0.35))
    Path().oval(x, y - r * 0.08, r * 0.86, r * 0.82).to(c).fill(iris)
    Path().oval(x, y + r * 0.42, r * 0.7, r * 0.34).to(c).fill(al(dk(iris, 0.25), 0.55))
    pr = r * (0.62 if big else 0.55)
    Path().oval(x + r * 0.12, y + r * 0.04, pr, pr * 1.04).to(c).fill(pupil)
    if glow:
        Path().oval(x + r * 0.12, y + r * 0.04, pr * 0.45, pr * 0.45).to(c).fill(al(glow, 0.8))
    Path().oval(x + r * 0.34, y - r * 0.34, r * 0.28, r * 0.24, n=12).to(c).fill((255, 255, 255, 245))
    Path().oval(x - r * 0.22, y + r * 0.36, r * 0.12, r * 0.12, n=10).to(c).fill((255, 255, 255, 170))


# ===================================================================================
#  Looks: the shape of every bony fish (all sizes are fractions of the fish's length)
# ===================================================================================
BASE = D(depth=0.14, bl=0.79, hump=0.37, nose=1.8, ped=0.3, taper=1.2, top=1.0, bot=1.0, my=0.0,
         tail='fork', tl=0.21, ts=0.12, wave=0.06, wl=0.85,
         dorsal=(('soft', 0.38, 0.62, 0.06),), anal=(('soft', 0.64, 0.78, 0.04),),
         pect=0.115, pw=0.5, pang=0.6, pswing=0.42, py=0.32, ps=0.27, pelvic=0.045,
         finlets=0, adipose=False, eye=0.048, ex=0.085, ey=0.28, eyes=1, mouth='small', gs=0.22,
         scales=True, lateral=True, sheen=False, outline=True, pat=None,
         bump=0.0, bill=0.0, chin=0.0, cirri=False, slits=False, translucent=False, tip=None, sailfire=False, flap=0.0)

LOOKS = {
    # ----- Starter Shore -----
    'sardine': D(depth=0.105, bl=0.8, hump=0.4, nose=1.55, ped=0.28, taper=1.1, my=0.05, tail='fork', tl=0.2, ts=0.11,
                 dorsal=(('soft', 0.42, 0.56, 0.065),), anal=(('soft', 0.74, 0.84, 0.03),), pect=0.085,
                 eye=0.055, ex=0.075, ey=0.18, iris='#e6eef6', pat='spotrow', sheen=True, lateral=False, wave=0.064),
    'stickleback': D(depth=0.13, bl=0.82, hump=0.3, nose=1.75, ped=0.34, tail='round', tl=0.15, ts=0.1,
                     dorsal=(('spiny', 0.25, 0.43, 0.1, 3), ('soft', 0.48, 0.62, 0.045)),
                     anal=(('soft', 0.62, 0.74, 0.035),), pect=0.09, pelvic=0.04, eye=0.052,
                     ex=0.1, ey=0.34, iris='#e8d8a0', wave=0.05),
    'mackerel': D(depth=0.11, bl=0.81, hump=0.42, nose=1.5, ped=0.16, taper=1.0, tail='deep', tl=0.19, ts=0.13,
                  dorsal=(('tri', 0.3, 0.42, 0.06), ('soft', 0.56, 0.64, 0.045)), anal=(('soft', 0.58, 0.66, 0.035),),
                  finlets=5, pect=0.09, eye=0.046, ex=0.08, ey=0.2, iris='#d9e4ea', pat='bars', sheen=True, wave=0.051),
    'seabass': D(depth=0.14, hump=0.37, nose=1.75, ped=0.3, tail='emarg', tl=0.2, ts=0.13,
                 dorsal=(('spiny', 0.25, 0.47, 0.085, 9), ('soft', 0.5, 0.7, 0.06)), anal=(('soft', 0.62, 0.74, 0.045),),
                 pect=0.1, pelvic=0.05, eye=0.044, iris='#e8cf7a', mouth='big', wave=0.058),
    'flounder': D(depth=0.235, bl=0.86, hump=0.45, nose=2.0, ped=0.22, my=-0.05, tail='round', tl=0.13, ts=0.1,
                  dorsal=(('fringe', 0.1, 0.95, 0.045),), anal=(('fringe', 0.28, 0.95, 0.04),), pect=0.06, pelvic=0,
                  eye=0.036, ex=0.1, ey=0.66, eyes=2, iris='#e8d27a', mouth='small', pat='spots', wave=0.045, wl=1.15,
                  lateral=True),
    'snapper': D(depth=0.155, bl=0.78, hump=0.33, nose=1.35, my=0.12, ped=0.27, tail='emarg', tl=0.2, ts=0.14,
                 dorsal=(('spiny', 0.24, 0.46, 0.08, 10), ('soft', 0.48, 0.68, 0.065)), anal=(('tri', 0.6, 0.72, 0.06),),
                 pect=0.13, pw=0.24, pelvic=0.05, eye=0.045, ex=0.1, ey=0.38, iris='#ff6a4a', mouth='big', wave=0.058),
    'moonfish': D(depth=0.27, bl=0.82, hump=0.42, nose=2.3, my=0.1, ped=0.12, taper=1.4, tail='deep', tl=0.17, ts=0.17,
                  dorsal=(('sail', 0.18, 0.62, 0.2),), anal=(('long', 0.55, 0.82, 0.04),), pect=0.13, pw=0.2, pang=0.15,
                  pelvic=0.09, eye=0.05, ex=0.1, ey=0.3, iris='#ffcf5a', pat='spots', patc='#fff1ec', dc='#ff3d2a', tc='#ff3d2a',
                  pc='#ff5a3a', wave=0.045, scales=False),
    'goldtuna': D(depth=0.14, bl=0.81, hump=0.42, nose=1.7, ped=0.07, taper=0.85, tail='deep', tl=0.19, ts=0.2,
                  dorsal=(('tri', 0.3, 0.42, 0.06), ('sail', 0.52, 0.6, 0.1)), anal=(('sail', 0.55, 0.63, 0.085),),
                  finlets=7, pect=0.15, pw=0.2, pang=0.35, eye=0.038, ex=0.09, ey=0.18, iris='#ffe08a',
                  pat='tuna', sheen=True, wave=0.038, keel=True),
    'salmonking': D(depth=0.17, bl=0.8, hump=0.42, nose=1.75, ped=0.28, tail='fork', tl=0.24, ts=0.16,
                    dorsal=(('soft', 0.4, 0.58, 0.075),), anal=(('soft', 0.62, 0.76, 0.05),),
                    pect=0.13, pelvic=0.05, eye=0.045, ex=0.09, ey=0.24, iris='#fff0a0',
                    crown=True, bigscales=True, sheen=True, wave=0.05),
    'pike': D(depth=0.12, bl=0.84, hump=0.3, nose=1.15, ped=0.14, taper=0.9, tail='fork', tl=0.18, ts=0.13,
              dorsal=(('tri', 0.66, 0.78, 0.075),), anal=(('tri', 0.68, 0.79, 0.06),),
              pect=0.09, pelvic=0.04, eye=0.04, ex=0.12, ey=0.24, iris='#d8e880', mouth='fangs', wave=0.055),
    'wels': D(depth=0.24, bl=0.88, hump=0.38, nose=1.8, ped=0.18, taper=1.35, tail='round', tl=0.14, ts=0.12,
              dorsal=(('soft', 0.3, 0.44, 0.055),), anal=(('long', 0.56, 0.82, 0.05),),
              pect=0.1, pelvic=0.04, eye=0.032, ex=0.1, ey=0.4, iris='#c8b880',
              mouth='big', barbels=0.2, wave=0.05),
    'whiskerkoi': D(depth=0.15, bl=0.74, hump=0.36, nose=2.1, my=0.05, ped=0.38, tail='koi', tl=0.3, ts=0.16,
                    dorsal=(('long', 0.3, 0.72, 0.055),), anal=(('soft', 0.7, 0.8, 0.04),), pect=0.13, pw=0.42,
                    pelvic=0.07, eye=0.04, ex=0.1, ey=0.25, iris='#4a3020', barbels=0.2, pat='patches', bigscales=True,
                    wave=0.064),
    # ----- Coral Reef -----
    'clown': D(depth=0.165, bl=0.78, hump=0.4, nose=2.3, ped=0.42, tail='round', tl=0.18, ts=0.12,
               dorsal=(('spiny', 0.3, 0.48, 0.06, 7), ('soft', 0.5, 0.72, 0.07)), anal=(('soft', 0.6, 0.76, 0.06),),
               pect=0.09, pelvic=0.05, eye=0.06, ex=0.1, ey=0.22, iris='#ff8a2a', edge='#141414',
               dc='#ff9a3a', tc='#ff9a3a', pc='#ff9a3a', pat='clownbands', scales=False, wave=0.064),
    'tang': D(depth=0.21, bl=0.79, hump=0.42, nose=1.9, my=0.05, ped=0.2, tail='trunc', tl=0.17, ts=0.14,
              dorsal=(('long', 0.2, 0.86, 0.06),), anal=(('long', 0.44, 0.86, 0.05),), pect=0.1, pelvic=0.04,
              eye=0.05, ex=0.12, ey=0.3, iris='#26325a', pat='palette', dc='#2f6bff', edge='#0d1d4d', pc='#ffd23d',
              scalpel=True, scales=False, wave=0.051),
    'parrot': D(depth=0.17, bl=0.78, hump=0.4, nose=2.4, my=0.05, ped=0.35, tail='deep', tl=0.18, ts=0.15,
                dorsal=(('long', 0.26, 0.74, 0.04),), anal=(('long', 0.56, 0.76, 0.035),), pect=0.1, pelvic=0.04,
                eye=0.042, ex=0.11, ey=0.32, iris='#ff70b0', mouth='beak', pat='parrot', bigscales=True, wave=0.058),
    'butterfly': D(depth=0.26, bl=0.8, hump=0.45, nose=1.25, ped=0.18, tail='trunc', tl=0.13, ts=0.13,
                   dorsal=(('contour', 0.18, 0.86, 0.06),), anal=(('contour', 0.42, 0.86, 0.06),), pect=0.08,
                   pelvic=0.05, eye=0.04, ex=0.16, ey=0.2, iris='#ffd23d', mouth='snout', pat='eyespot',
                   eyeband=True, scales=False, wave=0.051),
    'lionfish': D(depth=0.15, bl=0.78, hump=0.38, nose=1.8, ped=0.3, tail='round', tl=0.18, ts=0.12,
                  dorsal=(('lion', 0.18, 0.56, 0.32, 13), ('soft', 0.58, 0.76, 0.07)), anal=(('soft', 0.62, 0.76, 0.06),),
                  pect=0, lionfan=0.4, pelvic=0.08, eye=0.045, ex=0.1, ey=0.3, iris='#ffb08a', pat='lionbands',
                  tentacles=True, scales=False, wave=0.045),
    'angelcrown': D(depth=0.26, bl=0.72, hump=0.42, nose=1.9, my=0.05, ped=0.16, tail='lyre', tl=0.2, ts=0.15,
                    dorsal=(('trail', 0.22, 0.75, 0.22),), anal=(('trail', 0.44, 0.75, 0.2),), pect=0.09,
                    pelvic=0.05, filaments=True, eye=0.045, ex=0.12, ey=0.3, iris='#ffd23d', crown=True,
                    pat='angelbands', scales=False, wave=0.051),
    # ----- Volcanic Biome -----
    'ashgoby': D(depth=0.12, bl=0.8, hump=0.28, nose=2.6, ped=0.5, tail='round', tl=0.18, ts=0.09,
                 dorsal=(('soft', 0.32, 0.44, 0.05), ('soft', 0.5, 0.76, 0.045)), anal=(('soft', 0.56, 0.76, 0.04),),
                 pect=0.1, pw=0.5, pelvic=0.05, eye=0.052, ex=0.1, ey=0.62, iris='#ffb050', pat='spots', wave=0.064),
    'embersmelt': D(depth=0.1, bl=0.8, hump=0.42, nose=1.55, ped=0.25, tail='fork', tl=0.2, ts=0.1,
                    dorsal=(('soft', 0.44, 0.54, 0.05),), adipose=True, anal=(('soft', 0.72, 0.82, 0.03),), pect=0.08,
                    eye=0.055, ex=0.08, ey=0.2, iris='#ffe08a', pat='embstripe', wave=0.064),
    'basalt': D(depth=0.18, bl=0.79, hump=0.36, nose=1.9, my=0.08, ped=0.4, taper=1.3, tail='round', tl=0.18, ts=0.13,
                dorsal=(('spiny', 0.25, 0.5, 0.07, 10), ('soft', 0.52, 0.72, 0.065)), anal=(('soft', 0.62, 0.76, 0.06),),
                pect=0.11, pw=0.45, pelvic=0.06, eye=0.036, ex=0.12, ey=0.42, iris='#ff8a3a', mouth='grouper',
                pat='hex', scales=False, wave=0.045),
    'obsidian': D(depth=0.155, bl=0.78, hump=0.33, nose=1.35, my=0.12, ped=0.27, tail='emarg', tl=0.2, ts=0.14,
                  dorsal=(('razor', 0.24, 0.46, 0.09, 10), ('soft', 0.48, 0.68, 0.065)), anal=(('tri', 0.6, 0.72, 0.06),),
                  pect=0.13, pw=0.24, pelvic=0.05, eye=0.045, ex=0.1, ey=0.38, iris='#b48cff', mouth='big',
                  pat='facets', scales=False, edge='#b48cff', wave=0.058),
    'phoenix': D(depth=0.15, bl=0.74, hump=0.36, nose=2.1, my=0.05, ped=0.36, tail='flame', tl=0.32, ts=0.18,
                 dorsal=(('flame', 0.28, 0.74, 0.08),), anal=(('flame', 0.66, 0.8, 0.05),), pect=0.14, pw=0.45,
                 pelvic=0.07, eye=0.042, ex=0.1, ey=0.25, iris='#fff2a0', barbels=0.08, pat='embers', bigscales=True,
                 tc='#ffd23d', dc='#ffb03a', pc='#ffd23d', wave=0.064, flamefins=True),
    # ----- Deep Trench Abyss -----
    'lantern': D(depth=0.12, bl=0.8, hump=0.32, nose=2.1, ped=0.28, tail='fork', tl=0.2, ts=0.1,
                 dorsal=(('soft', 0.4, 0.55, 0.05),), adipose=True, anal=(('soft', 0.62, 0.78, 0.035),), pect=0.08,
                 eye=0.075, ex=0.08, ey=0.12, iris='#7ffcff', pat='photo', scales=False, wave=0.064),
    'hatchet': D(depth=0.2, bl=0.8, hump=0.34, nose=1.6, ped=0.12, top=0.55, bot=1.5, my=-0.1, taper=1.0,
                 tail='fork', tl=0.15, ts=0.08, dorsal=(('tri', 0.44, 0.54, 0.05),), anal=(('soft', 0.66, 0.8, 0.03),),
                 pect=0.07, pelvic=0, eye=0.07, ex=0.11, ey=0.5, iris='#c8f0ff', pat='hatchet', scales=False,
                 wave=0.045, sheen=True),
    'barreleye': D(depth=0.12, bl=0.8, hump=0.3, nose=2.2, ped=0.32, tail='fork', tl=0.18, ts=0.1,
                   dorsal=(('soft', 0.5, 0.62, 0.04),), anal=(('soft', 0.62, 0.76, 0.035),), pect=0.14, pw=0.4,
                   pang=0.3, pelvic=0.06, eye=0, dome=True, pat=None, scales=True, wave=0.051),
    # ----- new in 1.3: Starter Shore -----
    'blenny': D(depth=0.15, bl=0.82, hump=0.2, nose=3.2, ped=0.45, taper=1.0, my=-0.02, tail='round', tl=0.14, ts=0.1,
                dorsal=(('long', 0.18, 0.92, 0.07),), anal=(('long', 0.5, 0.92, 0.05),), pect=0.13, pw=0.55, pang=0.9,
                pelvic=0.05, eye=0.07, ex=0.07, ey=0.85, iris='#ffb050', cirri=True, mouth='lips', pat='spots',
                scales=False, lateral=False, wave=0.07),
    'cod': D(depth=0.15, bl=0.8, hump=0.33, nose=1.7, my=0.04, ped=0.22, taper=1.0, tail='trunc', tl=0.16, ts=0.12,
             dorsal=(('soft', 0.28, 0.42, 0.07), ('soft', 0.46, 0.64, 0.06), ('soft', 0.68, 0.84, 0.05)),
             anal=(('soft', 0.5, 0.66, 0.045), ('soft', 0.7, 0.84, 0.04)), pect=0.1, pelvic=0.05,
             eye=0.045, ex=0.1, ey=0.32, iris='#d9c27a', chin=0.07, mouth='big', pat='spots', wave=0.055),
    'sunfish': D(depth=0.4, bl=0.9, hump=0.48, nose=2.4, ped=0.82, taper=0.5, tail='clavus', tl=0.12, ts=0.34,
                 dorsal=(('tri', 0.62, 0.86, 0.4),), anal=(('tri', 0.62, 0.86, 0.38),), flap=0.22, pect=0.07, pw=0.5,
                 pang=0.4, pelvic=0, eye=0.03, ex=0.11, ey=0.22, iris='#cfd8de', mouth='small', scales=False,
                 lateral=False, pat='spots', patc='#c8d0d6', wave=0.012, wl=0.5),
    # ----- new in 1.3: Coral Reef -----
    'anthias': D(depth=0.15, bl=0.78, hump=0.38, nose=1.9, my=0.04, ped=0.2, tail='lyre', tl=0.2, ts=0.13,
                 dorsal=(('spiny', 0.26, 0.48, 0.07, 9), ('soft', 0.5, 0.74, 0.07)), anal=(('soft', 0.62, 0.76, 0.05),),
                 pect=0.1, pelvic=0.06, eye=0.055, ex=0.1, ey=0.3, iris='#ff4f8a', tc='#ff9ac0', dc='#ffb03a',
                 pat='stripe', patc='#ffcf5a', wave=0.06),
    'alfonsino': D(depth=0.2, bl=0.79, hump=0.36, nose=1.6, my=0.05, ped=0.16, tail='deep', tl=0.2, ts=0.17,
                   dorsal=(('spiny', 0.32, 0.56, 0.1, 9),), anal=(('tri', 0.6, 0.72, 0.07),), pect=0.11, pelvic=0.06,
                   eye=0.085, ex=0.11, ey=0.2, iris='#ffe0d0', mouth='big', sheen=True, wave=0.055),
    'trigger': D(depth=0.24, bl=0.8, hump=0.42, nose=1.4, my=0.05, ped=0.2, taper=1.1, tail='trunc', tl=0.14, ts=0.13,
                 dorsal=(('tri', 0.3, 0.36, 0.13), ('contour', 0.5, 0.82, 0.08)), anal=(('contour', 0.5, 0.82, 0.08),),
                 pect=0.07, pelvic=0.0, eye=0.045, ex=0.2, ey=0.45, iris='#ffd23d', mouth='lips', lipcol='#ffd23d',
                 pat='trigger', scales=False, wave=0.04),
    'reefshark': D(depth=0.12, bl=0.8, hump=0.36, nose=1.5, my=-0.03, ped=0.12, taper=0.95, tail='shark', tl=0.24, ts=0.17,
                   dorsal=(('tri', 0.36, 0.48, 0.13), ('tri', 0.72, 0.78, 0.04)), anal=(('tri', 0.74, 0.8, 0.035),),
                   pect=0.17, pw=0.3, pang=0.55, pswing=0.15, py=0.55, ps=0.28, pelvic=0.05, eye=0.03, ex=0.09, ey=0.15,
                   iris='#e8e0c8', slits=True, gs=0.2, mouth='shark', tip='#16181c', scales=False, lateral=False,
                   wave=0.05, wl=0.75),
    'wrasse': D(depth=0.22, bl=0.8, hump=0.38, nose=1.9, my=0.05, ped=0.3, taper=1.2, tail='round', tl=0.17, ts=0.14,
                dorsal=(('long', 0.24, 0.8, 0.07),), anal=(('long', 0.56, 0.8, 0.07),), pect=0.13, pw=0.45,
                pelvic=0.06, eye=0.035, ex=0.11, ey=0.3, iris='#ffe08a', mouth='lips', lipcol='#5ac8b0', bump=0.5,
                pat='wrasse', bigscales=True, wave=0.045),
    # ----- new in 1.3: Volcanic Biome -----
    'pumice': D(depth=0.16, bl=0.79, hump=0.38, nose=1.7, my=0.05, ped=0.26, tail='emarg', tl=0.18, ts=0.13,
                dorsal=(('spiny', 0.26, 0.48, 0.08, 9), ('soft', 0.5, 0.7, 0.06)), anal=(('soft', 0.62, 0.74, 0.05),),
                pect=0.1, pelvic=0.05, eye=0.05, ex=0.1, ey=0.32, iris='#ffb080', pat='pores', scales=False, wave=0.055),
    'rockfish': D(depth=0.18, bl=0.79, hump=0.36, nose=1.8, my=0.06, ped=0.32, taper=1.25, tail='round', tl=0.17, ts=0.13,
                  dorsal=(('spiny', 0.22, 0.52, 0.11, 12), ('soft', 0.54, 0.72, 0.07)), anal=(('spiny', 0.62, 0.74, 0.06, 3),),
                  pect=0.15, pw=0.6, pang=0.7, pelvic=0.06, eye=0.05, ex=0.1, ey=0.38, iris='#ffd23d', mouth='big',
                  cirri=True, pat='mottle', scales=False, wave=0.05),
    'barracuda': D(depth=0.085, bl=0.82, hump=0.42, nose=1.25, my=0.04, ped=0.2, taper=0.9, tail='fork', tl=0.17, ts=0.13,
                   dorsal=(('tri', 0.34, 0.42, 0.06), ('tri', 0.62, 0.7, 0.05)), anal=(('tri', 0.64, 0.72, 0.045),),
                   pect=0.07, pelvic=0.04, eye=0.032, ex=0.16, ey=0.15, iris='#e8e0b0', mouth='under', pat='bars',
                   sheen=True, wave=0.055, wl=0.9),
    'sturgeon': D(depth=0.12, bl=0.82, hump=0.4, nose=1.25, my=0.08, ped=0.12, taper=0.9, tail='shark', tl=0.2, ts=0.15,
                  dorsal=(('tri', 0.66, 0.76, 0.06),), anal=(('tri', 0.72, 0.8, 0.045),), pect=0.13, pw=0.3, py=0.6,
                  pelvic=0.05, eye=0.025, ex=0.16, ey=0.2, iris='#c8b880', chin=0.045, barbn=4, mouth='small',
                  pat='scutes', scales=False, lateral=False, wave=0.04),
    'sailfish': D(depth=0.12, bl=0.8, hump=0.4, nose=1.3, my=0.03, ped=0.07, taper=0.85, tail='deep', tl=0.24, ts=0.24,
                  dorsal=(('sail', 0.18, 0.72, 0.36),), anal=(('tri', 0.66, 0.74, 0.07),), pect=0.13, pw=0.2,
                  pang=0.4, pelvic=0.1, eye=0.035, ex=0.12, ey=0.2, iris='#fff0c0', bill=0.3, pat='bars',
                  sheen=True, sailfire=True, flamefins=True, keel=True, wave=0.04),
    # ----- new in 1.3: Deep Trench Abyss -----
    'bristle': D(depth=0.11, bl=0.82, hump=0.3, nose=2.4, ped=0.25, tail='fork', tl=0.17, ts=0.09,
                 dorsal=(('soft', 0.46, 0.56, 0.04),), anal=(('long', 0.5, 0.82, 0.03),), pect=0.06, pelvic=0.03,
                 eye=0.05, ex=0.07, ey=0.2, iris='#9ff0ff', mouth='bristle', pat='photo', scales=False, wave=0.065),
    'rattail': D(depth=0.17, bl=0.88, hump=0.17, nose=2.2, my=0.08, ped=0.015, taper=2.6, tail='none', tl=0.1, ts=0.012,
                 dorsal=(('tri', 0.2, 0.28, 0.12), ('fringe', 0.36, 0.98, 0.02)), anal=(('fringe', 0.3, 0.98, 0.03),),
                 pect=0.1, pelvic=0.04, eye=0.06, ex=0.1, ey=0.3, iris='#c8e8ff', chin=0.03, mouth='small',
                 scales=True, wave=0.08, wl=1.0),
    'snailfish': D(depth=0.2, bl=0.84, hump=0.25, nose=3.0, my=0.02, ped=0.08, taper=0.7, tail='round', tl=0.12, ts=0.06,
                   dorsal=(('long', 0.3, 0.94, 0.05),), anal=(('long', 0.36, 0.94, 0.05),), pect=0.12, pw=0.7, pang=1.0,
                   pelvic=0, eye=0.04, ex=0.09, ey=0.35, iris='#30202a', mouth='small', translucent=True, scales=False,
                   lateral=False, wave=0.07, wl=1.0),
    'fangtooth': D(depth=0.24, bl=0.8, hump=0.3, nose=2.6, my=0.02, ped=0.24, taper=1.0, tail='fork', tl=0.16, ts=0.11,
                   dorsal=(('soft', 0.4, 0.62, 0.05),), anal=(('soft', 0.62, 0.76, 0.04),), pect=0.08, pelvic=0.04,
                   eye=0.035, ex=0.14, ey=0.6, iris='#8090a0', mouth='fangs', scales=True, wave=0.06),
    # ----- new in 1.4: Pallid Sea -----
    'herring': D(depth=0.12, bl=0.8, hump=0.4, nose=1.6, ped=0.24, taper=1.1, my=0.04, tail='fork', tl=0.2, ts=0.12,
                 dorsal=(('soft', 0.4, 0.54, 0.07),), anal=(('soft', 0.72, 0.82, 0.03),), pect=0.085,
                 eye=0.055, ex=0.08, ey=0.2, iris='#e6eef6', sheen=True, lateral=False, wave=0.062),
    'pollock': D(depth=0.13, bl=0.8, hump=0.36, nose=1.6, my=0.02, ped=0.18, taper=1.0, tail='emarg', tl=0.18, ts=0.13,
                 dorsal=(('soft', 0.3, 0.42, 0.07), ('soft', 0.46, 0.6, 0.06), ('soft', 0.64, 0.76, 0.05)),
                 anal=(('soft', 0.5, 0.64, 0.05), ('soft', 0.66, 0.76, 0.04)), pect=0.1, pelvic=0.04,
                 eye=0.045, ex=0.09, ey=0.25, iris='#e8e0c0', mouth='under', wave=0.055),
    'hake': D(depth=0.11, bl=0.82, hump=0.34, nose=1.5, my=0.05, ped=0.16, taper=1.05, tail='trunc', tl=0.15, ts=0.11,
              dorsal=(('tri', 0.28, 0.36, 0.08), ('long', 0.4, 0.88, 0.045)), anal=(('long', 0.46, 0.88, 0.04),),
              pect=0.11, pelvic=0.04, eye=0.05, ex=0.1, ey=0.28, iris='#d8e0e8', mouth='big', sheen=True, wave=0.058),
    'grenadier': D(depth=0.18, bl=0.88, hump=0.17, nose=2.7, my=0.08, ped=0.015, taper=2.6, tail='none', tl=0.1, ts=0.012,
                   dorsal=(('tri', 0.2, 0.28, 0.13), ('fringe', 0.36, 0.98, 0.02)), anal=(('fringe', 0.3, 0.98, 0.03),),
                   pect=0.1, pelvic=0.04, eye=0.07, ex=0.1, ey=0.3, iris='#b8d8f0', mouth='small', scales=True, wave=0.08, wl=1.0),
    'halibut': D(depth=0.2, bl=0.86, hump=0.42, nose=1.8, ped=0.16, my=-0.04, tail='emarg', tl=0.15, ts=0.13,
                 dorsal=(('fringe', 0.12, 0.92, 0.045),), anal=(('fringe', 0.3, 0.92, 0.04),), pect=0.07, pelvic=0,
                 eye=0.032, ex=0.11, ey=0.66, eyes=2, iris='#e8d27a', mouth='big', pat='spots', wave=0.042, wl=1.15),
    'redfish': D(depth=0.17, bl=0.79, hump=0.36, nose=1.7, my=0.06, ped=0.24, taper=1.15, tail='emarg', tl=0.17, ts=0.13,
                 dorsal=(('spiny', 0.22, 0.5, 0.1, 12), ('soft', 0.52, 0.7, 0.07)), anal=(('spiny', 0.62, 0.74, 0.06, 3),),
                 pect=0.14, pw=0.4, pelvic=0.06, eye=0.07, ex=0.1, ey=0.36, iris='#ffd0a0', mouth='big', wave=0.05),
    'ling': D(depth=0.085, bl=0.84, hump=0.3, nose=1.7, my=0.04, ped=0.1, taper=1.0, tail='round', tl=0.12, ts=0.09,
              dorsal=(('soft', 0.24, 0.36, 0.05), ('long', 0.38, 0.92, 0.04)), anal=(('long', 0.45, 0.92, 0.035),),
              pect=0.08, pelvic=0.03, eye=0.04, ex=0.09, ey=0.28, iris='#d8d0b0', chin=0.04, barbn=1, mouth='big',
              pat='mottle', wave=0.075, wl=1.05),
    'swordfish': D(depth=0.13, bl=0.8, hump=0.4, nose=1.3, my=0.03, ped=0.06, taper=0.85, tail='deep', tl=0.24, ts=0.24,
                   dorsal=(('tri', 0.26, 0.38, 0.17),), anal=(('tri', 0.66, 0.74, 0.07),), pect=0.15, pw=0.2, pang=0.5,
                   pelvic=0, eye=0.045, ex=0.12, ey=0.2, iris='#5ab0ff', bill=0.42, sheen=True, keel=True, scales=False,
                   lateral=False, wave=0.04),
    'sixgill': D(depth=0.12, bl=0.8, hump=0.36, nose=1.6, my=-0.03, ped=0.14, taper=0.95, tail='shark', tl=0.26, ts=0.15,
                 dorsal=(('tri', 0.6, 0.68, 0.07),), anal=(('tri', 0.72, 0.78, 0.035),), pect=0.16, pw=0.3, pang=0.55,
                 pswing=0.15, py=0.55, ps=0.28, pelvic=0.05, eye=0.032, ex=0.09, ey=0.15, iris='#62ff9a', slits=True,
                 gs=0.26, mouth='shark', scales=False, lateral=False, wave=0.05, wl=0.75),
    'chimaera': D(depth=0.16, bl=0.86, hump=0.3, nose=2.6, my=0.06, ped=0.015, taper=2.4, tail='none', tl=0.1, ts=0.012,
                  dorsal=(('tri', 0.18, 0.28, 0.16), ('fringe', 0.34, 0.95, 0.03)), anal=(('fringe', 0.5, 0.95, 0.025),),
                  pect=0.2, pw=0.25, pang=0.4, pswing=0.3, py=0.45, ps=0.3, pelvic=0.05, eye=0.075, ex=0.1, ey=0.28,
                  iris='#7fffb0', mouth='small', scales=False, wave=0.07, wl=1.0),
    'bluefin': D(depth=0.15, bl=0.81, hump=0.42, nose=1.7, ped=0.07, taper=0.85, tail='deep', tl=0.19, ts=0.2,
                 dorsal=(('tri', 0.3, 0.42, 0.06), ('sail', 0.52, 0.6, 0.09)), anal=(('sail', 0.55, 0.63, 0.08),),
                 finlets=8, pect=0.13, pw=0.2, pang=0.35, eye=0.036, ex=0.09, ey=0.18, iris='#e0e8ff',
                 pat='tuna', sheen=True, wave=0.038, keel=True),
    'greenland': D(depth=0.15, bl=0.82, hump=0.4, nose=2.2, my=-0.02, ped=0.12, taper=0.95, tail='shark', tl=0.22, ts=0.12,
                   dorsal=(('tri', 0.42, 0.5, 0.05), ('tri', 0.62, 0.68, 0.04)), anal=(), pect=0.12, pw=0.3, pang=0.55,
                   pswing=0.12, py=0.55, ps=0.28, pelvic=0.04, eye=0.02, ex=0.08, ey=0.15, iris='#b8c8d0', slits=True,
                   gs=0.2, mouth='shark', scales=False, lateral=False, wave=0.035, wl=0.75),
    'stormmarlin': D(depth=0.12, bl=0.8, hump=0.4, nose=1.3, my=0.03, ped=0.07, taper=0.85, tail='deep', tl=0.24, ts=0.24,
                     dorsal=(('sail', 0.18, 0.5, 0.22),), anal=(('tri', 0.66, 0.74, 0.07),), pect=0.15, pw=0.2,
                     pang=0.4, pelvic=0.08, eye=0.035, ex=0.12, ey=0.2, iris='#e8fbff', bill=0.36, pat='bars',
                     sheen=True, keel=True, wave=0.04),
    'ghostpike': D(depth=0.1, bl=0.84, hump=0.32, nose=1.25, my=0.03, ped=0.14, taper=0.95, tail='fork', tl=0.17, ts=0.13,
                   dorsal=(('tri', 0.66, 0.78, 0.07),), anal=(('tri', 0.68, 0.79, 0.06),), pect=0.08, pelvic=0.045,
                   eye=0.04, ex=0.13, ey=0.24, iris='#e8f4ff', mouth='under', translucent=True, pat='ribs',
                   scales=False, lateral=False, wave=0.06),
    'coelacanth': D(depth=0.17, bl=0.8, hump=0.36, nose=2.0, my=0.05, ped=0.3, taper=1.1, tail='coel', tl=0.2, ts=0.16,
                    dorsal=(('tri', 0.3, 0.4, 0.1), ('soft', 0.62, 0.7, 0.07)), anal=(('soft', 0.64, 0.72, 0.07),),
                    pect=0.13, pw=0.6, pelvic=0.07, eye=0.045, ex=0.1, ey=0.3, iris='#ffe8a0', mouth='big', pat='spots',
                    bigscales=True, wave=0.045),
    # ----- new in 1.4: Frostbite Shelf -----
    'capelin': D(depth=0.1, bl=0.8, hump=0.4, nose=1.55, ped=0.22, taper=1.05, tail='fork', tl=0.2, ts=0.11,
                 dorsal=(('soft', 0.44, 0.56, 0.06),), anal=(('soft', 0.62, 0.8, 0.035),), adipose=True, pect=0.09,
                 eye=0.05, ex=0.08, ey=0.2, iris='#e6eef6', sheen=True, lateral=False, wave=0.064),
    'polarcod': D(depth=0.12, bl=0.8, hump=0.36, nose=1.7, my=0.03, ped=0.16, taper=1.0, tail='fork', tl=0.17, ts=0.12,
                  dorsal=(('soft', 0.3, 0.42, 0.065), ('soft', 0.46, 0.6, 0.055), ('soft', 0.64, 0.76, 0.045)),
                  anal=(('soft', 0.5, 0.64, 0.045), ('soft', 0.66, 0.76, 0.035)), pect=0.1, pelvic=0.04,
                  eye=0.06, ex=0.09, ey=0.25, iris='#e8e0c0', chin=0.02, barbn=1, mouth='small', wave=0.058),
    'icefish': D(depth=0.11, bl=0.82, hump=0.3, nose=1.2, my=0.04, ped=0.14, taper=1.0, tail='trunc', tl=0.14, ts=0.11,
                 dorsal=(('soft', 0.28, 0.38, 0.08), ('long', 0.42, 0.82, 0.05)), anal=(('long', 0.48, 0.82, 0.045),),
                 pect=0.17, pw=0.6, pang=0.7, pelvic=0.08, eye=0.055, ex=0.14, ey=0.32, iris='#e8f0f8', mouth='under',
                 translucent=True, scales=False, dc='#2a2e36', pc='#2a2e36', wave=0.055),
    'sculpin': D(depth=0.17, bl=0.8, hump=0.32, nose=2.4, my=0.04, ped=0.3, taper=1.3, tail='round', tl=0.15, ts=0.12,
                 dorsal=(('spiny', 0.2, 0.42, 0.09, 9), ('soft', 0.44, 0.7, 0.07)), anal=(('soft', 0.54, 0.72, 0.06),),
                 pect=0.18, pw=0.7, pang=0.8, pelvic=0.05, eye=0.05, ex=0.12, ey=0.42, iris='#ffd23d', mouth='big',
                 cirri=True, pat='mottle', scales=False, wave=0.05),
    'toothfish': D(depth=0.15, bl=0.8, hump=0.36, nose=1.7, my=0.04, ped=0.2, taper=1.0, tail='trunc', tl=0.16, ts=0.13,
                   dorsal=(('spiny', 0.26, 0.4, 0.07, 8), ('long', 0.44, 0.82, 0.06)), anal=(('long', 0.48, 0.82, 0.055),),
                   pect=0.13, pw=0.4, pelvic=0.05, eye=0.04, ex=0.1, ey=0.3, iris='#c8d0e0', mouth='big', wave=0.05),
    'wolffish': D(depth=0.12, bl=0.84, hump=0.32, nose=2.2, my=0.06, ped=0.1, taper=1.0, tail='round', tl=0.12, ts=0.1,
                  dorsal=(('long', 0.2, 0.92, 0.05),), anal=(('long', 0.5, 0.92, 0.04),), pect=0.15, pw=0.5, pelvic=0,
                  eye=0.04, ex=0.11, ey=0.38, iris='#d8c8a0', mouth='fangs', pat='bars', scales=False, wave=0.07, wl=1.05),
    'sleepershark': D(depth=0.15, bl=0.82, hump=0.4, nose=2.2, my=-0.02, ped=0.12, taper=0.95, tail='shark', tl=0.2, ts=0.11,
                      dorsal=(('tri', 0.44, 0.52, 0.045), ('tri', 0.64, 0.7, 0.04)), anal=(), pect=0.11, pw=0.3, pang=0.55,
                      pswing=0.12, py=0.55, ps=0.28, pelvic=0.04, eye=0.018, ex=0.08, ey=0.15, iris='#9ab8c8', slits=True,
                      gs=0.2, mouth='shark', scales=False, lateral=False, wave=0.032, wl=0.75),
    'aurorachar': D(depth=0.15, bl=0.8, hump=0.38, nose=1.8, my=0.04, ped=0.22, taper=1.0, tail='emarg', tl=0.17, ts=0.14,
                    dorsal=(('soft', 0.34, 0.5, 0.09),), anal=(('soft', 0.66, 0.78, 0.06),), adipose=True, pect=0.12,
                    pelvic=0.06, eye=0.04, ex=0.1, ey=0.28, iris='#e8f0e0', mouth='big', pat='spots', sheen=True,
                    edge='#ffffff', wave=0.052),
    'glacierkoi': D(depth=0.15, bl=0.74, hump=0.36, nose=2.1, my=0.05, ped=0.38, tail='koi', tl=0.3, ts=0.16,
                    dorsal=(('long', 0.3, 0.72, 0.055),), anal=(('soft', 0.7, 0.8, 0.04),), pect=0.13, pw=0.42,
                    pelvic=0.07, eye=0.04, ex=0.1, ey=0.25, iris='#3a5a7a', barbels=0.2, pat='patches', bigscales=True,
                    wave=0.064),
    # ----- new in 1.4: Mariana Deep -----
    'flyingfish': D(depth=0.11, bl=0.8, hump=0.38, nose=1.7, ped=0.2, taper=1.0, tail='fork', tl=0.24, ts=0.15,
                    dorsal=(('soft', 0.6, 0.72, 0.05),), anal=(('soft', 0.62, 0.74, 0.04),), pect=0.5, pw=0.2, pang=0.06,
                    pswing=0.1, py=0.28, ps=0.36, pelvic=0.12, eye=0.06, ex=0.09, ey=0.25, iris='#e8f0ff', sheen=True,
                    lateral=False, wave=0.05),
    'bigscale': D(depth=0.17, bl=0.8, hump=0.4, nose=2.0, ped=0.25, taper=1.1, tail='fork', tl=0.16, ts=0.12,
                  dorsal=(('soft', 0.36, 0.52, 0.06),), anal=(('soft', 0.64, 0.76, 0.04),), pect=0.08, pelvic=0.04,
                  eye=0.05, ex=0.1, ey=0.3, iris='#c8a080', bigscales=True, mouth='big', wave=0.055),
    'tripodfish': D(depth=0.12, bl=0.84, hump=0.3, nose=1.9, my=0.04, ped=0.1, taper=1.1, tail='fork', tl=0.15, ts=0.11,
                    dorsal=(('soft', 0.3, 0.42, 0.07),), anal=(('long', 0.5, 0.86, 0.04),), pect=0.2, pw=0.25, pang=-0.6,
                    pelvic=0.05, filaments=True, eye=0.022, ex=0.1, ey=0.28, iris='#c8d0d8', mouth='small', wave=0.05),
    'hadalsnail': D(depth=0.2, bl=0.84, hump=0.25, nose=3.0, my=0.02, ped=0.08, taper=0.7, tail='round', tl=0.12, ts=0.06,
                    dorsal=(('long', 0.3, 0.94, 0.05),), anal=(('long', 0.36, 0.94, 0.05),), pect=0.12, pw=0.7, pang=1.0,
                    pelvic=0, eye=0.035, ex=0.09, ey=0.35, iris='#30202a', mouth='small', translucent=True, scales=False,
                    lateral=False, wave=0.07, wl=1.0),
    'cookiecutter': D(depth=0.12, bl=0.82, hump=0.4, nose=2.6, my=0.02, ped=0.14, taper=0.9, tail='shark', tl=0.18, ts=0.12,
                      dorsal=(('tri', 0.58, 0.64, 0.04), ('tri', 0.68, 0.74, 0.035)), anal=(), pect=0.08, pelvic=0.03,
                      eye=0.065, ex=0.1, ey=0.3, iris='#7fffb0', slits=True, mouth='small', scales=False, lateral=False, wave=0.05),
    'swallower': D(depth=0.13, bl=0.82, hump=0.3, nose=1.5, my=0.06, ped=0.12, taper=1.0, tail='fork', tl=0.15, ts=0.11,
                   dorsal=(('long', 0.4, 0.85, 0.04),), anal=(('long', 0.45, 0.85, 0.035),), pect=0.07, pelvic=0,
                   eye=0.03, ex=0.1, ey=0.3, iris='#8090a0', mouth='fangs', bot=1.7, scales=False, wave=0.06),
    'tonguefish': D(depth=0.2, bl=0.88, hump=0.4, nose=2.2, ped=0.02, my=-0.04, taper=2.0, tail='none', tl=0.1, ts=0.02,
                    dorsal=(('fringe', 0.08, 0.98, 0.04),), anal=(('fringe', 0.25, 0.98, 0.035),), pect=0, pelvic=0,
                    eye=0.028, ex=0.09, ey=0.62, eyes=2, iris='#d8c890', mouth='small', pat='spots', wave=0.05, wl=1.1),
    'lizardfish': D(depth=0.11, bl=0.84, hump=0.3, nose=1.4, my=0.03, ped=0.14, taper=1.0, tail='fork', tl=0.16, ts=0.12,
                    dorsal=(('tri', 0.34, 0.46, 0.09),), anal=(('soft', 0.7, 0.8, 0.04),), adipose=True, pect=0.1, pelvic=0.08,
                    eye=0.04, ex=0.1, ey=0.32, iris='#d8e880', mouth='fangs', wave=0.05),
    'faceless': D(depth=0.13, bl=0.86, hump=0.3, nose=2.6, my=0.08, ped=0.05, taper=1.6, tail='round', tl=0.1, ts=0.06,
                  dorsal=(('long', 0.3, 0.95, 0.04),), anal=(('long', 0.45, 0.95, 0.035),), pect=0.08, pelvic=0,
                  eye=0.006, ex=0.1, ey=0.35, iris='#c8b8b0', mouth='under', scales=False, wave=0.07, wl=1.0),
    'megamouth': D(depth=0.16, bl=0.82, hump=0.42, nose=2.8, my=0.0, ped=0.12, taper=0.95, tail='shark', tl=0.22, ts=0.13,
                   dorsal=(('tri', 0.42, 0.5, 0.06), ('tri', 0.66, 0.72, 0.04)), anal=(('tri', 0.7, 0.76, 0.03),), pect=0.15,
                   pw=0.3, pang=0.55, pswing=0.12, py=0.55, ps=0.28, pelvic=0.04, eye=0.022, ex=0.1, ey=0.25, iris='#b8c0c8',
                   slits=True, gs=0.22, mouth='big', scales=False, lateral=False, wave=0.035, wl=0.75),
    'goblinshark': D(depth=0.12, bl=0.82, hump=0.36, nose=1.6, my=0.03, ped=0.12, taper=0.95, tail='shark', tl=0.24, ts=0.12,
                     dorsal=(('tri', 0.46, 0.54, 0.05), ('tri', 0.66, 0.72, 0.045)), anal=(('tri', 0.7, 0.76, 0.04),), pect=0.12,
                     pw=0.3, pang=0.55, pswing=0.12, py=0.55, ps=0.28, pelvic=0.05, eye=0.022, ex=0.13, ey=0.3,
                     iris='#8aa0b0', slits=True, gs=0.22, mouth='fangs', bill=0.16, scales=False, lateral=False, wave=0.04, wl=0.75),
    'abyssangel': D(depth=0.26, bl=0.72, hump=0.42, nose=1.9, my=0.05, ped=0.16, tail='lyre', tl=0.24, ts=0.18,
                    dorsal=(('trail', 0.22, 0.75, 0.26),), anal=(('trail', 0.44, 0.75, 0.24),), pect=0.09,
                    pelvic=0.05, filaments=True, eye=0.045, ex=0.12, ey=0.3, iris='#ffffff', translucent=True,
                    scales=False, wave=0.045),
}

# special painters
SPECIAL = {
    'puffer': D(kind='puffer', spines=16, dots=True, brow=True),
    'magmapuff': D(kind='puffer', spines=18, cracks=True, brow=True),
    'seahorse': D(kind='seahorse'),
    'manta': D(kind='ray', style='manta'),
    'lavaray': D(kind='ray', style='sting'),
    'cindereel': D(kind='eel', head='moray', th=0.05, wave=0.07, wl=1.3, d0=0.25, a0=0.5, fh=0.7),
    'coralwyrm': D(kind='eel', head='wyrm', th=0.055, wave=0.07, wl=1.15, d0=0.12, a0=0.5, fh=1.2),
    'gulper': D(kind='eel', head='gulper', th=0.03, wave=0.08, wl=1.4, d0=0.4, a0=0.55, fh=0.8),
    'dragonfish': D(kind='eel', head='dragon', th=0.042, wave=0.06, wl=1.2, d0=0.78, a0=0.74, fh=1.6),
    'seraph': D(kind='eel', head='seraph', th=0.05, wave=0.06, wl=1.1, d0=0.2, a0=0.6, fh=0.9),
    'siltpuffer': D(kind='puffer', spines=12, dots=True, brow=True),
    'lamplighterjelly': D(kind='jelly'),
    'vaultoctopus': D(kind='squid'),
    'gorgonray': D(kind='ray'),
    'hippocampus': D(kind='seahorse'),
    'nereidjelly': D(kind='jelly'),
    'moonshardray': D(kind='ray'),
    'vampsquid': D(kind='squid', style='vampire'),
    'giantsquid': D(kind='squid', style='giant'),
    'angler': D(kind='angler'),
    'voidjelly': D(kind='jelly'),
    'wolfeel': D(kind='eel', head='wolf', th=0.07, wave=0.06, wl=1.1, d0=0.08, a0=0.5, fh=0.55),
    'moray': D(kind='eel', head='moray', th=0.06, wave=0.07, wl=1.25, d0=0.06, a0=0.45, fh=0.7),
    'eelpout': D(kind='eel', head='pout', th=0.065, wave=0.07, wl=1.1, d0=0.15, a0=0.45, fh=0.6),
    'viperfish': D(kind='eel', head='viper', th=0.045, wave=0.06, wl=1.2, d0=0.22, a0=0.74, fh=0.8),
    'frilledshark': D(kind='eel', head='frill', th=0.055, wave=0.065, wl=1.15, d0=0.68, a0=0.6, fh=1.2),
    'oarfish': D(kind='eel', head='oar', th=0.04, wave=0.05, wl=1.5, d0=0.0, a0=0.98, fh=0.9),
    'leviathan': D(kind='leviathan'),
    'kraken': D(kind='squid', style='kraken'),
    'watcherbelow': D(kind='leviathan'),
    'vaultguardian': D(kind='angler'),
    'chasmphantom': D(kind='jelly'),
    'lanternlurker': D(kind='angler'),
    'krakenling': D(kind='squid', style='giant'),
    'pallidwhale': D(kind='whale'),
    'frostpout': D(kind='eel', head='pout', th=0.07, wave=0.07, wl=1.1, d0=0.15, a0=0.45, fh=0.6),
    'lumpsucker': D(kind='puffer', spines=12, dots=True),
    'glasssquid': D(kind='squid', style='vampire'),
    'skate': D(kind='ray', style='sting'),
    'colossalsquid': D(kind='squid', style='giant'),
    'frostmanta': D(kind='ray', style='manta'),
    'polarjelly': D(kind='jelly'),
    'ancientcrab': D(kind='crab'),
    'cuskeel': D(kind='eel', head='pout', th=0.06, wave=0.07, wl=1.15, d0=0.2, a0=0.45, fh=0.6),
    'dumbo': D(kind='squid', style='vampire'),
    'stareater': D(kind='eel', head='dragon', th=0.04, wave=0.06, wl=1.2, d0=0.78, a0=0.74, fh=1.6),
    'midnightmanta': D(kind='ray', style='manta'),
    'challenger': D(kind='eel', head='dragon', th=0.045, wave=0.055, wl=1.15, d0=0.78, a0=0.74, fh=1.8),
    'siphonophore': D(kind='eel', head='oar', th=0.035, wave=0.05, wl=1.6, d0=0.0, a0=0.98, fh=0.9),
    'bloop': D(kind='bloop'),
    'nessie': D(kind='nessie'),
    'kelpie': D(kind='seahorse'),
    'lamprey': D(kind='eel', head='pout', th=0.05, wave=0.07, wl=1.2, d0=0.1, a0=0.45, fh=0.5),
    'euroeel': D(kind='eel', head='moray', th=0.05, wave=0.07, wl=1.2, d0=0.08, a0=0.45, fh=0.6),
    'locheel': D(kind='eel', head='wolf', th=0.06, wave=0.06, wl=1.1, d0=0.1, a0=0.5, fh=0.6),
    'wispjelly': D(kind='jelly'),
}

_merged = {}


def look(sp):
    lk = _merged.get(sp.id)
    if lk is None:
        lk = D(BASE)
        lk.update(LOOKS.get(sp.id) or {})
        if sp.id in SPECIAL:
            lk.update(SPECIAL[sp.id])
        _merged[sp.id] = lk
    return lk


# How far a fish's picture can reach from its centre (fractions of L), for the canvas size.
def extent(sp):
    lk = look(sp)
    k = lk.kind
    if k == 'ray':
        return 0.98, 0.72
    if k == 'jelly':
        return 0.98, 0.62
    if k == 'squid':
        return 0.98, 0.42
    if k == 'seahorse':
        return 0.62, 0.62
    if k == 'angler':
        return 0.9, 0.78
    if k == 'puffer':
        return 0.75, 0.62
    if k == 'eel':
        return 0.62, {'seraph': 0.55, 'wyrm': 0.55, 'oar': 0.5, 'viper': 0.42, 'frill': 0.38, 'wolf': 0.38}.get(lk.head, 0.36)
    if k == 'leviathan':
        return 0.62, 0.32
    if k == 'whale':
        return 0.58, 0.24
    if k == 'crab':
        return 0.56, 0.34
    if k == 'bloop':
        return 0.6, 0.3
    if k == 'nessie':
        return 0.6, 0.4
    hh = max(lk.depth * max(lk.top, lk.bot) * (1 + lk.bump) + 0.1, 0.32)
    for f in (lk.dorsal or ()):
        hh = max(hh, lk.depth + f[3] * (1 + lk.flap) + 0.08)
    for f in (lk.anal or ()):
        hh = max(hh, lk.depth + f[3] * (1 + lk.flap) + 0.08)
    if lk.lionfan:
        hh = max(hh, 0.62)
    if lk.tail == 'shark':
        hh = max(hh, lk.ts * 1.5 + 0.08)
    wx = 0.98 if lk.tail in ('lyre', 'koi', 'flame', 'shark') or lk.filaments else 0.86
    if lk.bill:
        wx = max(wx, 0.5 + lk.bill + 0.06)
    return wx, hh + 0.06


# ===================================================================================
#  Bony fish
# ===================================================================================
class Body:
    """The side profile of a bony fish."""

    def __init__(self, L, lk):
        self.L, self.lk = L, lk
        self.Dp = lk.depth * L
        self.xn = 0.5 * L
        self.bl = lk.bl * L
        self.xp = self.xn - self.bl

    def f(self, s):
        lk = self.lk
        if s <= lk.hump:
            u = 1 - s / lk.hump
            v = 1 - u ** lk.nose
            return v ** (1 / lk.nose) if v > 0 else 0.0
        u = (s - lk.hump) / (1 - lk.hump)
        return lk.ped + (1 - lk.ped) * _pw(math.cos(min(1.0, u) * math.pi / 2), lk.taper)

    def mid(self, s):
        return self.Dp * self.lk.my * (1 - s) ** 2

    def X(self, s):
        return self.xn - s * self.bl

    def top(self, s):
        b = self.lk.bump * math.exp(-((s - 0.09) / 0.07) ** 2) if self.lk.bump else 0.0
        return self.X(s), self.mid(s) - self.Dp * (self.lk.top * self.f(s) + b)

    def bot(self, s):
        return self.X(s), self.mid(s) + self.Dp * self.lk.bot * self.f(s)

    def outline(self, n=34):
        ss = [0.5 - 0.5 * math.cos(math.pi * i / n) for i in range(n + 1)]
        top = [self.top(s) for s in ss]
        bot = [self.bot(s) for s in reversed(ss)]
        return Path().move(*top[0]).pts(top[1:]).pts(bot).close()


def _pw(x, e):
    return x ** e if x > 0 else 0.0


def _fin_height(kind, u, ph, extra=0):
    u = clamp(u, 0.0, 1.0)
    if kind == 'soft':
        h = _pw(math.sin(math.pi * u ** 0.8), 0.7)
    elif kind == 'tri':
        h = (u / 0.22) if u < 0.22 else _pw((1 - u) / 0.78, 0.65)
    elif kind in ('spiny', 'razor', 'lion'):
        n = extra or 9
        env = _pw(math.sin(math.pi * (0.12 + 0.88 * u)), 0.45)
        if kind == 'lion':
            env = (0.55 + 0.45 * _pw(math.sin(math.pi * u ** 0.7), 1))
        notch = 0.5 + 0.5 * math.cos(TAU * n * u)
        h = env * (1 - (0.42 if kind == 'lion' else 0.3) * (1 - notch))
    elif kind == 'sail':
        h = _pw(u / 0.16, 0.7) if u < 0.16 else _pw((1 - u) / 0.84, 1.25)
    elif kind == 'long':
        h = (0.72 + 0.28 * math.sin(math.pi * u)) * min(1, u / 0.06) * min(1, (1 - u) / 0.06)
    elif kind == 'contour':
        h = _pw(math.sin(math.pi * u), 0.4) * (0.75 + 0.25 * u)
    elif kind == 'trail':
        h = 0.15 + 0.85 * u ** 1.1
        if u > 0.85:
            h *= _pw(1 - (u - 0.85) / 0.15, 0.5)
    elif kind == 'fringe':
        h = min(1, u / 0.1) * min(1, (1 - u) / 0.12) * (1 + 0.22 * math.sin(2 * ph - u * 16))
    elif kind == 'flame':
        env = _pw(math.sin(math.pi * u), 0.6)
        h = env * (0.55 + 0.45 * abs(math.sin(u * math.pi * 5 + ph)))
    else:
        h = math.sin(math.pi * u)
    return max(0.0, h)


def _fin_lean(kind, u):
    return {'soft': 0.45, 'tri': 0.75, 'spiny': 0.4, 'razor': 0.55, 'lion': 0.55, 'sail': 1.15, 'long': 0.3,
            'contour': 0.4, 'trail': 0.3 + 1.6 * u * u, 'fringe': 0.15, 'flame': 0.85}.get(kind, 0.4)


def median_fin(B, side, spec, ph, L):
    """A dorsal (side=-1) or anal (side=+1) fin. Returns its outline, the spine/ray lines and its height range."""
    kind, s0, s1, h = spec[0], spec[1], spec[2], spec[3] * L
    extra = spec[4] if len(spec) > 4 else 0
    n = 26 if kind in ('spiny', 'razor', 'lion', 'flame', 'fringe') else 16
    base, outer, rays = [], [], []
    for i in range(n + 1):
        u = i / n
        s = lerp(s0, s1, u)
        bx, by = B.top(s) if side < 0 else B.bot(s)
        hh = h * _fin_height(kind, u, ph, extra) * (1 + 0.05 * math.sin(2 * ph - u * 6) + B.lk.flap * math.sin(ph + side * 1.2))
        ox = bx - hh * _fin_lean(kind, u)
        oy = by + side * hh
        base.append((bx, by - side * B.Dp * 0.18))
        outer.append((ox, oy))
    p = Path().move(*base[0]).pts(base[1:]).pts(outer[::-1]).close()
    m = extra if kind in ('spiny', 'razor', 'lion') else max(4, int((s1 - s0) * 30))
    for j in range(m + 1):
        u = (j + 0.5) / (m + 1) if kind not in ('spiny', 'razor', 'lion') else j / max(1, m)
        s = lerp(s0, s1, u)
        bx, by = B.top(s) if side < 0 else B.bot(s)
        hh = h * _fin_height(kind, u, ph, extra) * (1 + 0.05 * math.sin(2 * ph - u * 6))
        if kind in ('spiny', 'razor', 'lion'):
            env = _pw(math.sin(math.pi * (0.12 + 0.88 * u)), 0.45) if kind != 'lion' else (0.55 + 0.45 * _pw(math.sin(math.pi * u ** 0.7), 1))
            hh = h * env * (1.12 if kind == 'lion' else 1.05)
        rays.append(((bx, by), (bx - hh * _fin_lean(kind, u), by + side * hh)))
    yb = B.top((s0 + s1) / 2)[1] if side < 0 else B.bot((s0 + s1) / 2)[1]
    return p, rays, yb, yb + side * h


def paint_fin(c, p, W, rays, y0, y1, col, sil, alpha=0.88, edge=None, raycol=None, rayw=None, L=40, tip=None, both=False):
    if sil:
        fill(c, p, W, SIL)
        return
    if tip is not None and both:
        vgrad(c, p, W, y0, y1, [(0, al(tip, alpha)), (0.22, al(col, alpha * 0.95)), (0.78, al(col, alpha * 0.95)), (1, al(tip, alpha))])
    elif tip is not None:
        vgrad(c, p, W, y0, y1, [(0, al(dk(col, 0.15), alpha)), (0.62, al(col, alpha * 0.95)), (0.8, al(tip, alpha)), (1, al(tip, alpha))])
    else:
        vgrad(c, p, W, y0, y1, [(0, al(dk(col, 0.15), alpha)), (0.55, al(col, alpha * 0.9)), (1, al(lt(col, 0.35), alpha * 0.7))])
    if rays and L >= 22:
        rp = Path()
        for (a, b) in rays:
            rp.move(*a).line(*b)
        stroke(c, rp, W, raycol or al(dk(col, 0.35), 0.5), rayw or max(0.45, L * 0.006))
    if edge:
        stroke(c, p, W, al(edge, 0.85), max(0.6, L * 0.012))


def tail_shape(B, lk, ph, L):
    x0 = B.xp + 0.03 * L
    ytop, ybot, ym = B.top(1.0)[1], B.bot(1.0)[1], B.mid(1.0)
    tl = lk.tl * L
    ts = lk.ts * L * (0.84 + 0.16 * math.cos(ph - 1.1))
    sk = math.sin(ph - 1.1) * 0.06 * L          # the tail twists as it beats
    kind = lk.tail
    p = Path().move(x0, ytop)
    if kind == 'fork':
        p.quad(x0 - tl * 0.45, ym - ts * 0.62 + sk * 0.4, x0 - tl, ym - ts + sk)
        p.quad(x0 - tl * 0.72, ym - ts * 0.26 + sk * 0.6, x0 - tl * 0.5, ym + sk * 0.5)
        p.quad(x0 - tl * 0.72, ym + ts * 0.26 + sk * 0.6, x0 - tl, ym + ts + sk)
        p.quad(x0 - tl * 0.45, ym + ts * 0.62 + sk * 0.4, x0, ybot)
    elif kind == 'deep':
        p.quad(x0 - tl * 0.22, ym - ts * 0.8 + sk * 0.3, x0 - tl, ym - ts * 1.05 + sk)
        p.quad(x0 - tl * 0.6, ym - ts * 0.4 + sk * 0.6, x0 - tl * 0.38, ym + sk * 0.5)
        p.quad(x0 - tl * 0.6, ym + ts * 0.4 + sk * 0.6, x0 - tl, ym + ts * 1.05 + sk)
        p.quad(x0 - tl * 0.22, ym + ts * 0.8 + sk * 0.3, x0, ybot)
    elif kind == 'emarg':
        p.quad(x0 - tl * 0.5, ym - ts * 0.72 + sk * 0.4, x0 - tl, ym - ts + sk)
        p.quad(x0 - tl * 0.86, ym - ts * 0.38 + sk * 0.7, x0 - tl * 0.8, ym + sk * 0.6)
        p.quad(x0 - tl * 0.86, ym + ts * 0.38 + sk * 0.7, x0 - tl, ym + ts + sk)
        p.quad(x0 - tl * 0.5, ym + ts * 0.72 + sk * 0.4, x0, ybot)
    elif kind == 'round':
        p.bez(x0 - tl * 0.3, ym - ts * 1.05 + sk * 0.3, x0 - tl * 1.08, ym - ts * 0.85 + sk, x0 - tl, ym + sk)
        p.bez(x0 - tl * 1.08, ym + ts * 0.85 + sk, x0 - tl * 0.3, ym + ts * 1.05 + sk * 0.3, x0, ybot)
    elif kind == 'trunc':
        p.quad(x0 - tl * 0.5, ym - ts * 0.82 + sk * 0.4, x0 - tl * 0.98, ym - ts + sk)
        p.quad(x0 - tl * 1.06, ym + sk, x0 - tl * 0.98, ym + ts + sk)
        p.quad(x0 - tl * 0.5, ym + ts * 0.82 + sk * 0.4, x0, ybot)
    elif kind == 'lyre':
        p.quad(x0 - tl * 0.55, ym - ts * 0.8 + sk * 0.4, x0 - tl * 1.65, ym - ts * 1.35 + sk * 1.4)
        p.quad(x0 - tl * 0.85, ym - ts * 0.5 + sk * 0.7, x0 - tl * 0.72, ym + sk * 0.6)
        p.quad(x0 - tl * 0.85, ym + ts * 0.5 + sk * 0.7, x0 - tl * 1.65, ym + ts * 1.35 + sk * 1.4)
        p.quad(x0 - tl * 0.55, ym + ts * 0.8 + sk * 0.4, x0, ybot)
    elif kind == 'shark':
        p.quad(x0 - tl * 0.42, ym - ts * 0.85 + sk * 0.4, x0 - tl * 1.18, ym - ts * 1.5 + sk)
        p.quad(x0 - tl * 0.8, ym - ts * 0.45 + sk * 0.6, x0 - tl * 0.6, ym + ts * 0.08 + sk * 0.6)
        p.quad(x0 - tl * 0.66, ym + ts * 0.5 + sk * 0.7, x0 - tl * 0.5, ym + ts * 0.82 + sk)
        p.quad(x0 - tl * 0.22, ym + ts * 0.5 + sk * 0.3, x0, ybot)
    elif kind == 'clavus':
        m = 18
        for i in range(1, m + 1):
            t = i / m
            y = lerp(ytop - ts * 0.08, ybot + ts * 0.08, t)
            bulge = math.sin(math.pi * t) * tl * 0.55 + tl * 0.28 * abs(math.sin(t * math.pi * 5)) * (0.85 + 0.15 * math.sin(ph + t * 4))
            p.line(x0 - bulge - sk * 0.2, y + sk * 0.15)
    elif kind == 'none':
        p.quad(x0 - tl * 0.5, ym - ts + sk * 0.5, x0 - tl, ym + sk)
        p.quad(x0 - tl * 0.5, ym + ts + sk * 0.5, x0, ybot)
    elif kind == 'coel':
        p.bez(x0 - tl * 0.3, ym - ts * 1.0 + sk * 0.3, x0 - tl * 0.95, ym - ts * 0.8 + sk, x0 - tl * 0.78, ym - ts * 0.16 + sk)
        p.quad(x0 - tl * 1.1, ym - ts * 0.2 + sk, x0 - tl * 1.32, ym + sk * 1.1)
        p.quad(x0 - tl * 1.1, ym + ts * 0.2 + sk, x0 - tl * 0.78, ym + ts * 0.16 + sk)
        p.bez(x0 - tl * 0.95, ym + ts * 0.8 + sk, x0 - tl * 0.3, ym + ts * 1.0 + sk * 0.3, x0, ybot)
    elif kind in ('koi', 'flame'):
        tipU = (x0 - tl, ym - ts + sk)
        tipD = (x0 - tl * 0.98, ym + ts + sk)
        notch = (x0 - tl * 0.5, ym + sk * 0.6)
        p.bez(x0 - tl * 0.25, ym - ts * 0.75, x0 - tl * 0.65, ym - ts * 1.1 + sk * 0.6, tipU[0], tipU[1])
        for lobe, (a, b) in enumerate(((tipU, notch), (notch, tipD))):
            m = 14
            for i in range(1, m + 1):
                t = i / m
                x = lerp(a[0], b[0], t)
                y = lerp(a[1], b[1], t)
                bulge = math.sin(math.pi * t) * tl * 0.14
                if kind == 'koi':
                    r = math.sin(math.pi * t) * tl * 0.06 * math.sin(2 * ph - t * 9 - lobe * 3)
                else:
                    r = math.sin(math.pi * t) * tl * (0.1 + 0.14 * abs(math.sin(t * math.pi * 3 + ph + lobe)))
                p.line(x - bulge - r, y)
        p.bez(x0 - tl * 0.65, ym + ts * 1.1 + sk * 0.6, x0 - tl * 0.25, ym + ts * 0.75, x0, ybot)
    else:
        p.quad(x0 - tl, ym - ts, x0 - tl * 0.6, ym)
        p.quad(x0 - tl, ym + ts, x0, ybot)
    p.close()
    pts = p.subs[0][0]
    rays = []
    m = len(pts) - 2
    for j in range(1, 8):
        q = pts[1 + int(j / 8 * m)]
        rays.append(((x0 - tl * 0.02, lerp(ytop, ybot, j / 8)), q))
    return p, rays, ym - ts, ym + ts


def pectoral(B, lk, ph, L, far=False):
    """A side fin that rows back and forth (the far one peeks out behind the body)."""
    s = lk.ps
    ax, ay = B.X(s), B.mid(s) + B.Dp * lk.py * B.f(s)
    Lp = lk.pect * L * (0.82 if far else 1.0)
    ang = lk.pang + lk.pswing * math.sin(ph + (2.2 if far else 0.9))
    dx, dy = -math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    wk = lk.pw * (0.72 + 0.28 * math.cos(ph + 0.9))
    sideA, sideB, rays = [], [], []
    m = 12
    for i in range(m + 1):
        u = i / m
        cx, cy = ax + dx * Lp * u, ay + dy * Lp * u
        w = Lp * wk * _pw(math.sin(math.pi * min(1.0, u ** 0.6)), 0.8) * (1 - 0.25 * u)
        sideA.append((cx + nx * w, cy + ny * w))
        sideB.append((cx - nx * w * 0.7, cy - ny * w * 0.7))
    p = Path().move(ax, ay).pts(sideA).pts(sideB[::-1]).close()
    for j in range(5):
        t = (j + 0.5) / 5
        ex = lerp(sideA[int(m * 0.85)][0], sideB[int(m * 0.85)][0], t)
        ey = lerp(sideA[int(m * 0.85)][1], sideB[int(m * 0.85)][1], t)
        rays.append(((ax, ay), (ex, ey)))
    return p, rays, ay, ay + Lp * 0.5


def lion_fans(B, lk, ph, L, far=False):
    """The lionfish's huge feathery pectoral fans: separate rays joined by a thin web."""
    s = 0.26
    ax, ay = B.X(s), B.mid(s) + B.Dp * 0.25
    R = lk.lionfan * L * (0.85 if far else 1.0)
    n = 11
    spread = 1.35 + 0.12 * math.sin(ph + (1.5 if far else 0))
    a0 = 0.18 + (0.15 if far else 0)
    webs, rays = Path(), []
    tips = []
    for k in range(n):
        u = k / (n - 1)
        a = a0 + u * spread + 0.06 * math.sin(2 * ph + k * 0.7)
        rr = R * (0.65 + 0.35 * math.sin(math.pi * (0.2 + 0.8 * u)))
        tips.append((ax - math.cos(a) * rr, ay + math.sin(a) * rr * 0.9))
    webs.move(ax, ay)
    for k, (tx, ty) in enumerate(tips):
        if k:
            px, py = tips[k - 1]
            webs.quad((px + tx) / 2 + (ax - (px + tx) / 2) * 0.22, (py + ty) / 2 + (ay - (py + ty) / 2) * 0.22, tx, ty, n=4)
        else:
            webs.line(tx, ty)
    webs.close()
    for t in tips:
        rays.append(((ax, ay), t))
    return webs, rays, tips


def paint_body(c, B, W, pal, sp, lk, ph, L, sil):
    body = B.outline()
    yT, yB = -B.Dp * lk.top + B.mid(0.3), B.Dp * lk.bot + B.mid(0.3)
    if sil:
        fill(c, body, W, SIL)
        return body
    col, belly = pal.col, pal.belly
    if lk.translucent:
        vgrad(c, body, W, yT, yB, [(0, al(dk(col, 0.2), 0.86)), (0.35, al(col, 0.72)), (0.7, al(mixc(col, belly, 0.6), 0.66)), (1, al(belly, 0.75))])
        bone = Path().move(B.X(0.18), B.mid(0.18) - Dp_(B) * 0.05)
        for i in range(1, 16):
            s_ = 0.18 + 0.8 * i / 15
            bone.line(B.X(s_), B.mid(s_) - Dp_(B) * 0.05)
        stroke(c, bone, W, (255, 255, 255, 60), max(0.6, L * 0.012), 'round')
        q = Path()
        for i in range(2, 15):
            s_ = 0.18 + 0.8 * i / 15
            q.move(B.X(s_), B.mid(s_) - Dp_(B) * 0.05).line(B.X(s_) - L * 0.012, B.mid(s_) - Dp_(B) * 0.45 * B.f(s_))
            q.move(B.X(s_), B.mid(s_) - Dp_(B) * 0.05).line(B.X(s_) - L * 0.012, B.mid(s_) + Dp_(B) * 0.4 * B.f(s_))
        stroke(c, q, W, (255, 255, 255, 34), max(0.5, L * 0.005))
        fill(c, Path().oval(B.X(0.3), B.mid(0.3) + Dp_(B) * 0.15, B.bl * 0.12, Dp_(B) * 0.3), W, (200, 60, 90, 70))
    else:
        vgrad(c, body, W, yT, yB, [(0, dk(col, 0.32)), (0.32, col), (0.62, mixc(col, belly, 0.6)), (1, belly)])
    body.to(c, W)
    c.clip_push()
    paint_pattern(c, B, W, pal, sp, lk, ph, L)
    if lk.scales or lk.bigscales:
        paint_scales(c, B, W, pal, lk, L)
    if lk.sheen:
        sh = Path()
        sh.move(B.X(0.12), B.mid(0.12) - B.Dp * 0.05)
        for i in range(1, 15):
            s = 0.12 + 0.86 * i / 14
            sh.line(B.X(s), B.mid(s) - B.Dp * 0.05 * B.f(s))
        for i in range(14, -1, -1):
            s = 0.12 + 0.86 * i / 14
            sh.line(B.X(s), B.mid(s) + B.Dp * 0.32 * B.f(s))
        sh.close()
        vgrad(c, sh, W, -B.Dp * 0.05, B.Dp * 0.32, [(0, (120, 230, 255, 70)), (0.5, (255, 170, 230, 55)), (1, (255, 255, 255, 0))], bands=6)
    # volume: a soft highlight on the back, shadow along the belly, a darker gill area
    fill(c, Path().oval(B.X(0.36), B.mid(0.36) - B.Dp * 0.55, B.bl * 0.3, B.Dp * 0.2), W, (255, 255, 255, 52))
    fill(c, Path().oval(B.X(0.3), B.mid(0.3) - B.Dp * 0.62, B.bl * 0.13, B.Dp * 0.07), W, (255, 255, 255, 80))
    fill(c, Path().oval(B.X(0.55), B.mid(0.55) + B.Dp * 1.05 * lk.bot, B.bl * 0.55, B.Dp * 0.32 * lk.bot), W, (0, 0, 0, 34))
    c.clip_pop()
    if lk.lateral and L >= 30:
        ln = Path().move(*_lat(B, lk.gs + 0.02))
        for i in range(1, 14):
            ln.line(*_lat(B, lk.gs + 0.02 + (0.98 - lk.gs) * i / 13))
        stroke(c, ln, W, al(dk(col, 0.35), 0.35), max(0.5, L * 0.006))
    if lk.outline:
        stroke(c, body, W, al(dk(col, 0.5), 0.55), max(0.55, L * 0.009))
    return body


def Dp_(B):
    return B.Dp


def _lat(B, s):
    return B.X(s), B.mid(s) - B.Dp * 0.38 * B.f(s)


def paint_scales(c, B, W, pal, lk, L):
    if L < 34:
        return
    big = bool(lk.bigscales)
    r = L * (0.034 if big else 0.022)
    col = al(dk(pal.col, 0.32), 0.3 if big else 0.16)
    rows = int(B.Dp * 2.2 / (r * 1.25)) + 1
    p = Path()
    for j in range(rows):
        yy = -B.Dp * 1.1 + j * r * 1.25
        off = (j % 2) * r
        x = B.X(0.22) - off
        while x > B.xp - r:
            p.move(x, yy - r * 0.85)
            for k in range(1, 7):
                a = -math.pi / 2 + math.pi * k / 6
                p.line(x - math.cos(a) * r * 0.75, yy + math.sin(a) * r * 0.85)
            x -= r * 1.8
    stroke(c, p, W, col, max(0.5, L * (0.008 if big else 0.005)))
    if big:
        fill_edge = Path()
        for j in range(rows):
            yy = -B.Dp * 1.1 + j * r * 1.25
            off = (j % 2) * r
            x = B.X(0.22) - off
            while x > B.xp - r:
                fill_edge.oval(x + r * 0.35, yy, r * 0.32, r * 0.5, n=8)
                x -= r * 2
        fill(c, fill_edge, W, (255, 255, 255, 26))


def _rng(sp):
    return random.Random(sum(ord(ch) * (i + 7) for i, ch in enumerate(sp.id)))


def paint_pattern(c, B, W, pal, sp, lk, ph, L):
    pat = lk.pat if lk.pat is not None else sp.pat
    pc = pal.patc
    rng = _rng(sp)
    Dp = B.Dp
    if pat in ('stripe', 'embstripe'):
        p = Path()
        top_, bot_ = [], []
        for i in range(17):
            s = 0.16 + 0.84 * i / 16
            top_.append((B.X(s), B.mid(s) - Dp * 0.02 * B.f(s) - Dp * 0.06))
            bot_.append((B.X(s), B.mid(s) + Dp * 0.16 * B.f(s) - Dp * 0.06))
        p.move(*top_[0]).pts(top_[1:]).pts(bot_[::-1]).close()
        if pat == 'embstripe':
            fill(c, p, W, al(pc, 0.45 + 0.25 * math.sin(ph)))
            q = Path().move(*top_[0])
            for (x, y), (_, y2) in zip(top_, bot_):
                q.line(x, (y + y2) / 2)
            stroke(c, q, W, al(lt(pc, 0.6), 0.9), max(0.6, L * 0.012))
        else:
            fill(c, p, W, al(pc, 0.55))
    elif pat == 'spotrow':
        p = Path()
        for k in range(6):
            s = 0.24 + k * 0.1
            p.oval(B.X(s), B.mid(s) - Dp * 0.18, L * 0.014, L * 0.014, n=10)
        fill(c, p, W, al(dk(pal.col, 0.55), 0.7))
        top_ = [(B.X(0.12 + 0.86 * i / 16), B.mid(0.12 + 0.86 * i / 16) - Dp * 0.05) for i in range(17)]
        q = Path().move(*top_[0]).pts(top_[1:])
        stroke(c, q, W, al(lt(pal.col, 0.5), 0.45), max(0.5, L * 0.01))
    elif pat == 'bars':
        p = Path()
        for k in range(10):
            s = 0.25 + k * 0.072
            x0, yt = B.top(s)
            ym = B.mid(s) - Dp * 0.12
            p.move(x0 + L * 0.01, yt - Dp * 0.2)
            steps = 5
            for j in range(1, steps + 1):
                t = j / steps
                p.line(x0 + (L * 0.022 if j % 2 else -L * 0.01), lerp(yt, ym, t))
        stroke(c, p, W, al(pc, 0.75), max(0.7, L * 0.02), 'round')
    elif pat == 'tuna':
        p = Path()
        for k in range(7):
            s = 0.3 + k * 0.08
            p.oval(B.X(s), B.mid(s) + Dp * 0.25, L * 0.012, Dp * 0.26, n=10)
        fill(c, p, W, (255, 255, 255, 60))
        q = Path().move(B.X(0.1), B.mid(0.1) - Dp * 0.15)
        for i in range(1, 15):
            s = 0.1 + 0.88 * i / 14
            q.line(B.X(s), B.mid(s) - Dp * 0.15 * B.f(s))
        stroke(c, q, W, al(lt(pal.col, 0.55), 0.6), max(0.6, L * 0.012))
    elif pat == 'spots':
        p = Path()
        for k in range(16 if L > 50 else 10):
            s = rng.uniform(0.1, 0.9)
            v = rng.uniform(-0.85, 0.7)
            r = rng.uniform(0.012, 0.028) * L
            p.oval(B.X(s), B.mid(s) + v * Dp * B.f(s), r, r * 0.9, n=10)
        fill(c, p, W, al(pc, 0.6))
    elif pat in ('clownbands', 'angelbands'):
        pos = (0.18, 0.5, 0.8) if pat == 'clownbands' else (0.22, 0.48)
        wid = (0.07, 0.085, 0.05) if pat == 'clownbands' else (0.05, 0.05)
        for s, w in zip(pos, wid):
            x = B.X(s)
            band = Path().move(x + w * L * 0.5, -Dp * 1.6).quad(x - w * L * 0.6 + w * L * 0.5, 0, x + w * L * 0.5, Dp * 1.6)
            band.line(x - w * L * 0.5, Dp * 1.6).quad(x - w * L * 1.6, 0, x - w * L * 0.5, -Dp * 1.6).close()
            if pat == 'clownbands':
                stroke(c, band, W, (20, 20, 20, 230), max(0.8, L * 0.016))
            fill(c, band, W, pc + (245,) if pat == 'clownbands' else al(pc, 0.9))
    elif pat == 'lionbands':
        p = Path()
        for k in range(15):
            s = 0.06 + k * 0.065
            x = B.X(s)
            w = L * 0.016
            p.move(x + w, -Dp * 1.4).quad(x - L * 0.03 + w, 0, x + w, Dp * 1.4).line(x - w, Dp * 1.4)
            p.quad(x - L * 0.03 - w, 0, x - w, -Dp * 1.4).close()
        fill(c, p, W, al(pc, 0.85))
    elif pat == 'eyespot':
        x, y = B.X(0.78), B.mid(0.78) - Dp * 0.45 * B.f(0.78) + Dp * 0.1
        fill(c, Path().oval(x, y, L * 0.05, L * 0.05), W, (255, 255, 255, 230))
        fill(c, Path().oval(x, y, L * 0.038, L * 0.038), W, (25, 25, 30, 240))
        p = Path()
        for k in range(6):
            s = 0.25 + k * 0.1
            p.move(B.X(s) + L * 0.03, -Dp * 1.2).line(B.X(s) - L * 0.05, Dp * 1.2)
        stroke(c, p, W, al(dk(pal.col, 0.3), 0.25), max(0.5, L * 0.008))
    elif pat == 'palette':
        p = Path()
        pts_t, pts_b = [], []
        for i in range(15):
            s = 0.24 + 0.6 * i / 14
            yc = B.mid(s) - Dp * (0.45 - 0.3 * math.sin(math.pi * (s - 0.24) / 0.6)) * B.f(s)
            w = Dp * (0.16 + 0.1 * math.sin(math.pi * (s - 0.24) / 0.6))
            pts_t.append((B.X(s), yc - w))
            pts_b.append((B.X(s), yc + w))
        p.move(*pts_t[0]).pts(pts_t[1:]).pts(pts_b[::-1]).close()
        fill(c, p, W, (13, 22, 52, 235))
        fill(c, Path().oval(B.X(0.62), B.mid(0.62) + Dp * 0.25, L * 0.07, Dp * 0.2), W, (13, 22, 52, 235))
    elif pat == 'patches':
        for (s, v, rx, ry) in ((0.2, -0.45, 0.13, 0.42), (0.47, -0.2, 0.15, 0.55), (0.72, -0.55, 0.1, 0.35), (0.12, 0.2, 0.06, 0.2)):
            p = Path()
            pts = []
            for i in range(18):
                a = TAU * i / 18
                wob = 1 + 0.18 * math.sin(a * 3 + s * 20) + 0.1 * math.sin(a * 5 + v * 7)
                pts.append((B.X(s) + math.cos(a) * rx * L * wob, B.mid(s) + v * Dp + math.sin(a) * ry * Dp * wob))
            p.move(*pts[0]).pts(pts[1:]).close()
            fill(c, p, W, al(pc, 0.95))
    elif pat == 'parrot':
        p = Path()
        for k in range(3):
            y = -Dp * (0.1 - k * 0.2)
            p.move(B.X(0.02), y).quad(B.X(0.1), y - Dp * 0.15, B.X(0.2), y + Dp * 0.05)
        stroke(c, p, W, al('#ff70b0', 0.8), max(0.7, L * 0.014), 'round')
        fill(c, Path().oval(B.X(0.55), B.mid(0.55) + Dp * 0.6, B.bl * 0.4, Dp * 0.35), W, (255, 140, 200, 60))
    elif pat == 'hex':
        r = L * 0.035
        p = Path()
        for j in range(-6, 7):
            for i in range(-1, 14):
                cx = B.X(0.04) - i * r * 1.72 - (j % 2) * r * 0.86
                cy = j * r * 1.5
                pts = [(cx + math.cos(TAU * k / 6 + math.pi / 6) * r * 0.93, cy + math.sin(TAU * k / 6 + math.pi / 6) * r * 0.93) for k in range(6)]
                p.move(*pts[0]).pts(pts[1:]).close()
        stroke(c, p, W, al(dk(pal.col, 0.5), 0.55), max(0.5, L * 0.008))
        fill(c, Path().oval(B.X(0.45), B.mid(0.45) - Dp * 0.3, B.bl * 0.25, Dp * 0.25), W, (255, 120, 60, 26))
    elif pat == 'facets':
        p = Path()
        for (s, v, w, hgt) in ((0.18, -0.5, 0.07, 0.35), (0.33, -0.55, 0.1, 0.3), (0.5, -0.45, 0.09, 0.3), (0.65, -0.4, 0.06, 0.25), (0.3, 0.2, 0.08, 0.2)):
            x, y = B.X(s), B.mid(s) + v * Dp
            p.move(x, y - hgt * Dp * 0.5).line(x - w * L * 0.5, y).line(x, y + hgt * Dp * 0.5).line(x + w * L * 0.5, y).close()
        fill(c, p, W, (230, 210, 255, 70))
        fill(c, Path().oval(B.X(0.4), B.mid(0.4) - Dp * 0.62, B.bl * 0.28, Dp * 0.08), W, (255, 255, 255, 120))
    elif pat == 'embers':
        p = Path()
        for k in range(12):
            s = rng.uniform(0.15, 0.85)
            v = rng.uniform(-0.7, 0.6)
            r = rng.uniform(0.01, 0.022) * L * (0.8 + 0.4 * abs(math.sin(ph + k)))
            p.oval(B.X(s), B.mid(s) + v * Dp * B.f(s), r, r, n=8)
        fill(c, p, W, (255, 236, 160, 200))
        fill(c, Path().oval(B.X(0.45), B.mid(0.45), B.bl * 0.4, Dp * 0.5), W, (255, 220, 120, 40))
    elif pat == 'photo':
        p = Path()
        for k in range(9):
            s = 0.18 + k * 0.085
            p.oval(B.X(s), B.mid(s) + Dp * 0.62 * B.f(s), L * 0.014, L * 0.014, n=8)
        for k in range(3):
            s = 0.2 + k * 0.17
            p.oval(B.X(s), B.mid(s) + Dp * 0.25 * B.f(s), L * 0.011, L * 0.011, n=8)
        fill(c, p, W, al(pc, 0.6 + 0.4 * (0.5 + 0.5 * math.sin(ph))))
    elif pat == 'hatchet':
        p = Path()
        for k in range(10):
            s = 0.2 + k * 0.05
            p.oval(B.X(s), B.bot(s)[1] - Dp * 0.18, L * 0.012, L * 0.016, n=8)
        fill(c, p, W, (140, 230, 255, 220))
        q = Path()
        for (s, v) in ((0.25, -0.1), (0.4, 0.3), (0.3, 0.8)):
            x, y = B.X(s), B.mid(s) + v * Dp
            q.move(x, y - Dp * 0.25).line(x - L * 0.06, y).line(x, y + Dp * 0.25).line(x + L * 0.05, y).close()
        fill(c, q, W, (255, 255, 255, 70))
    elif pat == 'pores':
        holes, rims = Path(), Path()
        for k in range(26 if L > 50 else 16):
            s = rng.uniform(0.12, 0.92)
            v = rng.uniform(-0.8, 0.75)
            r = rng.uniform(0.008, 0.017) * L
            x, y = B.X(s), B.mid(s) + v * Dp * B.f(s)
            rims.oval(x - r * 0.15, y - r * 0.2, r * 1.3, r * 1.2, n=10)
            holes.oval(x, y, r, r * 0.85, n=10)
        fill(c, rims, W, al(lt(pal.col, 0.35), 0.45))
        fill(c, holes, W, al(pc, 0.8))
    elif pat == 'ribs':
        q = Path().move(B.X(0.14), B.mid(0.14))
        for i in range(1, 17):
            s_ = 0.14 + 0.82 * i / 16
            q.line(B.X(s_), B.mid(s_) - Dp * 0.02)
        stroke(c, q, W, al(pc, 0.8), max(0.8, L * 0.011), 'round')
        p = Path()
        for k in range(12):
            s_ = 0.22 + k * 0.052
            x0, ym = B.X(s_), B.mid(s_)
            hh = Dp * 0.6 * B.f(s_)
            p.move(x0, ym).quad(x0 - L * 0.024, ym - hh * 0.6, x0 - L * 0.012, ym - hh)
            p.move(x0, ym).quad(x0 - L * 0.024, ym + hh * 0.6, x0 - L * 0.012, ym + hh)
        stroke(c, p, W, al(pc, 0.55), max(0.6, L * 0.0065), 'round')
    elif pat == 'mottle':
        for k in range(9):
            s = rng.uniform(0.1, 0.9)
            v = rng.uniform(-0.7, 0.45)
            rx, ry = rng.uniform(0.04, 0.08) * L, rng.uniform(0.25, 0.45) * Dp
            pts = []
            for i in range(14):
                a = TAU * i / 14
                wob = 1 + 0.25 * math.sin(a * 3 + k) + 0.12 * math.sin(a * 5 + k * 2)
                pts.append((B.X(s) + math.cos(a) * rx * wob, B.mid(s) + v * Dp + math.sin(a) * ry * wob))
            fill(c, Path().move(*pts[0]).pts(pts[1:]).close(), W, al(pc, 0.55))
        p = Path()
        for k in range(10):
            s = rng.uniform(0.15, 0.85)
            p.oval(B.X(s), B.mid(s) + rng.uniform(-0.6, 0.5) * Dp, L * 0.008, L * 0.008, n=8)
        fill(c, p, W, (255, 236, 200, 150))
    elif pat == 'wrasse':
        p = Path()
        for k in range(5):
            y0 = -Dp * (0.5 - k * 0.22)
            p.move(B.X(0.02), y0)
            for i in range(1, 9):
                t = i / 8
                p.line(B.X(0.02 + 0.2 * t), y0 + math.sin(t * 9 + k) * Dp * 0.06 + Dp * 0.1 * t)
        stroke(c, p, W, al(pc, 0.75), max(0.6, L * 0.008), 'round')
        q = Path()
        for j in range(-4, 5):
            yy = j * Dp * 0.22
            q.move(B.X(0.26), yy).line(B.X(0.92), yy + Dp * 0.06)
        stroke(c, q, W, al(lt(pal.col, 0.25), 0.35), max(0.5, L * 0.005))
    elif pat == 'scutes':
        p = Path()
        for row, (v, n_, sz) in enumerate(((-0.92, 11, 0.024), (-0.1, 14, 0.019), (0.78, 10, 0.016))):
            for k in range(n_):
                s = 0.2 + 0.72 * k / max(1, n_ - 1)
                x, y = B.X(s), B.mid(s) + v * Dp * B.f(s)
                r = sz * L * (1.05 - 0.4 * s)
                p.move(x + r, y).line(x, y - r * 0.75).line(x - r, y).line(x, y + r * 0.75).close()
        fill(c, p, W, al(pc, 0.9))
        stroke(c, p, W, al(dk(pc, 0.45), 0.7), max(0.5, L * 0.004))
    elif pat == 'trigger':
        sad = Path()
        pts_t, pts_b = [], []
        for i in range(13):
            s = 0.3 + 0.42 * i / 12
            pts_t.append(B.top(s))
            pts_b.append((B.X(s), B.mid(s) - Dp * (0.3 + 0.22 * math.sin(math.pi * i / 12)) * B.f(s)))
        sad.move(*pts_t[0]).pts(pts_t[1:]).pts(pts_b[::-1]).close()
        fill(c, sad, W, (255, 210, 61, 235))
        q = Path()
        for k in range(9):
            s = rng.uniform(0.34, 0.68)
            q.oval(B.X(s), B.mid(s) - Dp * rng.uniform(0.55, 0.85) * B.f(s), L * 0.01, L * 0.01, n=8)
        fill(c, q, W, (20, 24, 40, 230))
        p = Path()
        for k in range(12):
            s = rng.uniform(0.22, 0.86)
            p.oval(B.X(s), B.mid(s) + Dp * rng.uniform(0.15, 0.75) * B.f(s), L * 0.024, L * 0.024, n=12)
        fill(c, p, W, (250, 250, 250, 245))


def paint_face(c, B, W, pal, sp, lk, ph, L):
    """Gill cover, mouth, eyes and extras (whiskers, crown, beak, eye band...)."""
    Dp = B.Dp
    col = pal.col
    gs = lk.gs
    # gill cover (or a shark's gill slits), breathing a little
    gx = B.X(gs)
    br = math.sin(ph) * L * 0.006
    if lk.slits:
        sl = Path()
        for k in range(5):
            s_ = gs + 0.01 + k * 0.022
            x, yc = B.X(s_), B.mid(s_) + Dp * 0.05
            h = Dp * 0.34 * B.f(s_) * (1 - 0.07 * k)
            sl.move(x + L * 0.004, yc - h).quad(x - L * 0.008 - br * 0.6, yc, x + L * 0.003, yc + h)
        stroke(c, sl, W, al(dk(col, 0.5), 0.6), max(0.5, L * 0.006), 'round')
    else:
        g = Path().move(gx + L * 0.01, B.mid(gs) - Dp * 0.62 * B.f(gs)).quad(gx - L * 0.055 - br, B.mid(gs) + Dp * 0.1, gx + L * 0.005, B.mid(gs) + Dp * 0.8 * B.f(gs))
        stroke(c, g, W, al(dk(col, 0.45), 0.5), max(0.6, L * 0.011), 'round')
        stroke(c, Path().move(gx - L * 0.004, B.mid(gs) - Dp * 0.5 * B.f(gs)).quad(gx - L * 0.045 - br, B.mid(gs) + Dp * 0.1, gx - L * 0.002, B.mid(gs) + Dp * 0.7 * B.f(gs)), W,
               al(lt(col, 0.4), 0.35), max(0.5, L * 0.007), 'round')
    # mouth
    nx, ny = B.xn, B.mid(0.0)
    m = lk.mouth
    if m == 'big' or m == 'grouper':
        mo = Path().move(nx - L * 0.004, ny + Dp * 0.06).quad(nx - L * 0.06, ny + Dp * 0.12, nx - L * 0.11, ny + Dp * 0.3)
        stroke(c, mo, W, al(dk(col, 0.6), 0.85), max(0.7, L * 0.013), 'round')
        if m == 'grouper':
            jaw = Path().move(nx + L * 0.012, ny + Dp * 0.1).quad(nx - L * 0.02, ny + Dp * 0.5, nx - L * 0.12, ny + Dp * 0.42)
            stroke(c, jaw, W, al(dk(col, 0.55), 0.7), max(0.7, L * 0.012), 'round')
            stroke(c, Path().move(nx - L * 0.01, ny + Dp * 0.02).quad(nx - L * 0.05, ny - Dp * 0.05, nx - L * 0.1, ny + Dp * 0.12), W,
                   al(lt(col, 0.3), 0.5), max(0.6, L * 0.01), 'round')
    elif m == 'beak':
        bk = Path().move(nx + L * 0.012, ny - Dp * 0.08).quad(nx + L * 0.02, ny + Dp * 0.18, nx - L * 0.03, ny + Dp * 0.3)
        bk.line(nx - L * 0.045, ny - Dp * 0.18).close()
        fill(c, bk, W, (244, 240, 226))
        stroke(c, Path().move(nx + L * 0.016, ny + Dp * 0.06).line(nx - L * 0.04, ny + Dp * 0.06), W, (150, 150, 140), max(0.5, L * 0.007))
    elif m == 'snout':
        stroke(c, Path().move(nx, ny).line(nx - L * 0.02, ny + Dp * 0.04), W, al(dk(col, 0.6), 0.8), max(0.5, L * 0.009))
    elif m == 'fangs':
        gape = Dp * (0.06 + 0.05 * math.sin(ph))
        mo = Path().move(nx + L * 0.012, ny - Dp * 0.06).quad(nx - L * 0.06, ny + Dp * 0.02, nx - L * 0.15, ny + Dp * 0.2)
        mo.line(nx - L * 0.13, ny + Dp * 0.32 + gape).quad(nx - L * 0.04, ny + Dp * 0.42 + gape, nx + L * 0.025, ny + Dp * 0.22 + gape).close()
        fill(c, mo, W, (36, 8, 12))
        teeth = Path()
        for k, ln in enumerate((0.42, 0.22, 0.34, 0.18, 0.26)):
            t = (k + 0.5) / 5
            x = lerp(nx + L * 0.008, nx - L * 0.12, t)
            y = lerp(ny - Dp * 0.04, ny + Dp * 0.18, t)
            teeth.move(x - L * 0.006, y).line(x - L * 0.001, y + Dp * ln).line(x + L * 0.004, y).close()
            yb = lerp(ny + Dp * 0.24, ny + Dp * 0.36, t) + gape
            teeth.move(x - L * 0.005, yb).line(x, yb - Dp * ln * 0.9).line(x + L * 0.005, yb).close()
        fill(c, teeth, W, (245, 240, 225))
    elif m == 'under':
        jaw = Path().move(nx + L * 0.035, ny + Dp * 0.1).quad(nx - L * 0.05, ny + Dp * 0.32, nx - L * 0.15, ny + Dp * 0.3)
        jaw.line(nx - L * 0.14, ny + Dp * 0.12).quad(nx - L * 0.05, ny + Dp * 0.06, nx + L * 0.035, ny + Dp * 0.1).close()
        fill(c, jaw, W, dk(col, 0.25))
        teeth = Path()
        for k in range(7):
            x = nx + L * 0.02 - k * L * 0.019
            teeth.move(x - L * 0.004, ny + Dp * 0.1).line(x, ny - Dp * 0.06).line(x + L * 0.004, ny + Dp * 0.1).close()
        fill(c, teeth, W, (240, 240, 235))
        stroke(c, Path().move(nx + L * 0.03, ny + Dp * 0.08).line(nx - L * 0.14, ny + Dp * 0.12), W, al(dk(col, 0.6), 0.8), max(0.5, L * 0.006))
    elif m == 'lips':
        lc = _c(lk.lipcol) if lk.lipcol else dk(col, 0.15)
        fill(c, Path().oval(nx - L * 0.012, ny + Dp * 0.02, L * 0.026, Dp * 0.16, n=14), W, lc)
        fill(c, Path().oval(nx - L * 0.014, ny + Dp * 0.18, L * 0.022, Dp * 0.12, n=14), W, dk(lc, 0.12))
        stroke(c, Path().move(nx + L * 0.008, ny + Dp * 0.1).line(nx - L * 0.035, ny + Dp * 0.11), W, al(dk(lc, 0.55), 0.8), max(0.5, L * 0.006))
    elif m == 'shark':
        mo = Path().move(nx - L * 0.035, ny + Dp * 0.5).quad(nx - L * 0.07, ny + Dp * 0.62, nx - L * 0.11, ny + Dp * 0.52)
        stroke(c, mo, W, al(dk(col, 0.6), 0.85), max(0.6, L * 0.007), 'round')
        fill(c, Path().oval(nx - L * 0.01, ny + Dp * 0.12, L * 0.005, L * 0.004, n=8), W, al(dk(col, 0.6), 0.8))
    elif m == 'bristle':
        mo = Path().move(nx, ny + Dp * 0.02).line(nx - L * 0.13, ny + Dp * 0.28)
        stroke(c, mo, W, al(dk(col, 0.7), 0.95), max(0.6, L * 0.009), 'round')
        tb = Path()
        for k in range(9):
            t = (k + 0.5) / 9
            x, y = lerp(nx, nx - L * 0.13, t), lerp(ny + Dp * 0.02, ny + Dp * 0.28, t)
            tb.move(x, y).line(x + L * 0.002, y - Dp * 0.09)
        stroke(c, tb, W, (220, 230, 240, 200), max(0.4, L * 0.003))
    else:
        mo = Path().move(nx - L * 0.002, ny + Dp * 0.06).quad(nx - L * 0.02, ny + Dp * 0.2, nx - L * 0.042, ny + Dp * 0.09)
        stroke(c, mo, W, al(dk(col, 0.6), 0.85), max(0.55, L * 0.009), 'round')
    # a sailfish's spear
    if lk.bill:
        bl_ = lk.bill * L
        sp_ = Path().move(nx - L * 0.02, ny - Dp * 0.16).line(nx + bl_, ny + Dp * 0.02).line(nx - L * 0.02, ny + Dp * 0.12).close()
        fill(c, sp_, W, dk(col, 0.3))
        stroke(c, Path().move(nx, ny - Dp * 0.08).line(nx + bl_ * 0.95, ny + Dp * 0.01), W, al(lt(col, 0.5), 0.6), max(0.5, L * 0.004))
    # chin barbels (cod, rattail, sturgeon)
    if lk.chin:
        nb = lk.barbn or 1
        for k in range(nb):
            bx_ = nx - L * (0.035 + 0.022 * k) + (L * 0.06 if nb > 1 else 0)
            by_ = ny + Dp * (0.42 if nb == 1 else 0.3)
            q = Path().move(bx_, by_)
            for i in range(1, 9):
                t = i / 8
                q.line(bx_ - lk.chin * L * 0.35 * t + math.sin(2 * ph + k + t * 3) * L * 0.006 * t, by_ + lk.chin * L * t)
            stroke(c, q, W, al(lt(col, 0.25), 0.95), max(0.5, L * 0.007), 'round')
    # eyebrow tufts (blenny, rockfish)
    if lk.cirri:
        ex_, ey_ = B.X(lk.ex), B.mid(lk.ex) - lk.ey * B.Dp * lk.top * max(0.3, B.f(lk.ex))
        rr = lk.eye * L * 1.18
        q = Path()
        for k in range(3):
            bx_ = ex_ - rr * 0.5 + k * rr * 0.45
            by_ = ey_ - rr * 0.95
            sw = math.sin(2 * ph + k) * L * 0.004
            q.move(bx_, by_).line(bx_ + sw - L * 0.004, by_ - L * 0.035)
            q.move(bx_ + sw * 0.5 - L * 0.002, by_ - L * 0.018).line(bx_ + sw + L * 0.008, by_ - L * 0.03)
        stroke(c, q, W, al(lt(pal.fin, 0.1), 0.95), max(0.6, L * 0.008), 'round')
    # barbels (whiskers!)
    if lk.barbels:
        bl_ = lk.barbels * L
        wc = (255, 248, 236, 245)
        for k, (ang, ln) in enumerate(((-0.28, 1.0), (0.05, 0.9), (0.32, 0.75))):
            sx, sy_ = nx - L * 0.03, ny + Dp * 0.12
            p = Path().move(sx, sy_)
            for i in range(1, 11):
                t = i / 10
                a_ = ang + 0.25 * t * t + math.sin(2 * ph + k * 1.3) * 0.06 * t
                p.line(sx + math.cos(a_) * bl_ * ln * t, sy_ + math.sin(a_) * bl_ * ln * t)
            stroke(c, p, W, wc, max(0.55, L * 0.0075), 'round')
        fill(c, Path().oval(nx - L * 0.03, ny + Dp * 0.12, L * 0.012, L * 0.01), W, al(dk(pal.col, 0.2), 0.6))
    # eye band
    if lk.eyeband:
        ex = B.X(lk.ex)
        band = Path().move(ex + L * 0.035, -Dp * 1.3).quad(ex + L * 0.01, 0, ex + L * 0.04, Dp * 1.3).line(ex - L * 0.03, Dp * 1.3)
        band.quad(ex - L * 0.05, 0, ex - L * 0.03, -Dp * 1.3).close()
        c.save()
        B.outline().to(c, W)
        c.clip_push()
        fill(c, band, W, (25, 22, 20, 230))
        c.clip_pop()
        c.restore()
    # eyes
    r = lk.eye * L * 1.18
    if r > 0:
        ex, ey = B.X(lk.ex), B.mid(lk.ex) - lk.ey * B.Dp * lk.top * max(0.3, B.f(lk.ex))
        x, y = W(ex, ey)
        if lk.eyes == 2:
            x2, y2 = W(ex - L * 0.06, ey - Dp * 0.32)
            eye(c, x2, y2, r * 0.92, pal.iris)
        eye(c, x, y, r, pal.iris, glow=pal.glow if sp.id in ('lantern',) else None)
        fill(c, Path().oval(ex + L * 0.035, ey + r * 0.2, L * 0.006, L * 0.006, n=8), W, al(dk(col, 0.6), 0.7))
    if lk.tentacles:
        ex, ey = B.X(lk.ex), B.mid(lk.ex) - lk.ey * B.Dp * B.f(lk.ex)
        p = Path().move(ex, ey - r).quad(ex + L * 0.02, ey - r - L * 0.06, ex - L * 0.02, ey - r - L * 0.1 + math.sin(ph) * L * 0.01)
        stroke(c, p, W, al(pal.fin, 0.9), max(0.6, L * 0.01), 'round')
        p = Path().move(nx - L * 0.02, ny + Dp * 0.2).quad(nx - L * 0.01, ny + Dp * 0.5, nx - L * 0.05, ny + Dp * 0.7)
        stroke(c, p, W, al(pal.fin, 0.8), max(0.5, L * 0.008), 'round')
    if lk.crown:
        cx, cy = B.top(0.15)
        cr = Path().move(cx - L * 0.06, cy + L * 0.004).line(cx - L * 0.065, cy - L * 0.035).line(cx - L * 0.045, cy - L * 0.018)
        cr.line(cx - L * 0.03, cy - L * 0.048).line(cx - L * 0.015, cy - L * 0.018).line(cx + L * 0.005, cy - L * 0.035).line(cx, cy).close()
        fill(c, cr, W, (255, 210, 61))
        stroke(c, cr, W, (184, 134, 42), max(0.5, L * 0.006))
        for jx in (-0.065, -0.03, 0.005):
            dot(c, W, cx + L * jx, cy - L * (0.035 if jx != -0.03 else 0.048), L * 0.007, (255, 79, 109))
    if lk.dome:
        hx, hy = B.X(0.12), B.mid(0.12) - Dp * 0.55
        fill(c, Path().oval(hx, hy, L * 0.13, Dp * 0.95, n=26), W, (190, 240, 255, 70))
        stroke(c, Path().oval(hx, hy, L * 0.13, Dp * 0.95, n=26), W, (220, 250, 255, 170), max(0.6, L * 0.008))
        for k, ox in enumerate((-0.02, 0.035)):
            tx, ty = hx + ox * L, hy + Dp * 0.25
            fill(c, Path().oval(tx, ty - Dp * 0.15, L * 0.018, Dp * 0.32, n=12), W, (60, 230, 120, 230))
            fill(c, Path().oval(tx, ty - Dp * 0.42, L * 0.016, L * 0.012, n=10), W, (170, 255, 190, 255))
        fill(c, Path().oval(hx + L * 0.03, hy - Dp * 0.5, L * 0.04, Dp * 0.15), W, (255, 255, 255, 120))
        r2 = L * 0.02
        x, y = W(B.X(0.05), B.mid(0.05) - Dp * 0.05)
        eye(c, x, y, r2, (40, 60, 80))


def bony(c, sp, L, ph, pal, sil, lk):
    B = Body(L, lk)
    W = Wave(L, ph, lk.wave, lk.wl)
    tipc = (_c(lk.tip) if pal.mut not in ('albino', 'gilded') else None) if lk.tip else None
    # far-side fins first, then dorsal/anal/tail, the body, the face, and the near fins on top
    if lk.lionfan:
        webs, rays, tips = lion_fans(B, lk, ph, L, far=True)
        if sil:
            fill(c, webs, W, SIL)
        else:
            fill(c, webs, W, al(dk(pal.fin, 0.2), 0.55))
            paint_spines(c, W, rays, dk(pal.patc, 0.1), L, 0.012)
    elif lk.pect:
        p, rays, y0, y1 = pectoral(B, lk, ph, L, far=True)
        paint_fin(c, p, W, rays, y0, y1, dk(pal.pect, 0.25), sil, alpha=0.8, L=L)
    for spec in (lk.dorsal or ()):
        p, rays, y0, y1 = median_fin(B, -1, spec, ph, L)
        kind = spec[0]
        if kind == 'lion':
            if not sil:
                fill(c, p, W, al(pal.fin, 0.45))
                paint_spines(c, W, rays, pal.patc, L, 0.011, bands=pal.col)
            else:
                fill(c, p, W, SIL)
        elif kind == 'razor':
            paint_fin(c, p, W, rays, y0, y1, pal.dors, sil, alpha=0.8, edge=pal.edge, raycol=al(lt(pal.dors, 0.4), 0.8), L=L)
        elif kind == 'sail' and lk.sailfire and not sil:
            vgrad(c, p, W, y0, y1, [(0, (255, 90, 20, 235)), (0.45, (255, 170, 50, 235)), (0.8, (255, 230, 120, 225)), (1, (255, 250, 210, 200))], bands=8)
            rp = Path()
            for a, b in rays:
                rp.move(*a).line(*b)
            stroke(c, rp, W, (255, 245, 210, 150), max(0.5, L * 0.006))
            spots = Path()
            for k, (a, b) in enumerate(rays[1:-1]):
                if k % 2 == 0:
                    spots.oval(lerp(a[0], b[0], 0.55), lerp(a[1], b[1], 0.55), L * 0.008, L * 0.008, n=8)
            fill(c, spots, W, (120, 20, 10, 170))
        else:
            paint_fin(c, p, W, rays, y0, y1, pal.dors, sil, edge=pal.edge, L=L, tip=tipc)
    for spec in (lk.anal or ()):
        p, rays, y0, y1 = median_fin(B, 1, spec, ph, L)
        paint_fin(c, p, W, rays, y0, y1, pal.dors, sil, edge=pal.edge, L=L, tip=tipc)
    if lk.filaments and not sil:
        for k, (s, side) in enumerate(((0.36, 1),)):
            bx, by = B.bot(s)
            p = Path().move(bx, by)
            for i in range(1, 12):
                t = i / 11
                p.line(bx - L * 0.32 * t, by + L * 0.2 * t + math.sin(2 * ph - t * 5) * L * 0.02 * t)
            stroke(c, p, W, al(pal.fin, 0.9), max(0.6, L * 0.01), 'round')
    if lk.finlets:
        fl = Path()
        for k in range(lk.finlets):
            s = 0.7 + 0.27 * k / max(1, lk.finlets - 1)
            for side in (-1, 1):
                bx, by = B.top(s) if side < 0 else B.bot(s)
                fl.move(bx + L * 0.012, by + side * -L * 0.003).line(bx - L * 0.022, by + side * L * 0.028).line(bx - L * 0.012, by + side * -L * 0.004).close()
        fill(c, fl, W, SIL if sil else pal.dors)
    if lk.adipose:
        bx, by = B.top(0.84)
        ad = Path().move(bx + L * 0.03, by + L * 0.004).quad(bx, by - L * 0.05, bx - L * 0.035, by + L * 0.004).close()
        fill(c, ad, W, SIL if sil else al(pal.dors, 0.9))
    tp, trays, ty0, ty1 = tail_shape(B, lk, ph, L)
    if lk.flamefins and not sil:
        vgrad(c, tp, W, ty0, ty1, [(0, (255, 120, 20, 230)), (0.5, (255, 220, 90, 235)), (1, (255, 120, 20, 230))], bands=8)
        rp = Path()
        for a, b in trays:
            rp.move(*a).line(*b)
        stroke(c, rp, W, (255, 245, 200, 120), max(0.5, L * 0.007))
    else:
        paint_fin(c, tp, W, trays, ty0, ty1, pal.tail, sil, alpha=0.95, edge=pal.edge, L=L, tip=tipc, both=True)
    if lk.scalpel and not sil:
        bx, by = B.X(0.93), B.mid(0.93)
        sc = Path().move(bx + L * 0.03, by).line(bx - L * 0.01, by - L * 0.012).line(bx - L * 0.02, by + L * 0.004).close()
        fill(c, sc, W, (255, 210, 61))
    if lk.pelvic:
        bx, by = B.bot(0.36)
        sw = math.sin(ph + 1.7) * L * 0.006
        pv = Path().move(bx + L * 0.02, by - L * 0.004).quad(bx - L * 0.01, by + lk.pelvic * L * 0.8 + sw, bx - lk.pelvic * L * 0.7, by + lk.pelvic * L + sw)
        pv.quad(bx - L * 0.01, by + L * 0.01, bx - L * 0.02, by - L * 0.002).close()
        fill(c, pv, W, SIL if sil else al(dk(pal.fin, 0.15), 0.9))
    if lk.keel and not sil:
        bx, by = B.X(0.94), B.mid(0.94)
        fill(c, Path().oval(bx, by, L * 0.035, L * 0.008), W, al(dk(pal.col, 0.4), 0.8))
    paint_body(c, B, W, pal, sp, lk, ph, L, sil)
    if sil:
        if lk.pect and not lk.lionfan:
            p, rays, y0, y1 = pectoral(B, lk, ph, L)
            fill(c, p, W, SIL)
        return
    paint_face(c, B, W, pal, sp, lk, ph, L)
    if lk.lionfan:
        webs, rays, tips = lion_fans(B, lk, ph, L)
        fill(c, webs, W, al(pal.fin, 0.5))
        paint_spines(c, W, rays, pal.patc, L, 0.013, bands=pal.col)
    elif lk.pect:
        p, rays, y0, y1 = pectoral(B, lk, ph, L)
        if lk.flamefins:
            vgrad(c, p, W, y0, y1, [(0, (255, 140, 30, 220)), (1, (255, 230, 120, 200))], bands=5)
        else:
            paint_fin(c, p, W, rays, y0, y1, pal.pect, sil, alpha=0.78, edge=pal.edge, L=L, tip=tipc)


def paint_spines(c, W, rays, col, L, w, bands=None):
    p = Path()
    for a, b in rays:
        p.move(*a).line(*b)
    stroke(c, p, W, col, max(0.6, L * w), 'round')
    if bands and L >= 30:
        q = Path()
        for a, b in rays:
            for t in (0.3, 0.55, 0.8):
                x, y = lerp(a[0], b[0], t), lerp(a[1], b[1], t)
                q.oval(x, y, L * w * 0.75, L * w * 0.75, n=6)
        fill(c, q, W, bands)


# ===================================================================================
#  Shared helpers for the special painters
# ===================================================================================
def fan(bx, by, ang, ln, wd, n=12, back=0.25):
    """A rounded fin fan from (bx, by) pointing along angle ang (0 = forward/+x, pi = backward)."""
    dx, dy = math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    edge = []
    for i in range(n + 1):
        a = -1 + 2 * i / n
        r = ln * (0.72 + 0.28 * math.sqrt(max(0.0, 1 - a * a)))
        edge.append((bx + dx * r + nx * wd * a, by + dy * r + ny * wd * a))
    p = Path().move(bx + nx * wd * back, by + ny * wd * back).pts(edge).line(bx - nx * wd * back, by - ny * wd * back).close()
    rays = [((bx, by), edge[j]) for j in range(1, n, 2)]
    return p, rays, edge


def spine_edges(pts, thick):
    n = len(pts) - 1
    tops, bots, nrm = [], [], []
    for i in range(n + 1):
        x0, y0 = pts[max(0, i - 1)]
        x1, y1 = pts[min(n, i + 1)]
        dx, dy = x0 - x1, y0 - y1
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dy / d, -dx / d
        t = thick(i / n)
        x, y = pts[i]
        tops.append((x + ux * t, y + uy * t))
        bots.append((x - ux * t, y - uy * t))
        nrm.append((ux, uy))
    return tops, bots, nrm


def head_cap(cx, cy, ux, uy, r, k=1.3, n=12):
    fx, fy = -uy, ux
    dx, dy = -ux, -uy
    out = []
    for i in range(n + 1):
        th = math.pi / 2 - math.pi * i / n
        out.append((cx + fx * math.cos(th) * r * k + dx * math.sin(th) * r, cy + fy * math.cos(th) * r * k + dy * math.sin(th) * r))
    return out


def rot(ang, ox=0.0, oy=0.0, bob=0.0):
    cs, sn = math.cos(ang), math.sin(ang)

    def W(x, y):
        x -= ox
        y -= oy
        return ox + x * cs - y * sn, oy + x * sn + y * cs + bob
    return W


def glow_dot(c, x, y, r, col, core=(255, 255, 255)):
    Path().oval(x, y, r * 2.2, r * 2.2, n=16).to(c).fill(al(col, 0.18))
    Path().oval(x, y, r * 1.45, r * 1.45, n=14).to(c).fill(al(col, 0.35))
    Path().oval(x, y, r, r, n=12).to(c).fill(al(col, 0.95))
    Path().oval(x - r * 0.2, y - r * 0.2, r * 0.45, r * 0.45, n=10).to(c).fill(al(core, 0.9))


def cracks_along(rng, pts, nrm, th, count=4, i0=2, i1=None):
    """Glowing fissures that wander along a body, with a few short branches."""
    n = len(pts) - 1
    i1 = i1 if i1 is not None else n - 4
    p = Path()
    for k in range(count):
        i = rng.randint(i0, max(i0, i1 - 7))
        v = rng.uniform(-0.55, 0.55)
        q = None
        for j in range(rng.randint(5, 10)):
            ii = min(n, i + j)
            v = clamp(v + rng.uniform(-0.32, 0.32), -0.78, 0.78)
            x, y = pts[ii]
            ux, uy = nrm[ii]
            t = th(ii / n)
            nq = (x + ux * t * v, y + uy * t * v)
            if q is None:
                p.move(*nq)
            else:
                p.line(*nq)
            if q is not None and rng.random() < 0.35 and ii < n:
                bv = clamp(v + rng.choice((-1, 1)) * rng.uniform(0.35, 0.7), -0.9, 0.9)
                x2, y2 = pts[ii + 1]
                ux2, uy2 = nrm[ii + 1]
                t2 = th((ii + 1) / n)
                p.move(*nq).line(x2 + ux2 * t2 * bv, y2 + uy2 * t2 * bv).move(*nq)
            q = nq
    return p


# ===================================================================================
#  Puffers
# ===================================================================================
def puffer(c, sp, L, ph, pal, sil, lk):
    breathe = 1 + 0.035 * math.sin(2 * ph)
    R = L * 0.3 * breathe
    cx, cy = L * 0.05, math.sin(ph) * L * 0.012
    W = _flat
    col, belly = pal.col, pal.belly
    # tail (beats twice per cycle)
    ta = math.pi + 0.35 * math.sin(2 * ph)
    tp, trays, _ = fan(cx - R * 0.95, cy, ta, R * 0.62, R * 0.42)
    # dorsal / anal / pectoral fins buzz fast
    dp, drays, _ = fan(cx - R * 0.55, cy - R * 0.78, math.pi * 1.25 + 0.25 * math.sin(3 * ph), R * 0.32, R * 0.2)
    ap, arays, _ = fan(cx - R * 0.55, cy + R * 0.78, math.pi * 0.75 - 0.25 * math.sin(3 * ph), R * 0.3, R * 0.18)
    if sil:
        for q in (tp, dp, ap):
            fill(c, q, W, SIL)
    else:
        paint_fin(c, tp, W, trays, cy - R * 0.5, cy + R * 0.5, pal.fin, False, L=L)
        paint_fin(c, dp, W, drays, cy - R, cy - R * 0.6, pal.fin, False, L=L)
        paint_fin(c, ap, W, arays, cy + R * 0.6, cy + R, pal.fin, False, L=L)
    # spines
    n = lk.spines or 16
    sp_ = Path()
    for k in range(n):
        a = -2.6 + 5.2 * k / (n - 1)
        if abs(a) < 0.45:
            continue
        ln = R * (0.2 + 0.05 * math.sin(2 * ph + k)) * (1.1 if lk.cracks else 1)
        bx, by = cx + math.cos(a) * R * 0.92, cy + math.sin(a) * R * 0.92
        tx, ty = cx + math.cos(a) * (R + ln), cy + math.sin(a) * (R + ln)
        nx, ny = -math.sin(a) * R * 0.06, math.cos(a) * R * 0.06
        sp_.move(bx + nx, by + ny).line(tx, ty).line(bx - nx, by - ny).close()
    fill(c, sp_, W, SIL if sil else dk(pal.fin, 0.1))
    body = Path().oval(cx, cy, R * 1.06, R, n=36)
    if sil:
        fill(c, body, W, SIL)
        return
    vgrad(c, body, W, cy - R, cy + R, [(0, dk(col, 0.25)), (0.45, col), (0.7, mixc(col, belly, 0.7)), (1, belly)])
    body.to(c, W)
    c.clip_push()
    rng = _rng(sp)
    if lk.cracks:
        fill(c, Path().oval(cx - R * 0.3, cy - R * 0.5, R * 0.5, R * 0.3), W, (60, 20, 10, 110))
        cr = Path()
        for k in range(6):
            a0 = rng.uniform(-2.6, 2.6)
            r0 = rng.uniform(0.2, 0.5)
            cr.move(cx + math.cos(a0) * R * r0, cy + math.sin(a0) * R * r0)
            for j in range(1, 4):
                a0 += rng.uniform(-0.6, 0.6)
                cr.line(cx + math.cos(a0) * R * (r0 + 0.2 * j), cy + math.sin(a0) * R * (r0 + 0.2 * j))
        flick = 0.65 + 0.35 * math.sin(ph)
        stroke(c, cr, W, al(pal.patc, 0.45 * flick), max(1.0, L * 0.03), 'round')
        stroke(c, cr, W, al(lt(pal.patc, 0.6), 0.95 * flick), max(0.6, L * 0.012), 'round')
    else:
        dots = Path()
        for k in range(12):
            a = rng.uniform(-2.9, -0.2)
            r = rng.uniform(0.25, 0.85) * R
            dots.oval(cx + math.cos(a) * r, cy + math.sin(a) * r, R * 0.06, R * 0.06, n=10)
        fill(c, dots, W, al(pal.patc, 0.55))
    fill(c, Path().oval(cx - R * 0.15, cy - R * 0.55, R * 0.6, R * 0.22), W, (255, 255, 255, 60))
    fill(c, Path().oval(cx, cy + R * 0.95, R * 0.9, R * 0.3), W, (0, 0, 0, 30))
    c.clip_pop()
    stroke(c, body, W, al(dk(col, 0.5), 0.55), max(0.6, L * 0.01))
    # face: blush, grumpy brow, big eye, puckered mouth
    ex, ey, er = cx + R * 0.45, cy - R * 0.22, R * 0.24
    fill(c, Path().oval(ex - R * 0.05, ey + R * 0.42, R * 0.16, R * 0.09), W, (255, 120, 140, 90))
    eye(c, ex, ey, er, pal.iris)
    if lk.brow:
        stroke(c, Path().move(ex - er * 1.1, ey - er * 1.55).line(ex + er * 1.0, ey - er * 1.05), W, al(dk(col, 0.6), 0.9), max(0.8, L * 0.022), 'round')
    mx, my = cx + R * 1.03, cy + R * 0.14
    fill(c, Path().oval(mx, my, R * 0.11, R * 0.13), W, lt(col, 0.35))
    fill(c, Path().oval(mx + R * 0.02, my, R * 0.055, R * 0.075), W, (90, 30, 30))
    pp, prays, _ = fan(cx + R * 0.1, cy + R * 0.18, math.pi * 0.85, R * (0.34 + 0.08 * abs(math.sin(3 * ph))), R * 0.2)
    paint_fin(c, pp, W, prays, cy, cy + R * 0.4, pal.fin, False, alpha=0.8, L=L)


# ===================================================================================
#  Seahorse
# ===================================================================================
def seahorse(c, sp, L, ph, pal, sil, lk):
    W = rot(-0.06 + 0.06 * math.sin(ph), 0, 0, math.sin(ph) * L * 0.02)
    col, belly = pal.col, pal.belly
    curl = 1 + 0.08 * math.sin(ph + 1)
    ctrl = [(0.02, -0.25), (0.03, -0.12), (0.045, 0.02), (0.01, 0.16), (-0.03, 0.27), (-0.02, 0.37), (0.04, 0.42 * curl),
            (0.09, 0.39 * curl), (0.085, 0.335)]
    pts = []
    for i in range(len(ctrl) - 1):
        p0 = ctrl[max(0, i - 1)]
        p1, p2 = ctrl[i], ctrl[i + 1]
        p3 = ctrl[min(len(ctrl) - 1, i + 2)]
        for j in range(6):
            t = j / 6
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            pts.append((x * L, y * L))
    pts.append((ctrl[-1][0] * L, ctrl[-1][1] * L))

    def th(s):
        if s < 0.12:
            return L * (0.055 + 0.32 * s)
        if s < 0.42:
            return L * (0.093 + 0.03 * math.sin(math.pi * (s - 0.12) / 0.3))
        return L * max(0.012, 0.085 * _pw(1 - (s - 0.42) / 0.58, 1.15))
    # the belly bulges forward: shift the spine forward where the torso is
    tops, bots, nrm = spine_edges(pts, th)
    # dorsal fin on the back, fluttering fast
    di = int(len(pts) * 0.3)
    bx, by = bots[di]
    dfin, drays, _ = fan(bx, by, math.pi + 0.15 * math.sin(4 * ph), L * 0.1, L * 0.07 * (0.8 + 0.2 * math.sin(4 * ph)))
    body = Path().move(*tops[0]).pts(tops[1:]).pts(bots[::-1]).close()
    head_c = (L * 0.06, -L * 0.3)
    head = Path().oval(head_c[0], head_c[1], L * 0.095, L * 0.072, rot=0.25)
    snout = Path().move(L * 0.1, -L * 0.33).line(L * 0.28, -L * 0.29).line(L * 0.285, -L * 0.255).line(L * 0.11, -L * 0.265).close()
    crown = Path().move(L * 0.0, -L * 0.34).line(L * 0.01, -L * 0.41).line(L * 0.03, -L * 0.37).line(L * 0.045, -L * 0.42).line(L * 0.06, -L * 0.36).close()
    if sil:
        for q in (dfin, body, head, snout, crown):
            fill(c, q, W, SIL)
        return
    paint_fin(c, dfin, W, drays, by - L * 0.05, by + L * 0.05, pal.fin, False, alpha=0.75, L=L)
    for q in (crown, snout, body, head):
        vgrad(c, q, W, -L * 0.42, L * 0.42, [(0, lt(col, 0.1)), (0.5, col), (1, dk(col, 0.25))])
    # belly and ridges
    bel = Path()
    for i in range(int(len(pts) * 0.08), int(len(pts) * 0.5)):
        x, y = tops[i]
        if i == int(len(pts) * 0.08):
            bel.move(x, y)
        else:
            bel.line(x, y)
    stroke(c, bel, W, al(belly, 0.8), max(1.0, L * 0.035), 'round')
    rg = Path()
    for i in range(2, len(pts) - 2, 2):
        (ax, ay), (bx2, by2) = tops[i], bots[i]
        rg.move(ax, ay).line(bx2, by2)
    stroke(c, rg, W, al(dk(col, 0.35), 0.45), max(0.5, L * 0.008))
    rg2 = Path()
    for i in range(1, len(pts) - 1, 2):
        x, y = bots[i]
        ux, uy = nrm[i]
        rg2.move(x, y).line(x - ux * L * 0.018, y - uy * L * 0.018)
    stroke(c, rg2, W, al(dk(col, 0.3), 0.8), max(0.6, L * 0.012), 'round')
    stroke(c, body, W, al(dk(col, 0.5), 0.5), max(0.5, L * 0.009))
    stroke(c, snout, W, al(dk(col, 0.5), 0.5), max(0.5, L * 0.008))
    # pectoral fin behind the head
    pf, prays, _ = fan(L * 0.0, -L * 0.24, math.pi * 0.85, L * 0.06 * (0.8 + 0.2 * math.sin(4 * ph + 1)), L * 0.04)
    paint_fin(c, pf, W, prays, -L * 0.28, -L * 0.2, pal.fin, False, alpha=0.75, L=L)
    x, y = W(L * 0.075, -L * 0.315)
    eye(c, x, y, L * 0.034, pal.iris)
    fill(c, Path().oval(L * 0.27, -L * 0.273, L * 0.015, L * 0.012), W, dk(col, 0.4))


# ===================================================================================
#  Rays
# ===================================================================================
def ray(c, sp, L, ph, pal, sil, lk):
    manta = lk.style == 'manta'
    W = _flat
    col, belly = pal.col, pal.belly
    span = L * (0.6 if manta else 0.44)
    k1 = 0.78 + 0.22 * math.cos(ph)
    k2 = 0.78 + 0.22 * math.cos(ph + 0.5)
    sw1 = math.sin(ph) * L * 0.05
    sw2 = math.sin(ph + 0.5) * L * 0.05
    hx = L * (0.3 if manta else 0.26)
    rx = -L * 0.2

    def wing(sign, k, swv, n=16):
        tipx, tipy = (L * 0.02 + swv if manta else -L * 0.02 + swv), sign * span * k
        lead, trail = [], []
        for i in range(n + 1):
            t = i / n
            if manta:
                x = lerp(hx - L * 0.02, tipx, t)
                y = sign * L * 0.08 + (tipy - sign * L * 0.08) * (1 - _pw(1 - t, 1.8))
                x += math.sin(math.pi * t) * L * 0.08
            else:
                a = math.pi / 2 * t
                x = hx - L * 0.02 - (hx - tipx) * (1 - math.cos(a)) + math.sin(math.pi * t) * L * 0.04
                y = sign * L * 0.06 + (tipy - sign * L * 0.06) * math.sin(a)
            lead.append((x, y))
        for i in range(1, n + 1):
            t = i / n
            x = lerp(tipx, rx, t)
            y = tipy + (sign * L * 0.08 - tipy) * (t ** (0.7 if manta else 1.2))
            x -= math.sin(math.pi * t) * L * (0.07 if manta else 0.02)
            y += math.sin(2 * ph - t * 4) * L * 0.012 * math.sin(math.pi * t)
            trail.append((x, y))
        return lead, trail
    l1, t1 = wing(-1, k1, sw1)
    l2, t2 = wing(1, k2, sw2)
    outline = Path().move(hx, -L * 0.07)
    outline.pts(l1).pts(t1).line(rx - L * 0.03, 0).pts([q for q in reversed(t2)]).pts(list(reversed(l2))).line(hx, L * 0.07)
    if manta:
        outline.quad(hx + L * 0.03, 0, hx, -L * 0.07)
    else:
        outline.quad(hx + L * 0.06, 0, hx, -L * 0.07)
    outline.close()
    # tail
    tail = Path().move(rx, -L * 0.012)
    tl = L * (0.55 if manta else 0.5)
    pts_t = []
    for i in range(1, 13):
        t = i / 12
        pts_t.append((rx - tl * t, math.sin(ph - t * 3) * L * 0.03 * t))
    tail.pts(pts_t)
    for i in range(11, -1, -1):
        t = i / 12
        x, y = (rx - tl * t, math.sin(ph - t * 3) * L * 0.03 * t)
        tail.line(x, y + L * 0.024 * _pw(1 - t, 1.5))
    tail.close()
    if sil:
        fill(c, tail, W, SIL)
        fill(c, outline, W, SIL)
        return
    fill(c, tail, W, dk(col, 0.25))
    if not manta:
        fill(c, Path().move(rx - tl * 0.35, -L * 0.006).line(rx - tl * 0.5, -L * 0.04).line(rx - tl * 0.42, -L * 0.004).close(), W, lt(pal.patc, 0.2))
    vgrad(c, outline, W, -span, span, [(0, dk(col, 0.35)), (0.42, lt(col, 0.1)), (0.5, lt(col, 0.16)), (0.58, lt(col, 0.1)), (1, dk(col, 0.35))])
    outline.to(c, W)
    c.clip_push()
    if manta:
        for sign in (-1, 1):
            ch = Path().move(hx - L * 0.06, sign * L * 0.05).line(hx - L * 0.12, sign * L * 0.2).quad(hx - L * 0.2, sign * L * 0.18, hx - L * 0.2, sign * L * 0.08).close()
            fill(c, ch, W, (240, 245, 255, 150))
        fill(c, Path().oval(rx + L * 0.05, 0, L * 0.12, L * 0.05), W, (0, 0, 0, 50))
    else:
        rng = _rng(sp)
        cr = Path()
        for k in range(7):
            a = rng.uniform(0, TAU)
            r0 = rng.uniform(0.02, 0.1) * L
            x0, y0 = math.cos(a) * r0, math.sin(a) * r0 * 2
            cr.move(x0, y0)
            for j in range(4):
                a += rng.uniform(-0.7, 0.7)
                x0 += math.cos(a) * L * 0.05
                y0 += math.sin(a) * L * 0.07
                cr.line(x0, y0)
        flick = 0.7 + 0.3 * math.sin(ph)
        stroke(c, cr, W, al(pal.patc, 0.35 * flick), max(1.0, L * 0.022), 'round')
        stroke(c, cr, W, al(lt(pal.patc, 0.5), 0.9 * flick), max(0.6, L * 0.008), 'round')
        dots = Path()
        for k in range(14):
            dots.oval(rng.uniform(-0.15, 0.2) * L, rng.uniform(-0.3, 0.3) * L, L * 0.01, L * 0.01, n=8)
        fill(c, dots, W, (255, 220, 120, 160))
    fill(c, Path().oval(L * 0.05, -span * 0.3, L * 0.15, span * 0.12), W, (255, 255, 255, 40))
    c.clip_pop()
    stroke(c, outline, W, al(lt(col, 0.35) if manta else lt(pal.patc, 0.3), 0.5), max(0.6, L * 0.007))
    if manta:
        for sign in (-1, 1):
            cf = Path().move(hx - L * 0.01, sign * L * 0.05).quad(hx + L * 0.07, sign * L * 0.09, hx + L * 0.09, sign * L * 0.04 + math.sin(ph) * L * 0.005)
            cf.quad(hx + L * 0.05, sign * L * 0.03, hx + L * 0.01, sign * L * 0.025).close()
            fill(c, cf, W, dk(col, 0.15))
        stroke(c, Path().move(hx + L * 0.01, -L * 0.03).quad(hx + L * 0.03, 0, hx + L * 0.01, L * 0.03), W, (20, 20, 30, 200), max(0.8, L * 0.008))
        for sign in (-1, 1):
            eye(c, hx - L * 0.005, sign * L * 0.06, L * 0.014, (40, 40, 60))
    else:
        for sign in (-1, 1):
            fill(c, Path().oval(hx - L * 0.05, sign * L * 0.045, L * 0.022, L * 0.02), W, dk(col, 0.25))
            eye(c, hx - L * 0.045, sign * L * 0.045, L * 0.016, pal.iris)
            fill(c, Path().oval(hx - L * 0.1, sign * L * 0.05, L * 0.012, L * 0.008), W, (40, 10, 5, 200))


# ===================================================================================
#  Eels and serpents (cinder eel, coral wyrm, gulper, dragonfish, molten seraph)
# ===================================================================================
def eel(c, sp, L, ph, pal, sil, lk):
    W = _flat
    head = lk.head
    n = 44
    amp, wl = lk.wave, lk.wl
    T = lk.th * L
    x_head = 0.44 * L if head != 'gulper' else 0.4 * L
    span = 0.9 * L
    pts = []
    for i in range(n + 1):
        s = i / n
        pts.append((x_head - s * span, amp * L * (0.18 + 0.82 * s) * math.sin(ph - TAU * wl * s)))

    def th(s):
        if head == 'gulper':
            return T * (1.6 - 1.2 * s) if s < 0.1 else T * max(0.08, _pw(1 - (s - 0.1) / 0.9, 1.3) * 0.9 + 0.06)
        base = T * (0.85 + 0.15 * min(1, s / 0.08))
        if s > 0.55:
            base *= max(0.06, 1 - _pw((s - 0.55) / 0.45, 1.5) * 0.94)
        return base
    tops, bots, nrm = spine_edges(pts, th)
    col, belly = pal.col, pal.belly
    # median fins along the back and belly, meeting at the pointed tail
    fh = lk.fh * T

    def fin_side(sign, s0):
        i0 = int(s0 * n)
        outer, base = [], []
        for i in range(i0, n + 1):
            s = i / n
            ux, uy = nrm[i]
            edge = tops[i] if sign < 0 else bots[i]
            hh = fh * min(1, (s - s0) / 0.08) * (1 - 0.6 * max(0.0, (s - 0.85) / 0.15)) * (1 + 0.18 * math.sin(2 * ph - s * 14))
            if head == 'wyrm' and sign < 0:
                hh *= 0.65 + 0.55 * abs(math.sin(s * math.pi * 9 + ph))
            k = -1 if sign < 0 else 1
            outer.append((edge[0] - k * ux * hh, edge[1] - k * uy * hh))
            base.append((pts[i][0], pts[i][1]))
        p = Path().move(*base[0]).pts(base[1:]).pts(outer[::-1]).close()
        return p, outer
    dfin, dout = fin_side(-1, lk.d0)
    afin, aout = fin_side(1, lk.a0)
    body = Path().move(*tops[0]).pts(tops[1:]).pts(bots[::-1])
    cx, cy = pts[0]
    ux, uy = nrm[0]
    cap = head_cap(cx, cy, ux, uy, th(0), 1.25 if head != 'gulper' else 1.0)
    body.pts(cap).close()
    # wings for the seraph, behind the body
    wings = []
    if head == 'seraph':
        for j, (s, size, phase_off) in enumerate(((0.16, 0.34, 0.0), (0.34, 0.26, 1.2))):
            i = int(s * n)
            bx, by = tops[i]
            flap = math.sin(ph + phase_off)
            for k in range(5):
                a = -math.pi * (0.62 + 0.11 * k) - 0.18 * flap
                ln = L * size * (1 - 0.13 * k)
                fx = bx + math.cos(a) * ln
                fy = by + math.sin(a) * ln * (0.85 + 0.15 * flap)
                feather = Path().move(bx, by).quad((bx + fx) / 2 + L * 0.03, (by + fy) / 2 - L * 0.02, fx, fy)
                feather.quad((bx + fx) / 2 - L * 0.02, (by + fy) / 2 + L * 0.03, bx, by).close()
                wings.append((feather, by, fy))
            i2 = int((s + 0.04) * n)
            bx, by = bots[i2]
            for k in range(3):
                a = math.pi * (0.68 + 0.1 * k) + 0.15 * flap
                ln = L * size * 0.55 * (1 - 0.15 * k)
                fx, fy = bx + math.cos(a) * ln, by + math.sin(a) * ln
                feather = Path().move(bx, by).quad((bx + fx) / 2 + L * 0.02, (by + fy) / 2 + L * 0.02, fx, fy)
                feather.quad((bx + fx) / 2 - L * 0.02, (by + fy) / 2 - L * 0.01, bx, by).close()
                wings.append((feather, by, fy))
    plumes = []
    if head == 'oar':
        bx0, by0 = tops[1]
        for k in range(6):
            a = -math.pi * (0.62 + 0.07 * k) + 0.1 * math.sin(ph + k * 0.8)
            ln = L * (0.16 - 0.015 * k)
            q = Path().move(bx0 - k * L * 0.008, by0)
            for i in range(1, 11):
                t = i / 10
                aa = a - 0.35 * t + math.sin(2 * ph - t * 4 + k) * 0.12 * t
                q.line(bx0 - k * L * 0.008 + math.cos(aa) * ln * t, by0 + math.sin(aa) * ln * t)
            plumes.append(q)
    if sil:
        for f, _, _ in wings:
            fill(c, f, W, SIL)
        for q in plumes:
            stroke(c, q, W, SIL, max(1.0, L * 0.008), 'round')
        fill(c, dfin, W, SIL)
        fill(c, afin, W, SIL)
        fill(c, body, W, SIL)
        return
    for q in plumes:
        stroke(c, q, W, al(pal.fin, 0.95), max(1.0, L * 0.009), 'round')
    for f, y0, y1 in wings:
        vgrad(c, f, W, min(y0, y1), max(y0, y1), [(0, (255, 120, 30, 220)), (0.6, (255, 210, 90, 230)), (1, (255, 250, 220, 200))])
    fcol = pal.fin
    if head == 'seraph':
        vgrad(c, dfin, W, -T * 3, T, [(0, (255, 250, 200, 230)), (1, (255, 120, 30, 230))])
        vgrad(c, afin, W, -T, T * 3, [(0, (255, 120, 30, 220)), (1, (255, 240, 180, 200))])
    else:
        fill(c, dfin, W, al(fcol, 0.85))
        fill(c, afin, W, al(fcol, 0.8))
        rp = Path()
        for i in range(int(lk.d0 * n), n + 1, 2):
            j = i - int(lk.d0 * n)
            if j < len(dout):
                rp.move(*pts[i]).line(*dout[j])
        stroke(c, rp, W, al(dk(fcol, 0.3), 0.4), max(0.5, L * 0.004))
    # body: base colour, a lighter belly band and a highlight along the back
    fill(c, body, W, col)
    belly_band = Path().move(*pts[2])
    belly_band.pts([((p[0] + b[0]) / 2 + (b[0] - p[0]) * 0.1, (p[1] + b[1]) / 2 + (b[1] - p[1]) * 0.1) for p, b in zip(pts[2:], bots[2:])])
    belly_band.pts(bots[2:][::-1]).close()
    fill(c, belly_band, W, mixc(col, belly, 0.75))
    back = Path().move(*tops[1])
    back.pts([(t[0] + (p[0] - t[0]) * 0.35, t[1] + (p[1] - t[1]) * 0.35) for t, p in zip(tops[1:-6], pts[1:-6])])
    back.pts(tops[1:-6][::-1]).close()
    fill(c, back, W, al(lt(col, 0.18), 0.6))
    hl = Path().move(*tops[3])
    hl.pts([(t[0] + (p[0] - t[0]) * 0.3, t[1] + (p[1] - t[1]) * 0.3) for t, p in zip(tops[3:n // 2], pts[3:n // 2])])
    stroke(c, hl, W, (255, 255, 255, 70), max(0.6, T * 0.25), 'round')
    rng = _rng(sp)
    flick = 0.65 + 0.35 * math.sin(ph)
    if sp.pat == 'cracks':
        cr = cracks_along(rng, pts, nrm, th, count=5)
        stroke(c, cr, W, al(pal.patc, 0.38 * flick), max(1.0, T * 0.6), 'round')
        stroke(c, cr, W, al(lt(pal.patc, 0.55), 0.95 * flick), max(0.6, T * 0.2), 'round')
    if sp.pat in ('spots',) or head == 'wyrm':
        dots = Path()
        for i in range(3, n - 6, 3):
            x, y = pts[i]
            ux, uy = nrm[i]
            o = th(i / n) * (0.45 if i % 2 else -0.1)
            dots.oval(x + ux * o, y + uy * o, T * 0.22, T * 0.2, n=10)
        fill(c, dots, W, al(pal.patc, 0.9))
    if sp.pat == 'dots' or head == 'dragon':
        dots = Path()
        for i in range(4, n - 4, 2):
            x, y = bots[i]
            ux, uy = nrm[i]
            dots.oval(x + ux * T * 0.3, y + uy * T * 0.3, T * 0.13, T * 0.13, n=8)
        fill(c, dots, W, al(pal.patc, 0.5 + 0.5 * flick))
    stroke(c, body, W, al(dk(col, 0.45), 0.6), max(0.6, L * 0.006))
    # heads
    hx, hy = pts[0]
    fx, fy = -uy, ux
    tip = (cx + fx * th(0) * 1.25, cy + fy * th(0) * 1.25)
    r0 = th(0)
    if head == 'moray':
        gape = L * 0.012 * (1 + math.sin(ph)) / 2
        jaw = Path().move(tip[0], tip[1] + r0 * 0.15).line(hx - L * 0.06, hy + r0 * 0.35).line(tip[0] - L * 0.01, tip[1] + r0 * 0.35 + gape).close()
        fill(c, jaw, W, (60, 18, 10))
        teeth = Path()
        for k in range(4):
            tx_ = tip[0] - L * 0.012 * (k + 1)
            teeth.move(tx_, tip[1] + r0 * 0.18).line(tx_ - L * 0.004, tip[1] + r0 * 0.32).line(tx_ - L * 0.008, tip[1] + r0 * 0.18).close()
        fill(c, teeth, W, (250, 240, 220))
        eye(c, hx - L * 0.01, hy - r0 * 0.45, r0 * 0.38, pal.iris if pal.mut else (255, 190, 80))
        fill(c, Path().oval(hx - L * 0.07, hy, r0 * 0.18, r0 * 0.24), W, (20, 8, 6, 200))
    elif head == 'wyrm':
        acc = pal.acc or (255, 210, 61)
        for k, (ang, ln) in enumerate(((-2.4, 0.13), (-2.75, 0.1))):
            bx, by = hx - L * 0.01 * k, hy - r0 * 0.7
            br = Path().move(bx, by)
            ex, ey = bx + math.cos(ang) * L * ln, by + math.sin(ang) * L * ln
            br.quad(bx - L * 0.02, by - L * 0.06, ex, ey)
            br.move(lerp(bx, ex, 0.55), lerp(by, ey, 0.55)).line(lerp(bx, ex, 0.55) + L * 0.03, lerp(by, ey, 0.55) - L * 0.035)
            br.move(lerp(bx, ex, 0.75), lerp(by, ey, 0.75)).line(lerp(bx, ex, 0.75) - L * 0.01, lerp(by, ey, 0.75) - L * 0.04)
            stroke(c, br, W, (255, 140, 190), max(1.0, L * 0.016), 'round')
            for q in ((ex, ey), (lerp(bx, ex, 0.55) + L * 0.03, lerp(by, ey, 0.55) - L * 0.035), (lerp(bx, ex, 0.75) - L * 0.01, lerp(by, ey, 0.75) - L * 0.04)):
                dot(c, W, q[0], q[1], L * 0.01, acc)
        for k in range(2):
            wh = Path().move(tip[0] - L * 0.01, tip[1] + r0 * 0.2)
            for i in range(1, 12):
                t = i / 11
                wh.line(tip[0] - L * 0.01 - L * 0.22 * t, tip[1] + r0 * 0.2 + L * 0.06 * t * (1 + k) + math.sin(2 * ph - t * 5 + k) * L * 0.02 * t)
            stroke(c, wh, W, al(acc, 0.9), max(0.6, L * 0.006), 'round')
        eye(c, hx + r0 * 0.1, hy - r0 * 0.3, r0 * 0.42, pal.glow or (255, 143, 207), glow=(255, 220, 240))
        fill(c, Path().oval(tip[0] - r0 * 0.25, tip[1] - r0 * 0.25, r0 * 0.1, r0 * 0.07), W, (80, 20, 40))
        stroke(c, Path().move(tip[0], tip[1] + r0 * 0.15).line(hx - r0 * 0.5, hy + r0 * 0.45), W, (90, 20, 50, 200), max(0.6, L * 0.005))
    elif head == 'gulper':
        gape = L * (0.11 + 0.03 * math.sin(ph))
        hinge = (hx - L * 0.15, hy - r0 * 0.1)
        up = (tip[0] + L * 0.05, tip[1] - r0 * 0.45)
        lo = (tip[0] + L * 0.035, tip[1] + gape)
        pouch = Path().move(*up).quad(tip[0] - L * 0.02, tip[1] - r0 * 0.5, *hinge).quad(hx - L * 0.06, hy + gape * 0.9, *lo).close()
        vgrad(c, pouch, W, tip[1] - r0, tip[1] + gape, [(0, (60, 20, 44)), (1, (120, 40, 80))])
        fill(c, Path().move(*up).quad(tip[0] - L * 0.01, tip[1] - r0 * 0.2, *hinge).quad(hx - L * 0.04, hy + gape * 0.35, tip[0] + L * 0.03, tip[1] + gape * 0.35).close(), W, (25, 8, 20, 200))
        stroke(c, Path().move(*up).quad(tip[0] - L * 0.02, tip[1] - r0 * 0.5, *hinge), W, al(lt(col, 0.35), 0.9), max(0.7, L * 0.008), 'round')
        stroke(c, Path().move(*hinge).quad(hx - L * 0.06, hy + gape * 0.9, *lo), W, al(lt(col, 0.35), 0.9), max(0.7, L * 0.008), 'round')
        eye(c, up[0] - L * 0.02, up[1] + r0 * 0.05, r0 * 0.28, (255, 120, 160))
        tx, ty = pts[-1]
        glow_dot(c, tx - L * 0.01, ty, L * 0.016, pal.glow or (255, 90, 138))
    elif head == 'dragon':
        jaw = Path().move(tip[0], tip[1]).line(hx - L * 0.05, hy + r0 * 0.2).line(tip[0] - L * 0.01, tip[1] + r0 * 0.7).close()
        fill(c, jaw, W, (10, 4, 14))
        fangs = Path()
        for k, ln in enumerate((0.9, 0.5, 0.7)):
            fxx = tip[0] - L * 0.012 * (k + 0.5)
            fangs.move(fxx, tip[1] + r0 * 0.05).line(fxx - L * 0.003, tip[1] + r0 * 0.05 + r0 * ln).line(fxx - L * 0.006, tip[1] + r0 * 0.05).close()
            fangs.move(fxx - L * 0.004, tip[1] + r0 * 0.75).line(fxx - L * 0.006, tip[1] + r0 * 0.75 - r0 * ln * 0.6).line(fxx - L * 0.009, tip[1] + r0 * 0.75).close()
        fill(c, fangs, W, (235, 240, 255))
        bar = Path().move(hx, hy + r0 * 0.8)
        bx, by = hx - L * 0.01, hy + r0 * 0.8
        for i in range(1, 10):
            t = i / 9
            bar.line(bx - L * 0.04 * t, by + L * 0.12 * t + math.sin(ph - t * 3) * L * 0.012 * t)
        stroke(c, bar, W, al(lt(col, 0.4), 0.9), max(0.5, L * 0.005), 'round')
        glow_dot(c, bx - L * 0.04, by + L * 0.12 + math.sin(ph - 3) * L * 0.012, L * 0.012, pal.glow or (92, 207, 255))
        glow_dot(c, hx - r0 * 0.6, hy - r0 * 0.1, r0 * 0.25, pal.glow or (92, 207, 255))
        eye(c, hx + r0 * 0.15, hy - r0 * 0.35, r0 * 0.36, (120, 200, 255), glow=pal.glow)
    elif head == 'wolf':
        mo = Path().move(tip[0] - r0 * 0.05, tip[1] + r0 * 0.28).quad(hx - L * 0.02, hy + r0 * 0.62, hx - L * 0.075, hy + r0 * 0.42)
        stroke(c, mo, W, (40, 30, 28, 230), max(0.8, L * 0.008), 'round')
        lips = Path().oval(tip[0] - r0 * 0.12, tip[1] + r0 * 0.12, r0 * 0.3, r0 * 0.34, n=12)
        fill(c, lips, W, al(lt(col, 0.18), 0.9))
        teeth = Path()
        for k, (ox, up) in enumerate(((0.008, 1), (0.024, 1), (0.016, -1))):
            tx_ = tip[0] - L * ox
            ty_ = tip[1] + r0 * 0.3
            teeth.move(tx_ - L * 0.005, ty_).line(tx_, ty_ + up * r0 * (0.42 if k == 0 else 0.3)).line(tx_ + L * 0.005, ty_).close()
        fill(c, teeth, W, (248, 244, 230))
        eye(c, hx - L * 0.005, hy - r0 * 0.48, r0 * 0.24, (190, 205, 220))
        fill(c, Path().oval(hx - L * 0.04, hy - r0 * 0.4, r0 * 0.12, r0 * 0.1).oval(hx - L * 0.07, hy - r0 * 0.1, r0 * 0.1, r0 * 0.09), W, al(dk(col, 0.4), 0.8))
    elif head == 'pout':
        fill(c, Path().oval(tip[0] - r0 * 0.15, tip[1] + r0 * 0.15, r0 * 0.34, r0 * 0.3, n=12), W, al(lt(col, 0.3), 0.95))
        stroke(c, Path().move(tip[0] - r0 * 0.02, tip[1] + r0 * 0.18).quad(hx - L * 0.01, hy + r0 * 0.5, hx - L * 0.04, hy + r0 * 0.38), W,
               (120, 70, 60, 220), max(0.6, L * 0.006), 'round')
        eye(c, hx + r0 * 0.05, hy - r0 * 0.42, r0 * 0.3, (60, 40, 40))
        stroke(c, Path().move(hx - L * 0.05, hy - r0 * 0.6).quad(hx - L * 0.065, hy, hx - L * 0.05, hy + r0 * 0.6), W, al(dk(col, 0.25), 0.6), max(0.6, L * 0.005), 'round')
    elif head == 'viper':
        jaw = Path().move(tip[0], tip[1]).line(hx - L * 0.06, hy + r0 * 0.25).line(tip[0] - L * 0.015, tip[1] + r0 * 0.85).close()
        fill(c, jaw, W, (6, 6, 14))
        fangs = Path()
        for k, ln in enumerate((1.5, 0.8, 1.2)):
            fxx = tip[0] - L * 0.01 * (k + 0.4)
            fangs.move(fxx, tip[1] + r0 * 0.02).line(fxx - L * 0.004, tip[1] + r0 * (0.05 + ln)).line(fxx - L * 0.007, tip[1] + r0 * 0.02).close()
            fangs.move(fxx - L * 0.004, tip[1] + r0 * 0.85).line(fxx - L * 0.002, tip[1] + r0 * (0.85 - ln * 0.9)).line(fxx - L * 0.009, tip[1] + r0 * 0.85).close()
        fill(c, fangs, W, (235, 245, 255))
        bx_, by_ = tops[int(lk.d0 * n)]
        rod_ = Path().move(bx_, by_)
        ex_, ey_ = hx + L * 0.03, hy - r0 * 3.2
        for i in range(1, 12):
            t = i / 11
            rod_.line(lerp(bx_, ex_, t) + math.sin(ph + t * 2) * L * 0.006 * t, lerp(by_, ey_, t) - math.sin(math.pi * t) * L * 0.03)
        stroke(c, rod_, W, al(lt(col, 0.4), 0.9), max(0.5, L * 0.005), 'round')
        glow_dot(c, ex_ + math.sin(ph + 2) * L * 0.006, ey_, L * 0.012, pal.glow or (127, 240, 255))
        glow_dot(c, hx - r0 * 0.5, hy - r0 * 0.05, r0 * 0.2, pal.glow or (127, 240, 255))
        eye(c, hx + r0 * 0.12, hy - r0 * 0.35, r0 * 0.4, (150, 220, 255), glow=pal.glow)
    elif head == 'frill':
        for k in range(6):
            i = 2 + k
            x, y = pts[i]
            ux2, uy2 = nrm[i]
            t = th(i / n)
            fr = Path().move(x + ux2 * t * 1.05, y + uy2 * t * 1.05)
            for j in range(1, 11):
                v = 1.05 - 2.1 * j / 10
                wig = math.sin(j * 2.2 + ph * 2 + k) * L * 0.006
                fr.line(x + ux2 * t * v - uy2 * 0 + wig, y + uy2 * t * v + wig * 0.3)
            stroke(c, fr, W, al(mixc(col, (200, 80, 70), 0.55), 0.85), max(0.8, L * 0.006), 'round')
        mo = Path().move(tip[0] + L * 0.004, tip[1] + r0 * 0.05).line(hx - L * 0.045, hy + r0 * 0.3).line(tip[0], tip[1] + r0 * 0.55).close()
        fill(c, mo, W, (40, 20, 18))
        teeth = Path()
        for k in range(5):
            t = (k + 0.5) / 5
            x, y = lerp(tip[0], hx - L * 0.04, t), lerp(tip[1] + r0 * 0.12, hy + r0 * 0.3, t)
            for dx_ in (-L * 0.003, 0.0, L * 0.003):
                teeth.move(x + dx_ - L * 0.0015, y).line(x + dx_, y + r0 * 0.14).line(x + dx_ + L * 0.0015, y).close()
        fill(c, teeth, W, (250, 248, 240))
        eye(c, hx + r0 * 0.05, hy - r0 * 0.45, r0 * 0.3, (90, 200, 120))
    elif head == 'oar':
        stroke(c, Path().move(tip[0], tip[1] + r0 * 0.25).line(hx - r0 * 0.4, hy + r0 * 0.45), W, (90, 100, 120, 220), max(0.5, L * 0.004))
        eye(c, hx + r0 * 0.2, hy - r0 * 0.15, r0 * 0.5, (200, 220, 240), glow=pal.glow)
        sheen = Path().move(*tops[2]).pts([(t[0] + (p_[0] - t[0]) * 0.5, t[1] + (p_[1] - t[1]) * 0.5) for t, p_ in zip(tops[2:n - 4], pts[2:n - 4])])
        stroke(c, sheen, W, (255, 255, 255, 90), max(0.6, T * 0.3), 'round')
    elif head == 'seraph':
        halo_y = hy - r0 * 2.3
        Path().oval(hx - r0 * 0.3, halo_y, r0 * 1.2, r0 * 0.38).to(c, W).stroke((255, 240, 160, 230), max(1.0, L * 0.01))
        Path().oval(hx - r0 * 0.3, halo_y, r0 * 1.2, r0 * 0.38).to(c, W).stroke((255, 255, 230, 120), max(1.5, L * 0.022))
        eye(c, hx + r0 * 0.15, hy - r0 * 0.3, r0 * 0.38, (255, 250, 220), glow=(255, 255, 255))
        stroke(c, Path().move(tip[0], tip[1] + r0 * 0.2).line(hx - r0 * 0.3, hy + r0 * 0.4), W, (180, 80, 20, 220), max(0.6, L * 0.005))


# ===================================================================================
#  Squid
# ===================================================================================
def squid(c, sp, L, ph, pal, sil, lk):
    W = _flat
    vamp = lk.style == 'vampire'
    col, belly = pal.col, pal.belly
    pulse = 1 + 0.06 * math.sin(ph)
    if vamp:
        mtip, mbase, mw = L * 0.36, L * 0.02, L * 0.12 * pulse
    else:
        mtip, mbase, mw = L * 0.48, L * 0.04, L * 0.07 * pulse
    hx = mbase - L * 0.06
    # arms
    arms = []
    kraken = lk.style == 'kraken'
    narms = 12 if kraken else 8
    for k in range(narms):
        u = k / (narms - 1)
        y0 = (u - 0.5) * (L * 0.09 if vamp else L * 0.06)
        ln = L * (0.34 if vamp else 0.36) * (0.85 + 0.15 * math.sin(u * math.pi))
        spread = (u - 0.5) * (L * 0.22 if vamp else L * 0.1) * (1.05 - 0.15 * math.sin(ph))
        pts_ = []
        for i in range(13):
            t = i / 12
            x = hx - L * 0.02 - ln * t
            y = y0 + spread * t + math.sin(ph - t * 4 + k * 0.8) * L * 0.025 * t
            pts_.append((x, y))
        arms.append(pts_)
    tentacles = []
    if not vamp:
        tentacle_sides = (-1, 1, -1, 1) if kraken else (-1, 1)
        for k, sgn in enumerate(tentacle_sides):
            pts_ = []
            for i in range(19):
                t = i / 18
                lane = k // 2
                reach = 0.43 + 0.07 * lane
                y0 = sgn * L * (0.02 + 0.025 * lane)
                pts_.append((hx - L * 0.02 - L * reach * t,
                             y0 + sgn * L * 0.05 * t + math.sin(ph - t * 5 + k) * L * 0.03 * t))
            tentacles.append(pts_)

    def arm_poly(pts_, w0):
        n = len(pts_) - 1
        top, bot, _ = spine_edges(pts_, lambda s: w0 * (1 - 0.85 * s))
        return Path().move(*top[0]).pts(top[1:]).pts(bot[::-1]).close()
    mantle = Path().move(mbase, -mw * 0.8)
    for i in range(1, 15):
        t = i / 14
        x = lerp(mbase, mtip, t)
        y = -mw * (_pw(math.sin(math.pi * (0.15 + 0.85 * t)), 0.6) if not vamp else math.sqrt(max(0.0, 1 - t ** 2.2)))
        mantle.line(x, y)
    for i in range(14, -1, -1):
        t = i / 14
        x = lerp(mbase, mtip, t)
        y = mw * (_pw(math.sin(math.pi * (0.15 + 0.85 * t)), 0.6) if not vamp else math.sqrt(max(0.0, 1 - t ** 2.2)))
        mantle.line(x, y)
    mantle.close()
    flap = 0.75 + 0.25 * math.cos(ph)
    if vamp:
        fins = [fan(mbase + (mtip - mbase) * 0.55, -mw * 0.82, -math.pi * 0.62, L * 0.11 * flap, L * 0.06)[0],
                fan(mbase + (mtip - mbase) * 0.55, mw * 0.82, math.pi * 0.62, L * 0.11 * flap, L * 0.06)[0]]
    else:
        fins = []
        for sgn in (-1, 1):
            f = Path().move(mtip - L * 0.13, sgn * mw * 0.3).line(mtip - L * 0.07, sgn * (mw * 0.3 + L * 0.075 * flap))
            f.line(mtip + L * 0.005, sgn * mw * 0.05).close()
            fins.append(f)
    headp = Path().oval(hx + L * 0.02, 0, L * 0.06, mw * 0.85 if not vamp else L * 0.09)
    web = None
    if vamp:
        web = Path().move(hx, -L * 0.04)
        tips = [a[int(len(a) * 0.72)] for a in arms]
        web.pts(tips).line(hx, L * 0.04).close()
    if sil:
        for a in arms:
            fill(c, arm_poly(a, L * 0.014), W, SIL)
        for tt in tentacles:
            fill(c, arm_poly(tt, L * 0.008), W, SIL)
        if web:
            fill(c, web, W, SIL)
        for f in fins:
            fill(c, f, W, SIL)
        fill(c, mantle, W, SIL)
        fill(c, headp, W, SIL)
        return
    for f in fins:
        fill(c, f, W, al(dk(col, 0.1), 0.92))
    if web:
        fill(c, web, W, al(dk(col, 0.35), 0.9))
    for k, a in enumerate(arms):
        fill(c, arm_poly(a, L * (0.016 if vamp else 0.013)), W, mixc(col, belly, 0.15 * (k % 2)))
    for tt in tentacles:
        fill(c, arm_poly(tt, L * 0.007), W, col)
        x, y = tt[-2]
        fill(c, Path().oval(x, y, L * 0.03, L * 0.014), W, dk(col, 0.1))
        dots = Path()
        for j in range(4):
            dots.oval(x + L * 0.02 - j * L * 0.013, y + L * 0.004, L * 0.003, L * 0.003, n=6)
        fill(c, dots, W, lt(belly, 0.4))
    if vamp:
        for a in arms:
            x, y = a[-1]
            glow_dot(c, x, y, L * 0.008, pal.glow or (106, 184, 255))
    elif L >= 70:
        sk = Path()
        for a in arms[::2]:
            for j in range(2, 11, 2):
                sk.oval(a[j][0], a[j][1] + L * 0.006, L * 0.0035, L * 0.0035, n=6)
        fill(c, sk, W, lt(belly, 0.35))
    vgrad(c, mantle, W, -mw, mw, [(0, dk(col, 0.2)), (0.4, col), (0.75, mixc(col, belly, 0.5)), (1, belly)])
    mantle.to(c, W)
    c.clip_push()
    rng = _rng(sp)
    if sp.pat == 'spots':
        dots = Path()
        for k in range(18):
            dots.oval(rng.uniform(mbase, mtip), rng.uniform(-0.8, 0.5) * mw, L * 0.008, L * 0.008, n=8)
        fill(c, dots, W, al(pal.patc, 0.7))
    fill(c, Path().oval((mbase + mtip) / 2, -mw * 0.5, (mtip - mbase) * 0.4, mw * 0.2), W, (255, 255, 255, 55))
    c.clip_pop()
    stroke(c, mantle, W, al(dk(col, 0.45), 0.6), max(0.6, L * 0.006))
    vgrad(c, headp, W, -L * 0.07, L * 0.07, [(0, dk(col, 0.1)), (1, mixc(col, belly, 0.4))])
    er = L * (0.05 if vamp else 0.034)
    eye(c, hx + L * 0.025, -L * 0.008, er, pal.iris if pal.mut else ((106, 184, 255) if vamp else (255, 220, 120)), big=True)


# ===================================================================================
#  Anglerfish
# ===================================================================================
def angler(c, sp, L, ph, pal, sil, lk):
    W = _flat
    col, belly = pal.col, pal.belly
    gape = L * (0.05 + 0.02 * math.sin(ph))
    bob = math.sin(ph) * L * 0.03
    sway = math.sin(ph + 1) * L * 0.025
    tail, trays, _ = fan(-L * 0.25, 0, math.pi + 0.25 * math.sin(ph), L * 0.2, L * 0.12)
    dors, drays, _ = fan(-L * 0.12, -L * 0.2, math.pi * 1.2, L * 0.1, L * 0.05)
    body = Path().move(-L * 0.25, -L * 0.07).bez(-L * 0.16, -L * 0.3, L * 0.12, -L * 0.3, L * 0.27, -L * 0.06)
    body.line(L * 0.3, -L * 0.03)
    body.line(L * 0.18, gape * 0.3)
    body.line(L * 0.35, gape + L * 0.02)
    body.bez(L * 0.33, L * 0.2, L * 0.05, L * 0.3, -L * 0.15, L * 0.18)
    body.quad(-L * 0.22, L * 0.12, -L * 0.25, L * 0.06).close()
    stalk = Path().move(L * 0.1, -L * 0.24).quad(L * 0.24 + sway, -L * 0.5, L * 0.42 + sway, -L * 0.36 + bob)
    if sil:
        for q in (tail, dors, body):
            fill(c, q, W, SIL)
        stroke(c, stalk, W, SIL, max(0.8, L * 0.012))
        glow_dot(c, L * 0.42 + sway, -L * 0.36 + bob, L * 0.025, (160, 255, 255))
        return
    paint_fin(c, tail, W, trays, -L * 0.12, L * 0.12, pal.fin, False, L=L)
    paint_fin(c, dors, W, drays, -L * 0.28, -L * 0.18, pal.fin, False, L=L)
    vgrad(c, body, W, -L * 0.3, L * 0.3, [(0, dk(col, 0.25)), (0.5, col), (1, mixc(col, belly, 0.8))])
    body.to(c, W)
    c.clip_push()
    rng = _rng(sp)
    sp_ = Path()
    for k in range(40):
        sp_.oval(rng.uniform(-0.25, 0.3) * L, rng.uniform(-0.28, 0.28) * L, L * 0.005, L * 0.005, n=6)
    fill(c, sp_, W, (255, 255, 255, 40))
    fill(c, Path().oval(L * 0.02, -L * 0.18, L * 0.18, L * 0.06), W, (255, 255, 255, 30))
    c.clip_pop()
    mouth = Path().move(L * 0.3, -L * 0.03).line(L * 0.17, gape * 0.3).line(L * 0.35, gape + L * 0.02).close()
    fill(c, mouth, W, (14, 6, 20))
    teeth = Path()
    for k in range(6):
        t = (k + 0.5) / 6
        x = lerp(L * 0.3, L * 0.19, t)
        y = lerp(-L * 0.03, gape * 0.3, t)
        ln = L * (0.03 + 0.02 * (k % 2))
        teeth.move(x - L * 0.006, y).line(x, y + ln).line(x + L * 0.006, y).close()
        x2 = lerp(L * 0.35, L * 0.2, t)
        y2 = lerp(gape + L * 0.02, gape * 0.35, t)
        teeth.move(x2 - L * 0.006, y2).line(x2, y2 - ln * 0.9).line(x2 + L * 0.006, y2).close()
    fill(c, teeth, W, (236, 236, 222, 240))
    stroke(c, body, W, al(dk(col, 0.5), 0.6), max(0.6, L * 0.006))
    stroke(c, stalk, W, dk(col, 0.1), max(0.8, L * 0.012), 'round')
    glow_dot(c, L * 0.42 + sway, -L * 0.36 + bob, L * 0.025, pal.glow or (159, 252, 255))
    eye(c, L * 0.17, -L * 0.12, L * 0.03, pal.iris if pal.mut else (200, 230, 210))
    pf, prays, _ = fan(L * 0.02, L * 0.08, math.pi * 0.8 + 0.2 * math.sin(ph), L * 0.09, L * 0.05)
    paint_fin(c, pf, W, prays, L * 0.04, L * 0.14, pal.fin, False, alpha=0.8, L=L)


# ===================================================================================
#  Jellyfish
# ===================================================================================
def jelly(c, sp, L, ph, pal, sil, lk):
    W = _flat
    col, belly = pal.col, pal.belly
    k = math.sin(ph)
    bx = L * 0.2
    blen = L * 0.25 * (1 - 0.1 * k)
    bw = L * 0.27 * (1 + 0.12 * k)
    tent = []
    for j in range(10):
        u = j / 9
        y0 = (u - 0.5) * bw * 1.7
        ln = L * (0.62 + 0.12 * math.sin(u * 7)) * (1 + 0.05 * math.sin(ph - 1))
        pts_ = [(bx, y0)]
        for i in range(1, 15):
            t = i / 14
            pts_.append((bx - ln * t, y0 * (1 - 0.3 * t) + math.sin(ph - t * 5 + j) * L * 0.03 * t))
        tent.append(pts_)
    arms = []
    for j in range(4):
        y0 = (j / 3 - 0.5) * bw * 0.6
        pts_ = []
        for i in range(15):
            t = i / 14
            pts_.append((bx + L * 0.02 - L * 0.5 * t, y0 * (1 - 0.4 * t) + math.sin(ph - t * 4 + j * 1.7) * L * 0.045 * t))
        arms.append(pts_)
    bell = Path().move(bx, -bw)
    for i in range(1, 25):
        a = -math.pi / 2 + math.pi * i / 24
        bell.line(bx + math.cos(a) * blen, math.sin(a) * bw)
    for i in range(1, 17):
        t = i / 16
        y = bw - 2 * bw * t
        bell.line(bx - abs(math.sin(t * math.pi * 8)) * L * 0.02, y)
    bell.close()
    if sil:
        for tt in tent:
            stroke(c, Path().move(*tt[0]).pts(tt[1:]), W, SIL, max(0.6, L * 0.008))
        for a in arms:
            stroke(c, Path().move(*a[0]).pts(a[1:]), W, SIL, max(1.0, L * 0.03), 'round')
        fill(c, bell, W, SIL)
        return
    for tt in tent:
        stroke(c, Path().move(*tt[0]).pts(tt[1:]), W, al(pal.fin, 0.55), max(0.6, L * 0.007), 'round')
    for j, a in enumerate(arms):
        p = Path().move(*a[0]).pts(a[1:])
        stroke(c, p, W, al(mixc(pal.fin, belly, 0.4), 0.7), max(1.0, L * 0.032), 'round')
        stroke(c, p, W, al(lt(belly, 0.3), 0.6), max(0.6, L * 0.012), 'round')
    vgrad(c, bell, W, -bw, bw, [(0, al(dk(col, 0.1), 0.85)), (0.5, al(lt(col, 0.2), 0.8)), (1, al(dk(col, 0.1), 0.85))])
    bell.to(c, W)
    c.clip_push()
    fill(c, Path().oval(bx + blen * 0.35, 0, blen * 0.55, bw * 0.6), W, al(belly, 0.45))
    rng = _rng(sp)
    stars = Path()
    for j in range(26):
        a = rng.uniform(-1.4, 1.4)
        r = rng.uniform(0.1, 0.9)
        x = bx + math.cos(a) * blen * r
        y = math.sin(a) * bw * r
        tw = 0.5 + 0.5 * math.sin(ph + j * 1.7)
        rr = L * (0.004 + 0.004 * tw)
        stars.oval(x, y, rr, rr, n=6)
    fill(c, stars, W, (255, 255, 255, 220))
    ring = Path().oval(bx + blen * 0.3, 0, blen * 0.32, bw * 0.45)
    stroke(c, ring, W, al(lt(pal.fin, 0.3), 0.45), max(0.8, L * 0.012))
    fill(c, Path().oval(bx + blen * 0.6, -bw * 0.45, blen * 0.25, bw * 0.2), W, (255, 255, 255, 70))
    c.clip_pop()
    stroke(c, bell, W, al(lt(col, 0.5), 0.7), max(0.6, L * 0.006))
    glow = Path()
    for i in range(9):
        t = i / 8
        glow.oval(bx - L * 0.004, bw - 2 * bw * t, L * 0.007, L * 0.007, n=6)
    fill(c, glow, W, al(pal.fin, 0.9))


# ===================================================================================
#  The Leviathan
# ===================================================================================
def leviathan(c, sp, L, ph, pal, sil, lk):
    W = _flat
    n = 60
    T = L * 0.052
    x_head = L * 0.4
    pts = []
    for i in range(n + 1):
        s = i / n
        pts.append((x_head - s * L * 0.88, L * 0.045 * (0.3 + 0.7 * s) * math.sin(ph - TAU * 1.05 * s)))

    def th(s):
        if s < 0.06:
            return T * (0.95 + 0.05 * s / 0.06)
        if s < 0.6:
            return T * (1.0 + 0.12 * math.sin(math.pi * (s - 0.06) / 0.54))
        return T * max(0.12, 1 - _pw((s - 0.6) / 0.4, 1.4) * 0.88)
    tops, bots, nrm = spine_edges(pts, th)
    col, belly, fin = pal.col, pal.belly, pal.fin
    glow = pal.glow or (0, 255, 213)
    # dorsal spines with a web
    dfin = Path().move(*tops[3])
    spikes = []
    for i in range(3, n - 2):
        s = i / n
        ux, uy = nrm[i]
        hh = T * (1.1 + 0.5 * math.sin(math.pi * min(1, s / 0.7))) * (1 + 0.12 * math.sin(2 * ph - s * 10))
        if i % 3 == 0:
            spikes.append((tops[i], (tops[i][0] + ux * hh - L * 0.01, tops[i][1] + uy * hh)))
            dfin.line(tops[i][0] + ux * hh - L * 0.01, tops[i][1] + uy * hh)
        else:
            dfin.line(tops[i][0] + ux * hh * 0.55, tops[i][1] + uy * hh * 0.55)
    dfin.pts([pts[i] for i in range(n - 2, 2, -1)]).close()
    # tail fluke
    ex, ey = pts[-1]
    ux, uy = nrm[-1]
    fl = T * 2.4 * (0.85 + 0.15 * math.cos(ph))
    fluke = Path().move(*pts[-4]).quad(ex - L * 0.02, ey + uy * fl, ex - L * 0.07, ey - fl * 0.95).quad(ex - L * 0.035, ey, ex - L * 0.07, ey + fl * 0.95)
    fluke.quad(ex - L * 0.02, ey - uy * fl, *pts[-4]).close()
    body = Path().move(*tops[0]).pts(tops[1:]).pts(bots[::-1])
    cx, cy = pts[0]
    hx, hy = cx, cy
    body.close()
    # head shape (a long dragon skull)
    r0 = th(0)
    jaw_a = 0.12 + 0.2 * max(0.0, math.sin(ph))
    snout = (hx + L * 0.13, hy + r0 * 0.1)
    head = Path().move(hx - L * 0.02, hy - r0 * 1.05).quad(hx + L * 0.06, hy - r0 * 1.25, snout[0], snout[1] - r0 * 0.35)
    head.quad(snout[0] + L * 0.012, snout[1], snout[0], snout[1] + r0 * 0.15).line(hx - L * 0.01, hy + r0 * 0.5).line(hx - L * 0.03, hy + r0 * 0.9).close()
    jx, jy = hx - L * 0.01, hy + r0 * 0.45
    jl = L * 0.13
    jaw = Path().move(jx, jy).line(jx + math.cos(jaw_a) * jl, jy + math.sin(jaw_a) * jl).line(jx + math.cos(jaw_a) * jl * 0.92, jy + math.sin(jaw_a) * jl + r0 * 0.3)
    jaw.quad(jx + L * 0.03, jy + r0 * 1.1, jx - L * 0.03, jy + r0 * 0.6).close()
    horns = []
    for k, (ang, ln) in enumerate(((-2.75, 0.13), (-2.95, 0.1))):
        bx, by = hx + L * 0.01 - k * L * 0.02, hy - r0 * 0.9
        tx, ty = bx + math.cos(ang) * L * ln, by + math.sin(ang) * L * ln
        horns.append(Path().move(bx + L * 0.012, by).quad(bx - L * 0.02, by - L * 0.05, tx, ty).quad(bx - L * 0.01, by - L * 0.02, bx - L * 0.012, by + L * 0.005).close())
    if sil:
        for q in (dfin, fluke, body, head, jaw, *horns):
            fill(c, q, W, SIL)
        return
    fill(c, dfin, W, al(fin, 0.5))
    sp_ = Path()
    for a, b in spikes:
        sp_.move(*a).line(*b)
    stroke(c, sp_, W, al(lt(fin, 0.3), 0.9), max(0.8, L * 0.004), 'round')
    fill(c, fluke, W, al(fin, 0.75))
    for h in horns:
        vgrad(c, h, W, hy - L * 0.08, hy, [(0, (220, 240, 235)), (1, dk(col, 0.1))])
    fill(c, jaw, W, dk(col, 0.15))
    fill(c, body, W, col)
    bb = Path().move(*pts[1])
    bb.pts([((p[0] + b[0]) / 2, (p[1] + b[1]) / 2) for p, b in zip(pts[1:], bots[1:])]).pts(bots[1:][::-1]).close()
    fill(c, bb, W, mixc(col, belly, 0.8))
    plates = Path()
    for i in range(2, n - 3, 2):
        (ax, ay), (bx2, by2) = ((pts[i][0] + bots[i][0]) / 2, (pts[i][1] + bots[i][1]) / 2), bots[i]
        plates.move(ax, ay).line(bx2, by2)
    stroke(c, plates, W, al(dk(belly, 0.3), 0.5), max(0.6, L * 0.002))
    sc = Path()
    for i in range(2, n - 4):
        x, y = pts[i]
        ux, uy = nrm[i]
        fx_, fy_ = -uy, ux
        t = th(i / n)
        for o in (0.2, 0.62):
            px, py = x + ux * t * o, y + uy * t * o
            r = t * 0.22
            first = True
            for j in range(6):
                a = -math.pi / 2 + math.pi * j / 5
                qx = px - fx_ * math.cos(a) * r + ux * math.sin(a) * r
                qy = py - fy_ * math.cos(a) * r + uy * math.sin(a) * r
                if first:
                    sc.move(qx, qy)
                    first = False
                else:
                    sc.line(qx, qy)
    stroke(c, sc, W, al(dk(col, 0.4), 0.35), max(0.5, L * 0.0015))
    pulse = 0.55 + 0.45 * math.sin(ph)
    line = Path()
    for i in range(3, n - 3, 2):
        x, y = pts[i]
        ux, uy = nrm[i]
        t = th(i / n)
        line.oval(x + ux * t * 0.35, y + uy * t * 0.35, t * 0.12, t * 0.12, n=8)
    fill(c, line, W, al(glow, 0.35 + 0.5 * pulse))
    hl = Path().move(*tops[2]).pts([(t[0] + (p[0] - t[0]) * 0.25, t[1] + (p[1] - t[1]) * 0.25) for t, p in zip(tops[2:n // 2], pts[2:n // 2])])
    stroke(c, hl, W, (255, 255, 255, 50), max(0.8, T * 0.2), 'round')
    stroke(c, body, W, al(dk(col, 0.5), 0.6), max(0.8, L * 0.002))
    vgrad(c, head, W, hy - r0 * 1.2, hy + r0, [(0, lt(col, 0.1)), (0.6, col), (1, mixc(col, belly, 0.6))])
    stroke(c, head, W, al(dk(col, 0.5), 0.6), max(0.8, L * 0.002))
    teeth = Path()
    for k in range(9):
        t = (k + 0.5) / 9
        x = lerp(hx + L * 0.005, snout[0] - L * 0.01, t)
        y = lerp(hy + r0 * 0.45, snout[1] + r0 * 0.12, t)
        teeth.move(x - L * 0.004, y).line(x, y + r0 * 0.38).line(x + L * 0.004, y).close()
        jx2 = jx + math.cos(jaw_a) * jl * t
        jy2 = jy + math.sin(jaw_a) * jl * t
        teeth.move(jx2 - L * 0.004, jy2).line(jx2, jy2 - r0 * 0.3).line(jx2 + L * 0.004, jy2).close()
    fill(c, teeth, W, (236, 250, 245))
    for k in range(2):
        wh = Path().move(snout[0] - L * 0.02, snout[1] + r0 * 0.1)
        for i in range(1, 16):
            t = i / 15
            wh.line(snout[0] - L * 0.02 - L * 0.25 * t, snout[1] + r0 * 0.1 + L * 0.04 * t * (1 + k) + math.sin(2 * ph - t * 6 + k * 2) * L * 0.012 * t)
        stroke(c, wh, W, al(glow, 0.8), max(0.8, L * 0.003), 'round')
    gill = Path()
    for k in range(3):
        gx = hx - L * 0.035 - k * L * 0.012
        gill.move(gx, hy - r0 * 0.6).quad(gx - L * 0.012, hy, gx, hy + r0 * 0.6)
    stroke(c, gill, W, al(glow, 0.5 + 0.4 * pulse), max(0.8, L * 0.0025), 'round')
    ex2, ey2 = hx + L * 0.05, hy - r0 * 0.55
    glow_dot(c, ex2, ey2, r0 * 0.32, glow)
    fill(c, Path().oval(ex2 + r0 * 0.05, ey2, r0 * 0.07, r0 * 0.22), W, (0, 40, 40))
    stroke(c, Path().move(ex2 - r0 * 0.5, ey2 - r0 * 0.5).line(ex2 + r0 * 0.5, ey2 - r0 * 0.25), W, dk(col, 0.4), max(1.0, L * 0.004), 'round')


def whale(c, sp, L, ph, pal, sil, lk):
    """The Pallid Whale: a white sperm whale, scarred all over, still carrying the harpoons of old hunts."""
    W = _flat
    col, belly, fin = pal.col, pal.belly, pal.fin
    glow = pal.glow or (191, 232, 255)
    xh, xt = L * 0.46, -L * 0.36
    n = 30

    def X(s):
        return xh + (xt - xh) * s

    def bend(s):       # whales beat their tails up and down
        k = max(0.0, (s - 0.3) / 0.7)
        return L * 0.05 * k ** 1.8 * math.sin(ph - 2.4 * s)

    def top(s):
        if s < 0.34:
            y = -L * 0.088 + L * 0.003 * math.sin(s * 9)
        elif s < 0.5:
            y = lerp(-L * 0.088, -L * 0.074, (s - 0.34) / 0.16)
        else:
            y = lerp(-L * 0.074, -L * 0.013, ((s - 0.5) / 0.5) ** 1.1)
        return y + bend(s)

    def bot(s):
        if s < 0.05:
            y = lerp(L * 0.024, L * 0.05, s / 0.05)
        elif s < 0.36:
            y = lerp(L * 0.05, L * 0.088, ((s - 0.05) / 0.31) ** 0.7)
        elif s < 0.55:
            y = L * 0.088 - L * 0.01 * (s - 0.36) / 0.19
        else:
            y = lerp(L * 0.078, L * 0.013, ((s - 0.55) / 0.45) ** 1.05)
        return y + bend(s)
    ss = [i / n for i in range(n + 1)]
    body = Path().move(X(0), top(0)).pts([(X(s_), top(s_)) for s_ in ss[1:]])
    body.pts([(X(s_), bot(s_)) for s_ in reversed(ss[2:])])
    body.quad(xh + L * 0.03, L * 0.0, X(0), top(0)).close()
    # the flukes: seen edge-on, they show more of themselves as they sweep
    tx, ty = X(1.0), (top(1.0) + bot(1.0)) / 2
    tilt = math.cos(ph - 2.4)
    fh, fl = L * (0.022 + 0.06 * abs(tilt)), L * 0.15
    fluke = Path().move(tx + L * 0.03, ty - L * 0.01)
    fluke.quad(tx - fl * 0.45, ty - fh * 1.25, tx - fl, ty - fh * 0.85)
    fluke.quad(tx - fl * 0.74, ty, tx - fl, ty + fh * 0.85)
    fluke.quad(tx - fl * 0.45, ty + fh * 1.25, tx + L * 0.03, ty + L * 0.01).close()
    fx_, fy_ = X(0.39), bot(0.39) - L * 0.014
    sw = math.sin(ph * 0.8) * L * 0.012
    flip = Path().move(fx_ + L * 0.012, fy_).quad(fx_ - L * 0.03, fy_ + L * 0.06 + sw, fx_ - L * 0.075, fy_ + L * 0.05 + sw)
    flip.quad(fx_ - L * 0.04, fy_ + L * 0.02, fx_ - L * 0.02, fy_ - L * 0.004).close()
    jaw = Path().move(X(0.05), L * 0.036).line(X(0.33), L * 0.07).line(X(0.34), L * 0.084)
    jaw.quad(X(0.2), L * 0.074, X(0.05), L * 0.052).close()
    if sil:
        for q in (fluke, body, flip, jaw):
            fill(c, q, W, SIL)
        return
    fill(c, fluke, W, dk(col, 0.12))
    stroke(c, fluke, W, al(dk(col, 0.45), 0.6), max(0.8, L * 0.0025))
    vgrad(c, body, W, -L * 0.09, L * 0.09, [(0, dk(col, 0.1)), (0.42, col), (1, belly)])
    # wrinkled skin behind the head
    wr = Path()
    for k in range(16):
        s_ = 0.36 + k * 0.035
        x0, y0, y1 = X(s_), top(s_) + L * 0.012, bot(s_) - L * 0.012
        wr.move(x0, y0)
        for j in range(1, 7):
            t_ = j / 6
            wr.line(x0 + math.sin(j * 1.7 + k) * L * 0.004, lerp(y0, y1, t_))
    stroke(c, wr, W, al(dk(col, 0.2), 0.3), max(0.6, L * 0.0022), 'round')
    # old scars, crossing everywhere
    rng = _rng(sp)
    sc = Path()
    for k in range(22):
        s_ = rng.uniform(0.04, 0.82)
        v = rng.uniform(0.15, 0.85)
        x0 = X(s_)
        y0 = lerp(top(s_), bot(s_), v)
        a = rng.uniform(-0.9, 0.9)
        ln = rng.uniform(0.025, 0.075) * L
        sc.move(x0, y0).line(x0 + math.cos(a) * ln, y0 + math.sin(a) * ln * 0.6)
    stroke(c, sc, W, al(dk(col, 0.32), 0.55), max(0.6, L * 0.0028), 'round')
    stroke(c, sc, W, al((255, 214, 214), 0.25), max(0.4, L * 0.0012), 'round')
    # the lower jaw and its teeth
    fill(c, jaw, W, lt(belly, 0.2))
    teeth = Path()
    for k in range(11):
        u = k / 10
        x0, y0 = lerp(X(0.07), X(0.31), u), lerp(L * 0.039, L * 0.067, u)
        teeth.move(x0 - L * 0.0045, y0).line(x0, y0 - L * 0.013).line(x0 + L * 0.0045, y0).close()
    fill(c, teeth, W, (255, 252, 240))
    stroke(c, Path().move(X(0.04), L * 0.034).line(X(0.34), L * 0.068), W, al(dk(col, 0.55), 0.8), max(0.8, L * 0.003), 'round')
    fill(c, flip, W, dk(col, 0.06))
    stroke(c, flip, W, al(dk(col, 0.45), 0.6), max(0.6, L * 0.002))
    stroke(c, body, W, al(dk(col, 0.5), 0.55), max(0.8, L * 0.0026))
    # the blowhole and the eye
    stroke(c, Path().move(X(0.012), top(0.012) + L * 0.006).line(X(0.04), top(0.04) + L * 0.004), W, al(dk(col, 0.6), 0.9),
           max(0.8, L * 0.004), 'round')
    ex_, ey_ = X(0.35), L * 0.03 + bend(0.35)
    glow_dot(c, ex_, ey_, L * 0.016, glow)
    fill(c, Path().oval(ex_, ey_, L * 0.0085, L * 0.0065), W, (20, 26, 34))
    fill(c, Path().oval(ex_ + L * 0.002, ey_ - L * 0.002, L * 0.0025, L * 0.0022), W, (255, 255, 255))
    # harpoons from old hunts, still stuck in its back, trailing their ropes
    for k, (s_, ang, ln) in enumerate(((0.43, -2.25, 0.1), (0.53, -2.05, 0.085), (0.64, -2.4, 0.075))):
        bx, by = X(s_), top(s_) + L * 0.01
        hx, hy = bx + math.cos(ang) * L * ln, by + math.sin(ang) * L * ln
        stroke(c, Path().move(bx, by).line(hx, hy), W, (54, 50, 46), max(1.0, L * 0.006), 'round')
        stroke(c, Path().move(bx, by).line(hx, hy), W, al((150, 140, 120), 0.5), max(0.5, L * 0.0018), 'round')
        rope = Path().move(hx, hy)
        rope.quad(hx - L * 0.06, hy + L * 0.05 + math.sin(ph + k * 1.7) * L * 0.015,
                  hx - L * 0.15 - k * L * 0.02, hy + L * 0.02 + math.sin(ph * 1.3 + k) * L * 0.03)
        stroke(c, rope, W, al((140, 118, 84), 0.85), max(0.7, L * 0.0026), 'round')


def crab(c, sp, L, ph, pal, sil, lk):
    """The Ancient Crab: a colossal old crab crusted with frozen barnacles. One claw is bigger than a boat."""
    W = _flat
    col, belly, fin = pal.col, pal.belly, pal.fin
    glow = pal.glow or (159, 232, 255)
    bob = math.sin(ph * 2) * L * 0.004
    cx, cy = -L * 0.06, -L * 0.06 + bob
    rx, ry = L * 0.27, L * 0.15
    # the carapace: a knobbly dome
    top = []
    for i in range(41):
        a = math.pi * i / 40
        knob = L * 0.007 * abs(math.sin(a * 9)) + (L * 0.012 if i % 10 == 5 else 0)
        top.append((cx + rx * math.cos(a), cy - ry * math.sin(a) ** 0.75 - knob))
    shell = Path().move(*top[0]).pts(top[1:])
    shell.quad(cx - rx * 0.4, cy + L * 0.085, cx + rx, cy + L * 0.03).close()
    # legs: four on the far side, four on the near side; they walk as it swims
    def leg(i, far):
        x0 = cx + rx * (0.5, 0.17, -0.17, -0.5)[i] + (L * 0.02 if far else 0)
        y0 = cy + L * 0.06 - (L * 0.02 if far else 0)
        spread = (0.21, 0.09, -0.1, -0.22)[i] * L * (0.85 if far else 1)
        k = ph * 1.6 + i * 1.6 + (math.pi if far else 0)
        step = math.sin(k) * L * 0.028
        lift = max(0.0, math.cos(k)) * L * 0.02
        knee = (x0 + spread * 0.62 + step * 0.4, y0 - L * 0.065 - lift * 0.5)
        tip = (x0 + spread + step, y0 + L * 0.15 - lift)
        return (x0, y0), knee, tip
    legs_far = [leg(i, True) for i in range(4)]
    legs_near = [leg(i, False) for i in range(4)]
    # claws: a huge crusher in front and a smaller one behind it
    open_a = 0.12 + 0.3 * max(0.0, math.sin(ph * 0.9))

    def claw(scale, dx, dy, a):
        bx, by = cx + rx * 0.82 + dx, cy + L * 0.03 + dy
        ex_, ey_ = bx + L * 0.05 * scale, by + L * 0.06 * scale
        hx, hy = bx + L * 0.09 * scale, by + L * 0.01 * scale
        arm = (bx, by, ex_, ey_, hx, hy)
        palm = Path().oval(hx + L * 0.06 * scale, hy, L * 0.08 * scale, L * 0.055 * scale, -0.12)
        fx0, fy0 = hx + L * 0.11 * scale, hy + L * 0.01 * scale
        fixed = Path().move(fx0, fy0 - L * 0.025 * scale).quad(fx0 + L * 0.065 * scale, fy0 - L * 0.01 * scale, fx0 + L * 0.09 * scale, fy0 + L * 0.03 * scale)
        fixed.quad(fx0 + L * 0.045 * scale, fy0 + L * 0.03 * scale, fx0, fy0 + L * 0.03 * scale).close()
        px, py = fx0 - L * 0.005 * scale, fy0 - L * 0.03 * scale
        ln = L * 0.1 * scale
        tipx, tipy = px + math.cos(-a) * ln, py + math.sin(-a) * ln
        dac = Path().move(px, py + L * 0.012 * scale).quad(px + ln * 0.5 * math.cos(-a) + L * 0.01 * scale, py + ln * 0.5 * math.sin(-a) - L * 0.03 * scale, tipx, tipy)
        dac.quad(px + ln * 0.55 * math.cos(-a), py + ln * 0.55 * math.sin(-a) + L * 0.012 * scale, px, py + L * 0.03 * scale).close()
        return arm, palm, fixed, dac
    far_claw = claw(0.78, -L * 0.03, -L * 0.04, open_a * 0.8 + 0.08)
    near_claw = claw(1.3, 0.0, 0.0, open_a)

    def leg_path(lg):
        (x0, y0), (kx, ky), (tx, ty) = lg
        return Path().move(x0, y0).line(kx, ky).line(tx, ty)
    if sil:
        for lg in legs_far + legs_near:
            stroke(c, leg_path(lg), W, SIL, max(1.0, L * 0.032), 'round')
        for arm, palm, fixed, dac in (far_claw, near_claw):
            stroke(c, Path().move(arm[0], arm[1]).line(arm[2], arm[3]).line(arm[4], arm[5]), W, SIL, max(1.0, L * 0.035), 'round')
            for q in (palm, fixed, dac):
                fill(c, q, W, SIL)
        fill(c, shell, W, SIL)
        return
    dark = dk(col, 0.35)
    # far legs and the far claw sit behind the body
    for lg in legs_far:
        stroke(c, leg_path(lg), W, dk(fin, 0.25), max(1.0, L * 0.028), 'round')
        (_, _), _, (tx, ty) = lg
        fill(c, Path().oval(tx, ty, L * 0.006, L * 0.012), W, dk(fin, 0.4))
    arm, palm, fixed, dac = far_claw
    stroke(c, Path().move(arm[0], arm[1]).line(arm[2], arm[3]).line(arm[4], arm[5]), W, dk(col, 0.3), max(1.0, L * 0.03), 'round')
    for q in (palm, fixed, dac):
        fill(c, q, W, dk(col, 0.25))
    # the shell
    vgrad(c, shell, W, cy - ry, cy + L * 0.08, [(0, lt(col, 0.12)), (0.55, col), (1, dk(col, 0.3))])
    rim = Path().move(*top[0]).pts(top[1:])
    stroke(c, rim, W, al((232, 248, 255), 0.75), max(1.0, L * 0.009), 'round')
    rng = _rng(sp)
    frost = Path()
    for k in range(9):
        a = rng.uniform(0.3, 2.8)
        x, y = cx + rx * math.cos(a) * 0.95, cy - ry * math.sin(a) ** 0.75 * 0.9
        frost.oval(x, y + L * 0.006, rng.uniform(0.012, 0.03) * L, rng.uniform(0.005, 0.009) * L, rng.uniform(-0.3, 0.3))
    fill(c, frost, W, al((235, 250, 255), 0.7))
    bar = Path()
    holes = Path()
    for k in range(16):
        a = rng.uniform(0.25, 2.9)
        rr = rng.uniform(0.25, 0.85)
        x, y = cx + rx * math.cos(a) * rr * 1.05, cy - ry * math.sin(a) ** 0.75 * rr + L * 0.02
        r_ = rng.uniform(0.006, 0.013) * L
        bar.oval(x, y, r_, r_ * 0.85)
        holes.oval(x, y - r_ * 0.15, r_ * 0.35, r_ * 0.25)
    fill(c, bar, W, (214, 210, 196))
    fill(c, holes, W, (60, 52, 50))
    seam = Path().move(cx - rx * 0.9, cy + L * 0.03).quad(cx, cy + L * 0.055, cx + rx * 0.95, cy + L * 0.015)
    stroke(c, seam, W, al(dark, 0.6), max(0.8, L * 0.004), 'round')
    stroke(c, shell, W, al(dk(col, 0.55), 0.6), max(0.8, L * 0.003))
    # mouthparts, eyes on stalks, feelers
    mx_, my_ = cx + rx * 0.9, cy + L * 0.035
    mouth = Path()
    for k in range(3):
        mouth.oval(mx_ - k * L * 0.012, my_ + k * L * 0.006, L * 0.012, L * 0.008)
    fill(c, mouth, W, lt(belly, 0.1))
    for k, dx in enumerate((0.0, -L * 0.025)):
        sx0, sy0 = cx + rx * 0.82 + dx, cy - ry * 0.45
        sx1, sy1 = sx0 + L * 0.02, sy0 - L * 0.05 - k * L * 0.005
        stroke(c, Path().move(sx0, sy0).line(sx1, sy1), W, dk(col, 0.15 + 0.1 * k), max(1.0, L * 0.009), 'round')
        glow_dot(c, sx1, sy1, L * 0.02, glow)
        fill(c, Path().oval(sx1, sy1, L * 0.011, L * 0.011), W, (16, 20, 26))
        fill(c, Path().oval(sx1 + L * 0.003, sy1 - L * 0.003, L * 0.003, L * 0.003), W, (255, 255, 255))
        feel = Path().move(sx0 + L * 0.01, sy0 + L * 0.01)
        feel.quad(sx0 + L * 0.12, sy0 - L * 0.06 + math.sin(ph * 2 + k) * L * 0.01, sx0 + L * 0.2, sy0 - L * 0.02 + k * L * 0.02)
        stroke(c, feel, W, al(lt(col, 0.2), 0.8), max(0.6, L * 0.0025), 'round')
    # near legs and the big crusher claw in front
    for lg in legs_near:
        (x0, y0), (kx, ky), (tx, ty) = lg
        stroke(c, Path().move(x0, y0).line(kx, ky), W, fin, max(1.0, L * 0.036), 'round')
        stroke(c, Path().move(kx, ky).line(tx, ty), W, fin, max(1.0, L * 0.026), 'round')
        stroke(c, Path().move(x0, y0).line(kx, ky), W, al(lt(fin, 0.25), 0.7), max(0.6, L * 0.01), 'round')
        fill(c, Path().oval(kx, ky, L * 0.012, L * 0.01), W, lt(fin, 0.1))
        fill(c, Path().oval(tx, ty, L * 0.007, L * 0.014), W, dk(fin, 0.3))
    arm, palm, fixed, dac = near_claw
    stroke(c, Path().move(arm[0], arm[1]).line(arm[2], arm[3]).line(arm[4], arm[5]), W, dk(col, 0.05), max(1.0, L * 0.05), 'round')
    vgrad(c, palm, W, arm[5] - L * 0.06, arm[5] + L * 0.06, [(0, lt(col, 0.15)), (1, dk(col, 0.25))])
    fill(c, fixed, W, dk(col, 0.1))
    fill(c, dac, W, dk(col, 0.05))
    teeth = Path()
    for k in range(5):
        tx0 = arm[4] + L * (0.15 + k * 0.016)
        teeth.oval(tx0, arm[5] + L * 0.008, L * 0.006, L * 0.004)
    fill(c, teeth, W, (240, 232, 220))
    stroke(c, palm, W, al(dk(col, 0.55), 0.6), max(0.8, L * 0.0025))
    fill(c, Path().oval(arm[4] + L * 0.05, arm[5] - L * 0.03, L * 0.025, L * 0.006, -0.12), W, al((235, 250, 255), 0.6))


def bloop(c, sp, L, ph, pal, sil, lk):
    """The Bloop: a whale-sized monster from the bottom of the sea, with a huge round mouth ringed with teeth."""
    W = _flat
    col, belly, fin = pal.col, pal.belly, pal.fin
    glow = pal.glow or (159, 255, 232)
    gape = 0.75 + 0.25 * math.sin(ph * 0.8)
    x0, x1 = L * 0.34, -L * 0.4

    def X(u):
        return x0 + (x1 - x0) * u

    def h(u):
        if u < 0.2:
            return L * (0.19 + 0.02 * math.sin(math.pi / 2 * u / 0.2))
        return L * max(0.022, 0.21 * (1 - (u - 0.2) / 0.8) ** 1.45)

    def off(u):
        return L * 0.03 * u ** 1.5 * math.sin(ph - 3.0 * u)
    n = 30
    top = [(X(i / n), off(i / n) - h(i / n)) for i in range(n + 1)]
    bot = [(X(i / n), off(i / n) + h(i / n) * 0.92) for i in range(n + 1)]
    body = Path().move(*top[0]).pts(top[1:]).pts(bot[::-1]).close()
    tx, ty = X(1.0), off(1.0)
    fh = L * (0.05 + 0.04 * abs(math.cos(ph - 3.0)))
    fluke = Path().move(tx + L * 0.03, ty - L * 0.015).quad(tx - L * 0.06, ty - fh * 1.3, tx - L * 0.13, ty - fh)
    fluke.quad(tx - L * 0.09, ty, tx - L * 0.13, ty + fh).quad(tx - L * 0.06, ty + fh * 1.3, tx + L * 0.03, ty + L * 0.015).close()
    fx_, fy_ = X(0.3), off(0.3) + h(0.3) * 0.75
    flip = Path().move(fx_ + L * 0.02, fy_).quad(fx_ - L * 0.03, fy_ + L * 0.08 + math.sin(ph) * L * 0.01, fx_ - L * 0.09, fy_ + L * 0.07)
    flip.quad(fx_ - L * 0.04, fy_ + L * 0.02, fx_ - L * 0.01, fy_ - L * 0.01).close()
    # the mouth: a huge round opening at the front, seen a little from the side
    mx, my = x0 + L * 0.02, off(0.0) + L * 0.01
    rx, ry = L * 0.12, L * (0.2 + 0.035 * gape)
    mouth = Path().oval(mx, my, rx, ry, 0.0, n=40)
    lip = Path().oval(mx, my, rx * 1.18, ry * 1.1, 0.0, n=48)
    if sil:
        for q in (fluke, body, flip, lip):
            fill(c, q, W, SIL)
        return
    # sound rings ahead of it: the noise it is named after
    for k in range(3):
        u = (ph / TAU * 0.6 + k / 3) % 1.0
        r = L * (0.08 + 0.12 * u)
        ring = Path()
        for i in range(17):
            a = -0.9 + 1.8 * i / 16
            px, py = mx + L * 0.04 + math.cos(a) * r, my + math.sin(a) * r * 1.4
            if i == 0:
                ring.move(px, py)
            else:
                ring.line(px, py)
        stroke(c, ring, W, al(glow, 0.3 * (1 - u)), max(0.8, L * 0.004), 'round')
    fill(c, fluke, W, dk(fin, 0.05))
    stroke(c, fluke, W, al(dk(col, 0.5), 0.6), max(0.8, L * 0.0025))
    vgrad(c, body, W, -L * 0.15, L * 0.14, [(0, dk(col, 0.25)), (0.45, col), (1, belly)])
    rng = _rng(sp)
    spots = Path()
    for k in range(40):
        u = rng.uniform(0.08, 0.85)
        v = rng.uniform(-0.85, 0.3)
        r_ = rng.uniform(0.004, 0.012) * L
        spots.oval(X(u), off(u) + v * h(u), r_ * 1.4, r_)
    fill(c, spots, W, al(dk(col, 0.35), 0.45))
    wr = Path()
    for k in range(18):
        u = 0.12 + k * 0.042
        y0, y1 = off(u) - h(u) * 0.9, off(u) + h(u) * 0.85
        wr.move(X(u), y0)
        for j in range(1, 7):
            wr.line(X(u) + math.sin(j * 1.9 + k) * L * 0.005, lerp(y0, y1, j / 6))
    stroke(c, wr, W, al(dk(col, 0.4), 0.35), max(0.6, L * 0.0025), 'round')
    gr = Path()
    for k in range(5):
        yy = L * (0.04 + k * 0.018)
        gr.move(X(0.06), off(0.06) + yy).quad(X(0.25), off(0.25) + yy * 1.15, X(0.42), off(0.42) + yy * 0.8)
    stroke(c, gr, W, al(dk(belly, 0.3), 0.5), max(0.6, L * 0.003), 'round')
    fill(c, flip, W, dk(col, 0.1))
    stroke(c, flip, W, al(dk(col, 0.5), 0.6), max(0.6, L * 0.002))
    stroke(c, body, W, al(dk(col, 0.6), 0.6), max(0.8, L * 0.003))
    # lips, the dark throat and rows of teeth all the way round
    fill(c, lip, W, lt(belly, 0.05))
    stroke(c, lip, W, al(dk(col, 0.5), 0.7), max(0.8, L * 0.003))
    fill(c, mouth, W, (14, 22, 22))
    fill(c, Path().oval(mx + rx * 0.25, my, rx * 0.55, ry * 0.6), W, (4, 8, 8))
    teeth = Path()
    for ring_k, (sc_, ln) in enumerate(((1.0, 0.3), (0.72, 0.26))):
        m = 28 if ring_k == 0 else 22
        for i in range(m):
            a = TAU * i / m + ring_k * 0.16
            bx, by = mx + math.cos(a) * rx * sc_, my + math.sin(a) * ry * sc_
            ix, iy = mx + math.cos(a) * rx * (sc_ - ln), my + math.sin(a) * ry * (sc_ - ln)
            px, py = -math.sin(a) * L * 0.011, math.cos(a) * L * 0.011
            teeth.move(bx - px, by - py).line(ix, iy).line(bx + px, by + py).close()
    fill(c, teeth, W, (236, 232, 214))
    # a small pale eye high on the head
    ex_, ey_ = X(0.2), off(0.2) - h(0.2) * 0.62
    glow_dot(c, ex_, ey_, L * 0.016, glow)
    fill(c, Path().oval(ex_, ey_, L * 0.008, L * 0.007), W, (12, 20, 20))


def nessie(c, sp, L, ph, pal, sil, lk):
    """Nessie: the Loch Ness Monster. A plump body, four big flippers, a long tail and a long neck held high."""
    W = _flat
    col, belly, fin = pal.col, pal.belly, pal.fin
    glow = pal.glow or (200, 255, 154)
    sway = math.sin(ph)
    # ---- the long neck: a centre line from the shoulders up to the head
    nb = (L * 0.13, -L * 0.02)
    hx, hy = L * 0.42 + sway * L * 0.012, -L * 0.3 + math.cos(ph) * L * 0.01
    cx_, cy_ = L * 0.2, -L * 0.3
    spine = []
    for i in range(17):
        t = i / 16
        x = (1 - t) ** 2 * nb[0] + 2 * (1 - t) * t * cx_ + t * t * hx
        y = (1 - t) ** 2 * nb[1] + 2 * (1 - t) * t * cy_ + t * t * hy
        spine.append((x, y, lerp(L * 0.075, L * 0.032, t ** 0.8)))
    side_a, side_b = [], []
    for i, (x, y, w) in enumerate(spine):
        x2, y2 = spine[min(i + 1, 16)][:2]
        x1, y1 = spine[max(i - 1, 0)][:2]
        dx, dy = x2 - x1, y2 - y1
        n_ = math.hypot(dx, dy) or 1
        nx, ny = -dy / n_, dx / n_
        side_a.append((x + nx * w, y + ny * w))
        side_b.append((x - nx * w, y - ny * w))
    neck = Path().move(*side_a[0]).pts(side_a[1:]).pts(side_b[::-1]).close()
    # ---- the head: small, with a rounded snout
    head = Path().oval(hx + L * 0.035, hy - L * 0.004, L * 0.068, L * 0.04, -0.12, n=28)
    # ---- the body and tail
    def bh(u):          # u: 0 at the chest, 1 at the tail tip
        if u < 0.14:
            return L * 0.115 * (0.25 + 0.75 * math.sin(math.pi / 2 * u / 0.14) ** 0.7)
        if u < 0.42:
            return L * 0.115
        return L * 0.115 * max(0.0, 1 - (u - 0.42) / 0.58) ** 1.25 + L * 0.004

    def bx(u):
        return L * 0.25 - u * L * 0.81

    def bo(u):          # the tail swishes
        return L * 0.035 + L * 0.05 * max(0.0, u - 0.5) ** 1.6 * math.sin(ph * 1.0 - 3 * u)
    n = 32
    top = [(bx(i / n), bo(i / n) - bh(i / n) * 1.05) for i in range(n + 1)]
    bot = [(bx(i / n), bo(i / n) + bh(i / n) * 0.8) for i in range(n + 1)]
    body = Path().move(*top[0]).pts(top[1:]).pts(bot[::-1]).close()

    def flipper(x, y, k, far):
        a = 0.5 + 0.45 * math.sin(ph + k)
        ln = L * (0.17 if k < 1 else 0.14)
        ex, ey = x - math.cos(a) * ln, y + math.sin(a) * ln * 0.8
        w = L * 0.035
        return Path().move(x + w, y - w * 0.4).quad(ex + w * 0.6, ey + w * 1.2, ex - w * 0.2, ey).quad(
            x - w * 1.6, y + w * 0.2, x - w * 0.8, y - w * 0.6).close()
    flips_far = [flipper(L * 0.1, L * 0.09, 0.4, True), flipper(-L * 0.17, L * 0.1, 2.2, True)]
    flips_near = [flipper(L * 0.06, L * 0.1, 0.0, False), flipper(-L * 0.21, L * 0.11, 1.8, False)]
    if sil:
        for q in flips_far + [body, neck, head] + flips_near:
            fill(c, q, W, SIL)
        return
    for q in flips_far:
        fill(c, q, W, dk(fin, 0.3))
    vgrad(c, body, W, -L * 0.1, L * 0.12, [(0, dk(col, 0.2)), (0.55, col), (1, belly)])
    stroke(c, body, W, al(dk(col, 0.6), 0.65), max(0.8, L * 0.003))
    vgrad(c, neck, W, -L * 0.34, L * 0.0, [(0, lt(col, 0.04)), (1, dk(col, 0.12))])
    # mottled, mossy hide
    rng = _rng(sp)
    spots = Path()
    for k in range(34):
        u = rng.uniform(0.05, 0.8)
        v = rng.uniform(-0.95, -0.1)
        r_ = rng.uniform(0.006, 0.016) * L
        spots.oval(bx(u), bo(u) + v * bh(u), r_ * 1.5, r_)
    for k in range(9):
        x, y, w = spine[2 + k]
        spots.oval(x, y - w * 0.4, w * 0.25, w * 0.18)
    fill(c, spots, W, al(dk(col, 0.35), 0.55))
    # a ridge of little bumps along the back: the "humps" in every blurry photo
    ridge = Path()
    for k in range(7):
        u = 0.08 + k * 0.09
        x, y = bx(u), bo(u) - bh(u) * 1.05
        ridge.move(x + L * 0.018, y + L * 0.004).quad(x, y - L * 0.022, x - L * 0.018, y + L * 0.004).close()
    fill(c, ridge, W, dk(col, 0.15))
    edge = al(dk(col, 0.6), 0.7)
    for side in (side_a, side_b):
        stroke(c, Path().move(*side[3]).pts(side[4:]), W, edge, max(0.8, L * 0.003), 'round')
    fill(c, head, W, col)
    hc_x, hc_y, hrx, hry, hr = hx + L * 0.035, hy - L * 0.004, L * 0.068, L * 0.04, -0.12
    arc = []
    for i in range(23):
        a = -2.3 + 4.6 * i / 22
        px, py = math.cos(a) * hrx, math.sin(a) * hry
        arc.append((hc_x + px * math.cos(hr) - py * math.sin(hr), hc_y + px * math.sin(hr) + py * math.cos(hr)))
    stroke(c, Path().move(*arc[0]).pts(arc[1:]), W, edge, max(0.8, L * 0.003), 'round')
    for q in flips_near:
        fill(c, q, W, fin)
        stroke(c, q, W, al(dk(fin, 0.5), 0.6), max(0.6, L * 0.0025))
    # two little knobs on the head, a friendly smile, nostrils and a glowing eye
    knobs = Path().oval(hx - L * 0.004, hy - L * 0.04, L * 0.008, L * 0.013, -0.3).oval(hx + L * 0.016, hy - L * 0.042, L * 0.007, L * 0.012, 0.2)
    fill(c, knobs, W, dk(col, 0.1))
    smile = Path().move(hx + L * 0.045, hy + L * 0.012).quad(hx + L * 0.07, hy + L * 0.02, hx + L * 0.098, hy + L * 0.004)
    stroke(c, smile, W, al(dk(col, 0.7), 0.9), max(0.7, L * 0.004), 'round')
    fill(c, Path().oval(hx + L * 0.095, hy - L * 0.012, L * 0.004, L * 0.003), W, dk(col, 0.6))
    ex_, ey_ = hx + L * 0.032, hy - L * 0.014
    glow_dot(c, ex_, ey_, L * 0.012, glow)
    fill(c, Path().oval(ex_ + L * 0.002, ey_, L * 0.005, L * 0.006), W, (14, 20, 12))


def watcher(c, sp, L, ph, pal, sil, lk):
    W = _flat
    col, belly = pal.col, pal.belly
    body = Path().oval(-L * 0.035, 0, L * 0.25, L * 0.22)
    arms = []
    for k in range(8):
        u = k / 7
        y0 = (u - 0.5) * L * 0.22
        reach = L * (0.32 + 0.12 * (k % 3) / 2)
        sway = math.sin(ph * 1.4 + k * 0.8) * L * 0.035
        arm = Path().move(-L * 0.13, y0)
        arm.bez(-L * 0.24, y0 + sway, -reach * 0.7, y0 - sway,
                -reach, y0 + math.sin(ph + k) * L * 0.08)
        arms.append(arm)
    if sil:
        for arm in arms:
            stroke(c, arm, W, SIL, max(1.0, L * 0.035), 'round')
        fill(c, body, W, SIL)
        return
    for arm in arms:
        stroke(c, arm, W, al(dk(col, 0.5), 0.72), max(1.0, L * 0.044), 'round')
        stroke(c, arm, W, al(mixc(col, belly, 0.24), 0.98), max(1.0, L * 0.031), 'round')
        tipx, tipy = arm.subs[0][0][-1]
        glow_dot(c, tipx, tipy, L * 0.012, pal.glow or '#ff294f')
    vgrad(c, body, W, -L * 0.22, L * 0.22,
          [(0, dk(col, 0.35)), (0.48, col), (0.78, mixc(col, belly, 0.35)), (1, dk(col, 0.16))])
    stroke(c, body, W, al(dk(col, 0.65), 0.9), max(1.0, L * 0.008))
    ring = Path().oval(L * 0.035, -L * 0.012, L * 0.135, L * 0.135)
    ring.to(c, W).stroke(al(pal.glow or '#ff294f', 0.42), max(1.0, L * 0.035))
    ring.to(c, W).stroke(al(lt(pal.glow or '#ff294f', 0.45), 0.9), max(1.0, L * 0.012))
    eye(c, L * 0.035, -L * 0.012, L * 0.105, pal.iris if pal.mut else (255, 54, 87), big=True)
    fill(c, Path().oval(L * 0.075, -L * 0.012, L * 0.028, L * 0.07), W, (18, 8, 24))
    glow_dot(c, L * 0.01, -L * 0.04, L * 0.018, (255, 246, 225))


PAINTERS_SPECIAL = {'puffer': puffer, 'seahorse': seahorse, 'ray': ray, 'eel': eel, 'squid': squid, 'angler': angler,
                    'jelly': jelly, 'leviathan': leviathan, 'whale': whale, 'crab': crab, 'bloop': bloop,
                    'nessie': nessie, 'watcher': watcher}


# ===================================================================================
#  Dispatcher
# ===================================================================================
def draw_fish(c, sp, L, mut=None, sil=False, ph=0.0):
    """Draw a fish facing right, centred on the pen's origin, L pixels long."""
    lk = look(sp)
    pal = palette(sp, mut, lk)
    k = lk.kind
    fn = PAINTERS.get(k)
    if fn is None:
        bony(c, sp, L, ph, pal, sil, lk)
    else:
        fn(c, sp, L, ph, pal, sil, lk)


PAINTERS = PAINTERS_SPECIAL
