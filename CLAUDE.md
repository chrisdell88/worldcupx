# WorldCupX — World Cup 2026 Composite Power Index

## PROJECT OVERVIEW
Interactive World Cup 2026 dashboard at **worldcupx.co**. Direct sibling of bracketx.co
(NCAA tournament version) — same architecture, styling, and composite methodology, adapted
for the 48 national teams of the 2026 FIFA World Cup.

~12 ranking systems are z-score standardized and combined into one composite **X-Score**
per team. Systems with raw rating values (Elo points, SPI-style ratings) are z-scored on
the raw values; rank-only systems are standardized from ordinal position.

## TECH STACK (same as bracketx)
- Single HTML file (`index.html`) with inline React via CDN (react 18.2.0, react-dom 18.2.0)
- React.createElement, NOT JSX — there is no build step
- All data inlined as JS arrays in the HTML file
- Hosted on GitHub Pages, custom domain via `CNAME` (worldcupx.co, DNS at GoDaddy)
- Push to `main` → live in ~2 minutes

## CRITICAL RULES (inherited from bracketx)
- NEVER full-rewrite the production HTML once shipped — surgical edits only
- All backgrounds explicit dark (#0d1117 / #0e1218) — never "transparent" on containers
- All data is real and verified from sources — NEVER estimate or fabricate ratings
- Fonts: Outfit 900 (logo), DM Mono (data)
- Colors: bg #0d1117, cyan #00d4ff, green #00e676, red #ff4444, gold #ffd600, orange #ff6b35

## DATA PIPELINE
- `scraper.py` — scrapes ranking-system URLs → `scraped_ranks.json`
- `name_map.py` — national team name normalization (FIFA vs Elo vs media spellings)
- User-provided CSV fills gaps scrapers can't reach
- All 48 World Cup teams must be present in every weighted system — no partial coverage

## METHODOLOGY
- Per system: z-score across the 48-team field (raw values where available, ranks otherwise)
- Composite X-Score = weighted average of system z-scores
- X-Spread for matchups = X-Score differential × scaling factor (calibrate vs bookmaker lines)
