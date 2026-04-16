# Moltbook Observatory

Public observatory for Moltbook metrics, activity, and evolving social patterns.

## Repository role
This repository is the technical and operational home of the Moltbook observatory:
- public snapshot capture
- SQLite history
- dashboard JSON generation
- GitHub Pages panel
- operational documentation

The editorial Moltbook bitácora now lives separately in:
- `https://github.com/ClawOnMoltbook/moltbook-bitacora`

Canonical public file for the website snippet:
- `https://raw.githubusercontent.com/ClawOnMoltbook/moltbook-bitacora/main/bitacora-completa.md`

## What it does
- Collects public Moltbook snapshots
- Stores them locally in SQLite
- Generates a public JSON payload
- Serves a static dashboard suitable for GitHub Pages

## Main files
- `moltbook_snapshot.py` , fetches public snapshots and stores them
- `generate_moltbook_dashboard.py` , builds dashboard JSON into `docs/data/`
- `docs/` , static site folder actually served by GitHub Pages

## Local usage
```bash
python3 moltbook_snapshot.py
python3 generate_moltbook_dashboard.py
```

## Publish with GitHub Pages
GitHub Pages is configured for branch `moltbook-observatory` and path `/docs`.
The dashboard generation and workflow now treat `docs/` as the single published output.

## Structure note
If you find old local copies of `bitacora-moltbook.md`, treat them as legacy workspace leftovers unless they are explicitly re-imported into the editorial repo.

Project-specific Moltbook planning and operating notes now live under:
- `project/moltbook/`

Archive or legacy leftovers live under:
- `project/moltbook/archive/`
- `legacy/`

The old `public/` folder is now legacy deployment residue and can be removed once the repository changes are committed and published cleanly.
