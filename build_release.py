"""Build a clean Whisker Bay ZIP for GitHub Releases and first-time installs."""
import argparse
import ast
import json
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_FILES = (
    'Play Whisker Bay.bat',
    'Play Whisker Bay.command',
    'play.py',
    'play.sh',
    'READ ME FIRST.txt',
    'SAVE DATA NOTE.txt',
    'server.py',
    'Start Server.bat',
    'Start Server.command',
    'start_server.sh',
    'updater.py',
    'WHATS NEW 1.7.0.txt',
)
SERVER_SETTINGS = {
    '_how_to': 'Optional: set an invite code here before starting the server. Default port matches the game client.',
    'port': 7777,
    'invite': '',
    'name': 'Whisker Bay',
    'motd': 'Welcome to the bay! Be nice, fish hard.',
}
ALLOWED_PACKAGE_EXTENSIONS = {'.py', '.ttf', '.txt', '.json', '.png', '.jpg', '.jpeg', '.ogg', '.wav'}


def version():
    path = os.path.join(HERE, 'whiskerbay', '__init__.py')
    with open(path, encoding='utf-8') as source:
        tree = ast.parse(source.read(), filename=path)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == '__version__'
            for target in node.targets
        ) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    raise RuntimeError('Could not determine the game version from whiskerbay/__init__.py.')


def package_files():
    files = []
    root_files = list(ROOT_FILES)
    root_files.extend(
        name for name in os.listdir(HERE)
        if name.lower().endswith('.txt')
        and name.startswith(('FRIENDS EDITION ', 'WHATS NEW '))
        and os.path.isfile(os.path.join(HERE, name))
    )
    for name in sorted(set(root_files)):
        path = os.path.join(HERE, name)
        if not os.path.isfile(path):
            raise FileNotFoundError(f'Required release file is missing: {name}')
        files.append((path, name))
    for parent, directories, names in os.walk(os.path.join(HERE, 'whiskerbay')):
        directories[:] = sorted(
            name for name in directories
            if name not in ('__pycache__', '.venv') and not name.startswith('.')
        )
        for name in sorted(names):
            extension = os.path.splitext(name)[1].lower()
            if extension not in ALLOWED_PACKAGE_EXTENSIONS or name.endswith('.pyc'):
                continue
            path = os.path.join(parent, name)
            relative = os.path.relpath(path, HERE).replace(os.sep, '/')
            files.append((path, relative))
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', help='Output ZIP path (default: dist/Whisker-Bay.zip)')
    args = parser.parse_args()
    release_version = version()
    output = args.output or os.path.join(HERE, 'dist', 'Whisker-Bay.zip')
    output = os.path.abspath(output)
    os.makedirs(os.path.dirname(output), exist_ok=True)

    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, relative in package_files():
            archive.write(path, relative)
        archive.writestr(
            'server_settings.json',
            json.dumps(SERVER_SETTINGS, indent=2) + '\n',
        )

    print(f'Built Whisker Bay {release_version}: {output}')
    print('This clean package excludes saves, server_data, virtual environments, and Python caches.')
    print('Upload this ZIP as the Whisker-Bay.zip asset on the matching GitHub Release.')


if __name__ == '__main__':
    main()
