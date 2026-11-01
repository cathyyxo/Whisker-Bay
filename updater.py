"""Check GitHub Releases and safely apply Whisker Bay updates."""
import ast
import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
import urllib.error
import urllib.request
import zipfile

OWNER = 'cathyyxo'
REPOSITORY = 'Whisker-Bay'
ASSET_NAME = 'Whisker-Bay.zip'
API_URL = f'https://api.github.com/repos/{OWNER}/{REPOSITORY}/releases/latest'
MAX_DOWNLOAD = 100 * 1024 * 1024
MAX_UNPACKED = 200 * 1024 * 1024
MAX_FILES = 500
ROOT_FILES = {
    'Play Whisker Bay.bat',
    'Play Whisker Bay.command',
    'play.py',
    'play.sh',
    'READ ME FIRST.txt',
    'SAVE DATA NOTE.txt',
    'server.py',
    'server_settings.json',
    'Start Server.bat',
    'Start Server.command',
    'start_server.sh',
    'updater.py',
}
PACKAGE_EXTENSIONS = {'.py', '.ttf', '.txt', '.json', '.png', '.jpg', '.jpeg', '.ogg', '.wav'}
VERSION_RE = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)$')


class UpdateError(Exception):
    """An update could not be verified or installed safely."""


class FatalUpdateError(UpdateError):
    """The updater could not restore the previous files after an install error."""


def _installed_version(root):
    init_path = os.path.join(root, 'whiskerbay', '__init__.py')
    with open(init_path, encoding='utf-8') as source:
        tree = ast.parse(source.read(), filename=init_path)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == '__version__'
            for target in node.targets
        ) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    raise UpdateError('Could not read the installed game version.')


def _version_tuple(version):
    match = VERSION_RE.fullmatch(str(version))
    if not match:
        raise UpdateError(f'Invalid release version: {version!r}.')
    return tuple(int(part) for part in match.groups())


def _request(url, accept, limit):
    request = urllib.request.Request(
        url,
        headers={
            'Accept': accept,
            'User-Agent': 'WhiskerBay-Updater',
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise UpdateError('The update download is larger than the allowed size.')
    return payload


def _release_info():
    try:
        payload = _request(API_URL, 'application/vnd.github+json', 2 * 1024 * 1024)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    try:
        release = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UpdateError('GitHub returned invalid release information.') from error
    if not isinstance(release, dict) or release.get('draft') or release.get('prerelease'):
        raise UpdateError('GitHub returned an invalid stable release.')
    return release


def _asset(release):
    assets = release.get('assets')
    if not isinstance(assets, list):
        raise UpdateError('The GitHub release has no usable asset list.')
    for asset in assets:
        if isinstance(asset, dict) and asset.get('name') == ASSET_NAME:
            url = asset.get('browser_download_url')
            digest = asset.get('digest')
            if not isinstance(url, str) or not url.startswith('https://'):
                raise UpdateError('The release update asset has an invalid download URL.')
            if not isinstance(digest, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
                raise UpdateError('GitHub did not provide a SHA-256 digest for the update asset.')
            return url, digest.split(':', 1)[1]
    raise UpdateError(f'The latest GitHub release is missing {ASSET_NAME}.')


def _safe_member(name):
    if not name or '\\' in name or ':' in name or name.startswith('/'):
        raise UpdateError(f'Unsafe path in update archive: {name!r}.')
    parts = name.split('/')
    if any(part in ('', '.', '..') for part in parts):
        raise UpdateError(f'Unsafe path in update archive: {name!r}.')
    if parts[0] == 'whiskerbay':
        if len(parts) < 2 or any(part in ('__pycache__', '.venv') for part in parts):
            raise UpdateError(f'Unsafe path in update archive: {name!r}.')
        if os.path.splitext(parts[-1])[1].lower() not in PACKAGE_EXTENSIONS:
            raise UpdateError(f'Unsupported file in update archive: {name!r}.')
        return parts
    is_release_notes = (
        parts[0].lower().endswith('.txt')
        and parts[0].startswith(('FRIENDS EDITION ', 'WHATS NEW '))
    )
    if len(parts) != 1 or (parts[0] not in ROOT_FILES and not is_release_notes):
        raise UpdateError(f'Unexpected file in update archive: {name!r}.')
    return parts


def _extract_archive(payload, staging):
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except (OSError, zipfile.BadZipFile) as error:
        raise UpdateError('The downloaded update is not a valid ZIP file.') from error

    extracted = []
    total_size = 0
    seen = set()
    with archive:
        members = archive.infolist()
        if len(members) > MAX_FILES:
            raise UpdateError('The update archive contains too many files.')
        for member in members:
            if member.is_dir():
                continue
            parts = _safe_member(member.filename)
            if parts[0] in ('saves', 'server_data', '.venv'):
                raise UpdateError('The update archive contains user data or environment files.')
            if member.filename in seen:
                raise UpdateError(f'The update archive contains a duplicate path: {member.filename!r}.')
            seen.add(member.filename)
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise UpdateError(f'The update archive contains a symbolic link: {member.filename!r}.')
            if member.file_size < 0:
                raise UpdateError('The update archive contains an invalid file size.')
            total_size += member.file_size
            if total_size > MAX_UNPACKED:
                raise UpdateError('The unpacked update is larger than the allowed size.')
            destination = os.path.join(staging, 'files', *parts)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            try:
                with archive.open(member) as source, open(destination, 'wb') as target:
                    shutil.copyfileobj(source, target)
            except (OSError, RuntimeError, zipfile.BadZipFile) as error:
                raise UpdateError(f'Could not unpack {member.filename!r}.') from error
            extracted.append((parts, destination))
    if not extracted:
        raise UpdateError('The update archive contains no game files.')
    return extracted


def _install(payload, root):
    staging = tempfile.mkdtemp(prefix='.whiskerbay-update-', dir=root)
    extracted = []
    changed = []
    keep_staging = False
    try:
        extracted = _extract_archive(payload, staging)
        backup_root = os.path.join(staging, 'backup')
        try:
            for parts, staged_file in extracted:
                # Per-machine server settings are initialized by the starter ZIP and never overwritten.
                if parts == ['server_settings.json']:
                    continue
                destination = os.path.join(root, *parts)
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                backup = None
                if os.path.exists(destination):
                    backup = os.path.join(backup_root, *parts)
                    os.makedirs(os.path.dirname(backup), exist_ok=True)
                    shutil.copy2(destination, backup)
                changed.append((destination, backup))
                os.replace(staged_file, destination)
        except OSError as error:
            rollback_errors = []
            for destination, backup in reversed(changed):
                try:
                    if backup is not None and os.path.exists(backup):
                        os.replace(backup, destination)
                    elif os.path.exists(destination):
                        os.remove(destination)
                except OSError as rollback_error:
                    rollback_errors.append(f'{destination}: {rollback_error}')
            if rollback_errors:
                detail = '; '.join(rollback_errors)
                keep_staging = True
                raise FatalUpdateError(
                    f'Update failed and rollback was incomplete: {detail}. '
                    f'Recovery files were kept at {staging}.'
                ) from error
            raise UpdateError(f'Could not install the update; the previous files were restored: {error}') from error
    finally:
        if not keep_staging:
            try:
                shutil.rmtree(staging)
            except OSError as error:
                print(f'Warning: could not remove temporary update files at {staging}: {error}')


def check_for_updates(root=None):
    """Install the latest stable release if a newer one is available."""
    root = os.path.abspath(root or os.path.dirname(__file__))
    installed = _installed_version(root)
    try:
        release = _release_info()
    except (urllib.error.URLError, TimeoutError, OSError, UpdateError) as error:
        print(f'Update check unavailable ({error}). Starting installed version {installed}.')
        return False
    if release is None:
        print(f'No game release is published yet. Starting installed version {installed}.')
        return False

    tag = release.get('tag_name')
    if not isinstance(tag, str):
        print('Update check failed (release has no version tag). Starting installed version.')
        return False
    try:
        if _version_tuple(tag) <= _version_tuple(installed):
            print(f'Whisker Bay {installed} is up to date.')
            return False
        url, expected_digest = _asset(release)
        print(f'Whisker Bay {tag} is available. Downloading update...')
        payload = _request(url, 'application/octet-stream', MAX_DOWNLOAD)
        actual_digest = hashlib.sha256(payload).hexdigest()
        if actual_digest != expected_digest:
            raise UpdateError('The update SHA-256 digest does not match GitHub release metadata.')
        _install(payload, root)
    except FatalUpdateError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError, UpdateError) as error:
        print(f'Update was not applied ({error}). Starting installed version {installed}.')
        return False
    print(f'Updated Whisker Bay to {tag}.')
    return True
