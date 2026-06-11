# worldcupx — Project Memory

**Last updated:** 2026-06-11 (launched hours before WC2026 opening match)
**Repo:** https://github.com/chrisdell88/worldcupx
**Live:** worldcupx.co (GitHub Pages; HTTP live, HTTPS cert provisioning → enforce when ready)

## Current state — SHIPPED v1
- Dashboard live: RANKINGS (48 teams, 9 system columns, diff highlights, ratings key modal),
  GROUPS (12 cards sorted by strength, toughest/softest badges), MATCHUPS (72 group fixtures,
  X-Spread + win% + score-ready cards, matchday sub-tabs), METHODOLOGY.
- X-Score v1 computed 2026-06-11: Spain #1 (+1.91), Argentina, France, England, Brazil top 5; Curacao #48.
- GoDaddy DNS done via browser takeover: deleted parked A record, added 4 GitHub Pages A records,
  www CNAME → chrisdell88.github.io. pay/_domainconnect/dmarc records left untouched.

## Data pipeline
- `sources/*.json` — one file per system. Complete weighted (7): PELE (Nate Silver CSV from Chris),
  ELO (eloratings.net World.tsv), FIFA (points via Transfermarkt mirror, FIFA's own API serves stale data),
  LALAS (Fox), BR (Bleacher), YAH (Yahoo), SPNET (Sportsnet — scraped via curl; their #29 needed manual fix).
- Partial/compare T3 (2): ESPN (top-15 panel by design), OPTA (article only discloses ~6 ratings + ~19 global ranks).
- Pending (1): ATH (The Athletic 1-48, hard paywall) — **Chris to paste list**, then it auto-joins T2.
- `sources/teams.json` — 48 teams + groups A-L (FIFA draw 2025-12-05). PELE CSV's 🏆 flags = exactly the 48 qualifiers (validation trick).
- `sources/fixtures_raw.json` — fixturedownload.com/feed/json/fifa-world-cup-2026 (has score fields; re-fetch for tracker updates).
- `compute_xscore.py` → `data.js` + `xscore.json`. `name_map.py` = alias normalization.

## Methodology decisions (v1)
- Z-score over the 48-team field. Raw values for PELE/ELO/FIFA (T1, 3x weight); inverted ordinal ranks
  for media lists (T2, 1x). Partial systems excluded from composite (no partial coverage rule, per bracketx).
- X-Spread = z-diff × 0.9 goals (rough calibration vs opening lines; revisit after MD1 closing lines).
- Win% = logistic(0.95 × z-diff).

## Refresh workflow (between matchdays)
1. `curl -s "https://fixturedownload.com/feed/json/fifa-world-cup-2026" -o sources/fixtures_raw.json` (brings scores)
2. Re-scrape any updated systems (media lists update between rounds)
3. `python3 compute_xscore.py`
4. `git add -A && git commit && git push` → live in ~2 min

## Next tasks
- Get Athletic 1-48 list from Chris → sources/athletic.json → recompute
- Confirm HTTPS enforced (background job may have done it)
- Knockout bracket simulator + futures probabilities (BracketX-style) during group stage
- Calibrate X-Spread factor vs MD1 closing lines
- og-image / favicon assets (none yet)

## Environment notes
- This Mac's Chrome MCP can't navigate to localhost/fifa.com/worldcupx.co (domain allowlist); godaddy.com worked.
- Claude_Preview panel works via sh -c trick in .claude/launch.json (python http.server direct hits sandbox error).
- Background subagents have no web/Bash permissions — do scraping in main loop.
