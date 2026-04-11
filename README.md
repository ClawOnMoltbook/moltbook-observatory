# Moltbook Observatory

Public observatory for Moltbook metrics, activity, and evolving social patterns.

## What it does
- Collects public Moltbook snapshots
- Stores them locally in SQLite
- Generates a public JSON payload
- Serves a static dashboard suitable for GitHub Pages

## Main files
- `moltbook_snapshot.py` — fetches public snapshots and stores them
- `generate_moltbook_dashboard.py` — builds `public/data/latest.json`
- `public/` — static site for GitHub Pages

## Local usage
```bash
python3 moltbook_snapshot.py
python3 generate_moltbook_dashboard.py
```

## Publish with GitHub Pages
Push this repository to GitHub and enable Pages from the main branch `/public` folder, or use a GitHub Actions deployment flow.
