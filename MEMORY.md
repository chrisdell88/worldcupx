# worldcupx — Project Memory

**Last updated:** 2026-06-14 (matchday 2 starting; group stage in progress)
**Repo:** https://github.com/chrisdell88/worldcupx
**Live:** worldcupx.co (GitHub Pages; HTTP live, HTTPS cert still provisioning — see open items)

## Current state — v3 SHIPPED (reviewed + calibrated + branded)
Tabs: RANKINGS · STANDINGS · GROUPS · MATCHUPS · FUTURES · ABOUT(methodology)
- **8 weighted systems**: PELE/ELO/FIFA (T1×3) + LALAS/BR/YAH/SPNET/ATH (T2×1). Compare-only: ESPN(15), OPTA(partial). X-Score: Spain #1.
- **Live results**: client-side ESPN fetch overlays live/just-finished scores (60s); STANDINGS + accuracy recompute in-browser; ticker, FT/LIVE badges, winner ▸, X-SCORE ✓/UPSET, next-kickoff countdown, goal-flash. Accuracy 5/7.
- **FUTURES**: 20k Monte Carlo (WIN GROUP / REACH KO / TITLE). Spain ~27%.
- **Branding**: favicon.svg + PNGs, apple-touch-icon, og-image (1200×630), OG/Twitter meta. Rendered via macOS `qlmanage` (no PIL/rsvg/convert available; `sips` for crop).

## Full-scale review (2026-06-14) — DONE, fixes applied
Ran 3 parallel agents (code/security, data integrity, QA/UX). Data verdict: SOLID (groups, standings, X-Score math, 5/7 accuracy all verified by hand). Applied P1+P2+P3:
- FIFA standings tiebreaker (overall pts/GD/GF → head-to-head → X-rank; "≈" tied hint) in Python + mirrored client-side
- crash guards (sd==0, empty weighted set, missing data.js → fail-loud not blank)
- staleness badge on repeated ESPN-fetch failure
- fixed dead goal-flash CSS; dropped broken sticky headers
- ticker speed scales w/ count; abbreviated names; Matchups auto-opens current matchday; tz labels; tap tooltips; ABOUT tab; tab scroll-hint
- aligned accuracy wording with code (favorite wins outright; draw correct only if line <0.75)
P4 (deferred, minor): footer link target, deep-link tabs, data.js fetch-vs-script, Windows flag rendering.

## X-Spread calibration — DONE
`calibrate.py` fits the factor to DraftKings Asian-handicap lines (from ESPN, no account) across 65 fixtures: **0.74 goals/z-unit** (was 0.9), RMSE 0.53→0.47. Market mean total 2.56 ≈ our 2.6. Applied to X-Spread + futures sim.

## Data pipeline
- `refresh.py` — fixturedownload (completed) + ESPN sweep (live + FT patch) → live.json → recompute. Run then commit+push to bake history.
- `compute_xscore.py` — X-Score + standings(H2H) + accuracy + 20k futures sim → data.js + xscore.json.
- `calibrate.py` — one-off spread calibration vs ESPN/DraftKings lines.
- `name_map.py` — 48-team normalization. `sources/*.json` — systems + teams.json + fixtures_raw.json + live.json.
- ESPN odds: `competitions[].odds[0]` has `pointSpread.home.{open,close,current}.line` (Asian handicap), `moneyline`, `total`, `overUnder`. CORS-open, no key.

## ⚠️ OPEN ITEMS
1. **HTTPS cert** — still not issued after ~12h (DNS/CAA correct, domain verified, Let's Encrypt allowed). Git-side CNAME remove/re-add is a NO-OP (Pages keeps the domain setting). It's GitHub's auto-provision queue; completes within 24h. Watcher armed to enable enforcement on issue. Manual force (if still stuck >24h): repo Settings → Pages → clear custom domain, save, re-enter `worldcupx.co`, save (briefly 404s the apex). Do NOT delete/recreate Pages on a live site.
2. **GitHub Actions cron** — `.github/workflows/refresh.yml` written but gitignored & unpushed (gh token lacks `workflow` scope). To enable: `gh auth refresh -h github.com -s workflow`, then un-gitignore + push. Not blocking — client-side fetch keeps visitors live; run refresh.py + push manually to bake history.
3. **Weekly X-Score re-pull** (deferred per Chris).
4. **Knockout bracket** (deferred until group stage ends ~June 27) — then real bracket + replace futures' seeded-knockout approximation.
5. Possible later: live BOOK-odds column (ESPN moneyline/spread) like bracketx; win% recalibration vs market 3-way ML.

## Environment quirks
- gh token scopes: gist, read:org, repo (NO workflow). SSH not set up (publickey denied).
- Chrome MCP can't navigate localhost/fifa.com/worldcupx.co (allowlist); godaddy worked.
- Claude_Preview: `sh -c 'cd ... && python3 -m http.server 4173'` in .claude/launch.json.
- Image tooling: no PIL/cairosvg/rsvg/convert; use `qlmanage -t -s N -o dir file.svg` (pre-create dir) + `sips -c H W` to crop.
- Permission mode is per-session; global settings.json has bypassPermissions but the session UI overrides — Chris must pick "Bypass permissions" in the session selector.
