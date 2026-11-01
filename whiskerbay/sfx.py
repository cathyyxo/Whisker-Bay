"""Every sound in the game is synthesized here at start-up (no sound files needed)."""
import math
import random
import threading
from array import array

import pygame

from .settings import SET

TAU = math.pi * 2
MASTER = 0.55
NOTES = [523.25, 587.33, 659.25, 783.99, 880, 1046.5, 1174.7, 1318.5, 1568]


def _w_sine(p):
    return math.sin(TAU * p)


def _w_square(p):
    return 1.0 if p < 0.5 else -1.0


def _w_tri(p):
    return -1.0 + 4.0 * p if p < 0.5 else 3.0 - 4.0 * p


def _w_saw(p):
    return 2.0 * p - 1.0


WAVES = {'sine': _w_sine, 'square': _w_square, 'triangle': _w_tri, 'sawtooth': _w_saw}


class Buf:
    """A mono float buffer we mix tones and filtered noise into."""

    def __init__(self, sr, seconds):
        self.sr = sr
        self.d = [0.0] * (int(seconds * sr) + 2)

    def tone(self, f, dur, typ='sine', vol=0.2, slide=None, delay=0.0):
        sr, d = self.sr, self.d
        i0 = int(delay * sr)
        n_ramp = max(1, int(dur * sr))
        end = min(len(d), i0 + int((dur + 0.05) * sr))
        if end <= i0:
            return
        fr = (slide / f) ** (1.0 / n_ramp) if slide else 1.0
        att = max(1, int(0.01 * sr))
        ga = (vol / 0.0001) ** (1.0 / att)
        dec = max(1, n_ramp - att)
        gd = (0.0001 / vol) ** (1.0 / dec)
        wave = WAVES.get(typ, _w_sine)
        g, freq, ph, inv = 0.0001, float(f), 0.0, 1.0 / sr
        ga_end = att
        gd_end = att + dec
        for k in range(end - i0):
            if k < ga_end:
                g *= ga
            elif k < gd_end:
                g *= gd
            else:
                g = 0.0
            if k < n_ramp:
                freq *= fr
            ph += freq * inv
            ph -= int(ph)
            d[i0 + k] += wave(ph) * g * MASTER

    def noise(self, dur, freq, vol=0.3, delay=0.0, q=1.0, sweep=None):
        sr, d = self.sr, self.d
        i0 = int(delay * sr)
        n_ramp = max(1, int(dur * sr))
        end = min(len(d), i0 + int((dur + 0.05) * sr))
        qlin = 10 ** (q / 20.0)  # Web Audio treats a lowpass Q as decibels
        nyq = sr * 0.45
        fr = (sweep / freq) ** (1.0 / n_ramp) if sweep else 1.0
        g = vol
        gd = (0.0001 / vol) ** (1.0 / n_ramp)
        x1 = x2 = y1 = y2 = 0.0
        cut = float(freq)
        b0 = b1 = b2 = a1 = a2 = 0.0
        rnd = random.random
        for k in range(end - i0):
            if k % 16 == 0:
                w0 = TAU * min(cut, nyq) / sr
                cw, sw = math.cos(w0), math.sin(w0)
                alpha = sw / (2 * qlin)
                a0 = 1 + alpha
                b0 = (1 - cw) / 2 / a0
                b1 = (1 - cw) / a0
                b2 = b0
                a1 = -2 * cw / a0
                a2 = (1 - alpha) / a0
            x = rnd() * 2 - 1
            y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            x2, x1, y2, y1 = x1, x, y1, y
            if k < n_ramp:
                cut *= fr
                g *= gd
            else:
                g = 0.0
            d[i0 + k] += y * g * MASTER

    def sound(self, channels):
        pcm = array('h', (int((32767 if v > 1 else -32767 if v < -1 else v * 32767)) for v in self.d))
        if channels == 2:
            st = array('h', bytes(len(pcm) * 4))
            st[0::2] = pcm
            st[1::2] = pcm
            pcm = st
        return pygame.mixer.Sound(buffer=pcm.tobytes())


class _Sfx:
    def __init__(self):
        self.snd = {}
        self.ready = False
        self.ok = False
        self.drone_ch = None
        self.drone_on = False

    @property
    def muted(self):
        return bool(SET.get('muted'))

    def set_muted(self, m):
        SET['muted'] = bool(m)
        if m:
            self.stop_drone()
            self.stop_ambient()

    def start(self):
        """Build all the sounds on a background thread so the game opens instantly."""
        info = pygame.mixer.get_init() if pygame.mixer.get_init() else None
        if not info:
            return
        self.ok = True
        try:
            pygame.mixer.set_num_channels(32)
        except pygame.error:
            pass
        threading.Thread(target=self._build, args=(info[0], info[2]), daemon=True).start()

    def _build(self, sr, ch):
        try:
            self._make_all(sr, ch)
            self.ready = True
        except Exception as e:  # sound is a bonus; never crash the game over it
            print('Sound disabled:', e)

    def _make_all(self, sr, ch):
        def mk(seconds, fn):
            b = Buf(sr, seconds)
            fn(b)
            return b.sound(ch)

        S = self.snd
        S['cast'] = mk(0.45, lambda b: (b.noise(0.35, 2500, 0.18, 0, 1, 500), b.tone(300, 0.25, 'sine', 0.05, 900)))
        S['splash'] = mk(0.6, lambda b: (b.noise(0.5, 1400, 0.35, 0, 0.8, 200), b.tone(180, 0.2, 'sine', 0.08, 90)))
        S['bite'] = mk(0.3, lambda b: (b.tone(880, 0.09, 'square', 0.08), b.tone(1320, 0.12, 'square', 0.08, None, 0.1)))
        S['strike'] = mk(0.2, lambda b: (b.tone(220, 0.12, 'sawtooth', 0.12, 440), b.noise(0.12, 4000, 0.1)))
        S['tick'] = [mk(0.08, lambda b, f=f: b.tone(f, 0.025, 'square', 0.025)) for f in (1900, 1980, 2060, 2150)]
        S['slip'] = mk(0.14, lambda b: b.tone(300, 0.08, 'triangle', 0.05, 200))
        S['snap'] = mk(0.32, lambda b: (b.tone(900, 0.25, 'sawtooth', 0.14, 80), b.noise(0.25, 3000, 0.25)))
        S['lost'] = mk(0.75, lambda b: (b.tone(392, 0.18, 'triangle', 0.1), b.tone(330, 0.18, 'triangle', 0.1, None, 0.16), b.tone(262, 0.35, 'triangle', 0.1, None, 0.32)))
        S['coin'] = mk(0.27, lambda b: (b.tone(1568, 0.08, 'square', 0.05), b.tone(2093, 0.14, 'square', 0.05, None, 0.07)))

        def buy(b):
            for i, n in enumerate([0, 2, 4, 7]):
                b.tone(NOTES[n], 0.18, 'triangle', 0.09, None, i * 0.06)
        S['buy'] = mk(0.45, buy)
        S['nope'] = mk(0.2, lambda b: b.tone(200, 0.15, 'square', 0.06, 150))
        S['burn'] = mk(0.7, lambda b: (b.noise(0.6, 2200, 0.3, 0, 2, 300), b.tone(160, 0.4, 'sawtooth', 0.06, 60)))
        seqs = [[0, 2, 4], [0, 2, 4, 7], [0, 4, 7, 9], [0, 4, 7, 9, 11], [2, 4, 7, 9, 11, 12], [0, 4, 7, 11, 12, 14, 16], [0, 2, 4, 7, 9, 12, 14, 16]]
        for tier, seq in enumerate(seqs):
            def cr(b, seq=seq, tier=tier):
                for i, n in enumerate(seq):
                    b.tone(523.25 * 2 ** (n / 12), 0.28 + tier * 0.04, 'sine' if tier >= 4 else 'triangle', 0.09, None, i * (0.07 + tier * 0.005))
            S['catch%d' % tier] = mk(len(seq) * 0.11 + 0.7, cr)

        def lvl(b):
            for i, n in enumerate([0, 4, 7, 12]):
                b.tone(523.25 * 2 ** (n / 12), 0.35, 'triangle', 0.09, None, i * 0.1)
        S['level'] = mk(0.8, lvl)

        def ench(b):
            for i in range(10):
                b.tone(600 + i * 120, 0.3, 'sine', 0.04, 1200 + i * 150, i * 0.05)
        S['enchant'] = mk(0.85, ench)
        S['roar'] = mk(1.5, lambda b: (b.tone(70, 1.4, 'sawtooth', 0.18, 40), b.noise(1.4, 300, 0.3, 0, 3, 80)))
        S['thunder'] = mk(2.3, lambda b: (b.noise(2.2, 900, 0.5, 0, 0.7, 60), b.noise(1.2, 200, 0.4, 0.15)))

        def chime(b):
            for i, n in enumerate([0, 4, 7, 12, 16, 19, 24]):
                f = 523.25 * 2 ** (n / 12)
                b.tone(f, 1.6, 'sine', 0.08, None, i * 0.09)
                b.tone(f * 2.01, 0.9, 'sine', 0.025, None, i * 0.09)
        S['chime'] = mk(2.3, chime)
        S['drone'] = self._drone(sr, ch)
        # --- fish tricks and rod abilities ---
        S['warn'] = mk(0.2, lambda b: (b.tone(1200, 0.05, 'square', 0.04), b.tone(1200, 0.05, 'square', 0.04, None, 0.09)))

        def ready(b):
            for i, f in enumerate((880, 1320, 1760)):
                b.tone(f, 0.12, 'triangle', 0.07, None, i * 0.05)
        S['ready'] = mk(0.35, ready)
        S['dash'] = mk(0.3, lambda b: (b.noise(0.22, 3000, 0.16, 0, 1, 800), b.tone(600, 0.18, 'sine', 0.04, 1200)))
        S['zap'] = mk(0.35, lambda b: (b.tone(120, 0.28, 'sawtooth', 0.09, 90), b.noise(0.2, 5000, 0.18, 0, 4, 2000)))
        S['snapish'] = mk(0.15, lambda b: (b.tone(2200, 0.09, 'square', 0.05, 900), b.noise(0.08, 6000, 0.15)))
        S['warp'] = mk(0.55, lambda b: (b.tone(300, 0.45, 'sine', 0.07, 900), b.tone(900, 0.45, 'sine', 0.05, 300)))
        S['flashbang'] = mk(0.45, lambda b: (b.noise(0.4, 7000, 0.25, 0, 1, 2000), b.tone(2400, 0.1, 'sine', 0.05)))
        S['puff'] = mk(0.35, lambda b: (b.tone(120, 0.3, 'sine', 0.14, 260), b.noise(0.2, 400, 0.12)))
        S['ink'] = mk(0.45, lambda b: (b.noise(0.4, 600, 0.3, 0, 2, 200), b.tone(90, 0.2, 'sine', 0.08)))
        S['ab_tug'] = mk(0.25, lambda b: (b.noise(0.15, 2500, 0.15), b.tone(300, 0.18, 'triangle', 0.09, 150)))

        def quick(b):
            for i, n in enumerate((0, 4, 7, 12, 16)):
                b.tone(660 * 2 ** (n / 12), 0.1, 'triangle', 0.07, None, i * 0.04)
        S['ab_quick'] = mk(0.4, quick)

        def freeze(b):
            for i, f in enumerate((2600, 2200, 1900, 1600, 1300)):
                b.tone(f, 0.35, 'sine', 0.05, None, i * 0.05)
            b.noise(0.5, 8000, 0.12, 0, 1, 3000)
        S['ab_freeze'] = mk(0.75, freeze)
        S['ab_slice'] = mk(0.35, lambda b: (b.noise(0.25, 8000, 0.3, 0, 1, 1500), b.tone(1800, 0.2, 'sawtooth', 0.06, 400)))
        S['ab_inferno'] = mk(0.75, lambda b: (b.noise(0.7, 2500, 0.3, 0, 2, 400), b.tone(100, 0.6, 'sawtooth', 0.08, 60)))
        S['ab_gravity'] = mk(0.75, lambda b: (b.tone(200, 0.6, 'sine', 0.16, 60), b.tone(400, 0.6, 'sine', 0.06, 120)))

        def tidal(b):
            b.noise(0.3, 8000, 0.3, 0, 1, 1500)
            b.tone(1800, 0.2, 'sawtooth', 0.05, 400)
            for i, f in enumerate((2400, 2000, 1600)):
                b.tone(f, 0.3, 'sine', 0.05, None, 0.12 + i * 0.05)
            b.noise(0.6, 900, 0.25, 0.1, 0.8, 200)
        S['ab_tidal'] = mk(0.85, tidal)

        def net(b):
            b.noise(0.35, 1200, 0.18, 0, 1, 400)
            for i, n in enumerate((0, 7, 12)):
                b.tone(392 * 2 ** (n / 12), 0.3, 'triangle', 0.06, None, 0.05 + i * 0.05)
        S['ab_net'] = mk(0.5, net)
        S['ab_harpoon'] = mk(0.45, lambda b: (b.tone(160, 0.3, 'sawtooth', 0.12, 90), b.noise(0.12, 5000, 0.25), b.tone(900, 0.15, 'square', 0.04, 300, 0.05)))
        S['ab_slowmo'] = mk(0.9, lambda b: (b.tone(900, 0.8, 'sine', 0.08, 220), b.tone(1350, 0.8, 'sine', 0.04, 330), b.noise(0.6, 600, 0.1, 0, 1, 150)))

        def purr(b):
            for i in range(9):
                b.tone(26 + (i % 2) * 3, 0.06, 'sawtooth', 0.16, None, i * 0.055)
            b.tone(520, 0.18, 'triangle', 0.06, 820, 0.48)
        S['ab_purr'] = mk(0.75, purr)

        def shield(b):
            for i, f in enumerate((660, 990, 1320, 1760)):
                b.tone(f, 0.45, 'sine', 0.05, f * 1.02, i * 0.04)
            b.noise(0.4, 3000, 0.08, 0, 1, 1200)
        S['ab_shield'] = mk(0.65, shield)
        S['ab_storm'] = mk(1.0, lambda b: (b.noise(0.15, 7000, 0.35), b.tone(120, 0.3, 'sawtooth', 0.12, 70), b.noise(0.9, 700, 0.35, 0.05, 0.8, 80)))

        def gold(b):
            for i in range(7):
                b.tone(1568 * 2 ** ((i % 3) * 4 / 12), 0.12, 'square', 0.035, None, i * 0.05)
            b.tone(2093, 0.4, 'sine', 0.05, None, 0.3)
        S['ab_gold'] = mk(0.8, gold)

        def phoenix(b):
            b.noise(0.6, 2500, 0.25, 0, 2, 600)
            for i, n in enumerate((0, 4, 7, 12, 16)):
                b.tone(392 * 2 ** (n / 12), 0.35, 'triangle', 0.06, None, 0.1 + i * 0.06)
        S['ab_phoenix'] = mk(0.85, phoenix)
        S['ab_magnet'] = mk(0.7, lambda b: (b.tone(180, 0.6, 'square', 0.04, 240), b.tone(360, 0.6, 'sine', 0.06, 300), b.tone(90, 0.5, 'sine', 0.08)))

        def stars(b):
            for i in range(10):
                b.tone(1800 + (i * 377) % 1400, 0.18, 'sine', 0.04, None, i * 0.06)
        S['ab_stars'] = mk(0.9, stars)
        S['ab_anchor'] = mk(0.8, lambda b: (b.tone(70, 0.6, 'sine', 0.2, 50), b.noise(0.3, 900, 0.18, 0, 1, 200), b.tone(240, 0.25, 'triangle', 0.05, 180, 0.08)))
        S['ab_whirl'] = mk(0.9, lambda b: (b.noise(0.8, 600, 0.25, 0, 1.5, 2400), b.tone(300, 0.7, 'sine', 0.06, 700)))

        def echo(b):
            for i in range(3):
                b.tone(1250, 0.22, 'sine', 0.09 * (0.6 ** i), 1180, i * 0.18)
        S['ab_echo'] = mk(0.8, echo)
        # new in 1.4
        S['ab_barb'] = mk(0.45, lambda b: (b.noise(0.1, 6000, 0.3), b.tone(700, 0.2, 'square', 0.05, 260), b.tone(140, 0.3, 'sawtooth', 0.08, 90, 0.05)))
        S['ab_riptide'] = mk(0.9, lambda b: (b.noise(0.85, 900, 0.3, 0, 1.2, 300), b.tone(180, 0.7, 'sine', 0.08, 360)))
        S['ab_breach'] = mk(0.9, lambda b: (b.tone(60, 0.5, 'sine', 0.22, 40), b.noise(0.6, 2500, 0.35, 0.12, 1, 400)))
        S['ab_frenzy'] = mk(0.6, lambda b: [b.noise(0.05, 5000, 0.25, i * 0.07) for i in range(6)] + [b.tone(90, 0.5, 'sawtooth', 0.1, 140)])
        S['ab_mirror'] = mk(0.8, lambda b: (b.tone(1200, 0.5, 'sine', 0.06, 1205), b.tone(1800, 0.5, 'sine', 0.05, 1795, 0.08),
                                            b.tone(2400, 0.4, 'sine', 0.03, 2410, 0.16)))
        S['ab_permafrost'] = mk(0.9, lambda b: (b.noise(0.7, 8000, 0.2, 0, 1, 3000), b.tone(1500, 0.5, 'triangle', 0.05, 900),
                                                b.tone(80, 0.6, 'sine', 0.15, 50)))
        S['ab_carapace'] = S['ab_shield']
        # admin pranks
        S['honk'] = mk(0.55, lambda b: (b.tone(262, 0.42, 'sawtooth', 0.16, 247), b.tone(330, 0.42, 'square', 0.07, 311),
                                        b.noise(0.4, 900, 0.08, 0, 2)))
        S['beat'] = mk(0.3, lambda b: (b.tone(110, 0.18, 'sine', 0.3, 45), b.noise(0.05, 7000, 0.12, 0.0)))
        S['hat'] = mk(0.1, lambda b: b.noise(0.05, 9000, 0.1))
        S['boo'] = mk(1.4, lambda b: (b.tone(90, 1.2, 'sawtooth', 0.22, 40), b.noise(1.0, 600, 0.35, 0, 1, 150),
                                      b.tone(1400, 0.5, 'square', 0.06, 300)))
        S['jk'] = mk(0.9, lambda b: (b.tone(523, 0.18, 'triangle', 0.1), b.tone(415, 0.18, 'triangle', 0.1, None, 0.2),
                                     b.tone(330, 0.45, 'triangle', 0.1, 300, 0.4)))
        S['ab_song'] = mk(1.3, lambda b: (b.tone(58, 1.1, 'sine', 0.24, 34), b.tone(232, 0.9, 'sine', 0.06, 116, 0.12),
                                          b.noise(0.7, 300, 0.12, 0.2, 1, 80)))
        S['ab_siphon'] = mk(0.8, lambda b: (b.tone(900, 0.6, 'sine', 0.07, 200), b.noise(0.5, 1500, 0.15, 0, 1, 500)))
        S['ab_bloodmoon'] = mk(1.0, lambda b: (b.tone(55, 0.9, 'sawtooth', 0.12, 45), b.tone(110, 0.9, 'sine', 0.08, 98),
                                               b.noise(0.8, 400, 0.2, 0.1, 1, 120)))

        def sonar(b):
            b.tone(1400, 0.35, 'sine', 0.07, 1350)
            b.tone(1400, 0.25, 'sine', 0.025, 1350, 0.3)
        S['sonar'] = mk(0.7, sonar)

        def pet_catch(b):
            b.noise(0.2, 2400, 0.12, 0, 1, 500)
            for i, n in enumerate((0, 7, 12)):
                b.tone(660 * 2 ** (n / 12), 0.14, 'triangle', 0.05, None, 0.12 + i * 0.07)
        S['pet_catch'] = mk(0.6, pet_catch)
        S['crack'] = mk(0.25, lambda b: (b.noise(0.08, 5000, 0.3), b.tone(900, 0.06, 'square', 0.04, 500)))

        def hatch(b):
            b.noise(0.3, 3000, 0.25, 0, 1, 800)
            for i, n in enumerate((0, 4, 7, 12, 16)):
                b.tone(523 * 2 ** (n / 12), 0.3, 'triangle', 0.06, None, 0.15 + i * 0.08)
        S['hatch'] = mk(1.0, hatch)
        # --- life around the bay ---
        S['gull'] = mk(0.5, lambda b: (b.tone(1500, 0.14, 'sine', 0.035, 1100), b.tone(1450, 0.2, 'sine', 0.03, 1000, 0.18)))
        S['plop'] = mk(0.35, lambda b: (b.noise(0.25, 1800, 0.16, 0, 1, 300), b.tone(420, 0.12, 'sine', 0.05, 200)))
        S['ocean'] = self._ocean(sr, ch)

    def _drone(self, sr, ch):
        """A seamless 2-second loop of the storm's low rumble."""
        n = sr * 2
        b = Buf(sr, 4.0)
        d = b.d
        # sawtooth 55 Hz + sine 82.5 Hz, both whole cycles in 2 s, through a 260 Hz lowpass
        w0 = TAU * 260 / sr
        cw, sw = math.cos(w0), math.sin(w0)
        alpha = sw / (2 * 10 ** (1 / 20))
        a0 = 1 + alpha
        b0, b1, a1, a2 = (1 - cw) / 2 / a0, (1 - cw) / a0, -2 * cw / a0, (1 - alpha) / a0
        x1 = x2 = y1 = y2 = 0.0
        for k in range(2 * n):
            t = k / sr
            x = 2 * ((55 * t) % 1.0) - 1 + math.sin(TAU * 82.5 * t)
            y = b0 * x + b1 * x1 + b0 * x2 - a1 * y1 - a2 * y2
            x2, x1, y2, y1 = x1, x, y1, y
            d[k] = y * 0.09 * MASTER * 1.6
        b.d = d[n:2 * n]
        return b.sound(ch)

    def _ocean(self, sr, ch):
        """A seamless loop of soft waves: filtered noise that swells and fades."""
        secs = 6
        n = sr * secs
        fade = sr
        b = Buf(sr, secs + 1.2)
        d = b.d
        x1 = x2 = y1 = y2 = 0.0
        w0 = TAU * 500 / sr
        cw, sw = math.cos(w0), math.sin(w0)
        alpha = sw / 2
        a0 = 1 + alpha
        b0, b1, a1, a2 = (1 - cw) / 2 / a0, (1 - cw) / a0, -2 * cw / a0, (1 - alpha) / a0
        rnd = random.random
        for k in range(n + fade):
            x = rnd() * 2 - 1
            y = b0 * x + b1 * x1 + b0 * x2 - a1 * y1 - a2 * y2
            x2, x1, y2, y1 = x1, x, y1, y
            t = (k % n) / sr
            swell = 0.55 + 0.45 * math.sin(TAU * t / 3.0) * math.sin(TAU * t / 6.0 + 1.0)
            d[k] = y * 0.22 * swell * MASTER
        for k in range(fade):          # cross-fade the end into the start so the loop never clicks
            u = k / fade
            d[k] = d[k] * u + d[n + k] * (1 - u)
        b.d = d[:n]
        return b.sound(ch)

    def start_ambient(self):
        if getattr(self, 'amb_ch', None) or not self.ready or self.muted:
            return
        s = self.snd.get('ocean')
        if s is None:
            return
        try:
            s.set_volume(max(0.0, min(1.0, SET.get('vol', 0.8) * 0.5)))
            self.amb_ch = s.play(loops=-1, fade_ms=2500)
        except pygame.error:
            self.amb_ch = None

    def refresh_volume(self):
        """Apply a new volume to sounds that are already looping."""
        v = max(0.0, min(1.0, SET.get('vol', 0.8)))
        for name, k in (('ocean', 0.5), ('drone', 1.0)):
            s = self.snd.get(name)
            if s is not None:
                try:
                    s.set_volume(v * k)
                except pygame.error:
                    pass

    def stop_ambient(self):
        ch = getattr(self, 'amb_ch', None)
        self.amb_ch = None
        if ch:
            try:
                ch.fadeout(800)
            except pygame.error:
                pass

    # ---------------- playing ----------------
    def play(self, name, vol=1.0):
        if not self.ready or self.muted:
            return
        s = self.snd.get(name)
        if s is None:
            return
        if isinstance(s, list):
            s = random.choice(s)
        try:
            s.set_volume(max(0.0, min(1.0, SET.get('vol', 0.8) * vol)))
            s.play()
        except pygame.error:
            pass

    def catch(self, tier):
        self.play('catch%d' % max(0, min(6, tier)))

    def start_drone(self):
        if self.drone_on or not self.ready or self.muted:
            return
        s = self.snd.get('drone')
        if s is None:
            return
        try:
            s.set_volume(max(0.0, min(1.0, SET.get('vol', 0.8))))
            self.drone_ch = s.play(loops=-1, fade_ms=1500)
            self.drone_on = True
        except pygame.error:
            pass

    def stop_drone(self):
        if not self.drone_on:
            return
        self.drone_on = False
        try:
            if self.drone_ch:
                self.drone_ch.fadeout(1000)
        except pygame.error:
            pass
        self.drone_ch = None


Sfx = _Sfx()
