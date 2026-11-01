"""The world: profiles, casting, the hook, fish, bites, the reel bar, bosses, hazards and sailing."""
import math
import os
import random
import time

from . import settings
from .data import (ABILITIES, BAIT, BIOME_IDS, BIOMES, BOAT, BOATS, BOSS_STAGE_GIMS, BOSSES, CAVES, EGG, ENCH, FI, FISH, FUR_BONUSES,
                   FUR_REWARD, FURS, GIMMICKS, ISLE, KEEPER_LOGS, KITTEN, MUT, MUT_GIMS, MUTS, MYTHIC_GIM_POOL, PET, PET_DUPE_MIN,
                   PET_LEVEL_MIN, PET_MAX, QI, QUEST_VERSION, MATS, MUT_UPGRADES, QUESTS, RAR, REEL, RI, ROD, RODS,
                   ROD_SKILL, SKILLS, slice_amount)
from .sfx import Sfx
from .util import D, TAU, clamp, jround, lerp, pick, rand, sign, todot

P = None          # the active profile
LIVE = False      # True while a real player is fishing (the title screen uses a guest backdrop)
MODE = 'local'    # 'local' (saved on this computer) or 'online' (saved on the server)
PRANK = {}        # admin pranks running on this screen: seconds left for 'rev' (reversed controls), 'storm', 'zoom'
save_hook = None  # set by the online module: called with the profile whenever we save online


def now_ms():
    return int(time.time() * 1000)


def new_id():
    n = now_ms()
    digits = '0123456789abcdefghijklmnopqrstuvwxyz'
    s = ''
    while n:
        n, r = divmod(n, 36)
        s = digits[r] + s
    return s + ''.join(random.choice(digits) for _ in range(4))


# ===================================================================================
#  Profiles and saving
# ===================================================================================
def freshProfile(name, fur):
    t = now_ms()
    return D(
        v=1, id=new_id(), name=name, fur=fur, created=t, last=t, rev=0,
        coins=120, xp=0, level=1, biome='shore', unlocked=D(shore=True),
        rod='starter', rods=D(starter=D(ench=None)), boat='dinghy', boats=['dinghy'],
        gear=D(), baits=D(worm=10), bait='worm', fish_bait=None, relics=0, scales=0, mats=D(), kills=D(), recipes=D(),
        bag=[], nextUid=1, dex=D(), dexRewards=[],
        stats=D(casts=0, catches=0, lost=0, snapped=0, burned=0, earned=0, bestCatch=0, mythics=0,
                bosses=0, play=0, enchants=0, abilities=0, perfects=0, petCatches=0, hatched=0),
        cool=D(mythic=0, boss=0), quests=D(), qv=QUEST_VERSION, qp=D(), qc=D(), pets=D(), petOn=[], mut_upgrades=D(),
        logs=[], portal=D(started=False, ending=None), lives=0,
    )


def _num(x, default=0):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else default


def sanitize(p):
    """Make a loaded save safe to play: fill anything missing, drop anything broken."""
    if not isinstance(p, dict) or p.get('v') != 1:
        return None
    p = todot(p)
    old_qv = p.get('qv')
    base = freshProfile(str(p.get('name') or 'Whiskers')[:16], p.get('fur') or FURS[0])
    for k, v in base.items():
        if k not in p:
            p[k] = v
            continue
        cur = p[k]
        if k == 'bait':          # None means "bare hook", which is allowed
            continue
        if isinstance(v, bool):
            ok = isinstance(cur, bool)
        elif isinstance(v, (int, float)):
            ok = isinstance(cur, (int, float)) and not isinstance(cur, bool)
        elif isinstance(v, dict):
            ok = isinstance(cur, dict)
        elif isinstance(v, list):
            ok = isinstance(cur, list)
        elif isinstance(v, str):
            ok = isinstance(cur, str)
        else:
            ok = True
        if not ok:
            p[k] = v
    for k in base.stats:
        p.stats[k] = _num(p.stats.get(k), 0)
    for k in base.cool:
        p.cool[k] = _num(p.cool.get(k), 0)
    if not isinstance(p.mut_upgrades, dict):
        p.mut_upgrades = D()
    p.mut_upgrades = D({k: max(0, int(_num(v))) for k, v in p.mut_upgrades.items() if k in MUT})
    if p.fish_bait not in FI:
        p.fish_bait = None
    p.portal = D(started=bool(p.portal.get('started')), ending=p.portal.get('ending') if p.portal.get('ending') in ('repair', 'seal') else None)
    p.logs = [k for k in dict.fromkeys(p.logs) if k in {entry.id for entry in KEEPER_LOGS}]
    p.dexRewards = [k for k in dict.fromkeys(p.dexRewards) if k in BIOMES]
    p.lives = max(0, min(9, int(_num(p.lives, 0))))
    p.name = str(p.name)[:16]
    if not isinstance(p.fur, str) or not p.fur.startswith('#') or len(p.fur) != 7:
        p.fur = FURS[0]
    for k in ('coins', 'xp', 'level', 'relics', 'scales', 'nextUid', 'rev', 'last', 'created'):
        p[k] = _num(p.get(k), base[k])
    p.level = max(1, int(p.level))
    p.rods = D({k: (v if isinstance(v, dict) else D(ench=None)) for k, v in p.rods.items() if k in ROD})
    for r in p.rods.values():
        if r.get('ench') not in ENCH:
            r['ench'] = None
    if 'starter' not in p.rods:
        p.rods.starter = D(ench=None)
    if p.rod not in p.rods:
        p.rod = 'starter'
    p.boats = [b for b in p.boats if b in BOAT] or ['dinghy']
    if p.boat not in p.boats:
        p.boat = p.boats[0]
    if p.biome not in BIOMES:
        p.biome = 'shore'
    p.baits = D({k: max(0, int(_num(v))) for k, v in p.baits.items() if k in BAIT})
    if p.bait is not None and p.bait not in BAIT:
        p.bait = None
    p.gear = D({k: True for k, v in p.gear.items() if v})
    p.unlocked = D({k: True for k in p.unlocked if k in BIOMES})
    p.unlocked.shore = True
    if p.quests.get('p_mariana') or p.qc.get('p_mariana'):
        p.unlocked.atlantis = True
    bag = []
    for f in p.bag:
        if isinstance(f, dict) and f.get('sp') in FI:
            f = D(f)
            f.kg = _num(f.kg, FI[f.sp].w[0])
            f.val = max(1, int(_num(f.val, 1)))
            if f.mut not in MUT:
                f.mut = None
            f.lock = bool(f.lock)
            f.perfect = bool(f.perfect)
            bag.append(f)
    p.bag = bag
    p.quests = D({k: True for k in p.quests if k in QI})
    p.qc = D({k: True for k in p.qc if k in QI})
    qp = D()
    for k, v in p.qp.items():
        q = QI.get(k)
        if not q or not isinstance(v, dict):
            continue
        g = v.get('g') if isinstance(v.get('g'), list) else []
        sl = v.get('s') if isinstance(v.get('s'), list) else []
        g = [int(_num(x)) for x in g][:len(q.goals)] + [0] * max(0, len(q.goals) - len(g))
        sl = [[str(i) for i in x if i in FI] if isinstance(x, list) else [] for x in sl][:len(q.goals)]
        sl += [[] for _ in range(len(q.goals) - len(sl))]
        qp[k] = D(g=g, s=sl)
    p.qp = qp
    if old_qv != QUEST_VERSION:
        # Whisker Bay 1.3 reset every quest, and quest rods now belong to an island:
        # a quest rod from an island you haven't reached yet goes back until you earn it there.
        p.quests, p.qp, p.qc = D(), D(), D()
        taken = [r.name for r in RODS if r.quest and r.id in p.rods and not p.unlocked.get(r.at)]
        for r in RODS:
            if r.quest and r.id in p.rods and not p.unlocked.get(r.at):
                del p.rods[r.id]
        if p.rod not in p.rods:
            p.rod = max(p.rods.keys(), key=lambda k: (BIOME_IDS.index(ROD[k].at), ROD[k].price))
        p.qv = QUEST_VERSION
        p.migrated = taken or True
    p.pets = D({k: D(t=max(0.0, _num(v.get('t'), 0))) for k, v in p.pets.items() if k in PET and isinstance(v, dict)})
    p.petOn = [k for k in dict.fromkeys(x for x in p.petOn if isinstance(x, str)) if k in p.pets][:petSlots(p)]
    p.dex = D({k: v for k, v in p.dex.items() if k in FI and isinstance(v, dict)})
    for v in p.dex.values():
        v.n = int(_num(v.n, 1))
        v.kg = _num(v.kg, 0)
        if not isinstance(v.muts, dict):
            v.muts = D()
    # boss materials (1.3 kept Leviathan Scales in their own counter) and boss kills
    p.mats = D({k: max(0, int(_num(v))) for k, v in p.mats.items() if k in MATS})
    if p.scales > 0:
        p.mats.scale = (p.mats.get('scale') or 0) + int(p.scales)
        p.scales = 0
    p.kills = D({k: max(0, int(_num(v))) for k, v in p.kills.items() if k in FI})
    p.recipes = D({k: True for k, v in p.recipes.items() if k in ROD and v})
    for rod in RODS:
        if rod.need and p.unlocked.get(rod.at):
            p.recipes[rod.id] = True
    return p


PROFILE_DIR = os.path.join(settings.SAVE_DIR, 'profiles')
INDEX_FILE = os.path.join(PROFILE_DIR, 'index.json')


def readIndex():
    v = settings.read_json(INDEX_FILE, [])
    return [todot(x) for x in v if isinstance(x, dict) and isinstance(x.get('id'), str)] if isinstance(v, list) else []


def writeIndex(lst):
    settings.write_json(INDEX_FILE, lst)


def _safe_id(pid):
    return ''.join(ch for ch in str(pid) if ch.isalnum())[:40] or 'x'


def saveLocal(p):
    p.last = now_ms()
    settings.write_json(os.path.join(PROFILE_DIR, _safe_id(p.id) + '.json'), p)
    lst = [x for x in readIndex() if x.id != p.id]
    lst.insert(0, D(id=p.id, name=p.name, fur=p.fur, level=p.level, coins=jround(p.coins), last=p.last, dex=len(p.dex)))
    writeIndex(lst)


def loadLocal(pid):
    return sanitize(settings.read_json(os.path.join(PROFILE_DIR, _safe_id(pid) + '.json'), None))


def deleteLocal(pid):
    try:
        os.remove(os.path.join(PROFILE_DIR, _safe_id(pid) + '.json'))
    except OSError:
        pass
    writeIndex([x for x in readIndex() if x.id != pid])


def saveProfile():
    if not P or not LIVE:
        return
    P.last = now_ms()
    P.rev = (P.rev or 0) + 1
    if MODE == 'online' and save_hook:
        save_hook(P)
    else:
        saveLocal(P)


def xpNeed(l):
    return jround(40 * l ** 1.5)


def addXP(n):
    P.xp += n
    up = False
    while P.xp >= xpNeed(P.level):
        P.xp -= xpNeed(P.level)
        P.level += 1
        up = True
    if up:
        Sfx.play('level')
        extra = levelUnlockText(P.level)
        toast(f'Level {P.level}!' + (' ' + extra if extra else ''), 'gold')
        G.events.append(('level', P.level))


def levelUnlockText(l):
    for bid in BIOME_IDS:
        b = BIOMES[bid]
        if b.lvl == l and not P.unlocked.get(bid):
            q = QI.get(b.quest)
            if q and not questDone(q):
                return f'You are ready for {b.name}: finish the quest "{q.name}" to sail there.'
            return f'{b.name} is open to boats that can reach it.'
    return ''


# ---------------- islands you can sail to ----------------
def sailCheck(bid, p=None):
    """(can sail, why not) for an island: you need the right boat, and the first time also the level and the island quest."""
    p = p or P
    b = BIOMES[bid]
    if b.portal and not p.unlocked.get(bid):
        return False, 'Find the Keeper’s key in Atlantis'
    if BOAT[p.boat].tier < b.boat:
        return False, f'Needs the {BOATS[b.boat].name}'
    if p.unlocked.get(bid):
        return True, ''
    if p.level < b.lvl:
        return False, f'Needs level {b.lvl}'
    q = QI.get(b.quest)
    if q and not questDone(q, p):
        return False, f'Finish "{q.name}"'
    return True, ''


def petSlots(p=None):
    """How many pets fit in your pet boat: one, and a second seat once you reach the Volcanic Biome."""
    p = p or P
    return 2 if p.unlocked.get('volcano') else 1


def petLevel(pid, p=None):
    p = p or P
    rec = p.pets.get(pid)
    if not rec:
        return 0
    m = (rec.t or 0) / 60
    lvl = 1
    for i, need in enumerate(PET_LEVEL_MIN):
        if m >= need:
            lvl = i + 1
    return lvl


def petProgress(pid, p=None):
    """(level, fraction of the way to the next level)."""
    p = p or P
    lvl = petLevel(pid, p)
    if lvl >= PET_MAX:
        return lvl, 1.0
    m = (p.pets[pid].t or 0) / 60
    a, b = PET_LEVEL_MIN[lvl - 1], PET_LEVEL_MIN[lvl]
    return lvl, clamp((m - a) / (b - a), 0, 1)


def petPower(pid, lvl):
    """What a pet does at a level (all pets together stay a small helping paw, never the main event)."""
    f = (lvl - 1) / (PET_MAX - 1)
    if pid == 'gull':
        return D(bite=1.05 + 0.10 * f)
    if pid == 'otter':
        return D(tension=1 - (0.05 + 0.10 * f))
    if pid == 'parrot':
        return D(luck=1.04 + 0.08 * f)
    if pid == 'pup':
        hv = 1.12 + 0.13 * f
        hh = 1.0 if lvl < 5 else 1.05 + 0.20 * (lvl - 5) / 5
        att = {8: (1.1, 0.85), 9: (1.2, 0.7), 10: (1.35, 0.5)}.get(lvl, (1.0, 1.0))
        if lvl >= 10:
            att = (1.45, 0.62)
        return D(hookV=hv, hookH=hh, rare=att[0], small=att[1])
    if pid == 'kitten':
        sec, odds = KITTEN[lvl - 1]
        if lvl >= 8:
            odds = dict(odds)
            for k in list(odds):
                if k >= 2:
                    odds[k] = max(0, odds[k] - 5)
            odds[0] = odds.get(0, 0) + 8
            odds[1] = odds.get(1, 0) + 7
        return D(every=sec, odds=odds)
    return D()


def petEffectText(pid, lvl):
    """What a pet does at a level, in words."""
    pw = petPower(pid, lvl)
    if pid == 'gull':
        return f'Fish notice your hook {round((pw.bite - 1) * 100)}% sooner.'
    if pid == 'otter':
        return f'Line tension builds {round((1 - pw.tension) * 100)}% slower.'
    if pid == 'parrot':
        return f'+{round((pw.luck - 1) * 100)}% luck for rarer fish.'
    if pid == 'pup':
        t = f'Your hook moves {round((pw.hookV - 1) * 100)}% faster up and down'
        if pw.hookH > 1:
            t += f' and {round((pw.hookH - 1) * 100)}% faster sideways'
        if pw.rare > 1:
            t += f'. Rare fish notice your bait {round((pw.rare - 1) * 100)}% sooner and small fry {round((1 - pw.small) * 100)}% later'
        return t + '.'
    if pid == 'kitten':
        odds = ', '.join(f'{v}% {RAR[k].name}' for k, v in sorted(pw.odds.items()))
        return f'Catches a fish every {pw.every} s ({odds}).'
    return ''


def mutationUpgradeLevel(mid):
    if not mid or mid not in MUT:
        return 0
    return int(P.mut_upgrades.get(mid, 0) or 0)


def mutationUpgradeBonus(mid):
    lvl = mutationUpgradeLevel(mid)
    if not lvl or mid not in MUT_UPGRADES:
        return 1.0
    data = MUT_UPGRADES[mid]
    for target, bonus in zip(data['targets'], data['bonus']):
        if lvl >= target:
            return bonus
    return 1.0


def gearStats():
    r = ROD[P.rod]
    e = (P.rods.get(P.rod) or {}).get('ench')
    bio = P.biome
    bt = BAIT.get(P.bait) if P.bait else None
    bait = bt if bt and (P.baits.get(P.bait) or 0) > 0 and (not bt.at or bt.at == bio) else None
    fish_bait = FI.get(P.fish_bait) if P.fish_bait in FI else None
    fish_bonus = D(luck=1.0, bite=1.0, mut=1.0)
    if fish_bait and RI[fish_bait.r] <= 1:
        tier = RI[fish_bait.r]
        fish_bonus.luck = 1.12 + tier * 0.08
        fish_bonus.bite = 1.12 + tier * 0.08
        fish_bonus.mut = 1.0
    crew = 1 + min(0.15, 0.05 * G.crew)
    pw = D(bite=1.0, tension=1.0, luck=1.0, hookV=1.0, hookH=1.0, rare=1.0, small=1.0)
    for pid in P.petOn:
        for k, v in petPower(pid, petLevel(pid)).items():
            if k in pw:
                pw[k] *= v
    mut_bonus = max((mutationUpgradeBonus(mid) for mid, v in P.mut_upgrades.items() if v > 0), default=1.0)
    fur = FUR_BONUSES.get(P.fur, D())
    page_bonus = 1.05 if bio in P.dexRewards else 1.0
    tidecaller = 1.2 if e == 'tidecaller' else 1.0
    accessory_luck = (1.05 if P.gear.get('orichalcumcompass') else 1.0) * (1.06 if P.gear.get('pearlcharm') else 1.0)
    accessory_mut = 1.05 if P.gear.get('pearlcharm') else 1.0
    return D(
        rod=r, ench=e, bait=bait, fish_bait=fish_bait, crew=crew, isle=ISLE[bio],
        luck=r.luck * (1.3 if e == 'lucky' else 1) * (1.5 if e == 'mythical' else 1) * tidecaller * page_bonus * accessory_luck * fur.get('luck', 1) * (bait.luck if bait else 1) * fish_bonus.luck * mut_bonus * crew * pw.luck,
        control=r.control * (1.18 if e == 'steady' else 1) * (1.1 if e == 'mythical' else 1) * fur.get('control', 1),
        reel=r.reel * (1.25 if e == 'swift' else 1) * (1.1 if e == 'mythical' else 1) * fur.get('reel', 1) * (1.12 if P.gear.get('reel') else 1),
        str=r.str, tension=(0.6 if e == 'resilient' else 1) * pw.tension * fur.get('tension', 1)
        * (0.95 if P.gear.get('shellbracelet') else 1) * (0.93 if P.gear.get('moonbell') else 1),
        depth=min(BIOMES[bio].depth, jround(r.depth * (1.25 if e == 'diver' else 1))),
        heat=bool(r.heat or P.gear.get('shield') or e == 'blazing' or (bait and bait.heat)),
        light=1 + (0.5 if r.light else 0) + (1.2 if P.gear.get('lamp') else 0) + (0.6 if bait and bait.light else 0),
        magnet=e == 'magnet', mut=(1.8 if e == 'fortune' else 1) * accessory_mut * fur.get('mut', 1) * (bait.mut if bait and bait.mut else 1) * fish_bonus.mut * mut_bonus,
        val=1.15 if e == 'fortune' else 1,
        bite=r.lure * fur.get('bite', 1) * (bait.bite if bait else 1) * fish_bonus.bite * mut_bonus
        * (1.06 if P.gear.get('catcollar') else 1) * pw.bite, boss=bait.boss if bait and bait.boss else 1,
        notice=1.5 if e == 'magnet' else 1.0, chase=1.25 if e == 'magnet' else 1.0,
        hookV=pw.hookV * fur.get('hookV', 1), hookH=pw.hookH * fur.get('hookH', 1), rare=pw.rare, small=pw.small,
        sonar=3 if P.gear.get('sonar3') else 2 if P.gear.get('sonar2') else 1 if P.gear.get('sonar1') else 0,
    )


# Every species has a favourite depth (dz). It is at home within dr metres of it, and each 50 m beyond
# that cuts its chance by about 35 points (80% -> 45% -> 10% -> gone), so nothing lives everywhere.
def depthFactor(sp, d):
    off = abs(d - sp.dz) - sp.dr
    return 1.0 if off <= 0 else max(0.0, 1 - 0.4375 * off / 50)


_by_tier = {}


def islandFish(bio, tier):
    k = (bio, tier)
    lst = _by_tier.get(k)
    if lst is None:
        lst = _by_tier[k] = [f for f in FISH if f.b == bio and RI[f.r] == tier and not getattr(f, 'cave', False)]
    return lst


def tierCover(bio, tier, d):
    """How much of a rarity lives at this depth (0..1): the best-suited species of that rarity decides."""
    return max((depthFactor(f, d) for f in islandFish(bio, tier)), default=0.0)


# Rarity of a newly spawned fish at depth d (m). Luck shifts the odds up, and only rarities with a species
# living around this depth can appear. Mythic and Leviathan are capped and go quiet for a while after one
# shows up, so they never come in floods.
spawnCD = {'mythic': 0.0, 'legendary': 0.0}


def rarityWeights(bio, d, S):
    B = BIOMES[bio]
    df = clamp(d / B.depth, 0, 1)
    L = S.luck * (1 + 0.35 * df)
    pw = [0, 0.5, 1, 1.2, 1.4, 1.5, 1]
    w = []
    for i, r in enumerate(RAR):
        cov = tierCover(bio, i, d)
        if cov <= 0:
            w.append(0.0)
            continue
        x = r.w * L ** pw[i] * cov
        if i == 5:
            if spawnCD['mythic'] > 0:
                w.append(0.0)
                continue
            if P.cool.mythic > 0:
                x *= 0.15
        if i == 4 and spawnCD['legendary'] > 0:
            x *= 0.3
        if i == 6:
            if P.cool.boss > 0:
                w.append(0.0)
                continue
            x *= S.boss
        w.append(x)
    s = sum(w)
    for i, cap in ((4, 0.06), (5, 0.025), (6, 0.02)):
        if s > 0 and w[i] / s > cap:
            ex = w[i] - cap * s
            w[i] -= ex
            w[0] += ex
    s = sum(w) or 1
    return [x / s for x in w]


def rollRarity(bio, d, S):
    w = rarityWeights(bio, d, S)
    r = random.random()
    for i, x in enumerate(w):
        r -= x
        if r <= 0:
            return i
    return 0


def speciesFor(bio, tier, d=None):
    lst = [sp for sp in islandFish(bio, tier) if MODE == 'online' or not getattr(sp, 'limited', 0)]
    while not lst and tier > 0:
        tier -= 1
        lst = islandFish(bio, tier)
    if d is None:
        return pick(lst)
    ws = [depthFactor(f, d) for f in lst]
    tot = sum(ws)
    if tot <= 0:
        return min(lst, key=lambda f: abs(f.dz - d))
    r = random.random() * tot
    for f, x in zip(lst, ws):
        r -= x
        if r <= 0:
            return f
    return lst[-1]


def rollMutation(S, bio):
    m = S.mut * (1.3 if bio == 'reef' else 1)
    for mu in reversed(MUTS):
        if random.random() < mu.chance * m:
            return mu.id
    return None


def rollWeight(sp):
    return sp.w[0] + (sp.w[1] - sp.w[0]) * random.random() ** 1.8


def wfrac(sp, kg):
    return (kg - sp.w[0]) / ((sp.w[1] - sp.w[0]) or 1)


def catchValue(sp, kg, mut, perfect, S):
    return max(1, jround(sp.val * (0.55 + 0.9 * wfrac(sp, kg)) * (MUT[mut].mult if mut else 1) * (1.2 if perfect else 1) * S.val))


def catchXP(sp, kg, mut):
    return max(1, jround(RAR[RI[sp.r]].xp * ISLE[sp.b].xp * (1 + wfrac(sp, kg)) * (1.5 if mut else 1)))


def sizeWord(sp, kg):
    wf = wfrac(sp, kg)
    return 'Colossal' if wf > 0.9 else 'Giant' if wf > 0.7 else 'Tiny' if wf < 0.08 else ''


def holdSize():
    return BOAT[P.boat].hold


# ===================================================================================
#  Game state
# ===================================================================================
class Part:
    """A particle living in the water (x in pixels, d in metres)."""
    __slots__ = ('x', 'd', 'vx', 'vd', 'life', 'max', 'col', 'size', 'kind', 'g')

    def __init__(self, x, d, vx, vd, life, mx, col, size, kind='dot', g=0.0):
        self.x, self.d, self.vx, self.vd, self.life, self.max = x, d, vx, vd, life, mx
        self.col, self.size, self.kind, self.g = col, size, kind, g


class SPart:
    """A particle drawn straight on the screen (rain, embers, sparks)."""
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max', 'col', 'size', 'g', 'kind')

    def __init__(self, x, y, vx, vy, life, mx, col, size, g, kind):
        self.x, self.y, self.vx, self.vy, self.life, self.max = x, y, vx, vy, life, mx
        self.col, self.size, self.g, self.kind = col, size, g, kind


class Fish:
    __slots__ = ('sp', 'tier', 'mut', 'kg', 'size', 'dir', 'x', 'd', 'home', 'spd', 'amp', 'ph', 'state', 'st',
                 'nib', 'need', 'burst', 'dartT', 'tt', 'blinkT', 'alpha', 'vx', 'vd', 'spook', 'anim', 'turn', 'seed',
                 'pinged', 'touch', 'seen', 'sharedId', 'sharedX', 'sharedD', 'sharedBorn', 'sharedAmp',
                 'sharedPhase', 'sharedRoom')


class Game:
    def __init__(self):
        self.t = 0.0
        self.ts = 1.0
        self.tsTarget = 1.0
        self.W, self.H = 1280, 720
        self.S = clamp(min(self.W, self.H * 1.45) / 920, 0.6, 1.25)
        self.PPM = 5 * self.S
        self.mode = 'idle'
        self.modeT = 0.0
        self.cam = 0.0
        self.hook = D(x=0.0, d=-1.0, vx=0.0, vd=0.0, hold=False, speed=0.0)
        self.charge = 0.0
        self.chargeDir = 1
        self.fly = None
        self.fish = []
        self.sharedPopulation = {}
        self.sharedBoss = None
        self.bossSearchPending = False
        self.caveLayouts = {}
        self.parts = []
        self.sparts = []
        self.floats = []
        self.shake = 0.0
        self.flash = 0.0
        self.flashCol = '#ffffff'
        self.bite = self.reel = self.land = self.card = self.hype = None
        self.storm = 0.0
        self.stormOn = False
        self.remoteBoss = False   # another angler on this island is fighting the Leviathan
        self.sharedFish = None
        self.thunderT = 4.0
        self.bolt = 0.0
        self.boltX = 0.0
        self.erupt = 0.0
        self.eruptT = 30.0
        self.vents = []
        self.sail = None
        self.keys = {}
        self.act = False
        self.stats = None
        self.spawnT = 0.0
        self.autosave = 0.0
        self.bf = 0.22
        self.bv = 0.0
        self.nearDock = False
        self.toasts = []
        self.timers = []
        self.events = []
        self.crew = 0
        self.cheer = 0.0          # seconds of reel boost left from friends cheering
        self.surgeT = 0.0         # rod skill: faster hook movement and fish repellent
        self.surgeCD = 0.0        # short cooldown prevents repeated activation
        self.skillT = 0.0
        self.skillCD = 0.0
        self.emote = None         # (text, colour, time) bubble above your own cat
        self.ripples = []         # rings spreading on the water surface
        self.happy = 0.0          # the cat's little celebration hop after a catch
        self.kitT = 20.0          # seconds until the kitten tries for a fish
        self.petFx = None         # the kitten's catch, shown above the pet boat
        self.dread = 0.0          # 0..1: how close the Leviathan is (the water goes dark and cold)
        self.sonarT = -99.0       # when the sonar last announced a contact


G = Game()


def BIO():
    return BIOMES[P.biome]


def mouthOf(f):
    if f.sp.shape == 'nessie':        # her head is up on the end of that long neck
        return f.x + f.dir * f.size * 0.5, f.d - f.size * 0.31 / G.PPM
    return f.x + f.dir * f.size * 0.48, f.d


def refreshStats():
    G.stats = gearStats()


def surfBase():
    return G.H * 0.42


def sy(d):
    return surfBase() + (d - G.cam) * G.PPM


def boatX():
    return G.W * G.bf


def boatTick(dt):
    K = G.keys
    steer = ((1 if K.get('right') else 0) - (1 if K.get('left') else 0)) if G.mode == 'idle' else 0
    if PRANK.get('rev', 0) > 0:
        steer = -steer
    top = 0.06 + 0.012 * BOAT[P.boat].tier
    G.bv += (steer * top - G.bv) * min(1, dt * (2.2 if steer else 1.6))
    G.bf = clamp(G.bf + G.bv * dt, 0.1, 0.72)
    if (G.bf <= 0.1 or G.bf >= 0.72) and abs(G.bv) > 0.01:
        G.bv *= 0.5
    if abs(G.bv) > 0.02 and random.random() < dt * 30:
        s = sign(G.bv)
        addPart(Part(boatX() - s * 90 * G.S + rand(-8, 8), -0.5, -s * rand(10, 40), -rand(2, 6), 0.7, 0.7, '#e6f6ff', rand(1.5, 3.5) * G.S, 'dot', 14))
    G.nearDock = G.bf < 0.16


def rodTip():
    bend = 22 * G.S * (0.4 + (G.reel.ten if G.reel else 0)) if G.mode == 'reel' else 9 * G.S if G.mode == 'bite' else 0
    return boatX() + 112 * G.S, sy(0) - 126 * G.S + bend + math.sin(G.t * 1.6) * 2.5 * G.S


def setMode(m):
    G.mode = m
    G.modeT = 0.0


# ---------------- particles, floating text, toasts ----------------
def addPart(p):
    if len(G.parts) < 700:
        G.parts.append(p)


def burst(x, d, col, n, spd=1.0, kind='dot'):
    for _ in range(n):
        a = random.random() * TAU
        v = spd * rand(20, 120) * G.S
        addPart(Part(x, d, math.cos(a) * v, math.sin(a) * v / G.PPM, rand(0.5, 1.2), 1.2, col, rand(1.5, 4) * G.S, kind, 18 if kind == 'drop' else 0))


def floatText(x, d, text, col='#ffffff', size=18, dur=1.6):
    G.floats.append(D(x=x, d=d, text=text, col=col, size=size, t=0.0, dur=dur))


def toast(msg, kind=''):
    G.toasts.append(D(msg=msg, kind=kind, t=0.0, dur=4.2 if kind == 'gold' else 2.8))
    while len(G.toasts) > 4:
        G.toasts.pop(0)


def ripple(x, size=1.0):
    """Rings that spread across the water surface."""
    if len(G.ripples) < 24:
        G.ripples.append(D(x=x, t=0.0, life=1.4 + 0.5 * size, size=size))


def later(sec, fn):
    G.timers.append([sec, fn])


def shake(a):
    if settings.SET.get('shake', True):
        G.shake = max(G.shake, a)


def flash(a, col='#ffffff'):
    G.flash = max(G.flash, a)
    G.flashCol = col


# ---------------- arriving at an island ----------------
def enterBiome():
    G.fish = []
    G.sharedPopulation = {}
    G.sharedBoss = None
    G.bossSearchPending = False
    G.sharedFish = None
    G.parts = []
    G.sparts = []
    G.floats = []
    G.ripples = []
    G.hook.d = -1
    G.cam = 0
    G.bite = G.reel = G.land = None
    G.stormOn = False
    G.storm = 0
    Sfx.stop_drone()
    G.vents = []
    if P.biome == 'volcano':
        Dp = BIOMES['volcano'].depth
        for k in range(3):
            d0 = rand(70, 320)
            G.vents.append(D(fx=0.4 + k * 0.2 + rand(-0.05, 0.05), d0=d0, d1=min(Dp - 10, d0 + rand(160, 420)), ph=random.random() * 6))
        G.eruptT = rand(20, 40)
        G.erupt = 0
    refreshStats()
    if MODE != 'online':
        for _ in range(16):
            spawnFish(True)
    setMode('idle')


def caveLayout(biome):
    return G.caveLayouts.get(biome) or CAVES.get(biome)


def setCaveLayout(biome, layout):
    if biome not in BIOMES:
        return False
    if layout is None:
        G.caveLayouts.pop(biome, None)
        return True
    if not isinstance(layout, dict):
        return False
    rooms, corridors = layout.get('rooms'), layout.get('corridors')
    if not isinstance(rooms, list) or not 1 <= len(rooms) <= 12 or not isinstance(corridors, list):
        return False
    parsed_rooms = []
    for room in rooms:
        if not isinstance(room, dict):
            return False
        x, d = room.get('x'), room.get('d')
        if (not isinstance(x, list) or len(x) != 2 or not isinstance(d, list) or len(d) != 2
                or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value)
                       for value in x + d)
                or not 0 <= x[0] < x[1] <= 1 or not 0 <= d[0] < d[1] <= BIOMES[biome].depth):
            return False
        parsed_rooms.append(D(x=tuple(x), d=tuple(d)))
    parsed_corridors = []
    if len(corridors) != len(parsed_rooms) or any(
            not isinstance(point, list) or len(point) != 2
            or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value)
                   for value in point)
            or not 0 <= point[0] <= 1 or not 0 <= point[1] <= BIOMES[biome].depth
            for point in corridors):
        return False
    parsed_corridors = [tuple(point) for point in corridors]
    base = CAVES.get(biome)
    if base:
        G.caveLayouts[biome] = D(name=base.name, x=base.x, d=base.d, fish=base.fish,
                                 rooms=parsed_rooms, corridors=parsed_corridors)
    else:
        G.caveLayouts[biome] = D(name='Cave', x=(0.05, 0.95), d=(0, BIOMES[biome].depth),
                                 fish=[], rooms=parsed_rooms, corridors=parsed_corridors)
    return True


# ---------------- fish spawning ----------------
def spawnWindow():
    B = BIO()
    view = G.H / G.PPM
    return max(3, G.cam - 25), min(B.depth - 4, G.cam + view + 110)


FISH_K = 1.2   # how big fish look in the water, relative to their listed length
SWIM_K = 1.3   # cruising speed (1.3 = 30% quicker than 1.2)


def spawnFish(initial, force=None, at=None):
    lo, hi = spawnWindow()
    if hi <= lo and force is None:
        return
    d = rand(lo, hi) if at is None else at
    S = G.stats
    special_x = None
    special_room = None
    if force is not None:
        sp = force
    else:
        cave = caveLayout(P.biome)
        cave_fish = [FI[k] for k in cave.fish] if cave else []
        cave_lo = max(lo, cave.d[0]) if cave else 1
        cave_hi = min(hi, cave.d[1]) if cave else 0
        cave_rooms = [(i, room) for i, room in enumerate(cave.rooms)
                      if max(cave_lo, room.d[0]) < min(cave_hi, room.d[1])] if cave else []
        if MODE != 'online' and cave_fish and cave_rooms and random.random() < 0.12:
            sp = pick(cave_fish)
            special_room, room = pick(cave_rooms)
            d = rand(max(cave_lo, room.d[0]), min(cave_hi, room.d[1]))
            special_x = rand(room.x[0], room.x[1])
        else:
            tier = rollRarity(P.biome, d, S)
            if tier == 6 and any(f.tier == 6 for f in G.fish):
                tier = 0
            if MODE == 'online':
                if tier != 6:
                    return
                if not G.sharedBoss and not G.bossSearchPending:
                    G.bossSearchPending = True
                    G.events.append(('boss_search', D(b=P.biome)))
                return
            sp = speciesFor(P.biome, tier, d)
    tier = RI[sp.r]
    if force is None and (sp.dz - sp.dr - 60 > d or d > sp.dz + sp.dr + 60):
        d = clamp(d, sp.dz - sp.dr - 60, sp.dz + sp.dr + 60)
        d = clamp(d, lo, hi)
    if tier == 5:
        spawnCD['mythic'] = 150
    if tier == 4:
        spawnCD['legendary'] = 25
    kg = rollWeight(sp)
    wf = wfrac(sp, kg)
    dr = -1 if random.random() < 0.5 else 1
    size = sp.len * G.S * FISH_K * (0.78 + 0.45 * wf) * (0.71 if tier == 6 else 1)
    f = Fish()
    f.sp, f.tier, f.mut, f.kg, f.size, f.dir = sp, tier, rollMutation(S, P.biome), kg, size, dr
    # fish that appear in plain sight swim in from the sides; ones out of sight can start anywhere
    seen = G.cam - 4 - size / G.PPM < d < G.cam + G.H / G.PPM + 4 + size / G.PPM
    f.x = special_x * G.W if special_x is not None else (rand(0, G.W) if (initial or not seen) else (-size - 20 if dr > 0 else G.W + size + 20))
    f.d = f.home = d
    f.spd = (14 + 4.5 * tier) * G.S * rand(0.85, 1.15) * SWIM_K * (0.6 if tier == 6 else 1)
    f.amp = rand(1, 4)
    f.ph = random.random() * 10
    f.anim = random.random() * 10
    f.turn = 0.0
    f.seed = random.random() * 6.28
    f.state = 'swim'
    f.st = f.nib = f.need = f.burst = 0.0
    f.dartT = rand(0.5, 3)
    f.tt = rand(0.5, 2)
    f.blinkT = rand(2, 5)
    f.alpha = 1.0
    f.vx = f.vd = f.spook = 0.0
    f.pinged = False
    f.seen = False
    f.touch = 0.0
    f.sharedId = None
    f.sharedRoom = special_room
    G.fish.append(f)
    return f


def setSharedFish(data):
    """Receive the server's one island-wide Mythic target and mirror it in the local water."""
    if not isinstance(data, dict) or P is None or data.get('b') != P.biome:
        G.sharedFish = None
        G.fish[:] = [f for f in G.fish if not f.sharedId]
        return
    sp = FI.get(data.get('sp'))
    if (not isinstance(data.get('id'), str) or not sp or sp.b != P.biome or sp.r != 'mythic'
            or not isinstance(data.get('d'), (int, float)) or not isinstance(data.get('kg'), (int, float))):
        toast('The server sent invalid shared-fish data; this island’s shared fish was hidden.', 'bad')
        G.sharedFish = None
        return False
    old = G.sharedFish
    G.sharedFish = D(id=data['id'], b=data['b'], sp=sp.id, d=clamp(data['d'], 0, BIOMES[P.biome].depth),
                     kg=clamp(data['kg'], sp.w[0], sp.w[1]), x=clamp(data.get('x', 0.5), 0.05, 0.95),
                     mut=data.get('mut') if data.get('mut') in MUT else None)
    if old and old.id != G.sharedFish.id:
        G.fish[:] = [f for f in G.fish if f.sharedId != old.id]
    _spawnSharedFish()
    return True


def setSharedPopulation(biome, records, caves=None):
    """Mirror the server's ordinary fish population for the current island and depth range."""
    if P is None or biome != P.biome or not isinstance(records, list) or len(records) > 128:
        return False
    if not setCaveLayout(biome, caves):
        toast('The server sent an invalid cave layout; the previous layout remains active.', 'bad')
        return False
    cave = caveLayout(biome)
    valid = {}
    for data in records:
        if not isinstance(data, dict):
            continue
        fish_id = data.get('id')
        sp = FI.get(data.get('sp'))
        room = data.get('room')
        if sp and sp.cave:
            if (not cave or not isinstance(room, int) or isinstance(room, bool)
                    or not 0 <= room < len(cave.rooms)):
                continue
        else:
            room = None
        if (not isinstance(fish_id, str) or not fish_id or len(fish_id) > 64 or not sp or sp.b != biome
                or RI[sp.r] >= 5 or not isinstance(data.get('d'), (int, float))
                or isinstance(data.get('d'), bool) or not math.isfinite(data['d'])
                or not isinstance(data.get('kg'), (int, float)) or isinstance(data.get('kg'), bool)
                or not math.isfinite(data['kg']) or not isinstance(data.get('x'), (int, float))
                or isinstance(data.get('x'), bool) or not math.isfinite(data['x'])
                or not isinstance(data.get('born'), (int, float)) or isinstance(data.get('born'), bool)
                or not math.isfinite(data['born'])
                or not isinstance(data.get('amp'), (int, float)) or isinstance(data.get('amp'), bool)
                or not math.isfinite(data['amp']) or not isinstance(data.get('phase'), (int, float))
                or isinstance(data.get('phase'), bool) or not math.isfinite(data['phase'])):
            continue
        valid[fish_id] = data
    old_ids = set(G.sharedPopulation)
    for fish_id, data in valid.items():
        sp = FI[data['sp']]
        f = G.sharedPopulation.get(fish_id)
        if f is None:
            f = Fish()
            f.sp, f.tier = sp, RI[sp.r]
            f.mut = data.get('mut') if data.get('mut') in MUT else None
            f.kg = clamp(data['kg'], sp.w[0], sp.w[1])
            wf = wfrac(sp, f.kg)
            f.size = sp.len * G.S * FISH_K * (0.78 + 0.45 * wf)
            f.dir = -1 if data.get('dir') == -1 else 1
            f.x = clamp(data['x'], 0.02, 0.98) * G.W
            f.d = f.home = clamp(data['d'], 0, BIOMES[biome].depth)
            f.sharedX, f.sharedD, f.sharedBorn = clamp(data['x'], 0.02, 0.98), f.d, data['born']
            f.sharedAmp, f.sharedPhase = clamp(data['amp'], 0, 20), data['phase']
            f.sharedRoom = room
            f.spd = (14 + 4.5 * f.tier) * G.S * SWIM_K
            f.amp = rand(1, 4)
            f.ph = random.random() * 10
            f.anim = random.random() * 10
            f.turn = f.vx = f.vd = f.spook = 0.0
            f.seed = random.random() * 6.28
            f.state = 'swim'
            f.st = f.nib = f.need = f.burst = 0.0
            f.dartT, f.tt, f.blinkT = rand(0.5, 3), rand(0.5, 2), rand(2, 5)
            f.alpha, f.pinged, f.seen, f.touch = 1.0, False, False, 0.0
            f.sharedId = fish_id
            G.sharedPopulation[fish_id] = f
            G.fish.append(f)
        else:
            f.sp, f.tier = sp, RI[sp.r]
            f.sharedX, f.sharedD, f.sharedBorn = clamp(data['x'], 0.02, 0.98), clamp(data['d'], 0, BIOMES[biome].depth), data['born']
            f.sharedAmp, f.sharedPhase = clamp(data['amp'], 0, 20), data['phase']
            f.sharedRoom = room
    for fish_id in old_ids - set(valid):
        f = G.sharedPopulation.pop(fish_id)
        if G.reel and G.reel.f is f:
            continue
        if f in G.fish:
            G.fish.remove(f)
    return True


def setSharedBoss(data):
    G.bossSearchPending = False
    if not isinstance(data, dict) or P is None or data.get('b') != P.biome:
        old = G.sharedBoss
        active = old and (G.bite and G.bite.f is old or G.reel and G.reel.f is old)
        if not active:
            G.sharedBoss = None
            if old and old in G.fish:
                G.fish.remove(old)
        if data is None:
            G.spawnT = max(G.spawnT, 3.0)
        return data is None
    sp = FI.get(data.get('sp'))
    boss = BOSSES.get(P.biome)
    if (not isinstance(data.get('id'), str) or not sp or not boss or sp.id != boss.fish
            or not isinstance(data.get('d'), (int, float)) or isinstance(data.get('d'), bool)
            or not math.isfinite(data['d']) or not isinstance(data.get('kg'), (int, float))
            or isinstance(data.get('kg'), bool) or not math.isfinite(data['kg'])
            or not isinstance(data.get('x'), (int, float)) or isinstance(data.get('x'), bool)
            or not math.isfinite(data['x'])):
        toast('The server sent invalid shared-boss data; this encounter was hidden.', 'bad')
        return False
    old = G.sharedBoss
    G.sharedBoss = Fish()
    f = G.sharedBoss
    f.sp, f.tier = sp, 6
    f.mut = data.get('mut') if data.get('mut') in MUT else None
    f.kg = clamp(data['kg'], sp.w[0], sp.w[1])
    f.size = sp.len * G.S * FISH_K * (0.78 + 0.45 * wfrac(sp, f.kg)) * 0.71
    f.dir, f.x = 1, clamp(data['x'], 0.05, 0.95) * G.W
    f.d = f.home = clamp(data['d'], 0, BIOMES[P.biome].depth)
    f.spd = f.amp = f.ph = f.anim = f.turn = f.vx = f.vd = f.spook = 0.0
    f.seed = 0.0
    f.state = 'swim'
    f.st = f.nib = f.need = f.burst = 0.0
    f.dartT, f.tt, f.blinkT = 1.0, 1.0, 3.0
    f.alpha, f.pinged, f.seen, f.touch = 1.0, False, False, 0.0
    f.sharedId = data['id']
    f.sharedRoom = None
    if old and old in G.fish:
        G.fish.remove(old)
    G.fish.append(f)
    return True


def _showSharedBoss():
    f = G.sharedBoss
    if MODE != 'online' or not f or f in G.fish:
        return
    lo, hi = spawnWindow()
    if lo - 90 <= f.d <= hi + 100:
        G.fish.append(f)


def _spawnSharedFish():
    data = G.sharedFish
    if MODE != 'online' or not data:
        return
    existing = next((f for f in G.fish if f.sharedId == data.id), None)
    if existing:
        existing.state = 'swim'
        existing.x, existing.d, existing.home = data.x * G.W, data.d, data.d
        existing.dir = 1
        existing.vx = existing.vd = existing.spook = 0.0
        existing.alpha = 1.0
        return
    lo, hi = spawnWindow()
    if not lo - 90 <= data.d <= hi + 100:
        return
    sp = FI[data.sp]
    f = Fish()
    f.sp, f.tier, f.mut, f.kg = sp, 5, data.mut, data.kg
    f.size = sp.len * G.S * FISH_K * (0.78 + 0.45 * wfrac(sp, f.kg))
    f.dir, f.x = 1, data.x * G.W
    f.d = f.home = data.d
    f.spd = f.amp = 0.0
    f.ph = f.anim = f.turn = f.vx = f.vd = f.spook = 0.0
    f.seed = 0.0
    f.state = 'swim'
    f.st = f.nib = f.need = f.burst = 0.0
    f.dartT, f.tt, f.blinkT = 1.0, 1.0, 3.0
    f.alpha, f.pinged, f.seen, f.touch = 1.0, False, False, 0.0
    f.sharedId = data.id
    G.fish.append(f)


def removeSharedFish(shared_id, owner=None):
    """Remove a claimed shared target, cancelling a losing local reel if needed."""
    if not isinstance(shared_id, str):
        return
    if owner == (P.name if P else None):
        return
    if G.sharedFish and G.sharedFish.id == shared_id:
        G.sharedFish = None
    if G.sharedBoss and G.sharedBoss.sharedId == shared_id:
        G.sharedBoss = None
    G.sharedPopulation.pop(shared_id, None)
    for f in G.fish[:]:
        if f.sharedId != shared_id:
            continue
        if G.reel and G.reel.f is f and owner != (P.name if P else None):
            loseReel('slip')
            toast('Another angler hooked the shared fish first.', 'bad')
        elif G.bite and G.bite.f is f:
            G.bite = None
            f.state = 'flee'
            setMode('recall')
            toast('Another angler hooked the shared fish first.', 'bad')
        if f in G.fish:
            G.fish.remove(f)


def sharedClaimFailed(shared_id):
    if G.reel and G.reel.f.sharedId == shared_id:
        loseReel('slip')
    elif G.bite and G.bite.f.sharedId == shared_id:
        f = G.bite.f
        G.bite = None
        f.state = 'flee'
        setMode('recall')
    toast('Another angler reached that shared fish first.', 'bad')


def sharedBossDenied():
    if G.bite and G.bite.f.tier == 6:
        f = G.bite.f
        G.bite = None
        f.state = 'flee'
        setMode('recall')
        toast('Another angler hooked the island boss first.', 'bad')
    elif G.reel and G.reel.boss:
        loseReel('slip')


# How eagerly each rarity notices a hook (per second, inside its notice range). Small fry are greedy;
# rare fish are cautious, so you often have to steer the bait to them before the little ones get there.
NOTICE = [2.6, 2.0, 1.0, 0.7, 0.5, 0.38, 0.5]
# the chance that a fish that bumps into the bait without having noticed it bites anyway
BUMP = [1.0, 0.85, 0.45, 0.3, 0.2, 0.12, 0.15]


def noticeRange(f, S):
    return (98 + 15 * f.tier + 0.25 * min(f.size, 260)) * G.S * S.notice * (2.2 if f.tier == 6 else 1)


def attraction(f, S):
    """Pets that make your bait tastier to big fish (and boring to small fry)."""
    return S.small if f.tier <= 1 else S.rare if 2 <= f.tier <= 5 else 1.0


def spookSpeed(S):
    """Rare fish bolt if the hook moves faster than this (pixels a second): steering and sinking are fine, diving is not."""
    return 1.35 * 22 * (1 + BIO().depth / 1500) * G.PPM * S.hookV + 60 * G.S


def touchingBait(f, h):
    """True when the hook is in the fish's mouth area: from the snout back along the head."""
    rx = (h.x - f.x) * f.dir
    ry = (h.d - f.d) * G.PPM
    near = clamp(rx, f.size * 0.18, f.size * 0.5)
    reach = max(7 * G.S, f.size * (0.1 if f.sp.shape == 'eel' or f.tier == 6 else 0.14))
    return math.hypot(rx - near, ry) < reach


def fishTick(dt):
    G.surgeT = max(0.0, G.surgeT - dt)
    G.surgeCD = max(0.0, G.surgeCD - dt)
    G.skillT = max(0.0, G.skillT - dt)
    G.skillCD = max(0.0, G.skillCD - dt)
    _spawnSharedFish()
    _showSharedBoss()
    lo, hi = spawnWindow()
    S, h = G.stats, G.hook
    hookIn = G.mode == 'sinking'
    G.spawnT -= dt
    if MODE == 'online':
        if not any(f.tier == 6 for f in G.fish) and G.spawnT <= 0:
            spawnFish(False)
            G.spawnT = 0.25
    else:
        want = clamp(jround((hi - lo) / 8.5), 6, 46)
        if len(G.fish) < want and G.spawnT <= 0:
            for _ in range(3 if want - len(G.fish) > 8 else 1):
                spawnFish(False)
            G.spawnT = 0.25
    depth = BIO().depth
    for i in range(len(G.fish) - 1, -1, -1):
        f = G.fish[i]
        if f.state == 'hooked':
            continue
        away = (f.x < -f.size - 80 and f.dir < 0) or (f.x > G.W + f.size + 80 and f.dir > 0)
        if f.d < lo - 90 or f.d > hi + 150 or away:
            G.fish.pop(i)
            if f.sharedId:
                G.sharedPopulation.pop(f.sharedId, None)
            continue
        if f.sharedId in G.sharedPopulation and f.state == 'swim':
            elapsed = max(0.0, time.time() - f.sharedBorn)
            phase = f.sharedPhase
            shared_x = f.sharedX + f.dir * 0.025 * math.sin(elapsed * 0.22 + phase)
            shared_d = f.sharedD + f.sharedAmp * math.sin(elapsed * 0.16 + phase * 1.7)
            cave = caveLayout(P.biome) if f.sharedRoom is not None else None
            if cave and 0 <= f.sharedRoom < len(cave.rooms):
                room = cave.rooms[f.sharedRoom]
                shared_x = clamp(shared_x, room.x[0], room.x[1])
                shared_d = clamp(shared_d, room.d[0], room.d[1])
            f.x = clamp(shared_x, 0.02, 0.98) * G.W
            f.d = f.home = clamp(shared_d, 0, depth)
            f.ph += dt
            f.anim += dt * 0.8
            f.vx = f.vd = 0.0
            if hookIn and not G.bite and f.spook <= 0:
                mx, md = mouthOf(f)
                dist = math.hypot(h.x - mx, (h.d - md) * G.PPM)
                if dist < noticeRange(f, S) and random.random() < dt * NOTICE[f.tier] * S.bite * attraction(f, S):
                    f.state = 'chase'
                    f.st = 0
                elif f.touch <= 0 and touchingBait(f, h):
                    f.touch = 1.5
                    if random.random() < BUMP[f.tier] * min(1.0, attraction(f, S)):
                        startBite(f)
            continue
        beh = f.sp.beh
        f.ph += dt
        f.st += dt
        old_dir = f.dir
        # fish cruise at a gently changing pace instead of a constant speed
        spd = f.spd * (0.72 + 0.34 * math.sin(f.ph * 0.45 + f.seed))
        if beh in ('dart', 'boss'):
            f.dartT -= dt
            if f.dartT < 0:
                f.burst = 0.4
                f.dartT = rand(2.4, 5.0)
        if f.burst > 0:
            f.burst -= dt
            spd *= 2.0
        if beh == 'erratic':
            f.tt -= dt
            if f.tt < 0:
                f.tt = rand(0.9, 2.2)
                if random.random() < 0.25:
                    f.dir *= -1
                f.home = clamp(f.home + rand(-6, 6), 3, depth - 4)
        if beh == 'drift':
            spd *= 0.55
        if beh == 'abyss':
            f.blinkT -= dt
            if f.blinkT < 0:
                f.blinkT = rand(2.5, 5)
                burst(f.x, f.d, f.sp.glow or '#ffffff', 10, 0.6)
                f.x = clamp(f.x + rand(-140, 140) * G.S, 20, G.W - 20)
                f.d = f.home = clamp(f.home + rand(-10, 10), 3, depth - 4)
                f.alpha = 0.0
            f.alpha = min(1.0, f.alpha + dt * 2)
        tx = f.dir * spd
        td = (f.home + math.sin(f.ph * 0.7) * f.amp - f.d) * 1.2
        mx, md = mouthOf(f)
        dx = h.x - mx
        dd = (h.d - md) * G.PPM
        dist = math.hypot(dx, dd)
        # Surge pushes nearby Common, Uncommon and Rare fish away for its full duration.
        if hookIn and G.surgeT > 0 and f.tier <= 2 and dist < 190 * G.S:
            f.state = 'flee'
            f.st = 0.0
            f.spook = max(f.spook, 0.25)
        if 'pup' in P.petOn and petLevel('pup') >= 10 and f.tier <= 1 and hookIn and dist < 240 * G.S:
            f.state = 'flee'
            f.st = 0.0
            f.spook = max(f.spook, 0.4)
        if f.spook > 0:
            f.spook -= dt
        f.touch = max(0.0, f.touch - dt)
        if hookIn and not G.bite and f.spook <= 0 and f.state in ('swim', 'chase'):
            # The race for the bait: fish that notice the hook swim straight for it, and the first
            # one whose mouth touches it takes it. No nibbling, no dancing around the hook.
            R = noticeRange(f, S)
            if f.state == 'swim':
                # shy fish only notice a bait that is sitting still (park it near them and wait)
                calm = f.tier < 2 or h.speed < spookSpeed(S) * 0.5
                if calm and dist < R and random.random() < dt * NOTICE[f.tier] * S.bite * attraction(f, S):
                    f.state = 'chase'
                    f.st = 0
                elif f.touch <= 0 and touchingBait(f, h):
                    f.touch = 1.5
                    if random.random() < BUMP[f.tier] * min(1.0, attraction(f, S)):
                        startBite(f)
                        continue
            if f.state == 'chase':
                if dist > R * 1.9 or f.st > 14:
                    f.state = 'swim'
                elif 2 <= f.tier < 6 and h.speed > spookSpeed(S) * (1.3 - 0.13 * f.tier):
                    f.state = 'flee'
                    f.st = 0
                    f.spook = 3
                else:
                    rel = h.x - f.x
                    if rel > f.size * 0.12:
                        f.dir = 1
                    elif rel < -f.size * 0.12:
                        f.dir = -1
                    ax = h.x - f.dir * f.size * 0.42 - f.x
                    ad = (h.d - f.d) * G.PPM
                    dl = math.hypot(ax, ad)
                    cs = f.spd * (1.3 + 0.07 * f.tier) * S.chase * (1.45 if dl < f.size * 1.2 + 40 * G.S else 1.0)
                    if dl > 0.5:
                        tx = ax / dl * cs
                        td = ad / dl * cs / G.PPM
                    else:
                        tx = td = 0.0
                    if touchingBait(f, h):
                        startBite(f)
                        continue
        elif f.state == 'chase':
            f.state = 'swim'
        if f.state == 'flee':
            tx = -sign(dx or 1) * f.spd * 1.8
            td = -sign(dd or 1) * 2
            f.dir = sign(tx) or f.dir
            if f.st > 1.4:
                f.state = 'swim'
        k3 = min(1, dt * (5.0 if f.state == 'chase' else 2.2))
        f.vx += (tx - f.vx) * k3
        f.vd += (td - f.vd) * k3
        f.x += f.vx * dt
        f.d = clamp(f.d + f.vd * dt, 2, depth - 3)
        if f.sp.cave:
            cave = caveLayout(P.biome)
            if cave and cave.rooms:
                room_index = f.sharedRoom if isinstance(f.sharedRoom, int) and f.sharedRoom < len(cave.rooms) else None
                if room_index is None:
                    room_index = min(
                        range(len(cave.rooms)),
                        key=lambda index: (
                            max(cave.rooms[index].x[0] - f.x / G.W, 0, f.x / G.W - cave.rooms[index].x[1]) ** 2
                            + max(cave.rooms[index].d[0] - f.d, 0, f.d - cave.rooms[index].d[1]) ** 2
                        ),
                    )
                room = cave.rooms[room_index]
                left, right = room.x[0] * G.W, room.x[1] * G.W
                if f.x < left or f.x > right:
                    f.x = clamp(f.x, left, right)
                    f.vx *= -0.5
                    f.dir = 1 if f.vx >= 0 else -1
                f.d = clamp(f.d, room.d[0], room.d[1])
        if f.state == 'swim' and abs(f.vx) > 4:
            f.dir = 1 if f.vx > 0 else -1
        if f.dir != old_dir:
            f.turn = 0.32
        elif f.turn > 0:
            f.turn = max(0.0, f.turn - dt)
        # tail beats speed up when the fish swims faster
        f.anim += dt * (0.45 + 0.75 * min(1.6, abs(f.vx) / max(8.0, f.spd)))


# ---------------- casting & the hook ----------------
def canCast():
    if len(P.bag) >= holdSize():
        toast(f'Your bag is full ({holdSize()} fish). Sell at the shop or buy a bigger boat.', 'bad')
        Sfx.play('nope')
        return False
    return True


def startCharge():
    if not canCast():
        return
    setMode('charge')
    G.charge = 0
    G.chargeDir = 1


def releaseCast():
    tx, ty = rodTip()
    p = clamp(G.charge, 0.05, 1)
    bx = boatX()
    landX = clamp(bx + 70 * G.S + p * (G.W * 0.95 - bx - 70 * G.S), bx + 60 * G.S, G.W - 30)
    G.fly = D(x0=tx, y0=ty, x1=landX, t=0.0, dur=0.55 + p * 0.25, p=p)
    P.stats.casts += 1
    Sfx.play('cast')
    setMode('flying')


def hookTick(dt):
    h, S, K = G.hook, G.stats, G.keys
    ox, od = h.x, h.d
    if G.mode == 'flying':
        F = G.fly
        F.t += dt
        u = min(1, F.t / F.dur)
        h.x = lerp(F.x0, F.x1, u)
        yy = lerp(F.y0, sy(0), u) - math.sin(u * math.pi) * (90 + 120 * F.p) * G.S
        h.d = (yy - surfBase()) / G.PPM + G.cam
        if u >= 1:
            h.d = 0
            h.hold = False
            setMode('sinking')
            Sfx.play('splash')
            burst(h.x, 0, '#dff6ff', 18, 1.1, 'drop')
            ripple(h.x, 1.0)
    elif G.mode == 'sinking':
        steer = (1 if K.get('right') else 0) - (1 if K.get('left') else 0)
        surge = 1.4 if G.surgeT > 0 else 1.0
        h.vx += (steer * 210 * G.S * S.hookH * surge - h.vx) * min(1, dt * 6)
        h.x = clamp(h.x + h.vx * dt, 16, G.W - 16)
        Dp = BIO().depth
        v = 0 if h.hold else 22 * (1 + Dp / 1500) * S.hookV * surge
        if K.get('down'):
            v = 70 * (1 + Dp / 700) * S.hookV * surge
            h.hold = False
        if K.get('up'):
            v = -48 * (1 + Dp / 700) * S.hookV * surge
        h.d = clamp(h.d + v * dt, 0, S.depth)
        if h.d >= S.depth - 0.01 and v > 0:
            h.d = S.depth
        if K.get('up') and h.d <= 0.01:
            setMode('idle')
            h.d = -1
        if P.biome == 'volcano' and not S.heat:
            for vt in G.vents:
                if vt.d0 < h.d < vt.d1 and abs(h.x - vt.fx * G.W) < 18 * G.S:
                    burnLine()
                    break
    elif G.mode in ('recall', 'burned'):
        h.d = max(0, h.d - (120 if G.mode == 'recall' else 160) * dt)
        if h.d <= 0 and G.modeT > 0.4:
            setMode('idle')
            h.d = -1
    h.vx = (h.x - ox) / max(dt, 1e-3)
    h.vd = (h.d - od) / max(dt, 1e-3)
    h.speed = math.hypot(h.vx, h.vd * G.PPM)


def burnLine():
    P.stats.burned += 1
    useBait()
    Sfx.play('burn')
    shake(6)
    flash(0.35, '#ff7a2a')
    burst(G.hook.x, G.hook.d, '#ff9a3c', 26, 1.2)
    toast('A lava vent burned through your line. Steer around the glowing columns, or get heat protection.', 'bad')
    setMode('burned')


def useBait():
    if P.bait and (P.baits.get(P.bait) or 0) > 0:
        P.baits[P.bait] -= 1
        if not P.baits[P.bait]:
            toast(f'Out of {BAIT[P.bait].name}. Buy more at the shop.')
        refreshStats()


def recall():
    if G.mode == 'sinking':
        setMode('recall')


# ---------------- bites ----------------
def startBite(f):
    for o in G.fish:
        if o is not f and o.state == 'chase':
            o.state = 'swim'
            o.spook = 1.0
    f.state = 'hooked'
    G.bite = D(f=f, t=0.0, win=0.9 if f.tier == 6 else 0.42)
    G.hook.x, G.hook.d = mouthOf(f)
    G.hook.d = f.d
    setMode('bite')
    if f.sharedId:
        G.events.append(('shared_claim', D(id=f.sharedId, b=P.biome)))
    Sfx.play('bite')
    if f.tier == 6:
        G.stormOn = True
        Sfx.play('roar')
        Sfx.start_drone()
        shake(14)
        toast(f'{f.sp.name.upper()} HAS TAKEN THE BAIT!', 'gold')
        G.events.append(('boss', True))


def strike():
    f = G.bite.f
    G.bite = None
    lure = P.bait if f.tier == 6 and P.bait and BAIT.get(P.bait) and BAIT[P.bait].boss else None
    useBait()
    Sfx.play('strike')
    startReel(f)
    if lure and G.reel:
        G.reel.refundBait = lure





# ---------------- quests ----------------
# Progress is counted from catches made while the quest's island is open, so quests start fresh.
def _qrec(q, p=None):
    p = p or P
    r = p.qp.get(q.id)
    if r is None:
        r = p.qp[q.id] = D(g=[0] * len(q.goals), s=[[] for _ in q.goals])
    return r


def questOpen(q, p=None):
    p = p or P
    if q.hidden:
        if q.id == 'q_trident':
            return bool(p.portal.started)
        if q.isle == 'redhollow':
            return bool(p.unlocked.get('redhollow'))
    return bool(p.unlocked.get(q.isle))


def goalProgress(q, i, p=None):
    """(have, need) for one goal of a quest."""
    p = p or P
    g = q.goals[i]
    r = p.qp.get(q.id)
    if g.kind == 'species':
        have = len(r.s[i]) if r else 0
    else:
        have = r.g[i] if r else 0
    return min(int(have), g.n), g.n


def questSkipped(q, p=None):
    """An island quest whose next island you had already reached before 1.3 counts as done."""
    p = p or P
    return bool(q.island and q.unlock and p.unlocked.get(q.unlock))


def questDone(q, p=None):
    p = p or P
    if questSkipped(q, p):
        return True
    return all(goalProgress(q, i, p)[0] >= g.n for i, g in enumerate(q.goals))


def questProgress(q, p=None):
    """(have, need) summed over all goals, for progress bars."""
    p = p or P
    if questSkipped(q, p):
        return 1, 1
    have = need = 0
    for i, g in enumerate(q.goals):
        a, b = goalProgress(q, i, p)
        w = 1.0 / b
        have += a * w
        need += 1
    return have, need


def unlockKeeperLog(log_id):
    if log_id not in {entry.id for entry in KEEPER_LOGS} or log_id in P.logs:
        return False
    P.logs.append(log_id)
    entry = next(x for x in KEEPER_LOGS if x.id == log_id)
    toast(f'Keeper’s Log found: {entry.title}. Read it in Fishpedia.', 'gold')
    recipes = [rod for rod in RODS if rod.need and rod.at == log_id and not P.recipes.get(rod.id)]
    for rod in recipes:
        P.recipes[rod.id] = True
    if recipes:
        toast(f'The {BIOMES[log_id].name} ruins revealed {len(recipes)} crafting blueprint{"s" if len(recipes) != 1 else ""}.', 'gold')
    return True


def goalText(g):
    from .data import BIOMES as _B
    where = f' on {_B[g.isle].name}' if g.isle else ''
    if g.kind == 'catch':
        if g.sp:
            return f'Catch {"a" if g.n == 1 else g.n} {FI[g.sp].name}{"" if g.n == 1 else "s"}{where}'
        if g.tier is not None:
            t = RAR[g.tier].name
            what = f'{t} fish' if g.tier >= 5 else f'{t} (or rarer) fish'
            return f'Catch {g.n} {what}{where}'
        return f'Catch {g.n} fish{where}'
    if g.kind == 'species':
        return f'Catch {g.n} different species{where}'
    if g.kind == 'perfect':
        return f'Land {g.n} Perfect catches'
    if g.kind == 'mut':
        return f'Catch {g.n} {MUT[g.mut].name} fish'
    if g.kind == 'earn':
        return f'Earn {g.n:,} coins by selling'
    if g.kind == 'boss':
        return f'Defeat {bossName(g.sp)}' if g.sp else 'Defeat any boss'
    return ''


def questsWaiting():
    """Quests that are finished but not claimed yet."""
    return [q for q in QUESTS if questOpen(q) and q.id not in P.qc and not questSkipped(q) and questDone(q)]


def questEvent(kind, sp=None, tier=0, mut=None, perfect=False, coins=0):
    """Count a catch (or a sale) toward every open quest."""
    if P is None:
        return
    for q in QUESTS:
        if not questOpen(q) or q.id in P.qc or questSkipped(q):
            continue
        r = _qrec(q)
        for i, g in enumerate(q.goals):
            if kind == 'sell':
                if g.kind == 'earn':
                    r.g[i] += coins
                continue
            isle = sp.b
            if g.kind == 'catch':
                if (not g.isle or g.isle == isle) and (g.tier is None or tier >= g.tier) and (not g.sp or g.sp == sp.id):
                    r.g[i] += 1
            elif g.kind == 'species':
                if (not g.isle or g.isle == isle) and sp.id not in r.s[i]:
                    r.s[i].append(sp.id)
            elif g.kind == 'perfect':
                if perfect:
                    r.g[i] += 1
            elif g.kind == 'mut':
                if mut == g.mut:
                    r.g[i] += 1
            elif g.kind == 'boss':
                if tier == 6 and (not g.sp or g.sp == sp.id):
                    r.g[i] += 1


def checkQuests():
    """Celebrate (once) when a quest is finished."""
    if not LIVE or P is None:
        return
    new = []
    for q in QUESTS:
        if q.id in P.quests or not questOpen(q) or questSkipped(q) or not questDone(q):
            continue
        P.quests[q.id] = True
        new.append(q)
    if not new:
        return
    isl = [q for q in new if q.island]
    if isl and isl[0].unlock:
        nb = BIOMES[isl[0].unlock]
        msg = f'Island quest complete: {isl[0].name}! You may now sail to {"the " if nb.the else ""}{nb.name}' + \
              ('.' if P.level >= nb.lvl else f' once you reach level {nb.lvl}.') + ' Claim your reward in Quests.'
    elif len(new) == 1:
        q = new[0]
        msg = f'Quest complete: {q.name}! Open Quests to claim ' + (f'the {ROD[q.rod].name}.' if q.rod and q.rod not in P.rods else 'your reward.')
    else:
        msg = f'{len(new)} quests complete! Open Quests to claim your rewards.'

    def tell():
        toast(msg, 'gold')
        Sfx.play('level')
    later(1.2 if G.mode in ('landing', 'card') else 0.2, tell)


def claimQuest(qid):
    q = QI.get(qid)
    if not q or q.id in P.qc or not questOpen(q) or questSkipped(q) or not questDone(q):
        return False
    P.qc[q.id] = True
    P.quests[q.id] = True
    P.coins += q.coins or 0
    if q.unlock:
        P.unlocked[q.unlock] = True
    if q.id == 'q_trident':
        P.unlocked.redhollow = True
        toast('The Broken Trident resonates. Poseidon’s statue has opened the Red Hollow gate.', 'gold')
    if q.rewardMat:
        P.mats[q.rewardMat] = (P.mats.get(q.rewardMat) or 0) + 1
        toast(f'Quest reward: {MATS[q.rewardMat].drop}.', 'gold')
    if q.island:
        unlockKeeperLog(q.isle)
    if q.rod and q.rod not in P.rods:
        P.rods[q.rod] = D(ench=None)
        P.rod = q.rod
        refreshStats()
        r = ROD[q.rod]
        hype('NEW ROD!', r.tip or r.col, 2.2, False)
        later(0.1, lambda: Sfx.play('chime'))
        toast(f'You earned the {r.name} and {q.coins:,} coins! Its ability: {ABILITIES[r.ab].name}. It is equipped now.', 'gold')
    elif q.island:
        hype('QUEST COMPLETE', '#2fd3c0', 2.0, False)
        later(0.1, lambda: Sfx.play('chime'))
        nxt = ('the ' if BIOMES[q.unlock].the else '') + BIOMES[q.unlock].name if q.unlock else None
        toast(f'+{q.coins:,} coins!' + (f' Sail to {nxt} from the sea chart (M).' if nxt else ' Return to Poseidon’s statue for the next step.'), 'gold')
    elif q.rod:
        Sfx.play('coin')
        toast(f'Quest reward: +{q.coins:,} coins (you already own the {ROD[q.rod].name}).', 'gold')
    else:
        Sfx.play('coin')
        toast(f'Quest complete: {q.name}.', 'gold')
    saveProfile()
    return True


def choosePortalEnding(ending):
    """Resolve the Red Hollow ending once, after its island quest has been claimed."""
    if (ending not in ('repair', 'seal') or P.biome != 'redhollow' or P.portal.ending
            or not P.qc.get('p_hollow')):
        return False
    P.portal.ending = ending
    P.fur = FUR_REWARD
    saveProfile()
    toast('Keeper’s coat unlocked! Its colour carries a small luck and mutation bonus.', 'gold')
    return True


def useSkill():
    """Use a rod-specific Z skill while the hook is underwater."""
    if G.mode not in ('sinking', 'reel'):
        toast('Rod skills can only be used while the hook is in the water.', 'bad')
        Sfx.play('nope')
        return False
    if G.skillCD > 0:
        toast(f'Rod skill recharging: {G.skillCD:.1f}s', '')
        Sfx.play('nope')
        return False
    skill = ROD_SKILL.get(P.rod)
    if skill == 'survey':
        G.skillT = 3.0
        for f in G.fish:
            if f.tier >= 2:
                f.pinged = True
        floatText(G.hook.x, G.hook.d - 8, 'SONAR PULSE', '#ffe08a', 20)
        toast('Sonar Pulse marks every nearby Rare-or-better fish for 3 seconds.', 'good')
    elif skill == 'undertow':
        G.surgeT = 3.0
        floatText(G.hook.x, G.hook.d - 8, 'INK VEIL', '#9fffe8', 22)
        toast('INK VEIL! Hook movement +40%; nearby Common–Rare fish are repelled.', 'good')
    elif skill == 'anchorline':
        if G.mode != 'reel' or not G.reel:
            toast('Anchorline needs a hooked fish.', 'bad')
            Sfx.play('nope')
            return False
        G.reel.ten = max(0.0, G.reel.ten - 0.30)
        G.reel.abT['stun'] = max(G.reel.abT.get('stun', 0), 1.5)
        G.reel.warn = None
        floatText(G.hook.x, G.hook.d - 8, 'ANCHORLINE', '#ff5ab0', 20)
        toast('Anchorline cuts tension and stuns the fish.', 'good')
    elif skill == 'bloodtide':
        if G.mode != 'reel' or not G.reel:
            toast('Bloodtide needs a hooked fish.', 'bad')
            Sfx.play('nope')
            return False
        G.reel.prog = min(1.0, G.reel.prog + 0.10)
        G.reel.warn = None
        floatText(G.hook.x, G.hook.d - 8, 'BLOODTIDE +10%', '#ff3a5e', 20)
        toast('Bloodtide clears the warning and adds 10% progress.', 'good')
    else:
        G.surgeT = 3.0
        floatText(G.hook.x, G.hook.d - 8, 'SURGE!', '#2fd3c0', 24)
        toast('SURGE! Hook movement +40%; nearby Common–Rare fish are repelled.', 'good')
        flash(0.16, '#2fd3c0')
    G.skillCD = 10.0
    Sfx.play('ab_whirl')
    return True


def useFishBait():
    """Hold a saved Common fish as a bait bonus. Pressing again clears the saved bait."""
    p = P()
    if p is None:
        return False
    if not p.fish_bait:
        toast('Catch a Common fish and it will be saved as bait for the next cast.', 'bad')
        return False
    p.fish_bait = None
    toast('Saved fish bait cleared. Food bait and fish bait will be re-evaluated on the next catch.', 'good')
    refreshStats()
    saveProfile()
    return True


# ---------------- the reel bar (Fisch style), with fish tricks and rod abilities ----------------
def _reel_gims(R):
    """The tricks this fish can use right now (the Leviathan changes tricks every stage)."""
    if R.boss:
        B = BOSSES.get(R.sp.b)
        special = list(B.gims.get(R.stage, [])) if B else []
        pool = list(dict.fromkeys(special + BOSS_STAGE_GIMS.get(R.stage, [])))
        passive = [g for g in pool if GIMMICKS[g].kind == 'passive']
        active = list(dict.fromkeys(g for g in pool if GIMMICKS[g].kind != 'passive'))
        pool_size = max(6, {1: 7, 2: 9, 3: 10}.get(R.stage, 7) - len(passive))
        if len(active) > pool_size:
            active = random.sample(active, pool_size)
        else:
            additions = [g for g in MYTHIC_GIM_POOL if g not in active]
            active.extend(random.sample(additions, min(pool_size - len(active), len(additions))))
        return passive + random.sample(active, random.randint(3, min(5, len(active))))
    g = list(R.sp.gim or [])
    for x in (MUT_GIMS.get(R.f.mut, []) if R.f.mut else []):
        if x not in g:
            g.append(x)
    if R.tier == 5:
        passive = [x for x in g if GIMMICKS[x].kind == 'passive']
        active = [x for x in g if GIMMICKS[x].kind != 'passive'][:5]
        target = min(5, max(3, random.randint(3, 5), len(active)))
        pool = [x for x in MYTHIC_GIM_POOL if x not in active and GIMMICKS[x].kind != 'passive']
        active.extend(random.sample(pool, min(target - len(active), len(pool))))
        return passive + active
    return g


# Each way of fighting moves at its own pace, so that a darting fish is about as hard as a calm one of
# the same rarity (darting and erratic fish change direction suddenly, so they move a bit slower).
BEH_K = {'calm': 1.0, 'drift': 1.45, 'dart': 0.5, 'erratic': 0.48, 'abyss': 0.6, 'boss': 1.0}
THRASH_K = 1.3     # a thrashing fish is this much faster once it is more than half caught
DASH_K = 1.8       # a dash
SLIP_K = 1.22      # progress lost when a slippery fish gets out
LINE_TENSION_K = 1.5  # tension builds faster while the fish is outside the reel bar

def bossName(fid):
    """'the Pallid Whale' (for the middle of a sentence)."""
    n = FI[fid].name
    return 'the ' + n[4:] if n.startswith('The ') else n


def bossBeh(R):
    B = BOSSES.get(R.sp.b)
    return (B.behs if B else ['calm', 'dart', 'abyss'])[R.stage - 1]


# Bosses fight in stages; each one is faster, tougher and has nastier tricks.
BOSS_SPEED = [1.0, 1.0, 1.1, 1.2]       # by stage (1-3)
BOSS_GAIN = [1.0, 1.0, 1.2, 1.4]        # catch progress is divided by this

# Version 1.5 makes rarer fish more deliberate fights. Values are speed
# multipliers: dividing movement speed by these values slows the fish.
RARITY_REEL_SLOW = (1.0, 1.3, 1.3, 1.75, 2.5, 4.0, 5.0)


def startReel(f):
    S, sp, tier = G.stats, f.sp, f.tier
    boss = tier == 6
    T = REEL[tier]
    I = ISLE[sp.b]
    size_k = 1 + 0.12 * clamp(wfrac(sp, f.kg), 0, 1)
    zw = clamp(S.control * T.zone * I.zone / size_k ** 0.5, 0.1, 0.55)
    G.reel = D(f=f, sp=sp, tier=tier, boss=boss, stage=1, stages=3 if boss else 1,
               zw=zw, zw0=zw, pos=0.5 - zw / 2, vel=0.0, fx=0.5, ft=0.5, fT=0.0,
               prog=0.3, ten=0.0, perfect=True, t=0.0, grace=1.0, tick=0.0, blink=0.0, lastIn=True,
               speed=T.speed * I.spd * size_k * (sp.rk or 1.0) * (1.06 if f.mut else 1)
                     / RARITY_REEL_SLOW[min(6, max(0, tier))], gain=T.gain / I.gain, loss=T.loss * I.loss,
               tenr=T.ten * I.ten * size_k,
               gims=[], gimT=rand(2.8, 4.5), gimCD=D(), warn=None, eff=D(), decoys=[], reborn=False,
               ab=S.rod.ab, charge=0.0, ready=False, abT=D(), label='', labelT=0.0, labelCol='#ffffff',
               slashT=0.0, flashT=0.0, zapT=0.0, pawT=0.0, harpT=0.0, starT=0.0, pingT=0.0, gold=False, saved=False,
               barb=False, chill=False)
    R = G.reel
    R.gims = _reel_gims(R)
    passive = [GIMMICKS[g].name for g in R.gims if GIMMICKS[g].kind == 'passive']
    if passive:
        _label(R, ' + '.join(passive).upper(), GIMMICKS[[g for g in R.gims if GIMMICKS[g].kind == 'passive'][0]].col, 1.6)
    setMode('reel')


def _label(R, text, col, dur=1.2):
    R.label, R.labelCol, R.labelT = text, col, dur


def _trigger(R, g):
    """A fish trick goes off."""
    S = G.stats
    gm = GIMMICKS[g]
    R.gimCD[g] = gm.get('cool', 6.0)
    R.eff[g] = gm.dur or 1.0
    _label(R, gm.name.upper() + '!', gm.col)
    if g == 'dash':
        R.ft = rand(0.75, 0.95) if R.fx < 0.5 else rand(0.05, 0.25)
        Sfx.play('dash')
    elif g == 'glitch':
        R.pos = clamp(rand(0.04, 0.96 - R.zw), 0.0, 1.0 - R.zw)
        R.vel = rand(-0.2, 0.2)
        Sfx.play('warp')
    elif g in ('zap', 'sharp'):
        if R.abT.get('inferno', 0) <= 0:
            R.ten = min(0.98, R.ten + (0.12 if g == 'zap' else 0.14))
        if g == 'zap':
            R.vel += rand(-0.9, 0.9)
        Sfx.play('zap' if g == 'zap' else 'snapish')
        shake(3)
    elif g == 'decoy':
        R.decoys = [D(x=clamp(1 - R.fx + rand(-0.1, 0.1), 0.08, 0.92), ft=rand(0.1, 0.9), fT=rand(0.6, 1.2))]
        Sfx.play('warp')
    elif g == 'split':
        R.decoys = [D(x=clamp(R.fx + o, 0.05, 0.95), ft=rand(0.1, 0.9), fT=rand(0.5, 1.0)) for o in (-0.18, 0.18)]
        Sfx.play('warp')
    elif g == 'flash':
        R.flashT = gm.dur
        Sfx.play('flashbang')
    elif g == 'burn':
        if S.heat:
            R.eff.pop('burn', None)
            _label(R, 'HEAT PROOF!', '#ffd27a')
        Sfx.play('burn')
    elif g == 'puff':
        Sfx.play('puff')
    elif g == 'ink':
        Sfx.play('ink')
    elif g in ('camo', 'warp', 'regen', 'stun'):
        Sfx.play('warp' if g != 'stun' else 'zap')


def useAbility():
    """Fire your rod's ability once it's charged (keep the fish in your bar to charge it)."""
    R = G.reel
    if G.mode != 'reel' or not R:
        return False
    if R.charge < 1:
        Sfx.play('nope')
        return False
    ab = R.ab
    A = ABILITIES[ab]
    R.charge = 0.0
    R.ready = False
    if ab == 'tug':
        R.prog += 0.10
        R.ft = R.pos + R.zw / 2
        floatText(G.hook.x, G.hook.d - 8, 'TUG +10%', A.col, 20)
    elif ab == 'grip':
        R.abT['freeze'] = A.dur
        R.abT['magnet'] = A.dur
        R.warn = None
        R.decoys = []
        floatText(G.hook.x, G.hook.d - 8, 'TENTACLE GRIP', A.col, 22)
    elif ab in ('quick', 'inferno', 'gravity', 'net', 'slowmo', 'shield', 'gold', 'phoenix', 'magnet', 'stars', 'anchor', 'whirl',
                'riptide', 'frenzy', 'mirror', 'bloodmoon'):
        R.abT[ab] = A.dur
        if ab == 'gold':
            R.gold = True
        elif ab == 'stars':
            R.starT = 0.0
    elif ab == 'echo':
        R.abT['echo'] = A.dur
        R.prog += 0.08
        R.pingT = 1.0
        if R.warn:
            R.warn[1] += 0.6
        floatText(G.hook.x, G.hook.d - 8, 'PING +8%', A.col, 22)
    elif ab == 'carapace':
        R.abT['shield'] = A.dur
    elif ab == 'song':
        R.prog += 0.20
        R.abT['freeze'] = A.dur
        R.eff.clear()
        R.warn = None
        R.decoys = []
        R.flashT = 0
        floatText(G.hook.x, G.hook.d - 8, 'DEEP SONG +20%', A.col, 22)
    elif ab == 'breach':
        R.abT['breach'] = A.dur
        R.prog += 0.12
        floatText(G.hook.x, G.hook.d - 8, 'BREACH +12%', A.col, 22)
    elif ab == 'barb':
        R.barb = True
        R.prog += 0.05
        floatText(G.hook.x, G.hook.d - 8, 'BARBED +5%', A.col, 22)
    elif ab == 'siphon':
        amt = R.ten * 0.5
        R.prog += amt
        R.ten = 0.0
        floatText(G.hook.x, G.hook.d - 8, f'SIPHON +{jround(amt * 100)}%', A.col, 22)
    elif ab == 'permafrost':
        R.abT['freeze'] = A.dur
        R.chill = True
        R.eff.clear()
        R.warn = None
        R.decoys = []
        R.flashT = 0
        floatText(G.hook.x, G.hook.d - 8, 'PERMAFROST', A.col, 22)
    elif ab == 'harpoon':
        R.prog += 0.22
        if R.abT.get('inferno', 0) <= 0 and R.abT.get('shield', 0) <= 0:
            R.ten = min(0.95, R.ten + 0.15)
        R.harpT = 0.45
        floatText(G.hook.x, G.hook.d - 8, 'HARPOON +22%', A.col, 22)
    elif ab == 'purr':
        R.pos = clamp(R.fx - R.zw / 2, 0, 1 - R.zw)
        R.vel = 0.0
        R.prog += 0.06
        R.pawT = 0.7
        floatText(G.hook.x, G.hook.d - 8, 'PURRFECT +6%', A.col, 22)
    elif ab == 'storm':
        R.prog += 0.15
        R.abT['freeze'] = 1.5
        R.eff.clear()
        R.warn = None
        R.decoys = []
        R.flashT = 0
        R.zapT = 0.6
        floatText(G.hook.x, G.hook.d - 8, 'LIGHTNING +15%', A.col, 22)
    elif ab in ('freeze', 'tidal'):
        R.abT['freeze'] = A.dur
        R.eff.clear()
        R.warn = None
        R.decoys = []
        R.flashT = 0
    if ab in ('slice', 'tidal'):
        amt = slice_amount(R.tier, 0.30 if ab == 'slice' else 0.25)
        R.prog += amt
        R.slashT = 0.55
        floatText(G.hook.x, G.hook.d - 8, f'SLICE +{jround(amt * 100)}%', A.col, 24)
    _label(R, A.name.upper() + '!', A.col, 1.3)
    Sfx.play('ab_' + ab)
    flash(0.18, A.col)
    shake(4)
    P.stats.abilities = (P.stats.abilities or 0) + 1
    return True


def reelTick(dt):
    R, S = G.reel, G.stats
    R.t += dt
    frozen = R.abT.get('freeze', 0) > 0
    for k in list(R.abT.keys()):
        R.abT[k] -= dt
        if R.abT[k] <= 0:
            del R.abT[k]
    for k in list(R.gimCD):
        R.gimCD[k] = max(0.0, R.gimCD[k] - dt)
        if R.gimCD[k] <= 0:
            del R.gimCD[k]
    for k in list(R.eff.keys()):
        R.eff[k] -= dt
        if R.eff[k] <= 0:
            del R.eff[k]
            if k in ('decoy', 'split'):
                R.decoys = []
    R.labelT = max(0.0, R.labelT - dt)
    R.slashT = max(0.0, R.slashT - dt)
    R.flashT = max(0.0, R.flashT - dt)
    R.zapT = max(0.0, R.zapT - dt)
    R.pawT = max(0.0, R.pawT - dt)
    R.harpT = max(0.0, R.harpT - dt)
    R.pingT = max(0.0, R.pingT - dt)
    # --- fish tricks: a warning first, then the trick ---
    timed = [g for g in R.gims if GIMMICKS[g].kind != 'passive']
    if timed and not frozen and R.t > R.grace:
        if R.warn:
            R.warn[1] -= dt
            if R.warn[1] <= 0:
                _trigger(R, R.warn[0])
                R.warn = None
        else:
            R.gimT -= dt
            if R.gimT <= 0:
                ready = [g for g in timed if R.gimCD.get(g, 0) <= 0]
                if ready:
                    g = random.choice(ready)
                    R.warn = [g, (0.6 if g == 'dash' else 0.75) + (0.6 if R.abT.get('echo', 0) > 0 else 0)]
                    R.gimT = rand(3.6, 6.4) * (1.15 - 0.06 * R.tier) * (0.8 if R.boss and R.stage == 3 else 1)
                    Sfx.play('warn')
                else:
                    R.gimT = min(R.gimCD.get(g, 0.2) for g in timed)
    # --- your bar ---
    eff = R.eff
    heavy = 'heavy' in R.gims
    push, fall = 2.9, 2.4 * (1.45 if heavy else 1)
    hold = G.act
    anchored = R.abT.get('anchor', 0) > 0
    if eff.get('warp') or PRANK.get('rev', 0) > 0:
        acc = -push if hold else fall * 0.9
    else:
        acc = push if hold else -fall
    if anchored and not hold:
        acc = 0.0
        R.vel *= max(0.0, 1 - dt * 9)
    zw_target = min(0.9, R.zw0 * (0.6 if eff.get('puff') else 1) * (1.6 if R.abT.get('net', 0) > 0 else 1)
                    * (2.0 if R.abT.get('breach', 0) > 0 else 1))
    R.zw += (zw_target - R.zw) * min(1, dt * 6)
    if eff.get('stun'):
        R.vel = 0.0
    elif R.abT.get('magnet', 0) > 0:
        target = clamp(R.fx - R.zw / 2, 0, 1 - R.zw)
        R.pos += (target - R.pos) * min(1, dt * 9)
        R.vel = 0.0
    else:
        R.vel = clamp(R.vel + acc * dt, -1.1, 1.1)
        R.pos += R.vel * dt
    if R.pos < 0:
        R.pos = 0
        R.vel = -R.vel * 0.3 if abs(R.vel) > 0.25 else 0
    if R.pos > 1 - R.zw:
        R.pos = 1 - R.zw
        R.vel = -R.vel * 0.3 if abs(R.vel) > 0.25 else 0
    # --- the fish ---
    beh = bossBeh(R) if R.boss else R.sp.beh
    thrashing = 'thrash' in R.gims and R.prog > 0.6
    v = R.speed * BEH_K.get(beh, 1.0) * (BOSS_SPEED[R.stage] if R.boss else 1) * (THRASH_K if thrashing else 1)
    if eff.get('dash'):
        v *= DASH_K
    if R.abT.get('slowmo', 0) > 0:
        v *= 0.4
    if R.abT.get('frenzy', 0) > 0:
        v *= 1.4
    if R.chill:
        v *= 0.75
    if frozen:
        pass
    elif R.abT.get('gravity', 0) > 0:
        centre = R.pos + R.zw / 2
        R.fx += (centre - R.fx) * min(1, dt * 4)
    elif R.abT.get('whirl', 0) > 0:
        centre = R.pos + R.zw / 2
        R.fx += (centre - R.fx) * min(1, dt * 2.6)
        R.fx += math.sin(R.t * 9) * 0.004
    elif R.abT.get('riptide', 0) > 0:
        centre = R.pos + R.zw / 2
        R.fx += R.vel * dt + (centre - R.fx) * min(1, dt * 1.2)
    else:
        R.fT -= dt
        mv = v
        if beh == 'calm':
            if R.fT < 0:
                R.ft = rand(0.08, 0.92)
                R.fT = rand(1.4, 2.8)
        elif beh == 'dart':
            if R.fT < 0:
                R.ft = rand(0.55, 0.95) if R.fx < 0.5 else rand(0.05, 0.45)
                R.fT = rand(1.5, 2.7)
            mv = v * (1.45 if abs(R.ft - R.fx) > 0.05 else 0.4)
        elif beh == 'erratic':
            if R.fT < 0:
                R.ft = rand(0.05, 0.95)
                R.fT = rand(0.6, 1.3)
            mv = v * 1.25
        elif beh == 'drift':
            R.ft = 0.5 + math.sin(R.t * 0.7) * 0.3 + math.sin(R.t * 1.9) * 0.12
            mv = v * 0.9
        elif beh == 'abyss':
            if R.fT < 0:
                R.fT = rand(1.2, 2.2)
                if random.random() < (0.3 if R.boss else 0.22):
                    R.fx = clamp(R.fx + (-1 if random.random() < 0.5 else 1) * rand(0.15, 0.28), 0.05, 0.95)
                    R.blink = 1
                R.ft = rand(0.05, 0.95)
            mv = v * 1.15
        if eff.get('dash'):
            mv = max(mv, v)
        # never faster than your bar can follow (a dash may briefly outrun it)
        mv = min(mv, 1.25 if eff.get('dash') else 0.92)
        R.fx += clamp(R.ft - R.fx, -mv * dt, mv * dt)
        R.fx += math.sin(R.t * 11) * (0.0008 + 0.0007 * R.tier) * (2 if thrashing else 1)
    R.fx = clamp(R.fx, 0.03, 0.97)
    for dc in R.decoys:
        if not frozen:
            dc.fT -= dt
            if dc.fT < 0:
                dc.ft = rand(0.06, 0.94)
                dc.fT = rand(0.5, 1.1)
            dc.x += clamp(dc.ft - dc.x, -v * 1.2 * dt, v * 1.2 * dt)
    R.blink = max(0, R.blink - dt * 3)
    inside = abs(R.fx - (R.pos + R.zw / 2)) < R.zw / 2
    if not inside and R.abT.get('mirror', 0) > 0:
        inside = abs(R.fx - (1 - R.pos - R.zw / 2)) < R.zw / 2
    # --- catch progress, line tension and your ability charge ---
    if R.t > R.grace:
        gain = R.gain * S.reel / (BOSS_GAIN[R.stage] if R.boss else 1)
        if G.cheer > 0:
            gain *= 1.25
        if R.abT.get('quick', 0) > 0:
            gain *= 2.0
        if R.abT.get('inferno', 0) > 0:
            gain *= 1.5
        if R.abT.get('gold', 0) > 0:
            gain *= 2.5
        if R.abT.get('frenzy', 0) > 0:
            gain *= 3.0
        if R.abT.get('bloodmoon', 0) > 0:
            gain *= 2.2
        shield = R.abT.get('shield', 0) > 0
        loss = 0.0 if shield else R.loss * (SLIP_K if 'slippery' in R.gims else 1) * (0.5 if frozen else 1) * (0.6 if R.barb else 1)
        R.prog += (gain if inside else -loss) * dt
        if R.abT.get('stars', 0) > 0:
            R.prog += 0.1 * dt
            R.starT += dt
        if R.abT.get('whirl', 0) > 0:
            R.prog += 0.04 * dt
        if eff.get('regen') and not shield:
            R.prog -= 0.07 * dt
        heat = ((1.6 if G.erupt > 0 else 1.25) if P.biome == 'volcano' and not S.heat else 1)
        if R.abT.get('inferno', 0) > 0:
            R.ten = max(0.0, R.ten - 1.5 * dt)
        elif shield:
            R.ten = max(0.0, R.ten - 0.2 * dt)
        else:
            if inside:
                R.ten = max(0.0, R.ten - 0.32 * dt)
            else:
                R.ten += R.tenr / S.str * S.tension * heat * LINE_TENSION_K * dt
                R.perfect = False
            if eff.get('burn'):
                R.ten += 0.12 * dt
            if R.abT.get('bloodmoon', 0) > 0:
                R.ten += 0.15 * dt
        if inside and R.ab and not R.abT:
            need = ABILITIES[R.ab].charge * (0.65 if P.gear.get('charm') else 1)
            R.charge = min(1.0, R.charge + dt / need)
            if R.charge >= 1 and not R.ready:
                R.ready = True
                Sfx.play('ready')
        if inside:
            R.tick -= dt
            if R.tick < 0:
                Sfx.play('tick')
                R.tick = 0.11
        if R.lastIn and not inside:
            Sfx.play('slip')
    R.lastIn = inside
    f = R.f
    if not frozen:
        f.x = clamp(G.hook.x + math.sin(G.t * 6) * 9 * G.S * (0.4 if inside else 1.3), 20, G.W - 20)
        f.dir = 1 if math.sin(G.t * 2.2) > 0 else -1
    if R.boss and random.random() < dt * 0.5:
        shake(4)
    if (R.prog <= 0 or R.ten >= 1) and R.abT.get('phoenix', 0) > 0 and R.prog < 1:
        R.abT.pop('phoenix', None)
        R.prog = max(R.prog, 0.3)
        R.ten = 0.0
        R.saved = True
        _label(R, 'SAVED BY THE FLAME!', '#ffb03a', 1.6)
        Sfx.play('ab_phoenix')
        flash(0.3, '#ff7a1a')
        burst(G.hook.x, G.hook.d, '#ffb03a', 24, 1.2)
    if R.prog >= 1:
        if 'rebirth' in R.gims and not R.reborn:
            R.reborn = True
            R.prog = 0.55
            R.ten *= 0.5
            R.grace = R.t + 0.9
            _label(R, 'REBIRTH!', '#ffb03a', 1.6)
            Sfx.play('roar')
            flash(0.45, '#ffb03a')
            shake(10)
            burst(G.hook.x, G.hook.d, '#ffb03a', 30, 1.4)
        elif R.stage < R.stages:
            R.stage += 1
            R.prog = 0.3
            R.ten *= 0.4
            R.grace = R.t + 1.1
            R.gims = _reel_gims(R)
            R.gimCD.clear()
            R.eff.clear()
            R.decoys = []
            R.warn = None
            Sfx.play('roar')
            shake(18)
            flash(0.4, '#00ffd5')
            floatText(G.hook.x, G.hook.d - 10, f"STAGE {R.stage} / {R.stages}: IT'S FURIOUS", '#00ffd5', 22, 2)
            toast('Final stage. Hold on!' if R.stage == 3 else (BOSSES.get(R.sp.b) or BOSSES['trench']).stage, 'gold')
        else:
            winReel()
    elif R.prog <= 0:
        loseReel('slip')
    elif R.ten >= 1:
        loseReel('snap')


def loseReel(why):
    R = G.reel
    f = R.f
    G.reel = None
    if f.sharedId:
        G.events.append(('shared_release', D(id=f.sharedId, b=P.biome)))
    f.state = 'flee'
    f.st = 0
    f.spook = 4
    if why == 'snap':
        P.stats.snapped += 1
        Sfx.play('snap')
        shake(8)
        floatText(G.hook.x, G.hook.d - 6, 'SNAP!', '#ff4f6d', 26)
        toast(f'Line snapped! The {R.sp.name} got away.', 'bad')
    else:
        P.stats.lost += 1
        Sfx.play('lost')
        floatText(G.hook.x, G.hook.d - 6, 'It got away', '#ffb3c0', 20)
        toast(f'The {R.sp.name} slipped off the hook.', 'bad')
    if R.boss:
        G.stormOn = False
        Sfx.stop_drone()
        P.cool.boss = 12
        G.events.append(('boss', False))
        if R.refundBait:
            P.baits[R.refundBait] = (P.baits.get(R.refundBait) or 0) + 1
            refreshStats()
            toast(f'Boss lure refunded: {BAIT[R.refundBait].name}.', 'good')
    setMode('recall')
    saveProfile()


def winReel():
    R, S = G.reel, G.stats
    f = R.f
    G.reel = None
    val = catchValue(f.sp, f.kg, f.mut, R.perfect, S)
    if R.gold:
        val = jround(val * 1.25)
    rec = D(uid=P.nextUid, sp=f.sp.id, kg=round(f.kg, 3), mut=f.mut, val=val, perfect=R.perfect, at=P.biome, t=now_ms(), lock=False)
    P.nextUid += 1
    isNew = f.sp.id not in P.dex
    dx = P.dex.get(f.sp.id)
    if dx is None:
        dx = P.dex[f.sp.id] = D(n=0, kg=0, muts=D(), first=now_ms())
    dx.n += 1
    dx.kg = max(dx.kg, rec.kg)
    if f.mut:
        dx.muts[f.mut] = (dx.muts.get(f.mut) or 0) + 1
    P.bag.append(rec)
    P.stats.catches += 1
    if R.perfect:
        P.stats.perfects = (P.stats.perfects or 0) + 1
    P.stats.bestCatch = max(P.stats.bestCatch, val)
    if f.sp.id == 'oracleeel' and not P.portal.started:
        P.portal.started = True
        toast('The Oracle Eel whispers a riddle. A hidden quest has appeared in Quests.', 'gold')
    log_id = 'kraken' if f.sp.id == 'kraken' else P.biome
    unlockKeeperLog(log_id)
    if P.biome not in P.dexRewards and all(sp.id in P.dex for sp in FISH if sp.b == P.biome):
        P.dexRewards.append(P.biome)
        toast(f'{BIO().name} Fishpedia complete: +5% luck while fishing here.', 'gold')
    if f.mut:
        level = P.mut_upgrades.get(f.mut, 0) + 1
        P.mut_upgrades[f.mut] = level
        if level in MUT_UPGRADES[f.mut]['targets']:
            boost = mutationUpgradeBonus(f.mut)
            toast(f'{MUT[f.mut].name} upgrade reached: {boost:.0%} bonus to mutant catches.', 'gold')
    for k in P.cool:
        if P.cool[k] > 0:
            P.cool[k] -= 1
    if f.tier <= 1:
        P.fish_bait = f.sp.id
        toast(f'{f.sp.name} saved as fish bait.', 'good')
    if f.tier == 5:
        P.stats.mythics += 1
        P.cool.mythic = 25
    relicChance = [0.012, 0.015, 0.03, 0.06, 0.15, 0.5, 1][f.tier]
    extra = ''
    if random.random() < relicChance:
        P.relics += 1
        extra = ' +1 Enchant Relic'
    if f.tier == 6:
        B = BOSSES.get(f.sp.b)
        if B and B.mat:
            P.mats[B.mat] = (P.mats.get(B.mat) or 0) + 1
            extra += f' +1 {MATS[B.mat].name}'
        P.kills[f.sp.id] = (P.kills.get(f.sp.id) or 0) + 1
        P.stats.bosses += 1
        P.cool.boss = 40
        unlockKeeperLog('kraken' if f.sp.id == 'kraken' else f.sp.b)
        G.stormOn = False
        Sfx.stop_drone()
        G.events.append(('boss', False))
    xp = catchXP(f.sp, f.kg, f.mut)
    lvl0 = P.level
    addXP(xp)
    questEvent('catch', f.sp, f.tier, f.mut, R.perfect)
    if f in G.fish:
        G.fish.remove(f)
    if f.sharedId:
        G.sharedPopulation.pop(f.sharedId, None)
        if G.sharedBoss and G.sharedBoss.sharedId == f.sharedId:
            G.sharedBoss = None
    G.land = D(f=f, t=0.0, d0=G.hook.d)
    G.card = D(rec=rec, sp=f.sp, tier=f.tier, isNew=isNew, t=0.0, extra=extra, size=sizeWord(f.sp, f.kg), xp=xp,
               lvl=P.level, up=P.level > lvl0, xpNow=P.xp, xpNeed=xpNeed(P.level))
    setMode('landing')
    G.events.append(('catch', D(sp=f.sp.id, tier=f.tier, mut=f.mut, kg=rec.kg, val=val, isNew=isNew,
                                shared_id=f.sharedId)))
    checkQuests()
    saveProfile()


def landTick(dt):
    L = G.land
    L.t += dt
    u = min(1, L.t / 0.9)
    G.hook.d = L.d0 * (1 - u * u)
    if u >= 1:
        c = G.card
        Sfx.play('splash')
        burst(G.hook.x, 0, '#dff6ff', 22, 1.3, 'drop')
        ripple(G.hook.x, 1.4)
        G.happy = 1.0
        Sfx.catch(c.tier)
        if c.xp:
            floatText(G.hook.x, -6, f'+{c.xp} XP', '#9dffb0', 20, 1.8)
        if c.tier >= 5:
            hype((c.sp.name[4:] if c.sp.name.startswith('The ') else c.sp.name).upper() + ' SLAIN' if c.tier == 6 else 'MYTHIC CATCH', '#00ffd5' if c.tier == 6 else '#ffd23d', 4.2, True)
        elif c.tier == 4:
            hype('LEGENDARY!', '#ffb020', 2.4, False)
        elif c.rec.mut:
            flash(0.25, MUT[c.rec.mut].col)
            burst(G.hook.x, -2, MUT[c.rec.mut].col, 30, 1.4)
        if c.isNew:
            name = c.sp.name
            later(0.4, lambda: toast(f'New species: {name} added to your Fishpedia!', 'good'))
        setMode('card')
        G.hook.d = -1
        G.land = None


def hype(text, col, dur, big):
    """The cinematic for big catches: slow motion, light rays, gold text, a flash and bells."""
    G.hype = D(text=text, col=col, t=0.0, dur=dur, big=big)
    G.tsTarget = G.ts = 0.22 if big else 0.5
    flash(1 if big else 0.6, '#ffffff')
    shake(16 if big else 8)
    if big:
        later(0.12, lambda: Sfx.play('chime'))
    for _ in range(90 if big else 40):
        G.sparts.append(SPart(G.W / 2, G.H * 0.45, rand(-1, 1) * 420, rand(-520, -60), rand(1.2, 2.6), 2.6,
                              pick([col, '#ffffff', '#fff3b0']), rand(2, 5), 380, 'spark'))


# ---------------- weather & hazards ----------------
def presenceTick(dt):
    """Sonar Mk III contacts, and the dread when the Leviathan is near."""
    h = G.hook
    ox, od = (h.x, h.d) if h.d > 0 else (boatX(), 0.0)
    dmin = None
    for f in G.fish:
        if f.state == 'hooked':
            continue
        if f.tier == 6:
            d = math.hypot((f.x - ox) / G.PPM, f.d - od)
            dmin = d if dmin is None else min(dmin, d)
            if not f.seen and d < 380 and LIVE:
                f.seen = True
                toast((BOSSES.get(f.sp.b) or BOSSES['trench']).dread, 'gold')
                Sfx.play('roar')
                shake(5)
        if f.tier >= 4 and not f.pinged and G.stats and G.stats.sonar >= 3 and LIVE:
            f.pinged = True
            d = math.hypot((f.x - ox) / G.PPM, f.d - od)
            if f.tier >= 5 or G.t - G.sonarT > 12:
                G.sonarT = G.t
                what = f.sp.name if f.tier == 6 else f'{RAR[f.tier].name} {f.sp.name}'
                toast(f'Sonar: {what}, {round(d)} m away.', 'gold' if f.tier >= 5 else 'good')
            Sfx.play('sonar')
    want = clamp(1 - (dmin or 1e9) / 420, 0, 1) if G.mode not in ('reel', 'landing', 'card') else 0.0
    G.dread += (want - G.dread) * min(1.0, dt * 1.2)


def worldTick(dt):
    spawnCD['mythic'] = max(0, spawnCD['mythic'] - dt)
    spawnCD['legendary'] = max(0, spawnCD['legendary'] - dt)
    presenceTick(dt)
    G.storm = clamp(G.storm + (dt * 0.6 if (G.stormOn or G.remoteBoss or PRANK.get('storm', 0) > 0) else -dt * 0.35), 0, 1)
    if G.storm > 0.3:
        G.thunderT -= dt
        if G.thunderT < 0:
            G.thunderT = rand(2.5, 6)
            G.bolt = 1
            G.boltX = rand(0.15, 0.85)
            Sfx.play('thunder')
            shake(7)
            flash(0.5, '#cfe8ff')
        for _ in range(math.ceil(6 * G.storm)):
            if len(G.sparts) < 900:
                G.sparts.append(SPart(rand(-50, G.W + 50), -20, -120, rand(700, 900), 1.2, 1.2, '#a8c8ff', 1, 0, 'rain'))
    G.bolt = max(0, G.bolt - dt * 2.5)
    if P.biome == 'volcano':
        G.eruptT -= dt
        if G.eruptT < 0:
            G.erupt = 7
            G.eruptT = rand(40, 70)
            shake(12)
            Sfx.play('roar')
            toast('Eruption! Your heat protection keeps the line safe.' if G.stats.heat else 'Eruption! Heat makes your line strain harder until it calms down.', '' if G.stats.heat else 'bad')
        if G.erupt > 0:
            G.erupt -= dt
            for _ in range(3):
                G.sparts.append(SPart(G.W * rand(0.7, 0.95), G.H * 0.2, rand(-260, 160), rand(-420, -120), rand(1.5, 3), 3,
                                      pick(['#ff7a2a', '#ffd23d', '#ff3d1a']), rand(2, 4), 260, 'ember'))
        elif random.random() < dt * 4:
            G.sparts.append(SPart(G.W * rand(0.72, 0.9), sy(0) - 150 * G.S, rand(-30, 30), rand(-80, -30), rand(2, 4), 4, '#ff8a3a', rand(1.5, 3), -10, 'ember'))


def auraTick(dt):
    for f in G.fish:
        if not f.mut:
            continue
        m = MUT[f.mut]
        if random.random() > dt * (9 if m.aura == 'smoke' else 6):
            continue
        ang = random.random() * TAU
        r = f.size * 0.4
        if m.aura == 'spark':
            addPart(Part(f.x + math.cos(ang) * r, f.d + math.sin(ang) * r / G.PPM, rand(-40, 40), rand(-6, 6), 0.25, 0.25, m.col, 2 * G.S, 'zap'))
        elif m.aura == 'smoke':
            addPart(Part(f.x + rand(-r, r), f.d + rand(-2, 2), rand(-8, 8), rand(-4, -1), 1.3, 1.3, m.col, rand(5, 9) * G.S, 'smoke'))
        else:
            addPart(Part(f.x + math.cos(ang) * r, f.d + math.sin(ang) * r / G.PPM, rand(-10, 10), rand(-3, -1), 0.9, 0.9, m.col,
                         (2.4 if m.aura == 'glitter' else 2) * G.S, 'star' if m.aura == 'glitter' else 'dot'))
    if not BIOMES[P.biome].dark and random.random() < dt * 6:
        addPart(Part(rand(0, G.W), G.cam + rand(10, G.H / G.PPM), rand(-4, 4), -rand(2, 6), 3, 3, '#dff6ff', rand(1.5, 3.5) * G.S, 'bubble'))


def partsTick(dt):
    ps = G.parts
    i = len(ps) - 1
    while i >= 0:
        p = ps[i]
        p.life -= dt
        if p.life <= 0:
            ps[i] = ps[-1]
            ps.pop()
        else:
            p.x += p.vx * dt
            p.d += p.vd * dt
            p.vd += p.g * dt
        i -= 1


def spartsTick(dt):
    ps = G.sparts
    i = len(ps) - 1
    H = G.H
    while i >= 0:
        p = ps[i]
        p.life -= dt
        if p.life <= 0 or p.y > H + 30:
            ps[i] = ps[-1]
            ps.pop()
        else:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += p.g * dt
        i -= 1


# ---------------- selling ----------------
def onSold(total):
    """Coins from selling fish (counts toward quests that ask you to earn coins)."""
    P.coins += total
    P.stats.earned += total
    questEvent('sell', coins=total)
    checkQuests()


# ===================================================================================
#  Pets: they ride in the little boat behind yours and grow while you play
# ===================================================================================
def petTick(real):
    if not LIVE or P is None:
        return
    if G.petFx:
        G.petFx.t += real
        if G.petFx.t > 2.8:
            G.petFx = None
    if not P.petOn:
        return
    changed = False
    for pid in P.petOn:
        rec = P.pets.get(pid)
        if not rec:
            continue
        before = petLevel(pid)
        rec.t = (rec.t or 0) + real
        after = petLevel(pid)
        if after > before:
            pt = PET[pid]
            toast(f'{pt.name} the {pt.kind} grew to level {after}!' + (' Fully grown!' if after >= PET_MAX else ''), 'good')
            Sfx.play('level')
            changed = True
    if changed:
        refreshStats()
    if 'kitten' in P.petOn and not G.sail and G.mode != 'sail':
        G.kitT -= real
        if G.kitT <= 0:
            every, odds = KITTEN[petLevel('kitten') - 1]
            G.kitT = every
            kittenCatch(odds)


def kittenCatch(odds):
    """Mittens fishes from the pet boat: a small catch from this island, straight into your bag."""
    if len(P.bag) >= holdSize():
        if random.random() < 0.34:
            toast('Mittens wants to fish, but your bag is full!', '')
        return None
    r = random.random() * sum(odds.values())
    tier = 0
    for t, w in sorted(odds.items()):
        r -= w
        if r <= 0:
            tier = t
            break
    lst = islandFish(P.biome, tier)
    while not lst and tier > 0:
        tier -= 1
        lst = islandFish(P.biome, tier)
    sp = pick(lst)
    kg = sp.w[0] + (sp.w[1] - sp.w[0]) * 0.6 * random.random() ** 2.2
    val = catchValue(sp, kg, None, False, G.stats)
    rec = D(uid=P.nextUid, sp=sp.id, kg=round(kg, 3), mut=None, val=val, perfect=False, at=P.biome, t=now_ms(), lock=False, pet='kitten')
    P.nextUid += 1
    P.bag.append(rec)
    isNew = sp.id not in P.dex
    dx = P.dex.get(sp.id)
    if dx is None:
        dx = P.dex[sp.id] = D(n=0, kg=0, muts=D(), first=now_ms())
    dx.n += 1
    dx.kg = max(dx.kg, rec.kg)
    P.stats.petCatches = (P.stats.petCatches or 0) + 1
    xp = max(1, catchXP(sp, kg, None) // 2)
    addXP(xp)
    t = RI[sp.r]
    G.petFx = D(t=0.0, sp=sp, tier=t, xp=xp)
    art_ = 'an' if RAR[t].name[0] in 'AEIOU' else 'a'
    toast(f'{PET["kitten"].name} caught {art_} {RAR[t].name} {sp.name}! +{xp} XP' + (' (new species!)' if isNew else ''),
          'gold' if t >= 4 else 'good')
    Sfx.play('pet_catch')
    if t >= 4:
        G.events.append(('catch', D(sp=sp.id, tier=t, mut=None, kg=rec.kg, val=val, isNew=isNew)))
    saveProfile()
    return rec


def hatchEgg(eid):
    """Buy and hatch an egg. Returns what hatched (a duplicate pet becomes extra growth for the one you have)."""
    e = EGG.get(eid)
    if not e or not P.unlocked.get(e.at) or P.coins < e.price:
        return None
    P.coins -= e.price
    tot = sum(e.odds.values())
    r = random.random() * tot
    pid = list(e.odds)[-1]
    for k, w in e.odds.items():
        r -= w
        if r <= 0:
            pid = k
            break
    new = pid not in P.pets
    refund = 0
    if new:
        P.pets[pid] = D(t=0.0)
        if len(P.petOn) < petSlots():
            P.petOn.append(pid)
    elif petLevel(pid) >= PET_MAX:
        refund = int(e.price * 0.4)
        P.coins += refund
    else:
        P.pets[pid].t = (P.pets[pid].t or 0) + PET_DUPE_MIN * 60
    P.stats.hatched = (P.stats.hatched or 0) + 1
    if pid == 'kitten':
        G.kitT = min(G.kitT, 12.0)
    refreshStats()
    saveProfile()
    return D(pid=pid, new=new, refund=refund, egg=e)


def togglePet(pid):
    """Put a pet in the pet boat, or let it rest at home."""
    if pid not in P.pets:
        return False
    if pid in P.petOn:
        P.petOn.remove(pid)
    elif len(P.petOn) >= petSlots():
        return False
    else:
        P.petOn.append(pid)
        if pid == 'kitten':
            G.kitT = min(G.kitT, 15.0)
    refreshStats()
    saveProfile()
    return True


# ---------------- sailing between islands ----------------
def sailTo(bid):
    if bid == P.biome or G.sail:
        return
    ok, why = sailCheck(bid)
    if not ok:
        toast(why + ' to sail there.', 'bad')
        Sfx.play('nope')
        return
    G.sail = D(t=0.0, to=bid, swapped=False)
    setMode('sail')
    Sfx.play('cast')


def sailTick(dt):
    s = G.sail
    s.t += dt
    if s.t > 1.2 and not s.swapped:
        s.swapped = True
        P.biome = s.to
        P.unlocked[s.to] = True
        saveProfile()
        enterBiome()
        setMode('sail')
        toast(f"Welcome to {'the ' if BIO().the else ''}{BIO().name}. {BIO().desc}", 'good')
        G.events.append(('sail', s.to))
    if s.t > 2.6:
        G.sail = None
        setMode('idle')


# ---------------- input actions ----------------
def actDown():
    if not LIVE:
        return
    G.act = True
    m = G.mode
    if m == 'idle':
        startCharge()
    elif m == 'sinking':
        G.hook.hold = not G.hook.hold
    elif m == 'bite':
        strike()
    elif m == 'card' and G.card and G.card.t > 0.5:
        G.card = None
        setMode('idle')


def actUp():
    G.act = False
    if G.mode == 'charge':
        releaseCast()


# ---------------- starting and stopping ----------------
def guestBackdrop():
    """A scenic, never-saved profile shown behind the title screen."""
    global P, LIVE
    P = freshProfile('Guest', FURS[0])
    LIVE = False
    enterBiome()


def startPlaying(p, mode='local'):
    global P, LIVE, MODE
    P = p
    MODE = mode
    LIVE = True
    G.bf, G.bv = 0.22, 0.0
    G.toasts = []
    G.kitT = 20.0
    G.petFx = None
    enterBiome()
    mig = P.pop('migrated', None)
    if mig:
        taken = mig if isinstance(mig, list) else []
        toast('Whisker Bay 1.3: every quest starts fresh, and each island now has its own quests (press J).' +
              (f' Quest rods from islands you have not reached yet wait there for you: {", ".join(taken)}.' if taken else ''), 'gold')
    checkQuests()


def stopPlaying():
    """Save and drop back to the title screen."""
    global LIVE
    if LIVE:
        saveProfile()
    LIVE = False
    G.keys = {}
    G.act = False
    G.hype = None
    G.ts = G.tsTarget = 1.0
    Sfx.stop_drone()
    guestBackdrop()


# ---------------- one tick of the simulation ----------------
def tick(real):
    G.ts += (G.tsTarget - G.ts) * min(1, real * 2.5)
    dt = real * G.ts
    G.t += dt
    G.dt = dt
    for tm in G.timers[:]:
        tm[0] -= real
        if tm[0] <= 0:
            G.timers.remove(tm)
            tm[1]()
    for ts in G.toasts[:]:
        ts.t += real
        if ts.t > ts.dur + 0.45:
            G.toasts.remove(ts)
    if P is None:
        return
    if LIVE:
        P.stats.play += real
        petTick(real)
        G.autosave += real
        if G.autosave > 10:
            G.autosave = 0
            saveProfile()
    if not G.stats:
        refreshStats()
    G.cheer = max(0.0, G.cheer - real)
    boatTick(dt)
    if G.mode == 'charge':
        G.charge += G.chargeDir * dt * 1.25
        if G.charge > 1:
            G.charge = 1
            G.chargeDir = -1
        if G.charge < 0:
            G.charge = 0
            G.chargeDir = 1
    if G.mode in ('flying', 'sinking', 'recall', 'burned'):
        hookTick(dt)
    if G.mode == 'bite' and G.bite:
        G.bite.t += dt
        if G.bite.t > G.bite.win:      # a fish that takes the bait is hooked: no button race
            strike()
    if G.mode == 'reel' and G.reel:
        reelTick(dt)
    if G.mode == 'landing' and G.land:
        landTick(dt)
    if G.mode == 'sail' and G.sail:
        sailTick(real)
    G.modeT += dt
    fishTick(dt * (2.6 if PRANK.get('zoom', 0) > 0 else 1))
    worldTick(dt)
    auraTick(dt)
    partsTick(dt)
    spartsTick(real)
    for fl in G.floats[:]:
        fl.t += dt
        if fl.t > fl.dur:
            G.floats.remove(fl)
    if G.mode == 'card' and G.card:
        K = G.card
        K.t += real
        if K.rec.mut and random.random() < real * 30:
            u = min(1, K.t / 0.35)
            e = 1 - (1 - u) ** 3
            y = G.H * 0.5 - 150 + (1 - e) * 40
            G.sparts.append(SPart(G.W / 2 + rand(-80, 80), y + 100 + rand(-40, 40), rand(-30, 30), rand(-60, -10), 0.8, 0.8,
                                  MUT[K.rec.mut].col, rand(1.5, 3), 0, 'spark'))
    if G.hype:
        Hy = G.hype
        Hy.t += real
        if Hy.t > Hy.dur:
            G.hype = None
            G.tsTarget = 1
        elif Hy.t > Hy.dur * 0.55:
            G.tsTarget = 1
    if G.emote and G.t - G.emote[2] > 3:
        G.emote = None
    for rp in G.ripples[:]:
        rp.t += real
        if rp.t > rp.life:
            G.ripples.remove(rp)
    G.happy = max(0.0, G.happy - real * 1.4)
    G.shake = max(0.0, G.shake - real * 30)
    G.flash = max(0.0, G.flash - real * 2.2)
    inWater = G.hook.d > 0 and G.mode != 'card'
    lead = 0.03 if G.mode == 'reel' else 0.16    # while reeling, keep the fish above the reel panel
    want = max(0, G.hook.d - (G.H * lead) / G.PPM) if inWater else 0
    G.cam += (want - G.cam) * min(1, real * 4)
