"""A tiny immediate-mode UI kit: fonts, text, rounded boxes, buttons, text fields, scrolling."""
import math
import os
from collections import OrderedDict

import pygame

from .settings import FONT_DIR
from .util import clamp, hexc

# ---------------- theme ----------------
NIGHT = (7, 26, 46)
PANEL = (14, 42, 70)
PANEL2 = (20, 58, 95)
LINE = (43, 90, 132)
FOAM = (234, 246, 255)
MIST = (159, 194, 227)
SAND = (255, 217, 138)
CORAL = (255, 138, 91)
SEA = (47, 211, 192)
DANGER = (255, 79, 109)
INK = (42, 26, 0)

FONT_FILES = {'d': 'LilitaOne-Regular.ttf', 'b': 'Nunito-Bold.ttf', 'x': 'Nunito-ExtraBold.ttf', 'k': 'Nunito-Black.ttf'}
_fonts = {}


def font(kind, size):
    key = (kind, size)
    f = _fonts.get(key)
    if f is None:
        try:
            f = pygame.font.Font(os.path.join(FONT_DIR, FONT_FILES[kind]), size)
        except (OSError, pygame.error, FileNotFoundError):
            f = pygame.font.Font(None, int(size * 1.35))
        _fonts[key] = f
    return f


def C(c):
    """Normalise a colour to an (r, g, b) or (r, g, b, a) tuple."""
    if isinstance(c, str):
        return hexc(c)
    return tuple(int(v) for v in c)


_tcache = OrderedDict()


def text_surf(txt, kind='x', size=14, col=FOAM, outline=0, ocol=(0, 0, 0, 150)):
    col = C(col)
    key = (txt, kind, size, col, outline, ocol)
    s = _tcache.get(key)
    if s is not None:
        _tcache.move_to_end(key)
        return s
    f = font(kind, size)
    s = f.render(txt, True, col[:3])
    if len(col) == 4 and col[3] < 255:
        s.set_alpha(col[3])
        tmp = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        tmp.blit(s, (0, 0))
        s = tmp
    if outline:
        o = f.render(txt, True, ocol[:3])
        w, h = s.get_size()
        out = pygame.Surface((w + 2 * outline, h + 2 * outline), pygame.SRCALPHA)
        steps = max(8, outline * 6)
        for i in range(steps):
            a = 2 * math.pi * i / steps
            out.blit(o, (outline + round(math.cos(a) * outline), outline + round(math.sin(a) * outline)))
        if len(ocol) == 4 and ocol[3] < 255:
            out.fill((255, 255, 255, ocol[3]), special_flags=pygame.BLEND_RGBA_MULT)
        out.blit(s, (outline, outline))
        s = out
    _tcache[key] = s
    if len(_tcache) > 900:
        for _ in range(200):
            _tcache.popitem(last=False)
    return s


def text(surf, txt, x, y, kind='x', size=14, col=FOAM, align='left', valign='top', alpha=1.0, outline=0, ocol=(0, 0, 0, 150)):
    if txt is None or txt == '':
        return pygame.Rect(x, y, 0, 0)
    s = text_surf(str(txt), kind, size, col, outline, ocol)
    w, h = s.get_size()
    if align == 'center':
        x -= w / 2
    elif align == 'right':
        x -= w
    if valign == 'middle':
        y -= h / 2
    elif valign == 'baseline':
        y -= font(kind, size).get_ascent() + outline
    elif valign == 'bottom':
        y -= h
    if alpha < 0.999:
        s.set_alpha(int(255 * clamp(alpha, 0, 1)))
        surf.blit(s, (x, y))
        s.set_alpha(255)
    else:
        surf.blit(s, (x, y))
    return pygame.Rect(int(x), int(y), w, h)


def text_w(txt, kind='x', size=14):
    return font(kind, size).size(str(txt))[0]


def wrap(txt, kind, size, width):
    f = font(kind, size)
    lines = []
    for para in str(txt).split('\n'):
        words = para.split(' ')
        cur = ''
        for w in words:
            t = (cur + ' ' + w) if cur else w
            if f.size(t)[0] <= width or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def para(surf, txt, x, y, width, kind='b', size=14, col=MIST, lh=None):
    """Draw wrapped text; returns the height used."""
    lh = lh or int(size * 1.38)
    lines = wrap(txt, kind, size, width)
    for i, ln in enumerate(lines):
        text(surf, ln, x, y + i * lh, kind, size, col)
    return len(lines) * lh


# ---------------- boxes ----------------
_bcache = OrderedDict()


def box_surf(w, h, fill, border=None, radius=12, bw=1, grad=None):
    w, h = max(1, int(w)), max(1, int(h))
    key = (w, h, fill, border, radius, bw, grad)
    s = _bcache.get(key)
    if s is not None:
        _bcache.move_to_end(key)
        return s
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    r = min(radius, w // 2, h // 2)
    if grad:
        g = pygame.Surface((w, h), pygame.SRCALPHA)
        a, b = C(grad[0]), C(grad[1])
        for y in range(h):
            u = y / max(1, h - 1)
            pygame.draw.line(g, tuple(int(a[k] + (b[k] - a[k]) * u) for k in range(3)) + (255,), (0, y), (w, y))
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=r)
        g.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(g, (0, 0))
    elif fill is not None:
        pygame.draw.rect(s, C(fill), (0, 0, w, h), border_radius=r)
    if border is not None:
        pygame.draw.rect(s, C(border), (0, 0, w, h), width=bw, border_radius=r)
    _bcache[key] = s
    if len(_bcache) > 500:
        for _ in range(100):
            _bcache.popitem(last=False)
    return s


def box(surf, rect, fill, border=None, radius=12, bw=1, grad=None, alpha=1.0):
    r = pygame.Rect(rect)
    s = box_surf(r.w, r.h, fill, border, radius, bw, grad)
    if alpha < 0.999:
        s.set_alpha(int(255 * clamp(alpha, 0, 1)))
        surf.blit(s, r.topleft)
        s.set_alpha(255)
    else:
        surf.blit(s, r.topleft)


_overlays = {}


def overlay(surf, col, a):
    """Cover the whole surface with a colour at alpha a (0..1)."""
    if a <= 0.004:
        return
    w, h = surf.get_size()
    key = (w, h, C(col)[:3])
    o = _overlays.get(key)
    if o is None:
        o = pygame.Surface((w, h))
        o.fill(C(col)[:3])
        _overlays[key] = o
    o.set_alpha(int(255 * clamp(a, 0, 1)))
    surf.blit(o, (0, 0))


def radial_surface(w, h, fn, small=(160, 90)):
    """Build a smooth radial image cheaply: compute fn(u, v)->(r,g,b,a) on a small grid, then upscale."""
    sw, sh = small
    s = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for y in range(sh):
        for x in range(sw):
            s.set_at((x, y), fn((x + 0.5) / sw, (y + 0.5) / sh))
    return pygame.transform.smoothscale(s, (w, h))


# ---------------- input state for immediate-mode widgets ----------------
class _Input:
    def __init__(self):
        self.mouse = (0, 0)
        self.click = None       # where the mouse went down this frame
        self.consumed = False
        self.rclick = None
        self.wheel = 0
        self.typed = []         # text typed this frame
        self.keys = []          # (key, mod) pressed this frame
        self.focus = None       # the TextField with keyboard focus
        self.hot = False        # mouse is over something clickable (for the cursor)

    def frame(self):
        self.click = None
        self.rclick = None
        self.consumed = False
        self.wheel = 0
        self.typed = []
        self.keys = []
        self.hot = False

    def take(self, rect, clip=None):
        """True if this frame's click landed in rect (and nobody took it yet)."""
        if self.click is None or self.consumed:
            return False
        if not pygame.Rect(rect).collidepoint(self.click):
            return False
        if clip is not None and not pygame.Rect(clip).collidepoint(self.click):
            return False
        self.consumed = True
        return True

    def block(self, rect):
        """Eat clicks on a panel so they don't reach the water behind it."""
        if self.click is not None and not self.consumed and pygame.Rect(rect).collidepoint(self.click):
            self.consumed = True

    def over(self, rect, clip=None):
        if not pygame.Rect(rect).collidepoint(self.mouse):
            return False
        return clip is None or pygame.Rect(clip).collidepoint(self.mouse)


UI = _Input()


def button(surf, rect, label, style='', disabled=False, size=14, kind='k', clip=None, radius=12, col=None):
    r = pygame.Rect(rect)
    hover = UI.over(r, clip) and not disabled
    if hover:
        UI.hot = True
    a = 0.45 if disabled else 1.0
    tcol = FOAM
    if style == 'go':
        box(surf, r, None, (255, 243, 201), radius, 1, grad=((255, 236, 186) if hover else (255, 227, 163), (255, 206, 110) if hover else (255, 198, 90)), alpha=a)
        tcol = INK
    elif style == 'warn':
        box(surf, r, (255, 79, 109, 70 if hover else 46), DANGER, radius, 1, alpha=a)
        tcol = (255, 208, 216)
    elif style == 'tab':
        box(surf, r, (255, 255, 255, 18) if hover else (0, 0, 0, 0), LINE, radius, 1, alpha=a)
        tcol = MIST
    elif style == 'tabon':
        box(surf, r, SAND, SAND, radius, 1, alpha=a)
        tcol = INK
    elif style == 'hud':
        box(surf, r, (20, 58, 95, 230) if hover else (7, 26, 46, 190), (234, 246, 255, 50), radius, 1, alpha=a)
    elif style == 'hot':
        box(surf, r, (20, 58, 95, 230) if hover else (7, 26, 46, 190), SAND, radius, 2, alpha=a)
    elif style == 'ghost':
        box(surf, r, (255, 255, 255, 22) if hover else (0, 0, 0, 0), None, radius, 1, alpha=a)
    else:
        box(surf, r, (30, 74, 116) if hover else PANEL2, LINE, radius, 1, alpha=a)
    if label:
        text(surf, label, r.centerx, r.centery, kind, size, col or tcol, 'center', 'middle', alpha=a)
    if disabled:
        if UI.click and r.collidepoint(UI.click) and (clip is None or pygame.Rect(clip).collidepoint(UI.click)):
            UI.consumed = True
        return False
    return UI.take(r, clip)


def tabs(surf, x, y, items, current, size=14, maxw=None):
    """A row of pill tabs. items: [(id, label)]. Returns the clicked id (or None)."""
    picked = None
    cx = x
    for tid, label in items:
        w = text_w(label, 'k', size) + 28
        if maxw and cx + w > x + maxw:
            break
        if button(surf, (cx, y, w, 32), label, 'tabon' if tid == current else 'tab', size=size, radius=16):
            picked = tid
        cx += w + 6
    return picked


class TextField:
    def __init__(self, text='', maxlen=16, password=False, placeholder='', allowed=None):
        self.text = text
        self.maxlen = maxlen
        self.password = password
        self.placeholder = placeholder
        self.allowed = allowed   # a function(ch) -> bool, or None for anything printable
        self.blink = 0.0

    def draw(self, surf, rect, clip=None, size=16):
        r = pygame.Rect(rect)
        focused = UI.focus is self
        if UI.over(r, clip):
            UI.hot = True
        if UI.click and not UI.consumed and r.collidepoint(UI.click) and (clip is None or pygame.Rect(clip).collidepoint(UI.click)):
            UI.consumed = True
            UI.focus = self
            focused = True
        box(surf, r, NIGHT, SAND if focused else LINE, 12, 2 if focused else 1)
        shown = ('*' * len(self.text)) if self.password else self.text
        submit = False
        if focused:
            for ch in UI.typed:
                for c in ch:
                    if len(self.text) < self.maxlen and c.isprintable() and (self.allowed is None or self.allowed(c)):
                        self.text += c
            for key, mod in UI.keys:
                if key == pygame.K_BACKSPACE and self.text:
                    self.text = self.text[:-1] if not (mod & pygame.KMOD_CTRL) else ''
                elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    submit = True
                elif key == pygame.K_v and (mod & (pygame.KMOD_CTRL | pygame.KMOD_META)):
                    pasted = clipboard_get()
                    for c in pasted:
                        if len(self.text) < self.maxlen and c.isprintable() and (self.allowed is None or self.allowed(c)):
                            self.text += c
            shown = ('*' * len(self.text)) if self.password else self.text
        old = surf.get_clip()
        inner = r.inflate(-20, -4)
        surf.set_clip(inner.clip(old) if old else inner)
        f = font('x', size)
        tw = f.size(shown)[0]
        tx = inner.x + min(0, inner.w - tw - 6)
        if shown:
            text(surf, shown, tx, r.centery, 'x', size, FOAM, 'left', 'middle')
        elif self.placeholder:
            text(surf, self.placeholder, inner.x, r.centery, 'b', size, (110, 140, 170), 'left', 'middle')
        if focused and (pygame.time.get_ticks() // 500) % 2 == 0:
            cx = tx + tw + 1
            pygame.draw.line(surf, SAND, (cx, r.centery - size * 0.6), (cx, r.centery + size * 0.6), 2)
        surf.set_clip(old)
        return submit


def clipboard_get():
    try:
        if hasattr(pygame.scrap, 'get_text'):
            return pygame.scrap.get_text() or ''
        raw = pygame.scrap.get(pygame.SCRAP_TEXT)          # classic pygame
        if raw:
            return raw.decode('utf-8', 'ignore').rstrip('\x00')
    except (pygame.error, AttributeError, UnicodeError):
        pass
    return ''


def clipboard_put(txt):
    try:
        if hasattr(pygame.scrap, 'put_text'):
            pygame.scrap.put_text(txt)
            return True
        pygame.scrap.put(pygame.SCRAP_TEXT, txt.encode('utf-8'))   # classic pygame
        return True
    except (pygame.error, AttributeError):
        pass
    return False


def toggle(surf, rect, on, clip=None):
    r = pygame.Rect(rect)
    if UI.over(r, clip):
        UI.hot = True
    box(surf, r, SEA if on else (40, 64, 92), None, r.h // 2)
    k = r.h - 6
    x = r.right - k - 3 if on else r.x + 3
    box(surf, (x, r.y + 3, k, k), FOAM, None, k // 2)
    return UI.take(r, clip)


class Slider:
    def __init__(self):
        self.drag = False

    def draw(self, surf, rect, value, lo=0.0, hi=1.0, clip=None):
        r = pygame.Rect(rect)
        if UI.click and not UI.consumed and r.inflate(0, 16).collidepoint(UI.click) and (clip is None or pygame.Rect(clip).collidepoint(UI.click)):
            UI.consumed = True
            self.drag = True
        if self.drag:
            if not pygame.mouse.get_pressed()[0]:
                self.drag = False
            else:
                value = lo + clamp((UI.mouse[0] - r.x) / max(1, r.w), 0, 1) * (hi - lo)
        u = (value - lo) / (hi - lo)
        box(surf, (r.x, r.centery - 4, r.w, 8), (255, 255, 255, 36), None, 4)
        box(surf, (r.x, r.centery - 4, max(8, int(r.w * u)), 8), SAND, None, 4)
        pygame.draw.circle(surf, FOAM, (int(r.x + r.w * u), r.centery), 9)
        return value


class Scroll:
    """Remembers how far a panel's body is scrolled."""

    def __init__(self):
        self.off = 0.0
        self.content = 0
        self.drag = None

    def update(self, rect):
        r = pygame.Rect(rect)
        if UI.wheel and r.collidepoint(UI.mouse):
            self.off -= UI.wheel * 48
        mx = max(0, self.content - r.h)
        self.off = clamp(self.off, 0, mx)
        return int(self.off)

    def bar(self, surf, rect):
        r = pygame.Rect(rect)
        if self.content <= r.h:
            return
        frac = r.h / self.content
        bh = max(30, int(r.h * frac))
        mx = self.content - r.h
        by = r.y + int((r.h - bh) * (self.off / mx if mx else 0))
        track = pygame.Rect(r.right - 8, r.y, 6, r.h)
        knob = pygame.Rect(r.right - 8, by, 6, bh)
        if UI.click and not UI.consumed and track.inflate(10, 0).collidepoint(UI.click):
            UI.consumed = True
            self.drag = (UI.click[1], self.off)
        if self.drag:
            if not pygame.mouse.get_pressed()[0]:
                self.drag = None
            else:
                dy = UI.mouse[1] - self.drag[0]
                self.off = clamp(self.drag[1] + dy * self.content / r.h, 0, mx)
        box(surf, track, (255, 255, 255, 20), None, 3)
        box(surf, knob, (159, 194, 227, 150), None, 3)
