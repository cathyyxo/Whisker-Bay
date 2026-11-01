# Whisker Bay

Whisker Bay is a Python game with an optional multiplayer server.

## Publishing a game update

1. Update `__version__` in `whiskerbay/__init__.py`.
2. Update the community-facing release notes.
3. Commit and push the source to `main`.
4. Create and push a matching version tag, such as `v1.6.1`.
5. GitHub Actions checks that the tag matches the game version, builds a clean
   `Whisker-Bay.zip`, and publishes it as a GitHub Release asset.

Players with the updater-enabled package receive that release when they start
the game or server. The updater downloads the complete ZIP and preserves local
saves, server accounts, and server settings.

For a local package build, run:

```powershell
python build_release.py
```

The output is written to `dist/Whisker-Bay.zip`. It excludes save data and
server accounts. Never commit `saves/` or `server_data/`; both are ignored by
Git because they can contain private player information.

All release tags must use `vMAJOR.MINOR.PATCH` and exactly match
`whiskerbay/__version__`.
