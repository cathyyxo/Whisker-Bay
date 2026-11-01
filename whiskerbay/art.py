"""Drawing tools and the hand-painted art: fish, the cat and the boats. No image files are used."""
import math
import time
from collections import OrderedDict

import pygame
from pygame import gfxdraw

from . import fishart
from .data import BOAT, ENCH, MUT, ROD
from .util import TAU, clamp, hexc, mix, rgba

SIL = (4, 14, 26)


def _col(c, alpha=1.0):
    """Any colour ('#hex', (r,g,b) or (r,g,b,a)) -> (r,g,b,a) with alpha applied."""
    if isinstance(c, str):
        r, g, b = hexc(c)
        a = 255
    elif len(c) == 4:
        r, g, b, a = c
    else:
        r, g, b = c
        a = 255
    return (int(r), int(g), int(b), int(clamp(a * alpha, 0, 255)))


# pygame's gfxdraw takes 16-bit coordinates. Deep down (the Mariana Deep is 11 km) things like the boat or a
# line to the surface can be tens of thousands of pixels off the screen, so every gfxdraw call is clamped.
def _safe_gfx(fn, rect_first=False):
    def call(surf, *a):
        b = []
        for i, v in enumerate(a):
            if isinstance(v, int) and not isinstance(v, bool):
                v = -30000 if v < -30000 else 30000 if v > 30000 else v
            elif isinstance(v, (list, tuple)) and v:
                if isinstance(v[0], (list, tuple)):
                    v = [(max(-30000, min(30000, int(q[0]))), max(-30000, min(30000, int(q[1])))) for q in v]
                elif rect_first and i == 0:
                    v = tuple(max(-30000, min(30000, int(q))) for q in v)
            b.append(v)
        return fn(surf, *b)
    call.__wrapped__ = fn
    return call


if not getattr(gfxdraw, '_wb_safe', False):
    for _n in ('pixel', 'hline', 'vline', 'line', 'circle', 'aacircle', 'filled_circle', 'ellipse', 'aaellipse', 'filled_ellipse',
               'arc', 'pie', 'trigon', 'aatrigon', 'filled_trigon', 'polygon', 'aapolygon', 'filled_polygon', 'bezier'):
        if hasattr(gfxdraw, _n):
            setattr(gfxdraw, _n, _safe_gfx(getattr(gfxdraw, _n)))
    for _n in ('box', 'rectangle'):
        if hasattr(gfxdraw, _n):
            setattr(gfxdraw, _n, _safe_gfx(getattr(gfxdraw, _n), rect_first=True))
    gfxdraw._wb_safe = True


def _ip(pts):
    """Whole-pixel points, kept inside the range pygame's drawing functions accept (a line to a fish
    kilometres below the screen must not crash the game)."""
    return [(max(-30000, min(30000, int(round(px)))), max(-30000, min(30000, int(round(py))))) for px, py in pts]


def _clip(pts, fv):
    """Sutherland-Hodgman against one linear function: keep the part where fv(p) >= 0."""
    out = []
    n = len(pts)
    if n == 0:
        return out
    vals = [fv(p) for p in pts]
    for i in range(n):
        p, a = pts[i], vals[i]
        j = (i + 1) % n
        q, b = pts[j], vals[j]
        if a >= 0:
            out.append(p)
        if (a >= 0) != (b >= 0):
            t = a / (a - b)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def _stop_col(stops, s):
    s = clamp(s, 0, 1)
    for i in range(len(stops) - 1):
        o0, c0 = stops[i]
        o1, c1 = stops[i + 1]
        if s <= o1:
            u = 0 if o1 == o0 else (s - o0) / (o1 - o0)
            a, b = _col(c0), _col(c1)
            return tuple(int(a[k] + (b[k] - a[k]) * u) for k in range(4))
    return _col(stops[-1][1])


class Pen:
    """A canvas-like helper: an affine transform, paths made of lines and curves, fills and strokes.
    aa=True draws straight onto an opaque surface with antialiasing and real alpha blending.
    aa=False draws plain shapes (used on supersampled sprites; alpha goes through a temporary layer)."""

    def __init__(self, surf, aa=False):
        self.surf = surf
        self.aa = aa
        self.m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        self.stack = []
        self.alpha = 1.0
        self.subs = []
        self.cur = None
        self._clips = []

    # ---- transform ----
    def save(self):
        self.stack.append((self.m, self.alpha))

    def restore(self):
        self.m, self.alpha = self.stack.pop()

    def translate(self, x, y):
        a, b, c, d, e, f = self.m
        self.m = (a, b, c, d, a * x + c * y + e, b * x + d * y + f)

    def rotate(self, r):
        cs, sn = math.cos(r), math.sin(r)
        a, b, c, d, e, f = self.m
        self.m = (a * cs + c * sn, b * cs + d * sn, c * cs - a * sn, d * cs - b * sn, e, f)

    def scale(self, sx, sy=None):
        if sy is None:
            sy = sx
        a, b, c, d, e, f = self.m
        self.m = (a * sx, b * sx, c * sy, d * sy, e, f)

    def tp(self, x, y):
        a, b, c, d, e, f = self.m
        return (a * x + c * y + e, b * x + d * y + f)

    def k(self):
        a, b, c, d, e, f = self.m
        return math.sqrt(abs(a * d - b * c)) or 1.0

    # ---- paths ----
    def begin(self):
        self.subs = []
        self.cur = None

    def move(self, x, y):
        self.cur = [self.tp(x, y)]
        self.subs.append([self.cur, False])

    def line(self, x, y):
        if self.cur is None:
            self.move(x, y)
        else:
            self.cur.append(self.tp(x, y))

    @staticmethod
    def _n(*pts):
        L = 0.0
        for i in range(len(pts) - 1):
            L += abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1])
        return max(4, min(48, int(L / 3)))

    def quad(self, cx, cy, x, y):
        if self.cur is None:
            self.move(cx, cy)
        p0 = self.cur[-1]
        p1 = self.tp(cx, cy)
        p2 = self.tp(x, y)
        n = self._n(p0, p1, p2)
        for i in range(1, n + 1):
            t = i / n
            u = 1 - t
            self.cur.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0], u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))

    def bez(self, c1x, c1y, c2x, c2y, x, y):
        if self.cur is None:
            self.move(c1x, c1y)
        p0 = self.cur[-1]
        p1, p2, p3 = self.tp(c1x, c1y), self.tp(c2x, c2y), self.tp(x, y)
        n = self._n(p0, p1, p2, p3)
        for i in range(1, n + 1):
            t = i / n
            u = 1 - t
            a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
            self.cur.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))

    def close(self):
        if self.subs:
            self.subs[-1][1] = True

    @staticmethod
    def _sweep(a0, a1, ccw):
        if (not ccw and a1 - a0 >= TAU) or (ccw and a0 - a1 >= TAU):
            return TAU, True
        if not ccw:
            return (a1 - a0) % TAU, False
        return -((a0 - a1) % TAU), False

    def ellipse(self, x, y, rx, ry, rot=0.0, a0=0.0, a1=TAU, ccw=False):
        rx, ry = max(0.1, rx), max(0.1, ry)
        sweep, full = self._sweep(a0, a1, ccw)
        cr, sr = math.cos(rot), math.sin(rot)
        n = max(10, min(72, int(abs(sweep) * max(rx, ry) * self.k() / 4) + 8))
        pts = []
        for i in range(n if full else n + 1):
            a = a0 + sweep * i / n
            px, py = math.cos(a) * rx, math.sin(a) * ry
            pts.append(self.tp(x + px * cr - py * sr, y + px * sr + py * cr))
        if full or self.cur is None:
            self.cur = pts
            self.subs.append([pts, full])
        else:
            self.cur.extend(pts)

    def arc(self, x, y, r, a0, a1, ccw=False):
        self.ellipse(x, y, r, r, 0.0, a0, a1, ccw)

    def circle(self, x, y, r):
        self.ellipse(x, y, r, r)

    def rect(self, x, y, w, h):
        pts = [self.tp(x, y), self.tp(x + w, y), self.tp(x + w, y + h), self.tp(x, y + h)]
        self.cur = pts
        self.subs.append([pts, True])

    # ---- painting ----
    def _poly(self, surf, pts, col, aa=None):
        if len(pts) < 3:
            return
        if self.aa if aa is None else aa:
            ip = _ip(pts)
            gfxdraw.filled_polygon(surf, ip, col)
            gfxdraw.aapolygon(surf, ip, col)
        else:
            pygame.draw.polygon(surf, col, pts)

    def _paint(self, polys, col):
        """Paint polygons in one colour, with correct alpha blending."""
        polys = [p for p in polys if len(p) >= 3]
        if not polys or col[3] <= 0:
            return
        if col[3] >= 255 or (self.aa and len(polys) == 1):
            for p in polys:
                self._poly(self.surf, p, col)
            return
        xs = [q[0] for p in polys for q in p]
        ys = [q[1] for p in polys for q in p]
        sw, sh = self.surf.get_size()
        x0, y0 = max(0, int(min(xs)) - 2), max(0, int(min(ys)) - 2)
        x1, y1 = min(sw, int(max(xs)) + 3), min(sh, int(max(ys)) + 3)
        if x1 <= x0 or y1 <= y0:
            return
        layer = pygame.Surface((x1 - x0, y1 - y0), pygame.SRCALPHA)
        solid = col[:3] + (255,)
        for p in polys:
            pygame.draw.polygon(layer, solid, [(q[0] - x0, q[1] - y0) for q in p])
        layer.set_alpha(col[3])
        self.surf.blit(layer, (x0, y0))

    def fill(self, col):
        self._paint([s for s, _ in self.subs], _col(col, self.alpha))

    def fill_linear(self, x0, y0, x1, y1, stops, bands=14):
        """Fill the path with a linear gradient between two points (local coordinates)."""
        P0, P1 = self.tp(x0, y0), self.tp(x1, y1)
        gx, gy = P1[0] - P0[0], P1[1] - P0[1]
        L2 = gx * gx + gy * gy or 1.0

        def s_of(p):
            return ((p[0] - P0[0]) * gx + (p[1] - P0[1]) * gy) / L2
        for pts, _ in self.subs:
            if len(pts) < 3:
                continue
            for i in range(bands):
                lo = -1e9 if i == 0 else i / bands
                hi = 1e9 if i == bands - 1 else (i + 1) / bands
                poly = _clip(pts, lambda p, lo=lo: s_of(p) - lo)
                poly = _clip(poly, lambda p, hi=hi: hi - s_of(p))
                if len(poly) >= 3:
                    col = _col(_stop_col(stops, (i + 0.5) / bands), self.alpha)
                    if col[3] >= 255:
                        self._poly(self.surf, poly, col, aa=False)
                    else:
                        self._paint([poly], col)
            if self.aa:
                mid = _col(_stop_col(stops, 0.5), self.alpha)
                ip = _ip(pts)
                gfxdraw.aapolygon(self.surf, ip, mid)

    def fill_radial(self, cx0, cy0, r0, cx1, cy1, r1, stops, rings=12):
        """Radial gradient from the inner circle (offset 0) to the outer circle (offset 1)."""
        subs = [s for s, _ in self.subs if len(s) >= 3]
        if not subs:
            return
        target = self.surf
        layer = None
        if self.alpha < 1:
            layer = pygame.Surface(target.get_size(), pygame.SRCALPHA)
            self.surf = layer
        k = self.k()
        a_save = self.alpha
        self.alpha = 1.0
        base = _col(_stop_col(stops, 1.0))
        self._paint(subs, base)
        N = 24
        for i in range(1, rings + 1):
            u = i / (rings + 1)
            c = self.tp(cx1 + (cx0 - cx1) * u, cy1 + (cy0 - cy1) * u)
            R = (r1 + (r0 - r1) * u) * k
            if R <= 0.5:
                continue
            col = _col(_stop_col(stops, 1 - u))
            for pts in subs:
                poly = pts
                for j in range(N):
                    ph = TAU * (j + 0.5) / N
                    cs, sn = math.cos(ph), math.sin(ph)
                    lim = R * math.cos(math.pi / N)
                    poly = _clip(poly, lambda p, cs=cs, sn=sn, c=c, lim=lim: lim - ((p[0] - c[0]) * cs + (p[1] - c[1]) * sn))
                    if len(poly) < 3:
                        break
                if len(poly) >= 3:
                    self._poly(self.surf, poly, col, aa=False)
        self.alpha = a_save
        if layer is not None:
            self.surf = target
            layer.set_alpha(int(255 * a_save))
            target.blit(layer, (0, 0))

    def _stroke_polys(self, pts, closed, w, cap):
        # drop repeated points
        P = [pts[0]]
        for p in pts[1:]:
            if abs(p[0] - P[-1][0]) + abs(p[1] - P[-1][1]) > 0.01:
                P.append(p)
        hw = w / 2
        if len(P) < 2:
            if cap == 'round':
                return [self._circle_pts(P[0], hw)]
            return []
        polys = []
        if closed or len(P) <= 6:
            segs = list(zip(P, P[1:] + ([P[0]] if closed else [])))
            for a, b in segs:
                dx, dy = b[0] - a[0], b[1] - a[1]
                L = math.hypot(dx, dy) or 1
                nx, ny = -dy / L * hw, dx / L * hw
                polys.append([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)])
            if hw > 1.2:
                joints = P if closed else P[1:-1]
                for p in joints:
                    polys.append(self._circle_pts(p, hw))
            if not closed and cap == 'round' and hw > 0.8:
                polys.append(self._circle_pts(P[0], hw))
                polys.append(self._circle_pts(P[-1], hw))
            return polys
        left, right = [], []
        n = len(P)
        for i in range(n):
            if i == 0:
                dx, dy = P[1][0] - P[0][0], P[1][1] - P[0][1]
                L = math.hypot(dx, dy) or 1
                tx, ty, sc = dx / L, dy / L, 1.0
            elif i == n - 1:
                dx, dy = P[-1][0] - P[-2][0], P[-1][1] - P[-2][1]
                L = math.hypot(dx, dy) or 1
                tx, ty, sc = dx / L, dy / L, 1.0
            else:
                ax, ay = P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]
                bx, by = P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]
                la, lb = math.hypot(ax, ay) or 1, math.hypot(bx, by) or 1
                ax, ay, bx, by = ax / la, ay / la, bx / lb, by / lb
                tx, ty = ax + bx, ay + by
                L = math.hypot(tx, ty)
                if L < 1e-6:
                    tx, ty, L = ax, ay, 1
                tx, ty = tx / L, ty / L
                cosh = tx * ax + ty * ay
                sc = min(2.0, 1.0 / max(0.5, cosh))
            nx, ny = -ty * hw * sc, tx * hw * sc
            left.append((P[i][0] + nx, P[i][1] + ny))
            right.append((P[i][0] - nx, P[i][1] - ny))
        poly = left + right[::-1]
        polys.append(poly)
        if cap == 'round' and hw > 0.8:
            polys.append(self._circle_pts(P[0], hw))
            polys.append(self._circle_pts(P[-1], hw))
        return polys

    @staticmethod
    def _circle_pts(c, r):
        n = max(8, min(28, int(r * 2)))
        return [(c[0] + math.cos(TAU * i / n) * r, c[1] + math.sin(TAU * i / n) * r) for i in range(n)]

    def stroke(self, col, width=1.0, cap='butt'):
        col = _col(col, self.alpha)
        w = width * self.k()
        if self.aa and w <= 1.6:
            # thin lines: antialiased polylines
            for pts, closed in self.subs:
                if len(pts) >= 2:
                    if col[3] >= 250:
                        pygame.draw.aalines(self.surf, col[:3], closed, _ip(pts))
                    else:
                        ip = _ip(pts)
                        for i in range(len(ip) - 1):
                            gfxdraw.line(self.surf, ip[i][0], ip[i][1], ip[i + 1][0], ip[i + 1][1], col)
            return
        polys = []
        for pts, closed in self.subs:
            if len(pts) >= 1:
                polys.extend(self._stroke_polys(pts, closed, w, cap))
        if col[3] >= 255:
            for p in polys:
                self._poly(self.surf, p, col)
        else:
            self._paint(polys, col)

    # ---- clipping (sprite mode only): draw into a layer, then keep only what's inside the path ----
    def clip_push(self):
        subs = [s for s, _ in self.subs if len(s) >= 3]
        self._clips.append((self.surf, subs))
        self.surf = pygame.Surface(self.surf.get_size(), pygame.SRCALPHA)

    def clip_pop(self):
        layer = self.surf
        self.surf, subs = self._clips.pop()
        mask = pygame.Surface(layer.get_size(), pygame.SRCALPHA)
        for s in subs:
            pygame.draw.polygon(mask, (255, 255, 255, 255), s)
        layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.surf.blit(layer, (0, 0))


# ===================================================================================
#  Fish
# ===================================================================================
# How fast each body shape animates (radians of phase per second of swimming).
RATE = {'fish': 6, 'koi': 5.5, 'lion': 5, 'eel': 4, 'ray': 2.2, 'jelly': 2.4, 'squid': 3.2, 'puffer': 3.5,
        'angler': 2.2, 'seahorse': 2.4, 'leviathan': 1.5, 'whale': 1.1, 'crab': 2.6, 'bloop': 1.0, 'watcher': 0.9, 'nessie': 1.3}


def palette(sp, mut):
    return fishart.palette(sp, mut)


def draw_fish(c, sp, L, mut=None, sil=False, ph=0.0):
    """Draw a fish facing right, centred on the pen's origin, L pixels long (the painting lives in fishart.py)."""
    fishart.draw_fish(c, sp, L, mut, sil, ph)


def _blur(surf, radius):
    if radius < 1:
        return surf
    fn = getattr(pygame.transform, 'gaussian_blur', None)
    if fn:
        try:
            return fn(surf, int(radius))
        except (pygame.error, ValueError):
            pass
    w, h = surf.get_size()
    f = max(2, int(radius))
    small = pygame.transform.smoothscale(surf, (max(1, w // f), max(1, h // f)))
    return pygame.transform.smoothscale(small, (w, h))


def _glowify(surf, col, radius):
    g = surf.copy()
    g.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MIN)
    g.fill((col[0], col[1], col[2], 0), special_flags=pygame.BLEND_RGBA_ADD)
    w, h = surf.get_size()
    k = 3 if min(w, h) > 24 else 1   # blur a smaller copy: a glow doesn't need detail, and it's ~10x faster
    if k > 1:
        small = pygame.transform.smoothscale(g, (max(1, w // k), max(1, h // k)))
        g = pygame.transform.smoothscale(_blur(small, max(1, radius // k + 1)), (w, h))
    else:
        g = _blur(g, radius)
    out = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    out.blit(g, (0, 0))
    out.blit(g, (0, 0))
    out.blit(surf, (0, 0))
    return out


class Sprite:
    __slots__ = ('surf', 'ox', 'oy')

    def __init__(self, surf, ox, oy):
        self.surf, self.ox, self.oy = surf, ox, oy


_frames = {}
_xform = OrderedDict()
FRAMES = 16
_mem = {'frames': 0, 'xform': 0}
FRAME_BUDGET = 260 * 1024 * 1024     # bytes of painted fish frames kept around
XFORM_BUDGET = 160 * 1024 * 1024     # bytes of turned/scaled copies


def _bytes(surf):
    w, h = surf.get_size()
    return w * h * 4


def _render(sp, mut, sil, L, frame, nframes):
    """Paint one animation frame of a fish (facing right) at length L and cache it."""
    key = (sp.id, mut, sil, L, frame, nframes)
    ss = 1 if L > 400 else 2 if L > 60 else 3
    pal = fishart.palette(sp, mut)
    glow = (pal.glow and not sil)
    pad = 16 if glow else 4
    ew, eh = fishart.extent(sp)
    hw = L * ew + pad
    hh = L * eh + pad
    W, H = int(hw * 2 * ss), int(hh * 2 * ss)
    big = pygame.Surface((W, H), pygame.SRCALPHA)
    c = Pen(big, aa=False)
    c.translate(W / 2, H / 2)
    c.scale(ss)
    ph = TAU * frame / nframes
    draw_fish(c, sp, L, mut, sil, ph)
    surf = pygame.transform.smoothscale(big, (W // ss, H // ss)) if ss > 1 else big
    if sil:
        surf.fill((255, 255, 255, 209), special_flags=pygame.BLEND_RGBA_MULT)
    if glow:
        surf = _glowify(surf, pal.glow, 7)
    r = surf.get_bounding_rect(min_alpha=4)
    if r.w == 0 or r.h == 0:
        r = pygame.Rect(0, 0, 1, 1)
    crop = surf.subsurface(r).copy()
    s = Sprite(crop, (W // ss) / 2 - r.x, (H // ss) / 2 - r.y)
    _frames[key] = s
    _mem['frames'] += _bytes(crop)
    if len(_frames) > 5000 or _mem['frames'] > FRAME_BUDGET:
        for k in list(_frames.keys())[:max(1, len(_frames) // 4)]:
            _mem['frames'] -= _bytes(_frames.pop(k).surf)
        _xform.clear()
        _mem['xform'] = 0
    return s


_pending = OrderedDict()


def fish_frame(sp, mut, sil, L, frame, nframes=FRAMES, now=False):
    """A cached picture of a fish (facing right) at length L for one animation frame.
    A frame that isn't painted yet is queued, and the nearest finished frame stands in for it,
    so a new fish never makes the game stutter (see pump)."""
    L = max(8, int(round(L)))
    key = (sp.id, mut, sil, L, frame, nframes)
    s = _frames.get(key)
    if s is not None:
        return s
    if not now:
        for d in range(1, nframes // 2 + 1):
            for fr in ((frame - d) % nframes, (frame + d) % nframes):
                s = _frames.get((sp.id, mut, sil, L, fr, nframes))
                if s is not None:
                    if key not in _pending:
                        _pending[key] = (sp, mut, sil, L, frame, nframes)
                    return s
    s = _render(sp, mut, sil, L, frame, nframes)
    if not now:
        for k in range(1, nframes):
            fr = (frame + k) % nframes
            kk = (sp.id, mut, sil, L, fr, nframes)
            if kk not in _frames and kk not in _pending:
                _pending[kk] = (sp, mut, sil, L, fr, nframes)
    return s


def pump(budget=0.005):
    """Paint queued fish frames for a few milliseconds. Called once per screen frame."""
    if not _pending:
        return
    t0 = time.perf_counter()
    while _pending and time.perf_counter() - t0 < budget:
        key, args = _pending.popitem(last=False)
        if key not in _frames:
            _render(*args)


_halos = OrderedDict()
_halo_x = OrderedDict()


def _disc(r):
    return [(dx, dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1) if dx * dx + dy * dy <= r * r + r * 0.5]


_DISC2, _DISC6 = _disc(2), _disc(6)


def _halo(surf, col):
    """A soft light that follows a fish picture's own outline (Sonar Mk III): a thin rim hugging the body
    and a faint glow beyond it, nothing inside the fish."""
    key = (id(surf), col)
    v = _halos.get(key)
    if v is not None and v[2] is surf:
        _halos.move_to_end(key)
        return v
    w, h = surf.get_size()
    pad = 9
    m = pygame.mask.from_surface(surf, 60)
    size = (w + 2 * pad, h + 2 * pad)
    rim, glow = pygame.mask.Mask(size), pygame.mask.Mask(size)
    for dx, dy in _DISC2:
        rim.draw(m, (pad + dx, pad + dy))
    for dx, dy in _DISC6:
        glow.draw(m, (pad + dx, pad + dy))
    rim.erase(m, (pad, pad))
    glow.erase(m, (pad, pad))
    rgb = hexc(col) if isinstance(col, str) else tuple(col[:3])
    soft = glow.to_surface(setcolor=rgb + (90,), unsetcolor=rgb + (0,))
    soft = _blur(soft, 3)
    line = rim.to_surface(setcolor=mix(rgb, (255, 255, 255), 0.35) + (200,), unsetcolor=(0, 0, 0, 0))
    soft.blit(line, (0, 0))
    v = (soft, pad, surf)
    _halos[key] = v
    _mem['halo'] = _mem.get('halo', 0) + _bytes(soft)
    if len(_halos) > 700 or _mem['halo'] > 32 * 1024 * 1024:
        for _ in range(max(1, len(_halos) // 4)):
            _, old = _halos.popitem(last=False)
            _mem['halo'] -= _bytes(old[0])
    return v


def _halo_for(base, flip, abk, sbk, col):
    """The outline light for one animation frame, turned and scaled the same way as the fish."""
    key = (id(base), flip, abk, sbk, col)
    v = _halo_x.get(key)
    if v is not None and v[1] is base:
        _halo_x.move_to_end(key)
        return v[0]
    hs = _halo(base.surf, col)[0]
    if flip:
        hs = pygame.transform.flip(hs, True, False)
    scale = sbk / 50
    if abk != 0 or abs(scale - 1) >= 0.01:
        hs = pygame.transform.rotozoom(hs, -math.degrees(abk * 0.05), scale)
    _halo_x[key] = (hs, base)
    _mem['halox'] = _mem.get('halox', 0) + _bytes(hs)
    if len(_halo_x) > 1200 or _mem['halox'] > 48 * 1024 * 1024:
        for _ in range(max(1, len(_halo_x) // 4)):
            _, old = _halo_x.popitem(last=False)
            _mem['halox'] -= _bytes(old[0])
    return hs


def blit_fish(dst, sp, mut, sil, Lbase, size, frame, x, y, flip, ang, alpha=1.0, nframes=FRAMES, sx=1.0, outline=None, oa=1.0):
    """Draw a cached fish frame scaled to `size`, mirrored if flip, rotated by ang (radians, clockwise on screen).
    outline: a colour to light up the fish's own outline with (Sonar Mk III), at strength oa."""
    base = fish_frame(sp, mut, sil, Lbase, frame, nframes)
    sc = size / max(1, int(round(Lbase)))
    abk = int(round(ang / 0.05))
    sbk = int(round(sc * 50))
    key = (id(base), flip, abk, sbk)
    v = _xform.get(key)
    if v is None:
        surf, ox, oy = base.surf, base.ox, base.oy
        if flip:
            surf = pygame.transform.flip(surf, True, False)
            ox = surf.get_width() - ox
        scale = sbk / 50
        a = abk * 0.05
        if abk == 0 and abs(scale - 1) < 0.01:
            v = (surf, ox, oy)
        else:
            w, h = surf.get_size()
            deg = -math.degrees(a)
            rs = pygame.transform.rotozoom(surf, deg, scale)
            # where the fish's origin ends up after rotating about the picture's centre
            cx, cy = w / 2, h / 2
            dx, dy = (ox - cx) * scale, (oy - cy) * scale
            ca, sa = math.cos(a), math.sin(a)
            rx, ry = dx * ca - dy * sa, dx * sa + dy * ca
            v = (rs, rs.get_width() / 2 + rx, rs.get_height() / 2 + ry)
        _xform[key] = v
        _mem['xform'] += _bytes(v[0])
        if len(_xform) > 2500 or _mem['xform'] > XFORM_BUDGET:
            for _ in range(max(1, len(_xform) // 5)):
                _, old = _xform.popitem(last=False)
                _mem['xform'] -= _bytes(old[0])
    else:
        _xform.move_to_end(key)
    surf, ox, oy = v
    hs = _halo_for(base, flip, abk, sbk, outline) if outline is not None else None
    if sx < 0.97:
        # squash sideways while the fish turns around
        w, h = surf.get_size()
        nw = max(1, int(w * max(0.06, sx)))
        if hs is not None:
            hs = pygame.transform.smoothscale(hs, (max(1, int(hs.get_width() * max(0.06, sx))), hs.get_height()))
        surf = pygame.transform.smoothscale(surf, (nw, h))
        ox = ox * nw / w
    if hs is not None:
        # the outline picture is the fish picture padded evenly, so their centres line up
        cx, cy = x - ox + surf.get_width() / 2, y - oy + surf.get_height() / 2
        hs.set_alpha(int(255 * clamp(oa * alpha, 0, 1)))
        dst.blit(hs, (cx - hs.get_width() / 2, cy - hs.get_height() / 2))
        hs.set_alpha(255)
    if alpha < 0.99:
        surf.set_alpha(int(255 * clamp(alpha, 0, 1)))
        dst.blit(surf, (x - ox, y - oy))
        surf.set_alpha(255)
    else:
        dst.blit(surf, (x - ox, y - oy))


_portraits = {}


def portrait(sp, mut, w, h, sil=False, frame=3):
    """A small, static fish picture fitted into a w x h box (for menus)."""
    key = (sp.id, mut, w, h, sil, frame)
    s = _portraits.get(key)
    if s is not None:
        return s
    if sp.shape == 'leviathan':
        L = w * 1.0
    elif sp.shape in ('jelly', 'seahorse'):
        L = min(w, h) * 0.95
    else:
        L = min(w * 0.82, h * 1.9)
    fr = fish_frame(sp, mut, sil, L, frame, now=True)
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    ox = w / 2 - (w * 0.15 if sp.shape == 'leviathan' else 0)
    out.blit(fr.surf, (ox - fr.ox, h / 2 - fr.oy))
    _portraits[key] = out
    return out


def draw_portrait(dst, sp, mut, rect, sil=False, t=0.0):
    """An animated fish picture fitted into a box (the Fishpedia)."""
    x, y, w, h = rect
    lev = sp.shape == 'leviathan'
    if lev:
        L = w * 1.0
    elif sp.shape in ('jelly', 'seahorse'):
        L = min(w, h) * 0.95
    else:
        L = min(w * 0.82, h * 1.9)
    n = 24 if lev else FRAMES
    frame = int(t * RATE.get(sp.shape, 6) * 0.55 / TAU * n) % n
    fr = fish_frame(sp, mut, sil, L, frame, n)
    old = dst.get_clip()
    box = pygame.Rect(int(x), int(y), int(w), int(h))
    dst.set_clip(box.clip(old) if old else box)
    dst.blit(fr.surf, (x + w / 2 - (w * 0.15 if lev else 0) - fr.ox, y + h / 2 - fr.oy))
    dst.set_clip(old)


# ===================================================================================
#  The cat & boat (drawn every frame, so other players' boats can look different)
# ===================================================================================
_boats = {}
_rot = OrderedDict()


def _boat_parts(b, S):
    """The boat drawn once, in two layers: what sits behind the cat (cabin, mast, dome) and the hull in front."""
    key = (b.id, round(S, 3))
    v = _boats.get(key)
    if v is not None:
        return v
    tier = b.tier
    hl = 95 + min(tier, 3) * 16 + max(0, tier - 3) * 10
    ss = 2
    x0, y0, x1, y1 = -hl - 12, -160, hl + 26, 48
    W, H = int((x1 - x0) * S * ss), int((y1 - y0) * S * ss)
    out = []
    for layer in ('back', 'front'):
        big = pygame.Surface((W, H), pygame.SRCALPHA)
        c = Pen(big)
        c.scale(S * ss)
        c.translate(-x0, -y0)
        if layer == 'back':
            if tier == 1:
                c.begin()
                c.move(-30, -6)
                c.line(-30, -150)
                c.stroke('#6b4a2a', 5)
            elif tier == 2:
                for col, rr in (('#7a8590', (-hl + 14, -62, 70, 56)), ('#3a4450', (-hl + 14, -68, 76, 8)), ('#2a3036', (-hl + 70, -98, 12, 32))):
                    c.begin()
                    c.rect(*rr)
                    c.fill(col)
                c.begin()
                c.rect(-hl + 26, -50, 18, 16)
                c.rect(-hl + 52, -50, 18, 16)
                c.fill('#ffd88a')
            elif tier == 4:
                # a whaling schooner: two masts, gaff sails and rigging
                for mx, mh in ((-hl + 70, 150), (14, 140)):
                    c.begin()
                    c.move(mx, -8)
                    c.line(mx, -mh)
                    c.stroke('#4a3020', 5)
                    c.begin()
                    c.move(mx + 4, -mh + 8)
                    c.line(mx + 58, -mh + 22)
                    c.line(mx + 62, -26)
                    c.line(mx + 4, -22)
                    c.close()
                    c.fill_linear(0, -mh, 0, -22, [(0, '#f2ead8'), (1, '#cfc4aa')], bands=8)
                    c.stroke((90, 70, 50, 150), 1.4)
                c.begin()
                c.move(-hl + 70, -150)
                c.line(-hl - 8, -16)
                c.move(-hl + 70, -150)
                c.line(14, -140)
                c.move(14, -140)
                c.line(hl + 40, -30)
                c.stroke((60, 45, 30, 170), 1.3)
                c.begin()
                c.rect(-hl + 62, -118, 16, 8)
                c.fill('#5a3a24')
            elif tier == 5:
                # an icebreaker: a red and white bridge and a funnel
                c.begin()
                c.rect(-hl + 20, -66, 92, 56)
                c.fill('#f2f2ee')
                c.begin()
                c.rect(-hl + 16, -74, 100, 9)
                c.fill('#c8322a')
                for k in range(4):
                    c.begin()
                    c.rect(-hl + 28 + k * 21, -56, 13, 11)
                    c.fill('#7fd0ff')
                c.begin()
                c.move(-hl + 84, -74)
                c.line(-hl + 90, -118)
                c.line(-hl + 114, -118)
                c.line(-hl + 112, -74)
                c.fill('#c8322a')
                c.begin()
                c.rect(-hl + 89, -126, 26, 9)
                c.fill('#1d1d22')
                c.begin()
                c.move(-hl + 40, -74)
                c.line(-hl + 40, -104)
                c.stroke('#5a6470', 3)
            elif tier == 6:
                # a hadal sub: a conning tower with a periscope
                c.begin()
                c.move(-hl + 40, -6)
                c.line(-hl + 52, -64)
                c.line(-hl + 104, -64)
                c.line(-hl + 116, -6)
                c.fill_linear(0, -64, 0, -6, [(0, '#ffb43a'), (1, '#d97a10')], bands=8)
                c.begin()
                c.circle(-hl + 78, -40, 11)
                c.fill('#7ed6ff')
                c.stroke('#8a5a10', 3)
                c.begin()
                c.move(-hl + 64, -64)
                c.line(-hl + 64, -96)
                c.line(-hl + 78, -96)
                c.stroke('#5a6470', 3.5)
            elif tier == 3:
                c.begin()
                c.arc(-hl + 52, -26, 42, math.pi, 0)
                c.fill('#f2c14e')
                c.begin()
                c.circle(-hl + 52, -30, 22)
                c.fill('#7ed6ff')
                c.stroke('#b8862a', 5)
                c.begin()
                c.circle(-hl + 46, -36, 7)
                c.fill((255, 255, 255, 136))
        elif tier == 6:
            # the sub's hull: a fat capsule with a big viewport and a propeller
            c.begin()
            c.move(-hl - 4, -12)
            c.line(hl - 30, -16)
            c.quad(hl + 22, -14, hl + 22, 12)
            c.quad(hl + 20, 36, hl - 34, 38)
            c.line(-hl + 30, 38)
            c.quad(-hl - 8, 34, -hl - 4, -12)
            c.fill_linear(0, -16, 0, 40, [(0, '#ffc04a'), (1, '#b86a08')], bands=16)
            c.begin()
            c.circle(hl - 8, 8, 17)
            c.fill('#7ed6ff')
            c.stroke('#8a5a10', 4)
            c.begin()
            c.circle(hl - 14, 2, 5)
            c.fill((255, 255, 255, 150))
            c.begin()
            for k in range(4):
                c.circle(-hl + 50 + k * 40, 14, 4)
            c.fill((255, 255, 255, 191))
            c.begin()
            c.move(-hl - 6, -8)
            c.line(-hl - 14, -20)
            c.move(-hl - 6, 30)
            c.line(-hl - 14, 42)
            c.stroke('#5a6470', 5, 'round')
            c.begin()
            c.rect(-hl - 18, -8, 6, 40)
            c.fill('#3a4048')
        else:
            c.begin()
            c.move(-hl, -14)
            c.line(hl + 12, -20)
            c.quad(hl - 6, 32, hl - 56, 36)
            c.line(-hl + 46, 36)
            c.quad(-hl + 6, 30, -hl, -14)
            c.fill_linear(0, -14, 0, 40, [(0, b.col), (1, mix(b.col, "#000000", 0.45))], bands=16)
            if tier == 4:
                c.begin()
                for k in range(3):
                    c.move(-hl + 8, -4 + k * 11)
                    c.line(hl - 4 - k * 14, -8 + k * 11)
                c.stroke((0, 0, 0, 70), 1.4)
                c.begin()
                c.move(hl + 8, -20)
                c.line(hl + 54, -34)
                c.stroke('#4a3020', 4, 'round')
            elif tier == 5:
                c.begin()
                c.move(hl - 40, -20)
                c.line(hl + 12, -20)
                c.quad(hl - 2, 14, hl - 30, 30)
                c.line(hl - 64, 30)
                c.close()
                c.fill((242, 242, 238, 235))
            c.begin()
            c.rect(-hl, -17, 2 * hl + 12, 5)
            c.fill((255, 255, 255, 89))
            c.begin()
            c.move(-hl + 10, 8)
            c.line(hl - 12, 6)
            c.stroke((0, 0, 0, 64), 2)
            if tier >= 2:
                c.begin()
                for k in range(5):
                    c.circle(-hl + 30 + k * 36, 14, 3)
                c.fill((255, 255, 255, 191))
        surf = pygame.transform.smoothscale(big, (W // ss, H // ss))
        out.append((surf, -x0 * S, -y0 * S))
    _boats[key] = out
    return out


def _blit_rotated(dst, part, x, y, ang):
    """Blit a cached picture whose origin is at (ox, oy), turned by ang radians (clockwise on screen)."""
    surf, ox, oy = part
    q = int(round(ang / 0.004))
    key = (id(surf), q)
    v = _rot.get(key)
    if v is None:
        a = q * 0.004
        if q == 0:
            v = (surf, ox, oy)
        else:
            w, h = surf.get_size()
            rs = pygame.transform.rotozoom(surf, -math.degrees(a), 1)
            dx, dy = ox - w / 2, oy - h / 2
            ca, sa = math.cos(a), math.sin(a)
            v = (rs, rs.get_width() / 2 + dx * ca - dy * sa, rs.get_height() / 2 + dx * sa + dy * ca)
        _rot[key] = v
        if len(_rot) > 600:
            for _ in range(150):
                _rot.popitem(last=False)
    else:
        _rot.move_to_end(key)
    rs, rx, ry = v
    dst.blit(rs, (x - rx, y - ry))


def draw_boat_cat(c, x, y, lk):
    """lk: D(fur, boat, rod, ench, biome, mode, ten, t, S, hop)."""
    S, t = lk.S, lk.t
    b = BOAT.get(lk.boat) or BOAT['dinghy']
    roll = math.sin(t * 1.3) * 0.03 + (math.sin(t * 7) * 0.02 if lk.mode == 'reel' else 0)
    by = y + math.sin(t * 1.6) * 2.5 * S
    back, front = _boat_parts(b, S)
    _blit_rotated(c.surf, back, x, by, roll)
    c.save()
    c.translate(x, by)
    c.rotate(roll)
    c.scale(S)
    if b.tier == 1:
        c.begin()
        c.move(-26, -146)
        c.quad(10 + math.sin(t) * 6, -90, -26, -20)
        c.fill('#f4efe2')
    draw_cat(c, 22, -14, lk)
    c.restore()
    _blit_rotated(c.surf, front, x, by, roll)


def draw_cat(c, x, y, lk):
    t = lk.t
    fur = hexc(lk.fur or '#f4a53c')
    dk, cr, ink = mix(fur, '#000000', 0.25), mix(fur, '#ffffff', 0.7), (42, 26, 18)
    fight = lk.mode in ('reel', 'bite')
    happy = lk.mode in ('card', 'landing')
    c.save()
    c.translate(x, y - (lk.hop or 0))
    tw = math.sin(t * (8 if fight else 3)) * (5 if fight else 12)
    c.begin()
    c.move(-26, -8)
    c.bez(-64, -6, -66, -44 + tw, -46, -66 + tw * 0.7)
    c.stroke(fur, 10, 'round')
    c.begin()
    c.circle(-46, -66 + tw * 0.7, 5.5)
    c.fill(dk)
    c.begin()
    c.ellipse(-6, -24, 25, 25)
    c.fill(fur)
    c.begin()
    c.ellipse(4, -20, 13, 17)
    c.fill(cr)
    c.begin()
    for i in range(3):
        c.move(-28, -34 + i * 8)
        c.line(-19, -33 + i * 8)
    c.stroke(dk, 3.5)
    hx = 8
    hy = -64 + (3 if fight else 0) + math.sin(t * 1.6)
    c.begin()
    for s in (-1, 1):
        c.move(hx + s * 20, hy - 8)
        c.line(hx + s * 17, hy - 37 + (4 if fight else 0))
        c.line(hx + s * 3, hy - 18)
    c.fill(fur)
    c.begin()
    c.circle(hx, hy, 21)
    c.fill(fur)
    c.begin()
    for s in (-1, 1):
        c.move(hx + s * 15, hy - 13)
        c.line(hx + s * 15, hy - 29)
        c.line(hx + s * 7, hy - 18)
    c.fill('#ffb3c1')
    c.begin()
    c.ellipse(hx + 1, hy + 8, 10, 7)
    c.fill(cr)
    for s in (-8, 8):
        ex, ey = hx + s, hy - 2
        if happy:
            c.begin()
            c.arc(ex, ey + 3, 5, math.pi * 1.1, math.pi * 1.9)
            c.stroke(ink, 3, 'round')
        elif t % 4.1 < 0.13:
            c.begin()
            c.move(ex - 4, ey)
            c.line(ex + 4, ey)
            c.stroke(ink, 3, 'round')
        else:
            c.begin()
            c.ellipse(ex + 1.5, ey, 3.8, 3.4 if fight else 5.2)
            c.fill(ink)
            c.begin()
            c.circle(ex + 2.6, ey - 2, 1.5)
            c.fill((255, 255, 255))
            if fight:
                c.begin()
                c.move(ex - 5, ey - 8 + (2 if s > 0 else -1))
                c.line(ex + 5, ey - 8 + (-1 if s > 0 else 2))
                c.stroke(ink, 2, 'round')
    c.begin()
    c.circle(hx - 14, hy + 6, 3.6)
    c.circle(hx + 14, hy + 6, 3.6)
    c.fill((255, 120, 150, 115))
    c.begin()
    c.move(hx - 3, hy + 5)
    c.line(hx + 3, hy + 5)
    c.line(hx, hy + 8.5)
    c.fill('#ff8fa8')
    c.begin()
    c.move(hx, hy + 8.5)
    c.quad(hx - 3, hy + 13, hx - 6, hy + 10.5)
    c.move(hx, hy + 8.5)
    c.quad(hx + 3, hy + 13, hx + 6, hy + 10.5)
    c.stroke(ink, 1.5)
    c.begin()
    for s in (-1, 1):
        c.move(hx + s * 9, hy + 7)
        c.line(hx + s * 27, hy + 3)
        c.move(hx + s * 9, hy + 10)
        c.line(hx + s * 27, hy + 11)
    c.stroke((92, 70, 55), 1)
    if lk.biome == 'volcano':
        c.begin()
        c.rect(hx - 20, hy - 15, 40, 6)
        c.fill('#ff4f6d')
    else:
        c.begin()
        c.ellipse(hx, hy - 17, 31, 7)
        c.fill('#f3cf6a')
        c.begin()
        c.ellipse(hx, hy - 19, 17, 14, 0, math.pi, TAU)
        c.fill('#f3cf6a')
        c.begin()
        c.rect(hx - 17, hy - 22, 34, 4)
        c.fill('#5ccfff' if lk.biome == 'trench' else '#d1495b')
    c.begin()
    c.move(-14, -40)
    c.quad(8, -36, 26, -46)
    c.stroke(fur, 9, 'round')
    c.begin()
    c.circle(27, -47, 5.5)
    c.fill(cr)
    rod = ROD.get(lk.rod) or ROD['starter']
    bend = 22 * (0.4 + (lk.ten or 0)) if lk.mode == 'reel' else 9 if lk.mode == 'bite' else 0
    c.begin()
    c.move(16, -40)
    c.quad(66, -70 + bend * 0.4, 90, -104 + bend)
    if lk.ench and lk.ench in ENCH:
        c.stroke(rgba(ENCH[lk.ench].col, 0.45 + 0.35 * math.sin(t * 4)), 7, 'round')
    c.stroke(mix(rod.col, '#000000', 0.3), 5, 'round')
    c.stroke(rod.col, 2.2, 'round')
    if rod.tip:
        k = 0.55 + 0.45 * math.sin(t * 3.2)
        c.begin()
        c.circle(90, -104 + bend, 9)
        c.fill(rgba(rod.tip, 0.18 * k))
        c.begin()
        c.circle(90, -104 + bend, 5)
        c.fill(rgba(rod.tip, 0.4 + 0.3 * k))
        c.begin()
        c.circle(90, -104 + bend, 2.4)
        c.fill((255, 255, 255))
    c.begin()
    c.circle(26, -36, 5)
    c.fill('#9aa7b4')
    c.restore()


def mut_name(m):
    return MUT[m].name if m in MUT else ''


def draw_ability_icon(surf, ab, x, y, r, col, glyph=None, bg=(7, 26, 46)):
    """A round badge with a little picture of a rod ability (tug, quick, freeze, slice, inferno, gravity, tidal)."""
    p = Pen(surf, aa=True)
    glyph = glyph or col
    p.begin()
    p.circle(x, y, r)
    p.fill(bg)
    p.stroke(col, max(1.5, r * 0.14))
    p.save()
    p.translate(x, y)
    p.scale(r / 12)
    if ab == 'tug':
        p.begin()
        p.move(0, 7)
        p.line(0, -6)
        p.stroke(glyph, 2.6, 'round')
        p.begin()
        p.move(-5, -1)
        p.line(0, -7.5)
        p.line(5, -1)
        p.stroke(glyph, 2.6, 'round')
    elif ab == 'quick':
        for dx in (-4, 3):
            p.begin()
            p.move(dx - 3, -6)
            p.line(dx + 3, 0)
            p.line(dx - 3, 6)
            p.stroke(glyph, 2.6, 'round')
    elif ab in ('freeze', 'tidal'):
        if ab == 'tidal':
            p.begin()
            p.move(-8, 4)
            p.quad(-4, -8, 4, -5)
            p.quad(0, -3, 2, 1)
            p.quad(5, 4, 8, 2)
            p.stroke(glyph, 2.4, 'round')
            p.begin()
            p.move(-7, 7.5)
            p.line(7, 7.5)
            p.stroke(glyph, 1.6, 'round')
        else:
            for k in range(3):
                a = k * math.pi / 3
                ca, sa = math.cos(a), math.sin(a)
                p.begin()
                p.move(-ca * 8, -sa * 8)
                p.line(ca * 8, sa * 8)
                p.stroke(glyph, 2.2, 'round')
                for s in (-1, 1):
                    bx, by = ca * 5 * s, sa * 5 * s
                    p.begin()
                    p.move(bx + (ca * s - sa) * -2.4, by + (sa * s + ca) * -2.4)
                    p.line(bx, by)
                    p.line(bx + (ca * s + sa) * -2.4, by + (sa * s - ca) * -2.4)
                    p.stroke(glyph, 1.5, 'round')
    elif ab == 'slice':
        p.begin()
        p.move(-7, 7)
        p.line(7, -7)
        p.stroke(glyph, 2.8, 'round')
        p.begin()
        for a in range(4):
            ang = a * math.pi / 2
            p.move(5, -5)
            p.line(5 + math.cos(ang) * 3.5, -5 + math.sin(ang) * 3.5)
        p.stroke((255, 255, 255), 1.3)
    elif ab == 'inferno':
        p.begin()
        p.move(0, -9)
        p.quad(8, -1, 5, 5)
        p.quad(2, 9, 0, 9)
        p.quad(-2, 9, -5, 5)
        p.quad(-8, -1, 0, -9)
        p.fill(glyph)
        p.begin()
        p.move(0, -2)
        p.quad(4, 3, 2, 6)
        p.quad(0, 8, -2, 6)
        p.quad(-4, 3, 0, -2)
        p.fill('#ffe08a')
    elif ab == 'gravity':
        p.begin()
        a, rr = 0.0, 1.0
        p.move(0, 0)
        while rr < 9:
            p.line(math.cos(a) * rr, math.sin(a) * rr)
            a += 0.35
            rr += 0.28
        p.stroke(glyph, 2.0, 'round')
        p.begin()
        p.circle(0, 0, 2.2)
        p.fill(glyph)
    elif ab == 'net':
        p.begin()
        for k in (-4, 0, 4):
            p.move(k, -7.5)
            p.quad(k * 1.3, 0, k, 7.5)
            p.move(-7.5, k)
            p.quad(0, k * 1.3, 7.5, k)
        p.stroke(glyph, 1.5, 'round')
    elif ab == 'harpoon':
        p.begin()
        p.move(-7, 7)
        p.line(6, -6)
        p.stroke(glyph, 2.2, 'round')
        p.begin()
        p.move(7.5, -7.5)
        p.line(1.5, -6)
        p.line(6, -1.5)
        p.close()
        p.fill(glyph)
        p.begin()
        p.move(-2, 2)
        p.line(-5, -1)
        p.move(0, 0)
        p.line(-3, -3)
        p.stroke(glyph, 1.4, 'round')
    elif ab == 'slowmo':
        p.begin()
        p.move(-5.5, -8)
        p.line(5.5, -8)
        p.line(0, 0)
        p.close()
        p.move(-5.5, 8)
        p.line(5.5, 8)
        p.line(0, 0)
        p.close()
        p.stroke(glyph, 1.6)
        p.begin()
        p.move(-3, 6.5)
        p.line(3, 6.5)
        p.line(0, 2.5)
        p.close()
        p.fill(glyph)
    elif ab == 'purr':
        p.begin()
        p.ellipse(0, 3, 4.6, 3.8)
        p.fill(glyph)
        p.begin()
        for tx, ty in ((-5.5, -2.5), (-2, -6), (2, -6), (5.5, -2.5)):
            p.circle(tx, ty, 2)
        p.fill(glyph)
    elif ab in ('shield', 'carapace'):
        p.begin()
        p.move(0, -8.5)
        p.line(7, -5.5)
        p.quad(7, 4, 0, 8.5)
        p.quad(-7, 4, -7, -5.5)
        p.close()
        p.stroke(glyph, 1.8)
        p.begin()
        p.move(0, -5)
        p.line(4, -3.2)
        p.quad(4, 2.5, 0, 5)
        p.close()
        p.fill(glyph)
    elif ab == 'storm':
        p.begin()
        p.move(2, -9)
        p.line(-5, 1)
        p.line(-0.5, 1)
        p.line(-2, 9)
        p.line(5.5, -2)
        p.line(1, -2)
        p.close()
        p.fill(glyph)
    elif ab == 'gold':
        p.begin()
        p.circle(0, 0, 7.5)
        p.fill(glyph)
        p.begin()
        p.circle(0, 0, 5.2)
        p.stroke((150, 100, 20), 1.2)
        p.begin()
        p.ellipse(-2.2, -2.6, 2, 1.2, -0.6)
        p.fill((255, 255, 255, 200))
    elif ab == 'phoenix':
        p.begin()
        p.move(-6, 8)
        p.quad(-6, -4, 6, -9)
        p.quad(3, -2, 6, 1)
        p.quad(0, 2, 2, 5)
        p.quad(-2, 5, -6, 8)
        p.close()
        p.fill(glyph)
        p.begin()
        p.move(-6, 8)
        p.quad(-2, 0, 4, -6)
        p.stroke((255, 240, 200), 1.1)
    elif ab == 'magnet':
        p.begin()
        p.move(-5, -6)
        p.line(-5, 1)
        p.arc(0, 1, 5, math.pi, 0, True)
        p.line(5, -6)
        p.stroke(glyph, 3.2)
        p.begin()
        p.rect(-6.6, -8.5, 3.2, 3)
        p.rect(3.4, -8.5, 3.2, 3)
        p.fill((240, 240, 250))
    elif ab == 'stars':
        p.begin()
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            rr = 8 if k % 2 == 0 else 3.4
            p.line(math.cos(a) * rr, math.sin(a) * rr + 0.5)
        p.close()
        p.fill(glyph)
    elif ab == 'anchor':
        p.begin()
        p.move(0, -6)
        p.line(0, 7)
        p.move(-4, -3)
        p.line(4, -3)
        p.stroke(glyph, 2.0, 'round')
        p.begin()
        p.move(-7, 2)
        p.quad(-6, 8, 0, 8)
        p.quad(6, 8, 7, 2)
        p.stroke(glyph, 2.0, 'round')
        p.begin()
        p.circle(0, -8, 2)
        p.stroke(glyph, 1.4)
    elif ab == 'whirl':
        for k in range(2):
            p.begin()
            a, rr = k * math.pi, 1.5
            p.move(math.cos(a) * rr, math.sin(a) * rr)
            while rr < 8.5:
                a += 0.4
                rr += 0.45
                p.line(math.cos(a) * rr, math.sin(a) * rr * 0.8)
            p.stroke(glyph, 1.8, 'round')
    elif ab == 'echo':
        p.begin()
        p.circle(-5, 0, 2.2)
        p.fill(glyph)
        for k, rr in enumerate((4.5, 8.5)):
            p.begin()
            p.arc(-5, 0, rr, -0.9, 0.9)
            p.stroke(glyph, 1.7, 'round')
    elif ab == 'barb':
        p.begin()
        p.move(3, -8)
        p.line(3, 3)
        p.quad(3, 8, -2, 8)
        p.quad(-7, 8, -7, 2)
        p.line(-4, -1)
        p.stroke(glyph, 2.0, 'round')
        p.begin()
        p.circle(3, -8.5, 1.8)
        p.stroke(glyph, 1.3)
    elif ab == 'riptide':
        for yy in (-3.5, 3.5):
            p.begin()
            p.move(-8, yy)
            p.quad(-4, yy - 4, 0, yy)
            p.quad(4, yy + 4, 8, yy)
            p.stroke(glyph, 1.9, 'round')
    elif ab == 'breach':
        p.begin()
        p.move(-7, 6)
        p.quad(-3, -9, 5, -3)
        p.stroke(glyph, 2.2, 'round')
        p.begin()
        p.move(5, -3)
        p.line(8, -7)
        p.move(5, -3)
        p.line(9, 0)
        p.stroke(glyph, 1.8, 'round')
        p.begin()
        for xx in (-9, -5, -1):
            p.circle(xx, 8, 1.3)
        p.fill(glyph)
    elif ab == 'frenzy':
        for yy, d in ((-2, -1), (3, 1)):
            p.begin()
            p.move(-8, yy)
            for i in range(8):
                p.line(-8 + (i + 1) * 2, yy + (d * 4 if i % 2 == 0 else 0))
            p.stroke(glyph, 1.7, 'round')
    elif ab == 'mirror':
        p.begin()
        p.rect(-8, -5, 5, 10)
        p.rect(3, -5, 5, 10)
        p.stroke(glyph, 1.8)
        p.begin()
        p.move(0, -8)
        p.line(0, 8)
        p.stroke(glyph, 1.0, 'round')
    elif ab == 'permafrost':
        p.begin()
        for k in range(6):
            a = k * math.pi / 3
            ca, sa = math.cos(a), math.sin(a)
            p.move(0, 0)
            p.line(ca * 8, sa * 8)
            bx, by = ca * 5, sa * 5
            for da in (-0.8, 0.8):
                p.move(bx, by)
                p.line(bx + math.cos(a + da) * 3, by + math.sin(a + da) * 3)
        p.stroke(glyph, 1.4, 'round')
    elif ab == 'siphon':
        p.begin()
        p.move(0, -8)
        p.quad(7, 1, 0, 7.5)
        p.quad(-7, 1, 0, -8)
        p.stroke(glyph, 1.8)
        p.begin()
        p.move(0, 4)
        p.line(0, -3)
        p.move(-2.5, -0.5)
        p.line(0, -3.5)
        p.line(2.5, -0.5)
        p.stroke(glyph, 1.5, 'round')
    elif ab == 'song':
        p.begin()
        p.circle(0, 0, 2.6)
        p.fill(glyph)
        for rr in (5, 8.5):
            for a0 in (0, math.pi):
                p.begin()
                p.arc(0, 0, rr, a0 - 0.8, a0 + 0.8)
                p.stroke(glyph, 1.6, 'round')
    elif ab == 'bloodmoon':
        p.begin()
        p.circle(0, 0, 7.5)
        p.fill(glyph)
        p.begin()
        p.circle(3.5, -2.5, 6.4)
        p.fill(bg)
    else:
        p.begin()
        p.circle(0, 0, 4)
        p.fill(glyph)
    p.restore()
