# worldcupx — Project Memory

**Last updated:** 2026-06-13 (tournament underway, matchday 1 ~complete)
**Repo:** https://github.com/chrisdell88/worldcupx
**Live:** worldcupx.co (GitHub Pages; HTTP live, HTTPS cert still provisioning)

## Current state — v2 SHIPPED (live results)
Tabs: RANKINGS · STANDINGS · GROUPS · MATCHUPS · FUTURES · METHODOLOGY
- **8 weighted systems** now (The Athletic added — Chris pasted the 1-48 list). T1×3: PELE, ELO, FIFA. T2×1: LALAS, BR, YAH, SPNET, ATH. Compare-only T3: ESPN(15), OPTA(partial).
- X-Score: Spain #1, Argentina, France, England, Brazil top 5.
- **Live results pipeline** (no server infra needed for visitors):
  - Client-side ESPN fetch (CORS-open) overlays live + just-finished scores, refreshes 60s.
  - STANDINGS + accuracy chip recompute **client-side** from baked results + live overlay → site self-updates for every visitor.
  - Scrolling results ticker, FT/LIVE badges, scores, winner ▸, X-SCORE ✓/UPSET tags, next-kickoff countdown banner, goal-flash.
- **FUTURES:** 20k-sim Monte Carlo (compute_xscore.py) — WIN GROUP / REACH KO / TITLE odds. Spain 27% / Argentina 21% / France 15%. Seeded-knockout approx until bracket is known.
- Accuracy through matchday 1: X-Score 5/7.

## Data pipeline
- `refresh.py` — pulls fixturedownload (completed) + ESPN sweep (live + patches FT the feed missed), writes live.json, recomputes. **Run this to bake fresh results, then commit+push.**
- `compute_xscore.py` — X-Score + standings + accuracy + futures sim → data.js + xscore.json.
- `name_map.py` — 48-team normalization (handles ESPN/feed spellings).
- `sources/*.json` — one per system; teams.json (groups), fixtures_raw.json (schedule+scores), live.json.

## ⚠️ OPEN ITEMS
1. **HTTPS cert** — not provisioned after several hours (DNS + CAA all correct, Let's Encrypt allowed; just GitHub's queue). Background waiter armed to enable enforcement when it lands. If still stuck tomorrow: repo Settings → Pages → remove custom domain, re-add `worldcupx.co` to force re-provision.
2. **GitHub Actions auto-refresh cron** — `.github/workflows/refresh.yml` is written but **gitignored & unpushed** because the `gh` OAuth token lacks `workflow` scope. To enable hands-off cron: run `gh auth refresh -h github.com -s workflow`, then `git rm .gitignore entry` / force-add the file and push. Until then: client-side fetch keeps visitors live; run `python3 refresh.py && git commit && git push` manually to bake history.
3. **Weekly X-Score re-pull** (deferred per Chris) — re-fetch Elo/FIFA/media weekly to refresh the frozen index. Not urgent.
4. **Knockout bracket simulator** (deferred until group stage ends ~June 27) — then build real bracket + replace futures' seeded-knockout approximation.

## Methodology notes
- Z-score over 48-team field; raw values for PELE/ELO/FIFA, inverted ranks for media.
- X-Spread = z-diff × 0.9 goals. Win% = logistic(0.95 × z-diff).
- Futures: twin-Poisson scorelines (total 2.6 xG split by spread), top-2 + 8 best thirds advance, RNG seeded(42) for stable numbers between refreshes.
- Accuracy: non-draw correct if favorite avoids defeat; draw correct if |spread|<0.75.

## Environment quirks
- gh token scopes: gist, read:org, repo (NO workflow). SSH not set up (publickey denied).
- Chrome MCP can't navigate localhost/fifa.com/worldcupx.co (allowlist); godaddy worked.
- Claude_Preview: use `sh -c 'cd ... && python3 -m http.server'` in .claude/launch.json.
- Permission mode is per-session; global settings.json has bypassPermissions but session UI overrides — Chris must pick "Bypass permissions" in the session selector.
