# worldcupx — Project Memory

**Last updated:** 2026-06-11 (project created ~12h before first match of World Cup 2026)
**Repo:** https://github.com/chrisdell88/worldcupx
**Live:** worldcupx.co (GitHub Pages, CNAME committed; GoDaddy DNS setup pending)

## Current state
- Repo scaffolded: placeholder index.html (dark WORLDCUPX landing), CNAME, CLAUDE.md
- Waiting on Chris for: list of ~12 ranking-system URLs + one CSV he has locally
- Goal: as much of the bracketx feature set as possible before first kickoff
  (priority order: rankings table → methodology → match cards → bracket/futures later)

## Key decisions
- Same architecture as bracketx: single-file React-via-CDN, data inlined, GitHub Pages
- Z-score normalization: raw rating values where systems provide them, ordinal ranks otherwise (mix confirmed by Chris)
- Domain worldcupx.co owned at GoDaddy

## Next steps
1. Chris provides ranking URLs + CSV → build scraper.py + name_map.py
2. Compute X-Score composite for 48 teams
3. Build rankings dashboard from bracketx template
4. GoDaddy DNS: A records → GitHub Pages IPs, then enable HTTPS enforcement
