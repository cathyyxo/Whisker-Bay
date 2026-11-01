"""The admin panel (F9): pranks and gifts for the players on your server.

The host makes someone an admin by typing  admin <name>  in the server window. The server checks every admin
action, then hands it to the target's game, which carries it out here in effect(). Playing on your own
(offline), the panel works on yourself only, so you can try everything out.
"""
import math
import random

import pygame
from pygame import gfxdraw

from . import online, ui
from . import world as Wd
from .data import BIOMES, BIOME_IDS, BOATS, BOSSES, FI, FISH, MATS, RAR, RI, ROD, RODS
from .sfx import Sfx
from .ui import FOAM, LINE, MIST, SAND, SEA, DANGER, UI, TextField, box, button, para, text, text_w, wrap
from .util import D, clamp, fmt, hexc

G = Wd.G

TROLL = [
    ('scare', 'Jump scare', 'Eyes in the dark and a scream'),
    ('fakeleg', 'Fake Mythic', 'A huge MYTHIC CATCH... then "just kidding"'),
    ('fishrain', 'Fish rain', 'Fish fall from the sky into the water'),
    ('flip', 'Flip screen', 'Upside down for 10 seconds'),
    ('disco', 'Disco party', 'Flashing lights and a beat for 10 s'),
    ('honk', 'HONK', 'Honk. Honk. HONK.'),
    ('storm', 'Summon storm', 'Thunder and rain for 20 seconds'),
    ('scatter', 'Scare the fish', 'Every fish near them swims away'),
    ('slip', 'Make it slip', 'Knocks 35% off the fish they are reeling'),
    ('reverse', 'Reverse controls', 'Reel and steering flipped for 12 s'),
    ('zoomies', 'Fish zoomies', 'Fish swim 2.6x faster for 15 s'),
    ('mythic', 'Spawn Mythic', 'A random island Mythic appears for everyone online there.'),
    ('limited', 'Spawn limited fish', 'Uses server stock online; offline spawns are test copies.'),
    ('boss', 'Summon boss', "Their island's boss appears at their hook"),
]
HELP = [
    ('coins', 'Give coins', 'Gives the amount in the box'),
    ('xp', 'Give levels', 'Amount = levels (up to 50)'),
    ('lures', 'Give boss lures', 'Amount = lures for their island'),
    ('mats', 'Give boss drops', 'Amount of every boss material'),
    ('rods', 'Give every rod', 'All rods, quest rods too'),
    ('unlock', 'Unlock everything', 'Every island and every boat'),
    ('pull', 'Bring them to me', 'Sails them to your island'),
]
NAMES = {a: n for a, n, _ in TROLL + HELP}
NAMES['say'] = 'Banner message'

# what is running on this screen right now
FX = D(scare=0.0, flip=0.0, disco=0.0, beat=0.0, banner=None, rain=[], rainLeft=0, rainT=0.0, real=0, honks=[],
       pull=None, frm='')
PS = D(target='me', amount=TextField('100000', 12, placeholder='Amount', allowed=lambda ch: ch.isdigit()),
       msg=TextField('', 80, placeholder='A big message on their screen...'), sent='', sentT=0.0)


# ---------------- who may use it ----------------
def allowed():
    if online.active():
        return bool(online.st.admin)
    return Wd.LIVE


def open_panel():
    from . import screens
    if not allowed():
        if online.active():
            Wd.toast('Only admins can open the admin panel. The host types "admin <your name>" in the server window.', 'bad')
        return
    screens.open_panel('admin')


# ---------------- sending ----------------
def amount():
    try:
        return max(1, int(PS.amount.text or '1'))
    except ValueError:
        return 1


def send(act):
    arg = None
    if act in ('coins', 'xp', 'lures', 'mats'):
        arg = amount()
    elif act == 'say':
        arg = PS.msg.text.strip()
        if not arg:
            Wd.toast('Type a message first.', 'bad')
            return
    elif act == 'pull':
        arg = Wd.P.biome
    to = PS.target
    me = online.st.user if online.active() else Wd.P.name
    if act in ('mythic', 'limited') and online.connected():
        target = me if to == 'me' else to
        online.admin_send(act, target, arg)
        who = 'you' if to == 'me' else ('everyone' if to == '*' else to)
        PS.sent = f'{NAMES.get(act, act)} -> {who}'
        PS.sentT = 2.5
        Sfx.play('coin')
        return
    if to == 'me' or not online.connected():
        if act == 'pull':
            Wd.toast('You are already on your own island.', '')
            return
        effect(act, arg, me)
        who = 'you'
    else:
        online.admin_send(act, to, arg)
        who = 'everyone' if to == '*' else to
        Sfx.play('coin')
    PS.sent = f'{NAMES.get(act, act)} -> {who}'
    PS.sentT = 2.5


# ---------------- carrying them out ----------------
def effect(act, arg, frm):
    """An admin did something to this player (or to themselves). Runs on the target's computer."""
    P = Wd.P
    if not Wd.LIVE or P is None:
        return
    FX.frm = frm
    n = arg if isinstance(arg, int) else 1
    if act == 'scare':
        FX.scare = 2.0
        Sfx.play('boo')
        Wd.shake(26)
        Wd.flash(0.4, '#000000')
    elif act == 'fakeleg':
        lst = Wd.islandFish(P.biome, 5) or [f for f in FISH if RI[f.r] == 5]
        sp = random.choice(lst)
        Wd.hype('MYTHIC CATCH', RAR[5].col, 3.4, True)
        Sfx.catch(5)
        Wd.toast(f'You caught the {sp.name}!!! A Mythic!', 'gold')

        def jk():
            G.hype = None
            G.tsTarget = 1
            banner('...JUST KIDDING', f'pranked by {frm}', '#ff8ad8')
            Sfx.play('jk')
        Wd.later(2.6, jk)
    elif act == 'fishrain':
        FX.rainLeft = 46
        FX.real = 8
        Wd.toast(f'It is raining fish! (thanks, {frm})', 'good')
    elif act == 'flip':
        FX.flip = 10.0
        Sfx.play('warp')
    elif act == 'disco':
        FX.disco = 10.0
        FX.beat = 0.0
    elif act == 'honk':
        FX.honks = [0.0, 0.32, 0.64, 1.2]
    elif act == 'storm':
        Wd.PRANK['storm'] = 20.0
        Wd.toast(f'{frm} summoned a storm!', 'bad')
    elif act == 'scatter':
        h = G.hook
        for f in G.fish:
            if f.state == 'hooked':
                continue
            f.state = 'flee'
            f.st = 0
            f.spook = 4
            f.dir = 1 if f.x >= h.x else -1
        Sfx.play('splash')
        Wd.toast(f'{frm} scared all your fish away!', 'bad')
    elif act == 'slip':
        R = G.reel
        if R:
            R.prog = max(0.02, R.prog - 0.35)
            Wd._label(R, 'SLIPPERY!', '#9fffe8', 1.4)
            Sfx.play('slip')
            Wd.shake(8)
        else:
            b = P.bait
            if b and (P.baits.get(b) or 0) > 0:
                P.baits[b] -= 1
            Wd.toast('Something nibbled your bait right off the hook...', 'bad')
            Sfx.play('slip')
    elif act == 'reverse':
        Wd.PRANK['rev'] = 12.0
        Wd.toast('Your controls feel... backwards.', 'bad')
        Sfx.play('warp')
    elif act == 'zoomies':
        Wd.PRANK['zoom'] = 15.0
        Wd.toast('The fish have the zoomies!', '')
        Sfx.play('ab_frenzy')
    elif act == 'boss':
        summon_boss(frm)
    elif act == 'mythic':
        summon_mythic(frm)
    elif act == 'limited':
        summon_limited_local(frm)
    elif act == 'say':
        banner(str(arg or '')[:80], f'from {frm}', SAND)
        Sfx.play('chime')
    elif act == 'coins':
        n = clamp(n, 1, 1_000_000_000)
        P.coins += n
        Sfx.play('coin')
        Wd.toast(f'{frm} gave you {fmt(n)} coins!', 'gold')
    elif act == 'xp':
        n = clamp(n, 1, 50)
        for _ in range(n):
            Wd.addXP(max(1, Wd.xpNeed(P.level) - P.xp))
        Wd.toast(f'{frm} gave you {n} level{"" if n == 1 else "s"}!', 'gold')
    elif act == 'lures':
        n = clamp(n, 1, 99)
        B = BOSSES.get(P.biome)
        lures = [B.lure] if B else [b.lure for b in BOSSES.values()]
        for lu in lures:
            P.baits[lu] = (P.baits.get(lu) or 0) + n
        Sfx.play('buy')
        Wd.toast(f'{frm} gave you {n} boss lure{"" if n == 1 else "s"}' + ('' if B else ' of every kind') + '!', 'gold')
    elif act == 'mats':
        n = clamp(n, 1, 99)
        for m in MATS:
            P.mats[m] = (P.mats.get(m) or 0) + n
        Sfx.play('buy')
        Wd.toast(f'{frm} gave you {n} of every boss drop!', 'gold')
    elif act == 'rods':
        for r in RODS:
            if r.id not in P.rods:
                P.rods[r.id] = D(ench=None)
        Sfx.play('buy')
        Wd.toast(f'{frm} gave you every rod! Equip them in your bag.', 'gold')
    elif act == 'unlock':
        for bid in BIOME_IDS:
            P.unlocked[bid] = True
        for b in BOATS:
            if b.id not in P.boats:
                P.boats.append(b.id)
        P.boat = BOATS[-1].id
        Sfx.play('level')
        Wd.toast(f'{frm} unlocked every island and boat for you!', 'gold')
    elif act == 'pull':
        if arg in BIOMES and arg != P.biome:
            FX.pull = arg
            Wd.toast(f'{frm} is pulling you to {BIOMES[arg].name}!', 'gold')
    else:
        return
    if act in ('coins', 'xp', 'lures', 'mats', 'rods', 'unlock', 'slip'):
        Wd.refreshStats()
        Wd.saveProfile()


def summon_boss(frm):
    P = Wd.P
    B = BOSSES.get(P.biome)
    if not B:
        Wd.toast(f'{frm} tried to summon a boss, but {BIOMES[P.biome].name} does not have one. Phew.', '')
        return
    if G.reel and G.reel.boss:
        return
    G.fish[:] = [f for f in G.fish if f.tier != 6 or f.state == 'hooked']
    h = G.hook
    d = clamp(h.d if h.d > 0 else 40, 10, BIOMES[P.biome].depth - 10)
    f = Wd.spawnFish(False, force=FI[B.fish], at=d)
    if f:
        f.x = clamp(h.x + random.choice((-1, 1)) * 260 * G.S, 40, G.W - 40)
        f.dir = 1 if f.x < h.x else -1
        f.seen = True
    Wd.toast(B.dread, 'gold')
    Wd.toast(f'{frm} summoned {Wd.bossName(B.fish)}!', 'gold')
    Sfx.play('roar')
    Wd.shake(14)


def summon_mythic(frm):
    p = Wd.P
    pool = [sp for sp in Wd.islandFish(p.biome, 5) if not getattr(sp, 'limited', 0)]
    if not pool:
        Wd.toast(f'There are no regular Mythic fish in {BIOMES[p.biome].name}.', 'bad')
        return
    sp = random.choice(pool)
    depth = clamp(G.hook.d if G.hook.d > 0 else sp.dz, 10, BIOMES[p.biome].depth - 10)
    f = Wd.spawnFish(False, force=sp, at=depth)
    if not f:
        Wd.toast('Could not spawn that Mythic right now.', 'bad')
        return
    f.x = clamp(G.hook.x + random.choice((-1, 1)) * 260 * G.S, 40, G.W - 40)
    f.dir = 1 if f.x < G.hook.x else -1
    f.seen = True
    Wd.toast(f'{frm} summoned a {sp.name}!', 'gold')
    Sfx.play('roar')


def summon_limited_local(frm):
    pool = [sp for sp in FISH if sp.b == Wd.P.biome and sp.r == 'mythic' and getattr(sp, 'limited', 0)]
    if not pool:
        Wd.toast(f'There are no limited Mythic fish in {BIOMES[Wd.P.biome].name}.', 'bad')
        return
    sp = random.choice(pool)
    depth = clamp(G.hook.d if G.hook.d > 0 else sp.dz, 10, BIOMES[Wd.P.biome].depth - 10)
    f = Wd.spawnFish(False, force=sp, at=depth)
    if not f:
        Wd.toast('Could not spawn that limited fish right now.', 'bad')
        return
    f.x = clamp(G.hook.x + random.choice((-1, 1)) * 260 * G.S, 40, G.W - 40)
    f.dir = 1 if f.x < G.hook.x else -1
    f.seen = True
    Wd.toast(f'{frm} spawned a local test copy of {sp.name}; it does not use a server catch.', 'gold')
    Sfx.play('roar')


def banner(text_, sub, col):
    FX.banner = D(text=text_, sub=sub, col=col, t=0.0, dur=5.0)


# ---------------- every frame ----------------
def tick(real):
    for k in list(Wd.PRANK):
        Wd.PRANK[k] -= real
        if Wd.PRANK[k] <= 0:
            del Wd.PRANK[k]
    if not Wd.LIVE or Wd.P is None:
        FX.scare = FX.flip = FX.disco = 0.0
        FX.banner = None
        FX.rain = []
        FX.rainLeft = 0
        FX.honks = []
        FX.pull = None
        Wd.PRANK.clear()
        return
    FX.scare = max(0.0, FX.scare - real)
    FX.flip = max(0.0, FX.flip - real)
    PS.sentT = max(0.0, PS.sentT - real)
    if FX.disco > 0:
        FX.disco -= real
        FX.beat -= real
        if FX.beat <= 0:
            FX.beat += 0.21
            FX.step = (FX.get('step') or 0) + 1
            Sfx.play('beat' if FX.step % 2 == 0 else 'hat')
    if FX.banner:
        FX.banner.t += real
        if FX.banner.t > FX.banner.dur:
            FX.banner = None
    for i in range(len(FX.honks)):
        FX.honks[i] -= real
    for hk in [x for x in FX.honks if x <= 0]:
        FX.honks.remove(hk)
        Sfx.play('honk')
        Wd.shake(6)
        Wd.floatText(Wd.boatX() + random.uniform(-40, 40), -6, 'HONK!', random.choice(['#ffd23d', '#ff8ad8', '#7cf0ff']), 34, 1.2)
    rain_tick(real)
    if FX.pull and G.mode == 'idle' and not G.sail:
        to, FX.pull = FX.pull, None
        Wd.P.unlocked[to] = True
        G.sail = D(t=0.0, to=to, swapped=False)
        Wd.setMode('sail')
        Sfx.play('cast')


_pics = {}


def _pic(sp):
    s = _pics.get(sp.id)
    if s is None:
        from .art import portrait
        s = _pics[sp.id] = portrait(sp, None, 96, 54)
    return s


def rain_tick(real):
    P = Wd.P
    if FX.rainLeft > 0:
        FX.rainT -= real
        while FX.rainT <= 0 and FX.rainLeft > 0:
            FX.rainT += 0.09
            FX.rainLeft -= 1
            tier = random.choice((0, 0, 0, 1, 1, 2))
            lst = Wd.islandFish(P.biome, tier) or Wd.islandFish(P.biome, 0) or FISH[:5]
            sp = random.choice(lst)
            FX.rain.append(D(sp=sp, x=random.uniform(30, G.W - 30), y=-60.0, vy=random.uniform(150, 320),
                             vx=random.uniform(-40, 40), rot=random.uniform(0, 360), vr=random.uniform(-260, 260),
                             real=FX.real > 0))
            FX.real -= 1
    surf_y = Wd.sy(0)
    for r in FX.rain[:]:
        r.vy += 700 * real
        r.y += r.vy * real
        r.x += r.vx * real
        r.rot += r.vr * real
        if 0 < surf_y < G.H and r.y >= surf_y:
            FX.rain.remove(r)
            Wd.ripple(r.x, 0.8)
            Wd.burst(r.x, 0.5, '#e6f6ff', 6, 0.7)
            if random.random() < 0.4:
                Sfx.play('splash', 0.6)
            if r.real:
                f = Wd.spawnFish(False, force=r.sp, at=random.uniform(4, min(25, BIOMES[P.biome].depth - 4)))
                if f:
                    f.x = r.x
        elif r.y > G.H + 80:
            FX.rain.remove(r)


# ---------------- drawing (on top of everything) ----------------
def draw(c):
    if not Wd.LIVE:
        return
    for r in FX.rain:
        s = pygame.transform.rotate(_pic(r.sp), r.rot)
        c.blit(s, s.get_rect(center=(int(r.x), int(r.y))))
    if FX.disco > 0:
        draw_disco(c)
    if FX.banner:
        draw_banner(c)
    if FX.scare > 0:
        draw_scare(c)


def draw_disco(c):
    t = G.t
    k = min(1.0, FX.disco / 0.6, (10.0 - FX.disco) / 0.4 + 0.2)
    hue = (t * 160) % 360
    col = pygame.Color(0)
    col.hsva = (hue, 90, 100, 100)
    ui.overlay(c, (col.r, col.g, col.b), 0.22 * k)
    W, H = G.W, G.H
    lay = pygame.Surface((W, H), pygame.SRCALPHA)
    cx, cy = W / 2, 30
    for i in range(7):
        a = t * 1.3 + i * math.tau / 7
        cc = pygame.Color(0)
        cc.hsva = ((hue + i * 51) % 360, 80, 100, 100)
        w = 0.07
        p1 = (cx + math.cos(a - w) * 1600, cy + abs(math.sin(a - w)) * 1600)
        p2 = (cx + math.cos(a + w) * 1600, cy + abs(math.sin(a + w)) * 1600)
        pygame.draw.polygon(lay, (cc.r, cc.g, cc.b, int(60 * k)), [(cx, cy), p1, p2])
    c.blit(lay, (0, 0))
    gfxdraw.filled_circle(c, int(cx), int(cy), 26, (200, 205, 215))
    for j in range(16):
        a = j * math.tau / 16 + t * 2
        gfxdraw.filled_circle(c, int(cx + math.cos(a) * 16), int(cy + math.sin(a) * 16), 4,
                              (255, 255, 255) if (j + int(t * 8)) % 3 == 0 else (140, 150, 170))
    pygame.draw.line(c, (180, 180, 190), (cx, 0), (cx, cy - 26), 2)
    bob = abs(math.sin(t * 7.5)) * 8
    text(c, 'DISCO!', W / 2, 74 - bob, 'd', 40, (255, 255, 255), 'center', 'top', outline=3, ocol=(col.r // 2, col.g // 2, col.b // 2))


def draw_banner(c):
    Bn = FX.banner
    u = Bn.t
    a = min(1.0, u / 0.25, (Bn.dur - u) / 0.5)
    pop = 1 + 0.25 * max(0.0, 1 - u / 0.25)
    W, H = G.W, G.H
    lines = wrap(Bn.text, 'd', 52, W - 120)[:3]
    hh = 70 * len(lines) + 40
    y0 = H * 0.36 - hh / 2
    box(c, (40, y0 - 14, W - 80, hh + 20), (7, 12, 24, int(190 * a)), hexc(Bn.col) if isinstance(Bn.col, str) else Bn.col, 22, 2, alpha=a)
    for i, ln in enumerate(lines):
        size = int(52 * pop)
        text(c, ln, W / 2, y0 + 8 + i * 70, 'd', size, Bn.col, 'center', 'top', alpha=a, outline=3)
    text(c, Bn.sub, W / 2, y0 + 8 + len(lines) * 70, 'k', 18, MIST, 'center', 'top', alpha=a)


def draw_scare(c):
    u = 2.0 - FX.scare            # 0 .. 2 seconds
    W, H = G.W, G.H
    a = min(1.0, u / 0.08, FX.scare / 0.35)
    ui.overlay(c, (0, 0, 0), a)
    jx = random.uniform(-10, 10) * a
    jy = random.uniform(-8, 8) * a
    grow = 1 + 0.35 * min(1.0, u / 1.6)
    cx, cy = W / 2 + jx, H * 0.42 + jy
    lay = pygame.Surface((W, H), pygame.SRCALPHA)
    for side in (-1, 1):
        ex = cx + side * 190 * grow
        ey = cy - 30 * grow
        rx, ry = int(120 * grow), int(70 * grow)
        pygame.draw.ellipse(lay, (255, 40, 20, int(70 * a)), (ex - rx * 1.4, ey - ry * 1.6, rx * 2.8, ry * 3.2))
        pygame.draw.ellipse(lay, (255, 215, 60, int(255 * a)), (ex - rx, ey - ry, rx * 2, ry * 2))
        pygame.draw.ellipse(lay, (255, 120, 20, int(255 * a)), (ex - rx * 0.7, ey - ry * 0.7, rx * 1.4, ry * 1.4))
        pygame.draw.ellipse(lay, (10, 0, 0, int(255 * a)), (ex - rx * 0.13, ey - ry * 0.92, rx * 0.26, ry * 1.84))
        # angry brow
        pygame.draw.polygon(lay, (0, 0, 0, int(255 * a)), [(ex - rx * 1.2, ey - ry * (1.3 if side > 0 else 0.4)),
                                                          (ex + rx * 1.2, ey - ry * (0.4 if side > 0 else 1.3)),
                                                          (ex + rx * 1.2, ey - ry * 1.8), (ex - rx * 1.2, ey - ry * 1.8)])
    # a grin full of teeth
    mw, mh = 520 * grow, 120 * grow
    my = cy + 150 * grow
    pygame.draw.ellipse(lay, (60, 0, 0, int(255 * a)), (cx - mw / 2, my - mh / 2, mw, mh))
    nt = 13
    for i in range(nt):
        x0 = cx - mw / 2 + mw * (i + 0.5) / nt
        half = mw / nt * 0.42
        top = my - mh / 2 * math.sqrt(max(0.0, 1 - ((x0 - cx) / (mw / 2)) ** 2))
        bot = my + mh / 2 * math.sqrt(max(0.0, 1 - ((x0 - cx) / (mw / 2)) ** 2))
        pygame.draw.polygon(lay, (245, 240, 225, int(255 * a)), [(x0 - half, top), (x0 + half, top), (x0, top + mh * 0.42)])
        pygame.draw.polygon(lay, (245, 240, 225, int(255 * a)), [(x0 - half, bot), (x0 + half, bot), (x0, bot - mh * 0.4)])
    c.blit(lay, (0, 0))
    if u > 0.15:
        text(c, 'BEHIND YOU', W / 2 + jx * 1.5, H * 0.1 + jy, 'd', 72, (255, 50, 40), 'center', 'top', alpha=a, outline=4)
    if u > 1.2:
        text(c, f'(scared by {FX.frm})', W / 2, H - 50, 'k', 18, (200, 200, 200), 'center', 'top', alpha=a)


def present(screen):
    """Called just before the frame is shown: the upside-down prank."""
    if FX.flip > 0 and Wd.LIVE:
        screen.blit(pygame.transform.flip(screen, False, True), (0, 0))


# ---------------- the panel ----------------
def panel_sub():
    if online.connected():
        return f'{len(online.who)} online · actions hit the player you pick'
    return 'Offline: everything happens to you, so you can try it out'


def _section(c, body, y, title):
    text(c, title, body.x, y, 'd', 20, SAND)
    return y + 32


def panel(c, body, y, dt):
    y0 = y
    me = online.st.user if online.active() else ''
    # --- who ---
    y = _section(c, body, y, 'Target')
    opts = [('me', 'Me')]
    if online.connected():
        opts.append(('*', 'Everyone else'))
        opts += [(w.get('n'), w.get('n')) for w in online.who if w.get('n') and w.get('n') != me]
    if PS.target not in [o[0] for o in opts]:
        PS.target = 'me'
    x = body.x
    for tid, lab in opts:
        w = text_w(lab, 'k', 14) + 30
        if x + w > body.right:
            x = body.x
            y += 40
        if button(c, (x, y, w, 34), lab, 'tabon' if tid == PS.target else 'tab', radius=17, clip=body):
            PS.target = tid
        x += w + 8
    y += 46
    if online.connected() and button(c, (body.x, y, 150, 30), 'Refresh list', '', size=13, clip=body):
        online.request_boards()
    if PS.sentT > 0:
        text(c, 'Sent: ' + PS.sent, body.x + (162 if online.connected() else 0), y + 15, 'k', 14, SEA, 'left', 'middle')
    y += 42
    # --- pranks ---
    y = _section(c, body, y, 'Troll')
    y = _grid(c, body, y, TROLL, 'warn')
    # --- banner ---
    y = _section(c, body, y + 6, 'Banner message')
    fw = body.w - 150
    if PS.msg.draw(c, (body.x, y, fw, 40), clip=body, size=15):
        send('say')
    if button(c, (body.x + fw + 10, y, 140, 40), 'Show it', 'go', clip=body):
        send('say')
    y += 56
    # --- help ---
    y = _section(c, body, y, 'Help')
    text(c, 'Amount', body.x, y + 20, 'k', 14, MIST, 'left', 'middle')
    PS.amount.draw(c, (body.x + 70, y, 170, 40), clip=body, size=15)
    bx = body.x + 254
    for v in (1, 10, 100000, 1000000):
        lab = fmt(v)
        w = text_w(lab, 'k', 13) + 24
        if button(c, (bx, y + 4, w, 32), lab, 'ghost', size=13, clip=body):
            PS.amount.text = str(v)
        bx += w + 6
    y += 54
    y = _grid(c, body, y, HELP, '')
    y += para(c, 'Gifts save straight into their game. Pranks only last a few seconds and never take coins or fish, '
                 'except "Make it slip" (it can cost them the fish they are reeling, or one bait).', body.x, y + 4, body.w, size=13)
    return y + 20 - y0


def _grid(c, body, y, items, style):
    gap = 8
    cols = max(1, (body.w + gap) // (200 + gap))
    cw = (body.w - gap * (cols - 1)) / cols
    for i, (act, name, desc) in enumerate(items):
        rr, k = divmod(i, cols)
        r = pygame.Rect(int(body.x + k * (cw + gap)), int(y + rr * 70), int(cw), 62)
        if r.bottom < body.y or r.y > body.bottom:
            continue
        if button(c, r, '', style, clip=body, radius=12):
            send(act)
        text(c, name, r.x + 12, r.y + 10, 'k', 15, FOAM)
        ln = wrap(desc, 'b', 12, r.w - 20)[:2]
        for j, s in enumerate(ln):
            text(c, s, r.x + 12, r.y + 31 + j * 14, 'b', 12, MIST)
    rows = (len(items) + cols - 1) // cols
    return y + rows * 70 + 6
