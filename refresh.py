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
    for date in ESPN_DATES:
        try:
            d = get(f"{ESPN}?dates={date}")
        except Exception:
            continue
        for ev in d.get("events", []):
            comp = ev["competitions"][0]
            st = comp["status"]["type"]
            cs = comp["competitors"]
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

    # 5. recompute data.js
    subprocess.run([sys.executable, os.path.join(HERE, "compute_xscore.py")], check=True)

    completed = len(ft_nums)
    print(f"refresh ok: {completed} completed, {len(live_matches)} live, {patched} ESPN-patched")


if __name__ == "__main__":
    main()
