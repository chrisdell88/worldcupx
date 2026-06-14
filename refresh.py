#!/usr/bin/env python3
"""WorldCupX live refresh — run by GitHub Actions on a cron during the tournament.

Pulls authoritative completed scores from fixturedownload + fast live/just-finished
scores from ESPN, reconciles them against the fixture list, writes live.json for any
in-progress match, then recomputes data.js (rankings, standings, accuracy).

Stdlib only — no pip install needed in CI.
"""
import json
import os
import sys
import subprocess
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources")
sys.path.insert(0, HERE)
from name_map import normalize

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
FIXTURE_FEED = "https://fixturedownload.com/feed/json/fifa-world-cup-2026"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
# tournament dates to sweep ESPN for live/recent (UTC yyyymmdd). Group stage window.
ESPN_DATES = [f"202606{d:02d}" for d in range(11, 28)] + [f"202607{d:02d}" for d in range(1, 20)]


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def pair_key(a, b):
    return tuple(sorted([a, b]))


def main():
    # 1. authoritative schedule + completed scores
    fixtures = get(FIXTURE_FEED)
    with open(os.path.join(SRC, "fixtures_raw.json"), "w") as f:
        json.dump(fixtures, f)

    # index fixtures by normalized team pair (group stage only)
    by_pair = {}
    for m in fixtures:
        if not m.get("Group"):
            continue
        h, a = normalize(m["HomeTeam"]), normalize(m["AwayTeam"])
        if h and a:
            by_pair[pair_key(h, a)] = m

    # 2. ESPN sweep for live + just-finished (only fetch a few recent dates each run
    #    would be ideal, but a full sweep is cheap and robust against schedule drift)
    live_matches = []
    espn_ft = {}  # pair_key -> (home_norm, hs, as) for FT games ESPN knows
    odds_out = {}  # match number -> {sup, total} (DraftKings line via ESPN)
    for date in ESPN_DATES:
        try:
            d = get(f"{ESPN}?dates={date}")
        except Exception:
            continue
        for ev in d.get("events", []):
            comps = ev.get("competitions") or []
            if not comps:
                continue
            comp = comps[0]
            st = comp.get("status", {}).get("type", {})
            cs = comp.get("competitors") or []
            if not st or len(cs) < 2:
                continue
            try:
                hc = next(c for c in cs if c["homeAway"] == "home")
                ac = next(c for c in cs if c["homeAway"] == "away")
            except StopIteration:
                continue
            h, a = normalize(hc["team"]["displayName"]), normalize(ac["team"]["displayName"])
            if not (h and a):
                continue
            pk = pair_key(h, a)
            m = by_pair.get(pk)
            if not m:
                continue
            hs, as_ = hc.get("score"), ac.get("score")
            hs = int(hs) if hs not in (None, "") else None
            as_ = int(as_) if as_ not in (None, "") else None
            state = st["state"]  # pre | in | post
            if state == "in" and hs is not None:
                live_matches.append({
                    "n": m["MatchNumber"], "hs": hs, "as": as_,
                    "clock": st.get("shortDetail", st.get("detail", "LIVE")),
                })
            elif state == "post" and hs is not None:
                espn_ft[pk] = (h, hs, as_)
            # bookmaker line (DraftKings via ESPN) — store home goal-supremacy aligned to feed home
            o = (comp.get("odds") or [None])[0]
            if o:
                ps = (o.get("pointSpread") or {}).get("home") or {}
                line = next((( ps.get(ph) or {}).get("line") for ph in ("open", "close", "current")
                             if (ps.get(ph) or {}).get("line") not in (None, "")), None)
                if line is not None:
                    try:
                        sup = -float(str(line).replace("+", ""))  # -handicap = home supremacy (ESPN home)
                        if normalize(m["HomeTeam"]) != h:
                            sup = -sup  # align to feed's home team
                        odds_out[m["MatchNumber"]] = {"sup": sup, "total": o.get("overUnder")}
                    except ValueError:
                        pass

    # 3. patch fixtures: if ESPN says FT but feed hasn't caught up, fill the score
    patched = 0
    for m in fixtures:
        if not m.get("Group"):
            continue
        if m.get("HomeTeamScore") is not None:
            continue
        h, a = normalize(m["HomeTeam"]), normalize(m["AwayTeam"])
        pk = pair_key(h, a) if h and a else None
        if pk in espn_ft:
            home_norm, hs, as_ = espn_ft[pk]
            # espn_ft stored relative to ESPN home; align to feed's home
            if normalize(m["HomeTeam"]) == home_norm:
                m["HomeTeamScore"], m["AwayTeamScore"] = hs, as_
            else:
                m["HomeTeamScore"], m["AwayTeamScore"] = as_, hs
            patched += 1
    if patched:
        with open(os.path.join(SRC, "fixtures_raw.json"), "w") as f:
            json.dump(fixtures, f)

    # 4. write live.json (drop matches that are now FT in the feed)
    ft_nums = {m["MatchNumber"] for m in fixtures if m.get("HomeTeamScore") is not None}
    live_matches = [lm for lm in live_matches if lm["n"] not in ft_nums]
    with open(os.path.join(SRC, "live.json"), "w") as f:
        json.dump({"matches": live_matches}, f)

    # 4b. merge new odds into odds.json (keep prior lines for matches ESPN no longer lists)
    odds_path = os.path.join(SRC, "odds.json")
    existing = {}
    if os.path.exists(odds_path):
        try:
            existing = {int(k): v for k, v in json.load(open(odds_path)).items()}
        except Exception:
            existing = {}
    existing.update(odds_out)
    with open(odds_path, "w") as f:
        json.dump({str(k): v for k, v in existing.items()}, f)

    # 5. recompute data.js
    subprocess.run([sys.executable, os.path.join(HERE, "compute_xscore.py")], check=True)

    completed = len(ft_nums)
    print(f"refresh ok: {completed} completed, {len(live_matches)} live, {patched} ESPN-patched, {len(odds_out)} odds")


if __name__ == "__main__":
    main()
