---
name: moltbook-observatory-check
description: Review the health and freshness of the public Moltbook Observatory dashboard, GitHub Actions automation, published JSON data, and visible panel output. Use when the user says things like "revisa", asks to check whether the Moltbook observatory is updating correctly, wants a maintenance pass on the panel, or wants a quick diagnostic of dashboard freshness, workflow execution, public URL status, charts, or data consistency.
---

# Moltbook Observatory Check

Review the observatory in this order and reply with a short diagnosis.

## 1. Check the public panel

Open and verify:
- `https://clawonmoltbook.github.io/moltbook-observatory/`
- `https://clawonmoltbook.github.io/moltbook-observatory/data/latest.json`

Confirm:
- the page loads
- the JSON loads
- the JSON timestamps are recent enough for the configured cadence
- the panel appears to be using the same data snapshot shown in the JSON

## 2. Check the configured cadence

Read the repository files when needed:
- `.github/workflows/update-dashboard.yml`
- `generate_moltbook_dashboard.py`
- `public/index.html`
- `public/app.js`

Confirm:
- the GitHub Actions cron matches the intended cadence
- the panel wording matches the actual cadence
- no obvious mismatch exists between automation and UI text

## 3. Check the repository automation state

Inspect the GitHub repo and recent state using available web/API access when possible.

Look for:
- whether recent commits to dashboard data exist
- whether GitHub Pages is still serving the expected branch/path
- whether the workflow seems to have run recently enough

If GitHub workflow run status is not directly available, say so clearly and fall back to checking freshness via commits and public output.

## 4. Check content sanity

Look for obvious issues in the public JSON and panel:
- missing or empty sections
- stale timestamps
- obviously broken charts because of missing history
- impossible or suspiciously malformed values
- broken links for posts or agent profiles in the rendered data

Do not overreact to short daily-history series when the panel is still young.

## 5. Reply format

Use this structure:

- **Estado general:** OK / atención / roto
- **Última actualización visible:** ...
- **Cadencia configurada:** ...
- **Panel público:** ...
- **Datos JSON:** ...
- **Automatización:** ...
- **Problemas detectados:** ...
- **Acción recomendada:** ...

Keep it concise but specific.

## 6. If something is wrong

Prioritize fixes in this order:
1. public JSON not updating
2. workflow cadence mismatch
3. panel text mismatch
4. broken links or empty sections
5. cosmetic issues

When a fix is obvious and low-risk, apply it directly. Otherwise explain the issue and propose the smallest next step.
