#!/usr/bin/env python3
"""
Whisker Bay multiplayer server.

    python server.py                      # listen on port 7777
    python server.py --port 7777 --invite fishy123 --name "Nova's Bay"

It keeps everyone's accounts and saves in the 'server_data' folder next to this file,
relays boats, chat, emotes and big-catch announcements, and keeps the leaderboards.
Only needs Python 3.8 or newer: nothing to install.

While it runs you can type commands here:  help, list, say <message>, kick <name>, stop
"""
import argparse
import asyncio
import hashlib
import hmac
import json
import os
import random
import re
import secrets
import socket
import sys
import tempfile
import threading
import time

PROTO = 6
MAX_LINE = 1_000_000          # biggest message we accept (a save is usually well under 100 KB)
MAX_SAVE = 600_000
PBKDF2_ITER = 200_000
NAME_RE = re.compile(r'^[A-Za-z0-9_]{3,16}$')
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, 'server_data')
PLAYER_DIR = os.path.join(DATA_DIR, 'players')
BIOMES = ('shore', 'reef', 'volcano', 'trench')
MODES = ('idle', 'charge', 'flying', 'sinking', 'bite', 'reel', 'landing', 'card', 'recall', 'burned', 'sail')
RARITY = ['Common', 'Uncommon', 'Rare', 'Epic', 'Legendary', 'Mythic', 'Boss']
MUTS = {'albino': 'Albino', 'electric': 'Electric', 'gilded': 'Gilded', 'corrupted': 'Corrupted',
        'prismatic': 'Prismatic', 'tideworn': 'Tideworn'}
FISH_NAMES = {
    'sardine': 'Sardine', 'mackerel': 'Mackerel', 'seabass': 'Sea Bass', 'flounder': 'Flounder', 'puffer': 'Pufferfish',
    'snapper': 'Red Snapper', 'moonfish': 'Moonfish', 'goldtuna': 'Golden Tuna', 'whiskerkoi': 'Whisker Koi',
    'clown': 'Clownfish', 'tang': 'Blue Tang', 'parrot': 'Parrotfish', 'butterfly': 'Butterflyfish', 'lionfish': 'Lionfish',
    'seahorse': 'Seahorse', 'manta': 'Manta Ray', 'angelcrown': 'Crowned Angelfish', 'coralwyrm': 'Coral Wyrm',
    'ashgoby': 'Ash Goby', 'embersmelt': 'Ember Smelt', 'cindereel': 'Cinder Eel', 'basalt': 'Basalt Grouper',
    'magmapuff': 'Magma Puffer', 'obsidian': 'Obsidian Snapper', 'lavaray': 'Lava Ray', 'phoenix': 'Phoenix Carp',
    'seraph': 'Molten Seraph', 'lantern': 'Lanternfish', 'hatchet': 'Hatchetfish', 'gulper': 'Gulper Eel',
    'vampsquid': 'Vampire Squid', 'angler': 'Anglerfish', 'barreleye': 'Barreleye', 'giantsquid': 'Giant Squid',
    'dragonfish': 'Abyssal Dragonfish', 'voidjelly': 'Void Jelly', 'leviathan': 'The Leviathan',
}
ISLAND_NAMES = {'shore': 'Starter Shore', 'reef': 'Coral Reef', 'volcano': 'Volcanic Biome', 'trench': 'Deep Trench Abyss'}
BOSS_NAMES = {'trench': 'The Leviathan'}
# The game's data file needs nothing but Python, so when it sits next to this server (it does in the zip),
# the names of every island, fish and boss come straight from it and new islands work without editing this file.
_gd = None
LIMITED_FISH = {'firstlight': 3}
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from whiskerbay import data as _gd
    BIOMES = tuple(_gd.BIOME_IDS)
    FISH_NAMES = {f.id: f.name for f in _gd.FISH}
    ISLAND_NAMES = {b: _gd.BIOMES[b].name for b in _gd.BIOME_IDS}
    RARITY = [r.name for r in _gd.RAR]
    BOSS_NAMES = {b: _gd.FI[x.fish].name for b, x in _gd.BOSSES.items()}
except Exception:  # an old or missing game folder: fall back to the built-in names
    pass


def log(*a):
    print(time.strftime('[%H:%M:%S]'), *a, flush=True)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.tmp-', dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'))
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def read_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def hash_pw(pw, salt, iters=PBKDF2_ITER):
    return hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), bytes.fromhex(salt), iters).hex()


def token_hash(tok):
    return hashlib.sha256(tok.encode('utf-8')).hexdigest()


def clean_text(s, n):
    s = ''.join(ch for ch in str(s) if ch.isprintable())
    return s.strip()[:n]


def num(x, lo, hi, default=0.0):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or x != x:
        return default
    return max(lo, min(hi, x))


def summarize(save):
    """The few numbers the leaderboards need, pulled out of a save."""
    try:
        st = save.get('stats') or {}
        return {
            'coins': int(num(save.get('coins'), 0, 1e12)),
            'level': int(num(save.get('level'), 1, 100000, 1)),
            'best': int(num(st.get('bestCatch'), 0, 1e12)),
            'dex': len(save.get('dex') or {}),
            'bosses': int(num(st.get('bosses'), 0, 1e9)),
            'catches': int(num(st.get('catches'), 0, 1e9)),
            'earned': int(num(st.get('earned'), 0, 1e13)),
            'fur': str(save.get('fur') or '#f4a53c')[:7],
        }
    except AttributeError:
        return {}


class Accounts:
    def __init__(self):
        os.makedirs(PLAYER_DIR, exist_ok=True)
        self.cache = {}
        self.dirty = set()
        self.summary = {}
        for fn in os.listdir(PLAYER_DIR):
            if fn.endswith('.json'):
                acc = read_json(os.path.join(PLAYER_DIR, fn))
                if isinstance(acc, dict) and acc.get('name'):
                    self.summary[acc['name'].lower()] = dict(acc.get('summary') or {}, name=acc['name'])

    @staticmethod
    def path(name):
        return os.path.join(PLAYER_DIR, name.lower() + '.json')

    def get(self, name):
        key = name.lower()
        if key in self.cache:
            return self.cache[key]
        acc = read_json(self.path(name))
        if isinstance(acc, dict) and acc.get('name'):
            self.cache[key] = acc
            return acc
        return None

    def create(self, name, pw):
        salt = secrets.token_hex(16)
        acc = {'name': name, 'salt': salt, 'iter': PBKDF2_ITER, 'hash': hash_pw(pw, salt), 'created': int(time.time()),
               'tokens': [], 'save': None, 'summary': {}, 'rev': 0}
        self.cache[name.lower()] = acc
        self.flush_one(acc)
        self.summary[name.lower()] = {'name': name}
        return acc

    def mark(self, acc):
        self.dirty.add(acc['name'].lower())

    def flush_one(self, acc):
        try:
            write_json(self.path(acc['name']), acc)
        except OSError as e:
            log('Could not save', acc['name'], e)

    def flush(self):
        for key in list(self.dirty):
            acc = self.cache.get(key)
            if acc:
                self.flush_one(acc)
        self.dirty.clear()


class Client:
    def __init__(self, reader, writer):
        self.r, self.w = reader, writer
        self.id = secrets.token_hex(4)
        self.name = None
        self.acc = None
        self.state = None
        self.addr = writer.get_extra_info('peername')
        self.chat_times = []
        self.auth_times = []
        self.st_times = []
        self.shared_claim_times = []
        self.closed = False

    def send(self, obj):
        if self.closed:
            return
        try:
            if self.w.transport.get_write_buffer_size() > 4_000_000:
                log('Dropping a stuck connection:', self.name or self.addr)
                self.close()
                return
            self.w.write((json.dumps(obj, separators=(',', ':')) + '\n').encode('utf-8'))
        except (ConnectionError, RuntimeError, AttributeError):
            self.close()

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                self.w.close()
            except (ConnectionError, RuntimeError):
                pass


class Server:
    def __init__(self, args):
        self.args = args
        self.acc = Accounts()
        self.clients = set()
        self.by_name = {}
        adm = read_json(os.path.join(DATA_DIR, 'admins.json'))
        self.admins = set(str(x).lower() for x in adm) if isinstance(adm, list) else set()
        self.creating = set()
        self.loop = None
        self.shared_fish = {}
        self.shared_respawn = {}
        self.shared_bosses = {}
        saved_limited = read_json(os.path.join(DATA_DIR, 'limited_fish.json'))
        self.limited_remaining = {
            species: int(num(saved_limited.get(species), 0, initial, initial))
            if isinstance(saved_limited, dict) else initial
            for species, initial in LIMITED_FISH.items()
        }

    # ---------------- helpers ----------------
    def players(self):
        return [c for c in self.clients if c.name]

    def broadcast(self, obj, skip=None):
        for c in self.players():
            if c is not skip:
                c.send(obj)

    def sys(self, text, to=None):
        msg = {'t': 'sys', 'text': text}
        if to:
            to.send(msg)
        else:
            self.broadcast(msg)

    def who(self):
        out = []
        for c in self.players():
            st = c.state or {}
            out.append({'n': c.name, 'lvl': st.get('lvl', 1), 'b': st.get('b', 'shore'), 'fur': st.get('fur', '#f4a53c')})
        return sorted(out, key=lambda x: x['n'].lower())

    def shared_snapshot(self, biome):
        state = self.shared_fish.get(biome)
        if state is None:
            if time.time() < self.shared_respawn.get(biome, 0) or not _gd:
                return None
            species = [f for f in _gd.FISH if f.b == biome and f.r == 'mythic'
                       and (not getattr(f, 'limited', 0) or self.limited_remaining.get(f.id, 0) > 0)]
            if not species:
                return None
            limited = [f for f in species if getattr(f, 'limited', 0)]
            ordinary = [f for f in species if not getattr(f, 'limited', 0)]
            sp = random.choice(limited) if limited and (not ordinary or random.random() < 0.06) else random.choice(ordinary)
            state = self.shared_fish[biome] = {
                'id': secrets.token_urlsafe(12), 'b': biome, 'sp': sp.id, 'd': float(sp.dz),
                'kg': random.uniform(float(sp.w[0]), float(sp.w[1])), 'x': round(random.uniform(0.2, 0.8), 3),
                'mut': None, 'owner': None,
            }
        if state.get('owner'):
            return None
        return {key: state[key] for key in ('id', 'b', 'sp', 'd', 'kg', 'x', 'mut')}

    def send_shared_fish(self, c, biome):
        c.send({'t': 'shared_fish', 'fish': self.shared_snapshot(biome)})

    def broadcast_shared_fish(self, biome):
        fish = self.shared_snapshot(biome)
        for c in self.players():
            if c.state and c.state.get('b') == biome:
                c.send({'t': 'shared_fish', 'fish': fish})

    # ---------------- connection ----------------
    async def handle(self, reader, writer):
        c = Client(reader, writer)
        self.clients.add(c)
        try:
            while not c.closed:
                try:
                    line = await reader.readline()
                except ValueError:
                    log('Message too big from', c.addr, '- disconnecting')
                    break
                if not line:
                    break
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if isinstance(msg, dict):
                    try:
                        await self.on_msg(c, msg)
                    except Exception as e:  # never let one bad message take the server down
                        log('Error handling', msg.get('t'), 'from', c.name or c.addr, '->', repr(e))
        except (ConnectionError, asyncio.IncompleteReadError, OSError):
            pass
        finally:
            self.drop(c)

    def drop(self, c):
        if c not in self.clients:
            return
        self.clients.discard(c)
        c.close()
        for biome, state in list(self.shared_fish.items()):
            if state.get('owner') == c.id:
                state['owner'] = None
                self.broadcast_shared_fish(biome)
        for biome, state in list(self.shared_bosses.items()):
            if state.get('owner') == c.id:
                del self.shared_bosses[biome]
                self.broadcast({'t': 'boss', 'id': c.id, 'n': c.name, 'on': False, 'b': biome})
        if c.name and self.by_name.get(c.name.lower()) is c:
            del self.by_name[c.name.lower()]
            if c.acc:
                self.acc.flush_one(c.acc)
                self.acc.dirty.discard(c.name.lower())
            self.broadcast({'t': 'leave', 'id': c.id})
            self.sys(f'{c.name} left the bay.')
            log(f'{c.name} left ({len(self.players())} online)')

    # ---------------- messages ----------------
    async def on_msg(self, c, m):
        t = m.get('t')
        if t == 'hello':
            c.send({'t': 'welcome', 'v': PROTO, 'name': self.args.name, 'motd': self.args.motd,
                    'needCode': bool(self.args.invite), 'online': len(self.players())})
            if m.get('v') != PROTO:
                c.send({'t': 'auth_err', 'msg': 'This server runs a different game version. Everyone must use the same Whisker Bay build and server.'})
                return
        if t in ('login', 'register', 'resume'):
            await self.on_auth(c, t, m)
            return
        if t == 'ping':
            c.send({'t': 'pong', 'at': m.get('at')})
            return
        if not c.name:
            return
        if t == 'st':
            self.on_state(c, m)
        elif t == 'chat':
            self.on_chat(c, m)
        elif t == 'emote':
            e = int(num(m.get('e'), 0, 9))
            self.broadcast({'t': 'emote', 'id': c.id, 'e': e}, skip=c)
        elif t == 'catch':
            self.on_catch(c, m)
        elif t == 'boss':
            self.on_boss(c, bool(m.get('on')))
        elif t == 'shared_claim':
            self.on_shared_claim(c, m)
        elif t == 'shared_release':
            self.on_shared_release(c, m)
        elif t == 'adm':
            self.on_admin(c, m)
        elif t == 'save':
            self.on_save(c, m)
        elif t == 'lb':
            self.on_lb(c)
        elif t == 'who':
            c.send({'t': 'who', 'list': self.who()})
        elif t == 'logout':
            tok = m.get('token')
            if isinstance(tok, str) and c.acc:
                h = token_hash(tok)
                c.acc['tokens'] = [x for x in c.acc.get('tokens', []) if x != h]
                self.acc.mark(c.acc)

    async def on_auth(self, c, kind, m):
        now = time.time()
        c.auth_times = [x for x in c.auth_times if now - x < 60]
        if len(c.auth_times) >= 8:
            c.send({'t': 'auth_err', 'msg': 'Too many tries. Wait a minute and try again.'})
            return
        c.auth_times.append(now)
        user = str(m.get('user') or '').strip()
        if not NAME_RE.match(user):
            c.send({'t': 'auth_err', 'msg': 'Names are 3-16 letters, numbers or _ (no spaces).'})
            return
        loop = asyncio.get_running_loop()
        if kind == 'register':
            pw = str(m.get('pass') or '')
            if not 4 <= len(pw) <= 64:
                c.send({'t': 'auth_err', 'msg': 'Passwords need 4 to 64 characters.'})
                return
            if self.args.invite and str(m.get('code') or '').strip() != self.args.invite:
                c.send({'t': 'auth_err', 'msg': 'This server needs an invite code to make an account. Ask the host for it.', 'needCode': True})
                return
            if self.acc.get(user) or user.lower() in self.creating:
                c.send({'t': 'auth_err', 'msg': f'"{user}" is taken. Try another name, or log in if it is yours.'})
                return
            self.creating.add(user.lower())
            try:
                acc = await loop.run_in_executor(None, self.acc.create, user, pw)
            finally:
                self.creating.discard(user.lower())
            log(f'New account: {user}')
            self.login(c, acc, True)
            return
        acc = self.acc.get(user)
        if kind == 'resume':
            tok = m.get('token')
            ok = acc is not None and isinstance(tok, str) and any(hmac.compare_digest(token_hash(tok), h) for h in acc.get('tokens', []))
            if not ok:
                c.send({'t': 'auth_err', 'msg': 'Your saved login ran out. Please log in again.', 'expired': True})
                return
            self.login(c, acc, False, reuse=tok)
            return
        pw = str(m.get('pass') or '')
        if acc is None:
            await asyncio.sleep(0.3)
            c.send({'t': 'auth_err', 'msg': f'No account called "{user}" here. Make one with "Create account".'})
            return
        h = await loop.run_in_executor(None, hash_pw, pw, acc['salt'], acc.get('iter', PBKDF2_ITER))
        if not hmac.compare_digest(h, acc['hash']):
            await asyncio.sleep(0.5)
            c.send({'t': 'auth_err', 'msg': 'Wrong password.'})
            return
        self.login(c, acc, True)

    def login(self, c, acc, new_token, reuse=None):
        name = acc['name']
        old = self.by_name.get(name.lower())
        if old is not None and old is not c:
            old.send({'t': 'kicked', 'msg': 'You logged in somewhere else, so this game was disconnected.'})
            old.name = None
            self.clients.discard(old)
            old.close()
            self.broadcast({'t': 'leave', 'id': old.id}, skip=c)
        tok = reuse
        if new_token:
            tok = secrets.token_urlsafe(24)
            acc['tokens'] = (acc.get('tokens') or [])[-7:] + [token_hash(tok)]
            self.acc.mark(acc)
        c.name, c.acc = name, acc
        self.by_name[name.lower()] = c
        c.send({'t': 'auth_ok', 'user': name, 'token': tok, 'save': acc.get('save'), 'rev': acc.get('rev', 0),
                'motd': self.args.motd, 'server': self.args.name})
        for o in self.players():
            if o is not c and o.state:
                c.send(dict(o.state, t='st', id=o.id, n=o.name))
        c.send({'t': 'who', 'list': self.who()})
        if name.lower() in self.admins:
            c.send({'t': 'admin', 'on': True})
        self.sys(f'{name} joined the bay!', None)
        log(f'{name} joined from {c.addr[0] if c.addr else "?"} ({len(self.players())} online)')

    def on_state(self, c, m):
        now = time.time()
        c.st_times = [x for x in c.st_times if now - x < 1]
        if len(c.st_times) > 25:
            return
        c.st_times.append(now)
        b = m.get('b') if m.get('b') in BIOMES else 'shore'
        st = {
            'b': b, 'x': num(m.get('x'), 0, 1, 0.3), 'm': m.get('m') if m.get('m') in MODES else 'idle',
            'hx': num(m.get('hx'), -0.1, 1.1, 0.5), 'hd': num(m.get('hd'), -1, 3000, -1), 'ten': num(m.get('ten'), 0, 1, 0),
            'fur': clean_text(m.get('fur') or '#f4a53c', 7), 'boat': clean_text(m.get('boat') or 'dinghy', 12),
            'rod': clean_text(m.get('rod') or 'starter', 12), 'ench': clean_text(m.get('ench') or '', 12) or None,
            'lvl': int(num(m.get('lvl'), 1, 100000, 1)), 'boss': bool(m.get('boss')),
            'pets': [clean_text(x, 10) for x in (m.get('pets') if isinstance(m.get('pets'), list) else [])[:2] if isinstance(x, str)],
        }
        old_biome = c.state.get('b') if c.state else None
        c.state = st
        if st['boss']:
            lock = self.shared_bosses.get(b)
            if lock and lock.get('owner') == c.id:
                lock['expires'] = now + 240
        if old_biome != b:
            self.send_shared_fish(c, b)
        self.broadcast(dict(st, t='st', id=c.id, n=c.name), skip=c)

    def on_boss(self, c, on):
        state = c.state or {}
        biome = state.get('b')
        if biome not in BOSS_NAMES:
            c.send({'t': 'boss_claim', 'ok': False})
            return
        now = time.time()
        lock = self.shared_bosses.get(biome)
        if on:
            if not state.get('boss') or state.get('m') not in ('bite', 'reel'):
                c.send({'t': 'boss_claim', 'ok': False, 'b': biome})
                return
            owner_connected = any(p.id == lock.get('owner') and p.name == lock.get('name') for p in self.players()) if lock else False
            if lock and (lock.get('expires', 0) <= now or not owner_connected):
                del self.shared_bosses[biome]
                lock = None
            if lock and lock.get('owner') != c.id:
                c.send({'t': 'boss_claim', 'ok': False, 'b': biome})
                return
            self.shared_bosses[biome] = {'owner': c.id, 'name': c.name, 'expires': now + 240}
            c.send({'t': 'boss_claim', 'ok': True, 'b': biome})
            self.broadcast({'t': 'boss', 'id': c.id, 'n': c.name, 'on': True, 'b': biome}, skip=c)
            boss = BOSS_NAMES.get(biome, 'a boss').upper()
            self.sys(f'{c.name} has hooked {boss} in the {ISLAND_NAMES.get(biome, "deep")}! Sail there and press 5 to cheer!')
        elif lock and lock.get('owner') == c.id:
            del self.shared_bosses[biome]
            self.broadcast({'t': 'boss', 'id': c.id, 'n': c.name, 'on': False, 'b': biome}, skip=c)

    def on_shared_claim(self, c, m):
        state = c.state or {}
        biome, fish_id = m.get('b'), m.get('id')
        times = [t for t in getattr(c, 'shared_claim_times', []) if time.time() - t < 5]
        if len(times) >= 5:
            c.shared_claim_times = times
            c.send({'t': 'shared_claim_result', 'id': fish_id, 'ok': False})
            return
        times.append(time.time())
        c.shared_claim_times = times
        fish = self.shared_fish.get(biome)
        if (biome != state.get('b') or not isinstance(fish_id, str) or not fish or fish.get('id') != fish_id
                or fish.get('owner') or state.get('m') not in ('bite', 'reel')
                or abs(state.get('hx', -2) - fish.get('x', 0.5)) > 0.24
                or abs(state.get('hd', -1000) - fish.get('d', 0)) > 90):
            c.send({'t': 'shared_claim_result', 'id': fish_id, 'ok': False})
            return
        fish['owner'] = c.id
        c.send({'t': 'shared_claim_result', 'id': fish_id, 'ok': True})
        self.broadcast({'t': 'shared_claimed', 'id': fish_id, 'b': biome, 'owner': c.name})

    def on_shared_release(self, c, m):
        biome, fish_id = m.get('b'), m.get('id')
        fish = self.shared_fish.get(biome)
        if not fish or fish.get('id') != fish_id or fish.get('owner') != c.id:
            return
        fish['owner'] = None
        self.broadcast_shared_fish(biome)

    def on_chat(self, c, m):
        text = clean_text(m.get('text', ''), 140)
        if not text:
            return
        now = time.time()
        c.chat_times = [x for x in c.chat_times if now - x < 10]
        if len(c.chat_times) >= 6:
            self.sys('Slow down a little: you can send 6 messages every 10 seconds.', c)
            return
        c.chat_times.append(now)
        if text.startswith('/'):
            cmd, _, rest = text.partition(' ')
            cmd = cmd.lower()
            if cmd in ('/who', '/online', '/list'):
                names = ', '.join(f"{p['n']} (Lv {p['lvl']}, {ISLAND_NAMES.get(p['b'], '?')})" for p in self.who())
                self.sys(f'Online: {names}', c)
            elif cmd == '/me' and rest.strip():
                self.broadcast({'t': 'chat', 'n': c.name, 'text': rest.strip()[:120], 'me': True})
            elif cmd == '/help':
                self.sys('Commands: /who (who is online), /me <action>. Keys 1-5 send emotes.', c)
            elif cmd == '/admin':
                code = str(self.args.admin_code or '')
                if code and hmac.compare_digest(rest.strip(), code):
                    self.set_admin(c.name, True)
                else:
                    self.sys('Wrong admin code (or this server has none).', c)
            else:
                self.sys('Unknown command. Try /help.', c)
            return
        st = c.state or {}
        self.broadcast({'t': 'chat', 'n': c.name, 'text': text, 'b': st.get('b')})
        log(f'<{c.name}> {text}')

    # ---- admins: the host makes them with the "admin <name>" command (or an admin code in chat) ----
    def set_admin(self, name, on):
        key = clean_text(name, 16).lower()
        if not key:
            return
        if on:
            self.admins.add(key)
        else:
            self.admins.discard(key)
        write_json(os.path.join(DATA_DIR, 'admins.json'), sorted(self.admins))
        c = self.by_name.get(key)
        if c:
            c.send({'t': 'admin', 'on': on})
            self.sys('You are an admin now: press F9 for the admin panel. Use it for good (or for laughs).' if on
                     else 'You are no longer an admin.', c)

    def on_admin(self, c, m):
        if not c.name or c.name.lower() not in self.admins:
            self.sys('Only admins can do that.', c)
            return
        act = m.get('act')
        if act not in ADMIN_ACTS:
            return
        arg = m.get('arg')
        arg = clean_text(arg, 120) if isinstance(arg, str) else int(num(arg, 0, 1e12)) if arg is not None else None
        to = str(m.get('to') or '')
        if to == '*':
            targets = [o for o in self.players() if o is not c]
        else:
            o = self.by_name.get(to.lower())
            targets = [o] if o else []
        for o in targets:
            o.send({'t': 'adm', 'act': act, 'arg': arg, 'from': c.name})
        log(f'[admin] {c.name}: {act} -> {to} ({len(targets)} player(s)){" " + str(arg) if arg not in (None, "") else ""}')

    def on_catch(self, c, m):
        sp = m.get('sp') if m.get('sp') in FISH_NAMES else None
        tier = int(num(m.get('tier'), 0, 6))
        mut = m.get('mut') if m.get('mut') in MUTS else None
        val = int(num(m.get('val'), 0, 1e12))
        if not sp:
            return
        shared_id = m.get('shared_id')
        state = c.state or {}
        shared = self.shared_fish.get(state.get('b'))
        if (isinstance(shared_id, str) and shared and shared.get('id') == shared_id and shared.get('owner') == c.id
                and shared.get('sp') == sp and tier == 5):
            biome = state.get('b')
            if self.limited_remaining.get(sp, 0) > 0:
                self.limited_remaining[sp] -= 1
                try:
                    write_json(os.path.join(DATA_DIR, 'limited_fish.json'), self.limited_remaining)
                except OSError as e:
                    log('Could not save limited-fish inventory:', e)
                fish_name = FISH_NAMES[sp]
                remaining = self.limited_remaining[sp]
                self.broadcast({'t': 'limited_caught', 'n': c.name, 'fish': fish_name, 'left': remaining})
            del self.shared_fish[biome]
            self.shared_respawn[biome] = time.time() + 60
            self.broadcast({'t': 'shared_caught', 'id': shared_id, 'b': biome})
        if tier >= 3 or mut in ('gilded', 'corrupted') or (mut and tier >= 2):
            name = (MUTS[mut] + ' ' if mut else '') + FISH_NAMES[sp]
            if tier == 6:
                text = f'{c.name} has SLAIN {FISH_NAMES[sp].upper()}! ({val:,} coins)'
            else:
                desc = f'{RARITY[tier]} {name}'
                article = 'an' if desc[0].lower() in 'aeiou' else 'a'
                text = f'{c.name} caught {article} {desc}! ({val:,} coins)'
            self.broadcast({'t': 'ann', 'text': text, 'tier': tier, 'n': c.name})
            log(text)

    def on_save(self, c, m):
        data = m.get('data')
        if not isinstance(data, dict):
            return
        size = len(json.dumps(data, separators=(',', ':')))
        if size > MAX_SAVE:
            self.sys('Your save is too big for this server, so it was not stored.', c)
            return
        acc = c.acc
        acc['save'] = data
        acc['rev'] = int(num(data.get('rev'), 0, 1e12, acc.get('rev', 0)))
        acc['summary'] = summarize(data)
        self.acc.summary[acc['name'].lower()] = dict(acc['summary'], name=acc['name'])
        self.acc.mark(acc)
        c.send({'t': 'saved', 'rev': acc['rev']})

    def on_lb(self, c):
        rows = list(self.acc.summary.values())
        out = {}
        for key in ('coins', 'level', 'best', 'dex', 'bosses', 'catches'):
            top = sorted(rows, key=lambda r: r.get(key, 0), reverse=True)[:10]
            out[key] = [{'n': r['name'], 'v': r.get(key, 0), 'fur': r.get('fur', '#f4a53c')} for r in top]
        c.send({'t': 'lb', 'boards': out, 'players': len(rows)})

    # ---------------- housekeeping ----------------
    async def autosave(self):
        while True:
            await asyncio.sleep(5)
            self.acc.flush()
            now = time.time()
            for biome, ready in list(self.shared_respawn.items()):
                if now >= ready:
                    del self.shared_respawn[biome]
                    self.broadcast_shared_fish(biome)
            for biome, lock in list(self.shared_bosses.items()):
                if now >= lock.get('expires', 0):
                    del self.shared_bosses[biome]
                    self.broadcast({'t': 'boss', 'id': lock['owner'], 'n': lock['name'], 'on': False, 'b': biome})

    def command(self, line):
        cmd, _, rest = line.strip().partition(' ')
        cmd = cmd.lower()
        if cmd in ('help', '?'):
            print('Commands: list | say <message> | kick <name> | admin <name> | unadmin <name> | admins | stop')
        elif cmd in ('list', 'who'):
            ps = self.who()
            print(f'{len(ps)} online:', ', '.join(f"{p['n']} (Lv {p['lvl']}, {p['b']})" for p in ps) or 'nobody yet')
        elif cmd == 'say' and rest:
            self.sys(f'[Host] {rest[:140]}')
            print('Sent.')
        elif cmd == 'kick' and rest:
            c = self.by_name.get(rest.strip().lower())
            if c:
                c.send({'t': 'kicked', 'msg': 'The host disconnected you.'})
                self.drop(c)
                print('Kicked', rest.strip())
            else:
                print('Nobody called', rest.strip(), 'is online.')
        elif cmd == 'admin' and rest:
            self.set_admin(rest.strip(), True)
            print(rest.strip(), 'is now an admin. They press F9 in the game for the admin panel.')
        elif cmd == 'unadmin' and rest:
            self.set_admin(rest.strip(), False)
            print(rest.strip(), 'is no longer an admin.')
        elif cmd == 'admins':
            print('Admins:', ', '.join(sorted(self.admins)) or 'nobody yet (type: admin <name>)')
        elif cmd in ('stop', 'quit', 'exit'):
            print('Saving and stopping...')
            self.acc.flush()
            for c in list(self.clients):
                c.send({'t': 'kicked', 'msg': 'The server is shutting down.'})
            self.loop.stop()
        elif cmd:
            print('Unknown command. Type help.')


def lan_addresses():
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))   # no packet is sent; this just picks the outgoing interface
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith('127.'):
                ips.add(ip)
    except OSError:
        pass
    return sorted(ips)


SETTINGS_FILE = os.path.join(HERE, 'server_settings.json')
SETTINGS_DEFAULT = {
    '_how_to': 'Change these with Notepad / TextEdit, save, then restart the server. '
               'invite = a code friends must type to make an account (leave "" for none). '
               'admin_code = anyone who types /admin <this code> in chat becomes an admin (leave "" to turn it off).',
    'port': 7777,
    'invite': '',
    'name': 'Whisker Bay',
    'motd': 'Welcome to the bay! Be nice, fish hard.',
    'admin_code': '',
}
# the things an admin can do to players (the game on their side carries them out)
ADMIN_ACTS = {'scare', 'fakeleg', 'fishrain', 'flip', 'disco', 'honk', 'storm', 'scatter', 'slip', 'reverse', 'zoomies', 'boss',
              'say', 'coins', 'xp', 'lures', 'mats', 'rods', 'unlock', 'pull'}


def load_settings():
    s = dict(SETTINGS_DEFAULT)
    got = read_json(SETTINGS_FILE)
    if isinstance(got, dict):
        for k in ('port', 'invite', 'name', 'motd', 'admin_code'):
            if k in got and isinstance(got[k], type(SETTINGS_DEFAULT[k])):
                s[k] = got[k]
    elif os.path.exists(SETTINGS_FILE):
        print('!' * 60)
        print(' server_settings.json has a typo, so it was ignored (no invite code!).')
        print(' Check every line has "quotes" around text and a comma at the end,')
        print(' except the last line before the closing }. Then restart the server.')
        print('!' * 60)
    else:
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(SETTINGS_DEFAULT, f, indent=2)
        except OSError:
            pass
    return s


def main():
    try:
        from updater import FatalUpdateError, check_for_updates
        check_for_updates(os.path.dirname(os.path.abspath(__file__)))
    except FatalUpdateError as e:
        print(f'Whisker Bay could not recover safely from an update error: {e}')
        sys.exit(1)
    cfg = load_settings()
    ap = argparse.ArgumentParser(description='Whisker Bay multiplayer server (defaults come from server_settings.json)')
    ap.add_argument('--port', type=int, default=cfg['port'], help='TCP port to listen on (default 7777)')
    ap.add_argument('--host', default=None, help='address to listen on (default: every network, IPv4 and IPv6)')
    ap.add_argument('--invite', default=cfg['invite'], help='invite code needed to create an account (optional)')
    ap.add_argument('--name', default=cfg['name'], help='server name shown to players')
    ap.add_argument('--motd', default=cfg['motd'], help='message of the day')
    ap.add_argument('--admin-code', dest='admin_code', default=cfg['admin_code'], help='players who type /admin <code> in chat become admins')
    args = ap.parse_args()
    args.invite = str(args.invite or '').strip()
    args.name = clean_text(args.name, 40) or 'Whisker Bay'
    args.motd = clean_text(args.motd, 200)

    srv = Server(args)

    async def run():
        srv.loop = asyncio.get_running_loop()
        try:
            # no host = listen on every network, IPv4 and IPv6 (so "localhost" works however a tunnel resolves it)
            server = await asyncio.start_server(srv.handle, args.host, args.port, limit=MAX_LINE)
        except OSError:
            if args.host is not None:
                raise
            server = await asyncio.start_server(srv.handle, '0.0.0.0', args.port, limit=MAX_LINE)
        asyncio.create_task(srv.autosave())
        print('=' * 60)
        print(f' Whisker Bay server "{args.name}" is running on port {args.port}')
        print('=' * 60)
        ips = lan_addresses()
        if ips:
            print(' Friends on the same Wi-Fi connect to:')
            for ip in ips:
                print(f'     {ip}:{args.port}')
        print(f' On this computer you can use:  localhost:{args.port}')
        print(' Friends in other houses: see "READ ME FIRST.txt", part 4.')
        print(' Settings (invite code, name, port): server_settings.json')
        if args.invite:
            print(f' New accounts need the invite code: {args.invite}')
        print(' Type "help" for commands. Close this window or type "stop" to shut down.')
        print('=' * 60, flush=True)
        async with server:
            await server.serve_forever()

    def console():
        while True:
            try:
                line = input()
            except (EOFError, KeyboardInterrupt):
                return
            if srv.loop:
                srv.loop.call_soon_threadsafe(srv.command, line)

    threading.Thread(target=console, daemon=True).start()
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    except OSError as e:
        print(f'Could not start the server on port {args.port}: {e}')
        print('Is another server already running? Try a different port with --port 7778')
        sys.exit(1)
    except RuntimeError:
        pass
    finally:
        srv.acc.flush()
        for c in list(srv.clients):
            if c.acc:
                srv.acc.flush_one(c.acc)
        print('Server stopped. Everyone\'s progress is saved in server_data.')


if __name__ == '__main__':
    main()
