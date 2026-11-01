#!/usr/bin/env python3
"""
Start Whisker Bay.

    python play.py

The first time, this installs the one thing the game needs: pygame-ce, a free game library.
"""
import importlib
import os
import subprocess
import sys

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

HERE = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(HERE, '.venv')


def pause_and_exit(code=1):
    try:
        input('\nPress Enter to close this window...')
    except (EOFError, KeyboardInterrupt):
        pass
    sys.exit(code)


def have_pygame():
    try:
        importlib.import_module('pygame')
        return True
    except ImportError:
        return False


def venv_python():
    p = os.path.join(VENV, 'Scripts', 'python.exe') if os.name == 'nt' else os.path.join(VENV, 'bin', 'python')
    return p if os.path.exists(p) else None


def run_in_venv():
    """If the game's private environment exists (and we're not already in it), run the game from there."""
    vp = venv_python()
    if vp and os.path.abspath(sys.executable) != os.path.abspath(vp):
        sys.exit(subprocess.call([vp, os.path.abspath(__file__)] + sys.argv[1:]))


def pip_install():
    in_venv = sys.prefix != getattr(sys, 'base_prefix', sys.prefix)
    attempts = []
    if not in_venv:
        attempts.append([sys.executable, '-m', 'pip', 'install', '--user', 'pygame-ce'])
    attempts.append([sys.executable, '-m', 'pip', 'install', 'pygame-ce'])
    for cmd in attempts:
        try:
            if subprocess.call(cmd) == 0:
                try:
                    import site
                    site.addsitedir(site.getusersitepackages())
                except (AttributeError, OSError):
                    pass
                importlib.invalidate_caches()
                return True
        except OSError:
            continue
    return False


def make_venv():
    print('\nSetting up a private Python environment for the game (folder ".venv")...')
    try:
        if subprocess.call([sys.executable, '-m', 'venv', VENV]) != 0:
            return False
        vp = venv_python()
        return bool(vp) and subprocess.call([vp, '-m', 'pip', 'install', 'pygame-ce']) == 0
    except OSError:
        return False


def main():
    if sys.version_info < (3, 8):
        print('Whisker Bay needs Python 3.8 or newer. Get it free from https://www.python.org/downloads/')
        pause_and_exit()
    from updater import FatalUpdateError, check_for_updates
    try:
        check_for_updates(HERE)
    except FatalUpdateError as e:
        print(f'\nWhisker Bay could not recover safely from an update error: {e}')
        pause_and_exit()
    if not have_pygame():
        run_in_venv()
        print('First time setup: installing pygame-ce (the free game library Whisker Bay uses).')
        print('This needs the internet once and takes about a minute...\n')
        if not pip_install() or not have_pygame():
            if make_venv():
                run_in_venv()
            print('\nCould not install pygame-ce automatically.')
            print('Open a terminal / command prompt in this folder and run:')
            print(f'    "{sys.executable}" -m pip install pygame-ce')
            print('then start the game again. (On Linux you may need: sudo apt install python3-venv python3-pip)')
            pause_and_exit()
    sys.path.insert(0, HERE)
    os.chdir(HERE)
    try:
        from whiskerbay.game import run
        run()
    except Exception:
        import traceback
        traceback.print_exc()
        print('\nWhisker Bay crashed. Your progress up to the last autosave is safe in the "saves" folder.')
        print('If this keeps happening, send the text above to whoever gave you the game.')
        pause_and_exit()


if __name__ == '__main__':
    main()
