"""Small helpers shared by every part of the game."""
import math
import random

TAU = math.pi * 2


class D(dict):
    """A dict you can also read with dots (missing keys give None, like JavaScript)."""
    __slots__ = ()

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            return None

    def __setattr__(self, k, v):
        self[k] = v

    def __delattr__(self, k):
        self.pop(k, None)


def todot(x):
    """Turn plain dicts (for example from JSON) into D objects, all the way down."""
    if isinstance(x, dict):
        return D({k: todot(v) for k, v in x.items()})
    if isinstance(x, list):
        return [todot(v) for v in x]
    return x


def clamp(v, a, b):
    return a if v < a else b if v > b else v


def lerp(a, b, t):
    return a + (b - a) * t


def rand(a, b):
    return a + random.random() * (b - a)


def pick(seq):
    return seq[int(random.random() * len(seq))]


def jround(x):
    """Round half up, the way the original JavaScript did."""
    return int(math.floor(x + 0.5))


def sign(x):
    return 1 if x > 0 else -1 if x < 0 else 0


def fmt(n):
    return f"{jround(n):,}"


def fmtW(kg):
    if kg >= 1000:
        return (f"{kg / 1000:.0f}" if kg >= 10000 else f"{kg / 1000:.1f}") + " t"
    if kg >= 10:
        return f"{kg:.0f} kg"
    if kg >= 1:
        return f"{kg:.1f} kg"
    return f"{jround(kg * 1000)} g"


_hex_cache = {}


def hexc(h):
    """'#rrggbb' -> (r, g, b). Tuples pass straight through."""
    if not isinstance(h, str):
        return tuple(h[:3])
    v = _hex_cache.get(h)
    if v is None:
        s = h.lstrip('#')
        if len(s) == 3:
            s = ''.join(ch * 2 for ch in s)
        n = int(s[:6], 16)
        v = (n >> 16, (n >> 8) & 255, n & 255)
        _hex_cache[h] = v
    return v


def mix(a, b, t):
    A, B = hexc(a), hexc(b)
    return (jround(lerp(A[0], B[0], t)), jround(lerp(A[1], B[1], t)), jround(lerp(A[2], B[2], t)))


def rgba(c, a):
    r, g, b = hexc(c)
    return (r, g, b, int(clamp(a, 0, 1) * 255))


def shade(c, k):
    """Multiply a colour's brightness by k (k < 1 darkens)."""
    r, g, b = hexc(c)
    return (int(clamp(r * k, 0, 255)), int(clamp(g * k, 0, 255)), int(clamp(b * k, 0, 255)))
