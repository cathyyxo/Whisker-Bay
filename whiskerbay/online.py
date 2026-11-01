"""Online play: logging in, cloud saves, other anglers' boats, chat, emotes, cheers and leaderboards."""
import json
import os
import random
import re
import time

from . import net, settings
from . import world as Wd
from .data import BIOMES, BOSSES, EMOTES, RAR
from .settings import SET, save_settings
from .util import D

PROTO = 6
conn = None
st = D(phase='off', server='', host='', port=7777, user='', token=None, remember=False, error='', status='',
       motd='', srvname='', needCode=False, kicked='', cloud=None, newangler=False, ping=None, admin=False)
peers = {}
chat = []
lb = None
who = []
_pending = None
_presence_t = 0.0
_last_payload = None
_last_payload_t = 0.0
_save_due = None
_save_t = 0.0
_retry_t = 0.0
_ping_t = 0.0
_crew = -1


def active():
    return Wd.MODE == 'online' and Wd.LIVE and st.phase in ('in', 'lost')


def connected():
    return active() and st.phase == 'in'


def parse_addr(s):
    s = (s or '').strip()
    for pre in ('tcp://', 'http://', 'https://'):
        if s.lower().startswith(pre):
            s = s[len(pre):]
    s = s.rstrip('/')
    if not s:
        return None
    if s.startswith('['):
        host, _, rest = s[1:].partition(']')
        port = rest.lstrip(':')
    elif s.count(':') == 1:
        host, port = s.split(':')
    else:
        host, port = s, ''
    try:
        port = int(port) if port else 7777
    except ValueError:
        return None
    if not host or not 0 < port < 65536:
        return None
    return host.strip(), port


def backup_path(server=None, user=None):
    key = re.sub(r'[^A-Za-z0-9]+', '_', f'{server or st.server}_{user or st.user}'.lower())[:80]
    return os.path.join(settings.SAVE_DIR, 'online_backups', key + '.json')


# ---------------- starting and stopping ----------------
def start(kind, server, user='', pw='', code='', remember=False, token=None):
    """kind: 'login' | 'register' | 'resume'. Connects and logs in in the background."""
    global conn, _pending
    close()
    addr = parse_addr(server)
    if not addr:
        st.error = 'Type the server address like 192.168.1.20:7777'
        return
    st.host, st.port = addr
    st.server = server.strip()
    st.user = user.strip()
    st.error = ''
    st.kicked = ''
    st.status = f'Connecting to {st.server}...'
    st.phase = 'connecting'
    st.remember = remember
    st.newangler = False
    _pending = D(kind=kind, user=user.strip(), pw=pw, code=code.strip(), token=token)
    conn = net.Conn()
    conn.connect(*addr)


def close(flush=False):
    global conn
    if conn:
        conn.close(flush=flush)
        conn = None
    st.phase = 'off'
    st.status = ''
    st.admin = False
    peers.clear()


def cancel():
    close()
    st.error = ''


def logout():
    """Forget the saved login on this computer and leave the server."""
    rem = SET.get('remember')
    if conn and rem and rem.get('token'):
        conn.send({'t': 'logout', 'token': rem['token']})
    SET['remember'] = None
    save_settings()
    leave()


def leave():
    """Stop playing online: upload the last save, then hang up."""
    flush_save(force=True)
    close(flush=True)
    st.token = None


# ---------------- saves ----------------
def queue_save(p):
    """Called by the game whenever it saves while playing online."""
    global _save_due
    snap = json.loads(json.dumps(p))
    _save_due = snap
    settings.write_json(backup_path(), snap)


def flush_save(force=False):
    global _save_due, _save_t
    if _save_due is None or conn is None or st.phase != 'in':
        return
    now = time.time()
    if force or now - _save_t > 2.5:
        conn.send({'t': 'save', 'data': _save_due})
        _save_due = None
        _save_t = now


def begin_play(p):
    """Start fishing with an online profile."""
    p.name = st.user
    Wd.save_hook = queue_save
    Wd.startPlaying(p, 'online')
    st.phase = 'in'
    st.newangler = False
    chat.clear()
    add_chat('', f'Connected to {st.srvname or st.server}. {st.motd}'.strip(), 'sys')
    add_chat('', 'Press T to chat, 1-5 for emotes, Tab for players and leaderboards.', 'sys')
    Wd.saveProfile()
    flush_save(force=True)
    Wd.toast(f'Welcome to the bay, {p.name}! You are online.', 'good')


def new_online_angler(fur, bring=None):
    """After making an account: start fresh, or copy one of this computer's anglers into it."""
    if bring:
        p = Wd.loadLocal(bring)
        if p is None:
            st.error = 'That angler could not be read.'
            return
        p.id = Wd.new_id()
    else:
        p = Wd.freshProfile(st.user, fur)
    begin_play(p)


# ---------------- chat & emotes ----------------
def add_chat(who_, text, kind='chat', col=None):
    chat.append(D(who=who_, text=text, kind=kind, col=col, t=time.time()))
    del chat[:-80]


def send_chat(text):
    text = text.strip()
    if not text or not connected():
        return
    conn.send({'t': 'chat', 'text': text[:140]})


def send_emote(i):
    if not active() or not 0 <= i < len(EMOTES):
        return
    e = EMOTES[i]
    Wd.G.emote = (e.text, e.col, Wd.G.t)
    if connected():
        conn.send({'t': 'emote', 'e': i})


def admin_send(act, to, arg=None):
    """An admin action for another player (to = their name, or '*' for everyone else). The server checks you are an admin."""
    if connected():
        conn.send({'t': 'adm', 'act': act, 'to': to, 'arg': arg})
        return True
    return False


def request_boards():
    if connected():
        conn.send({'t': 'lb'})
        conn.send({'t': 'who'})


# ---------------- other anglers ----------------
def visible_peers():
    P = Wd.P
    if P is None:
        return []
    return [p for p in peers.values() if p.biome == P.biome]


def _on_state(m):
    pid = m.get('id')
    if not isinstance(pid, str):
        return
    p = peers.get(pid)
    x = float(m.get('x') or 0.3)
    hx = float(m.get('hx') or 0.5)
    hd = float(m.get('hd') if m.get('hd') is not None else -1)
    if p is None:
        p = peers[pid] = D(id=pid, bf=x, hx=hx, hd=hd, seed=random.random() * 10, emote=None, tip=None, x=0.0)
    p.name = str(m.get('n') or '?')[:16]
    p.biome = m.get('b') if m.get('b') in BIOMES else 'shore'
    p.tbf, p.thx, p.thd = x, hx, hd
    p.mode = m.get('m') or 'idle'
    p.ten = float(m.get('ten') or 0)
    p.fur = m.get('fur') or '#f4a53c'
    p.boat, p.rod, p.ench = m.get('boat') or 'dinghy', m.get('rod') or 'starter', m.get('ench')
    p.lvl = int(m.get('lvl') or 1)
    p.boss = bool(m.get('boss'))
    pl = m.get('pets')
    p.pets = [str(x) for x in pl if isinstance(x, str)][:2] if isinstance(pl, list) else []
    p.last = time.time()


def _tick_peers(dt):
    global _crew
    G = Wd.G
    now = time.time()
    k = min(1.0, dt * 10)
    for pid in list(peers.keys()):
        p = peers[pid]
        if now - p.last > 20:
            del peers[pid]
            continue
        p.bf += (p.tbf - p.bf) * k
        p.hx += (p.thx - p.hx) * k
        if p.thd < 0 or p.hd < 0 or abs(p.thd - p.hd) > 200:
            p.hd = p.thd
        else:
            p.hd += (p.thd - p.hd) * k
        p.x = p.bf * G.W
    vis = visible_peers() if active() else []
    G.remoteBoss = any(p.boss for p in vis)
    n = len(vis)
    if n != _crew:
        if active() and n > _crew >= 0 and n > 0:
            Wd.toast(f'Crew bonus: {n} other angler{"s" if n > 1 else ""} here, +{min(15, 5 * n)}% luck!', 'good')
        _crew = n
        G.crew = n if active() else 0
        if Wd.P is not None:
            Wd.refreshStats()


def _send_presence(dt):
    global _presence_t, _last_payload, _last_payload_t
    G, P = Wd.G, Wd.P
    _presence_t -= dt
    if _presence_t > 0:
        return
    _presence_t = 0.12
    boss = bool((G.reel and G.reel.boss) or (G.bite and G.bite.f.tier == 6))
    payload = {'b': P.biome, 'x': round(G.bf, 3), 'm': G.mode, 'hx': round(G.hook.x / G.W, 3), 'hd': round(G.hook.d, 1),
               'ten': round(G.reel.ten, 2) if G.reel else 0, 'fur': P.fur, 'boat': P.boat, 'rod': P.rod,
               'ench': (P.rods.get(P.rod) or {}).get('ench'), 'lvl': P.level, 'boss': boss, 'pets': list(P.petOn)[:2]}
    now = time.time()
    if payload != _last_payload or now - _last_payload_t > 2:
        conn.send(dict(payload, t='st'))
        _last_payload = payload
        _last_payload_t = now


def _drain_events():
    G = Wd.G
    evs, G.events = G.events, []
    if not connected():
        return
    for kind, data in evs:
        if kind == 'catch':
            conn.send({'t': 'catch', 'sp': data.sp, 'tier': data.tier, 'mut': data.mut, 'val': data.val, 'kg': data.kg,
                       'shared_id': data.get('shared_id')})
        elif kind == 'boss':
            conn.send({'t': 'boss', 'on': bool(data)})
        elif kind == 'shared_claim':
            conn.send({'t': 'shared_claim', 'b': data.b, 'id': data.id})
        elif kind == 'shared_release':
            conn.send({'t': 'shared_release', 'b': data.b, 'id': data.id})


# ---------------- the per-frame pump ----------------
def pump(dt):
    global conn, _retry_t, _ping_t, _pending
    if st.phase == 'lost' and (conn is None or not conn.alive):
        _retry_t -= dt
        if _retry_t <= 0 and st.token:
            _retry_t = 5.0
            conn = net.Conn()
            conn.connect(st.host, st.port)
            _pending = D(kind='resume', user=st.user, token=st.token)
    if conn is not None:
        for m in conn.poll():
            _handle(m)
    if active():
        _tick_peers(dt)
        if st.phase == 'in' and conn is not None:
            _send_presence(dt)
            flush_save()
            _ping_t -= dt
            if _ping_t <= 0:
                _ping_t = 10
                conn.send({'t': 'ping', 'at': time.time()})
    else:
        _reset_crew()
    _drain_events()


def _reset_crew():
    global _crew
    if peers and not st.phase == 'newangler':
        peers.clear()
    G = Wd.G
    if G.crew or G.remoteBoss or _crew != -1:
        G.crew = 0
        G.remoteBoss = False
        _crew = -1
        if Wd.P is not None:
            Wd.refreshStats()


def _handle(m):
    global _pending, conn
    t = m.get('t')
    if t == '_open':
        conn.send({'t': 'hello', 'v': PROTO, 'game': 'whiskerbay'})
        if _pending:
            pd = _pending
            if pd.kind == 'resume':
                conn.send({'t': 'resume', 'user': pd.user, 'token': pd.token})
            else:
                conn.send({'t': pd.kind, 'user': pd.user, 'pass': pd.pw, 'code': pd.code})
            _pending = None
            if st.phase == 'connecting':
                st.status = 'Logging in...'
    elif t == '_fail':
        if st.phase == 'lost':
            st.status = 'Server unreachable. Retrying...'
            return
        close()
        st.error = f'Could not reach {st.server}. Is the server running, and is the address right?'
    elif t == '_closed':
        if st.phase == 'in':
            st.phase = 'lost'
            st.status = 'Lost connection. Retrying...'
            Wd.toast('Lost connection to the server. Keep fishing: progress is kept on this computer and uploads when you reconnect.', 'bad')
            add_chat('', 'Connection lost. Reconnecting...', 'sys')
            peers.clear()
        elif st.phase in ('connecting', 'newangler'):
            close()
            st.error = st.error or 'The server closed the connection.'
    elif t == 'welcome':
        st.motd = str(m.get('motd') or '')[:200]
        st.srvname = str(m.get('name') or '')[:40]
        st.needCode = bool(m.get('needCode'))
    elif t == 'auth_ok':
        _auth_ok(m)
    elif t == 'auth_err':
        msg = str(m.get('msg') or 'Login failed.')
        if m.get('needCode'):
            st.needCode = True
        if m.get('expired') and SET.get('remember'):
            SET['remember'] = None
            save_settings()
        if st.phase == 'lost':
            Wd.toast('Could not log back in. Keep playing: your progress is kept on this computer. Log in again from the title screen.', 'bad')
            st.token = None
            if conn:
                conn.close()
            conn = None
            return
        close()
        st.error = msg
    elif t == 'kicked':
        st.kicked = str(m.get('msg') or 'Disconnected.')
        if active():
            Wd.saveProfile()
            Wd.stopPlaying()
        close()
        st.error = st.kicked
    elif t == 'st':
        _on_state(m)
    elif t == 'shared_fish':
        Wd.setSharedFish(m.get('fish'))
    elif t == 'shared_claimed':
        Wd.removeSharedFish(m.get('id'), m.get('owner'))
    elif t == 'shared_claim_result':
        if not m.get('ok'):
            Wd.sharedClaimFailed(m.get('id'))
    elif t == 'shared_caught':
        Wd.removeSharedFish(m.get('id'))
    elif t == 'limited_caught':
        fish_name = str(m.get('fish') or 'a limited fish')[:48]
        remaining = max(0, min(999, int(m.get('left') or 0)))
        text = f'{m.get("n") or "An angler"} caught {fish_name}! {remaining} remain on this server.'
        add_chat('', text, 'ann', '#ffe08a')
        Wd.toast(text, 'gold')
    elif t == 'boss_claim':
        if not m.get('ok'):
            Wd.sharedBossDenied()
    elif t == 'leave':
        peers.pop(m.get('id'), None)
    elif t == 'chat':
        who_ = str(m.get('n') or '?')
        text = str(m.get('text') or '')
        if m.get('me'):
            add_chat('', f'* {who_} {text}', 'me')
        else:
            add_chat(who_, text, 'chat')
    elif t == 'sys':
        add_chat('', str(m.get('text') or ''), 'sys')
    elif t == 'ann':
        text = str(m.get('text') or '')
        tier = int(m.get('tier') or 0)
        add_chat('', text, 'ann', RAR[min(6, max(0, tier))].col)
        if m.get('n') != st.user:
            Wd.toast(text, 'gold' if tier >= 4 else 'good')
    elif t == 'emote':
        p = peers.get(m.get('id'))
        e = int(m.get('e') or 0)
        if p and 0 <= e < len(EMOTES):
            em = EMOTES[e]
            p.emote = (em.text, em.col, Wd.G.t)
            G = Wd.G
            if em.id == 'cheer' and p.biome == (Wd.P.biome if Wd.P else None) and ((G.reel and G.reel.boss) or (G.bite and G.bite.f.tier == 6)):
                G.cheer = 2.5
                Wd.floatText(G.hook.x, G.hook.d - 12, f'{p.name} cheers!', '#00ffd5', 18)
    elif t == 'boss':
        if m.get('on') and m.get('n') != st.user:
            B = BOSSES.get(m.get('b'))
            add_chat('', f'{m.get("n")} is fighting {Wd.bossName(B.fish) if B else "a boss"}!', 'ann', '#00ffd5')
    elif t == 'lb':
        globals()['lb'] = m
    elif t == 'who':
        lst = m.get('list')
        if isinstance(lst, list):
            globals()['who'] = lst
    elif t == 'admin':
        st.admin = bool(m.get('on'))
        if st.admin:
            Wd.toast('You are an admin on this server! Press F9 for the admin panel.', 'gold')
    elif t == 'adm':
        from . import admin
        admin.effect(str(m.get('act') or ''), m.get('arg'), str(m.get('from') or 'An admin')[:16])
    elif t == 'pong':
        try:
            st.ping = int((time.time() - float(m.get('at'))) * 1000)
        except (TypeError, ValueError):
            pass


def _auth_ok(m):
    global _retry_t
    st.token = m.get('token') or st.token
    st.user = str(m.get('user') or st.user)
    st.motd = str(m.get('motd') or st.motd)
    st.srvname = str(m.get('server') or st.srvname)
    st.error = ''
    st.status = ''
    SET['server'] = st.server
    SET['user'] = st.user
    if st.remember and st.token:
        SET['remember'] = {'server': st.server, 'user': st.user, 'token': st.token}
    save_settings()
    if st.phase == 'lost':
        st.phase = 'in'
        _retry_t = 0
        Wd.toast('Reconnected!', 'good')
        add_chat('', 'Reconnected.', 'sys')
        if Wd.P is not None:
            Wd.saveProfile()
            flush_save(force=True)
        return
    cloud = Wd.sanitize(m.get('save')) if isinstance(m.get('save'), dict) else None
    backup = Wd.sanitize(settings.read_json(backup_path(), None))
    pick = cloud
    if backup is not None and (cloud is None or (backup.rev or 0) > (cloud.rev or 0)):
        pick = backup
    if pick is not None:
        begin_play(pick)
    else:
        st.phase = 'newangler'
        st.newangler = True


def shutdown():
    """The window is closing: send the last save and hang up."""
    if active():
        Wd.saveProfile()
        flush_save(force=True)
    if conn:
        conn.close(flush=True, wait=1.5)
