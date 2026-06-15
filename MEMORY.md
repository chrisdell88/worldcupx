# worldcupx — Project Memory

**Last updated:** 2026-06-14 (matchday 2 starting; group stage in progress)
**Repo:** https://github.com/chrisdell88/worldcupx
**Live:** worldcupx.co (GitHub Pages; HTTP live, HTTPS cert still provisioning — see open items)

## v5 SHIPPED 2026-06-14 (book odds, PWA, SEO, team deep-dive)
- **Live book odds + EDGE badges**: refresh.py pulls DraftKings Asian-handicap + O/U from ESPN (`pointSpread.home.{open,close,current}.line`, aligned to feed home) → sources/odds.json. compute attaches `fixture.book={spread,total,edge}` (edge = X model − market, goals). Match cards show BOOK line + O/U + an EDGE badge when |edge|≥0.75.
- **PWA**: manifest.webmanifest + icon-192/512 + iOS web-app meta → installable to iPhone home screen (standalone). canonical added.
- **Deep-link tabs**: URL hash routing (#rankings…#about via SLUG map); survives reload + back button; tabs shareable.
- **SEO**: robots.txt, sitemap.xml, WebSite+SportsEvent JSON-LD.
- **Team deep-dive**: click any team (Rankings/Standings) → TeamModal: per-system ranks (all weighted + ESPN), best/worst, live group table (team highlighted), fixtures with results or projected X-Spread from team's perspective.
All verified desktop + mobile, no console errors.

## v7 SHIPPED 2026-06-15 (systems swap)
- **Removed ESPN + OPTA entirely** (no more compare/T3 tier). Deleted espn.json/opta.json.
- **Added The Ringer (ringer.json) + USA TODAY (usatoday.json) to T2 ×1** → now **10 weighted systems** (PELE/ELO ×4; FIFA/LALAS/BR/YAH/SPNET/ATH/RINGER/USAT ×1). USA TODAY is a tiered ranking with ties (stored as-is). The Ringer needed Australia (31st) recovered via a 2nd targeted fetch — first fetch dropped it.
- Ratings Key compare section auto-hides when WCX.compare is empty; methodology updated.
- `computed` date now auto-set each refresh via datetime.date.today().

## v6 SHIPPED 2026-06-14 (richer projections)
- **Win/Draw/Loss probabilities** on match cards: analytic twin-Poisson `outcome_probs(total, sup)` in compute → `fixture.prob={h,d,a}` (uses book O/U when available). Replaced the single misleading win% with a 3-segment W/D/L bar + labels.
- **Standings ADV column**: each team's knockout-reach % from the futures sim.
- **FUTURES "Top Market Edges" board**: upcoming fixtures sorted by |X-Spread − book line|, top 8, shown above the title-odds table.
- Ticker no longer pauses on hover (removed the hover-pause rule per Chris).

## Current state — v4 base (secure, scheduled, reweighted)
Tabs: RANKINGS · STANDINGS · GROUPS · MATCHUPS · FUTURES · ABOUT(methodology)
- **HTTPS LIVE**: cert approved + enforced (forced via `gh api DELETE` then `POST` recreate of the Pages site — the git CNAME toggle was a no-op). http→https 301.
- **Auto-refresh scheduled**: local scheduled task `worldcupx-refresh` (~/.claude/scheduled-tasks/), cron `11 */3 * * *` (every 3h), runs refresh.py + pushes. RUNS ONLY WHILE CLAUDE APP IS OPEN (catches up on launch). For always-on, GitHub Actions still needs `gh auth refresh -s workflow` (open item #2).
- **8 weighted systems, REWEIGHTED 2026-06-14**: T1 core models PELE+ELO **×4**; T2 FIFA+LALAS+BR+YAH+SPNET+ATH **×1**. (Was PELE/ELO/FIFA ×3.) Chris's OWN rankings to be added ~2026-06-15 at T1 ×4 (equal to ELO/PELE) — he'll paste the 48-team list + a label.
- **OPTA REMOVED**: only ~6 of 48 ratings are public (article cites scattered global ranks out of ~200), so the column mis-ranked Haiti/Curacao 5th/6th. Dropped from FILES/T3. opta.json kept in sources/ but unused. Re-add only if full 48 obtained.
- Compare-only: ESPN (top-15). X-Score: Spain #1.
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
1. **Chris's own rankings** — he'll paste the 48-team list (ranks or ratings) + a label (~2026-06-15). Add as sources/<abbr>.json, put in T1 at weight 4.0, recompute, push.
2. **HTTPS — DONE** (cert approved + enforced). Resolved by `gh api DELETE` + `POST` recreate of the Pages site. (Kept for reference: the recreate forces a fresh cert request; git CNAME toggle does NOT.)
3. **GitHub Actions cron (optional upgrade)** — `.github/workflows/refresh.yml` written but gitignored & unpushed (gh token lacks `workflow` scope). The local scheduled task covers refresh while the app is open; for always-on server-side, run `gh auth refresh -h github.com -s workflow`, then un-gitignore + push the workflow file (and optionally disable the local task to avoid double-pushes).
4. **Weekly X-Score re-pull** (deferred per Chris).
5. **Knockout bracket** (deferred until group stage ends ~June 27) — then real bracket + replace futures' seeded-knockout approximation.
6. Possible later: live BOOK-odds column (ESPN moneyline/spread) like bracketx; win% recalibration vs market 3-way ML.

## Environment quirks
- gh token scopes: gist, read:org, repo (NO workflow). SSH not set up (publickey denied).
- Chrome MCP can't navigate localhost/fifa.com/worldcupx.co (allowlist); godaddy worked.
- Claude_Preview: `sh -c 'cd ... && python3 -m http.server 4173'` in .claude/launch.json.
- Image tooling: no PIL/cairosvg/rsvg/convert; use `qlmanage -t -s N -o dir file.svg` (pre-create dir) + `sips -c H W` to crop.
- Permission mode is per-session; global settings.json has bypassPermissions but the session UI overrides — Chris must pick "Bypass permissions" in the session selector.
