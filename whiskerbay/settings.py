"""Where files live, and the player's settings (keys, volume, server address...)."""
import copy
import json
import os
import tempfile

from .data import DEFAULT_KEYS

GAME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(PKG_DIR, 'fonts')


def _pick_save_dir():
    """Saves live next to the game in a 'saves' folder. If that folder can't be written
    (for example the game sits somewhere read-only), fall back to the home folder."""
    for d in (os.path.join(GAME_DIR, 'saves'), os.path.join(os.path.expanduser('~'), '.whiskerbay', 'saves')):
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, '.write_test')
            with open(probe, 'w') as f:
                f.write('ok')
            os.remove(probe)
            return d
        except OSError:
            continue
    return os.path.join(GAME_DIR, 'saves')


SAVE_DIR = _pick_save_dir()
SETTINGS_FILE = os.path.join(SAVE_DIR, 'settings.json')


def write_json(path, data):
    """Write JSON safely: to a temp file first, then swap it in, so a crash never leaves half a save."""
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.tmp-', dir=d)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        os.replace(tmp, path)
        return True
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False


def read_json(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


DEFAULTS = {
    'binds': copy.deepcopy(DEFAULT_KEYS),
    'vol': 0.8,
    'muted': False,
    'shake': True,
    'sonarNames': True,
    'fullscreen': False,
    'showFps': False,
    'server': 'localhost:7777',
    'user': '',
    'remember': None,   # {'server', 'user', 'token'} when "keep me logged in" is on
    'chatFade': True,
    'seenPatchNotes': None,
}


def _load():
    s = copy.deepcopy(DEFAULTS)
    got = read_json(SETTINGS_FILE, None)
    if isinstance(got, dict):
        for k, v in got.items():
            if k in s:
                s[k] = v
        binds = copy.deepcopy(DEFAULT_KEYS)
        saved = got.get('binds') if isinstance(got.get('binds'), dict) else {}
        for a, keys in saved.items():
            if a in binds and isinstance(keys, list):
                binds[a] = [k for k in keys if isinstance(k, str)][:2]
        if saved.get('skill') == ['z'] and saved.get('dex') == ['f']:
            binds['skill'] = list(DEFAULT_KEYS['skill'])
            binds['dex'] = list(DEFAULT_KEYS['dex'])
        # actions added in a newer version keep their default keys only if nothing else already uses them
        used = {k for a, keys in saved.items() if a in binds for k in binds[a]}
        for a in binds:
            if a not in saved:
                binds[a] = [k for k in binds[a] if k not in used]
        s['binds'] = binds
    return s


SET = _load()


def save_settings():
    write_json(SETTINGS_FILE, SET)
