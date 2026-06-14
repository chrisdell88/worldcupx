#!/usr/bin/env python3
"""WorldCupX X-Score computation.

Reads sources/*.json, z-score normalizes each complete system across the 48-team
field (raw rating values where available, inverted ordinal ranks otherwise),
combines with tier weights into the composite X-Score, and writes data.js for
the dashboard plus xscore.json for inspection.

Tiers (mirrors bracketx):
  T1 (weight 3x): numeric model ratings — PELE, ELO, FIFA
  T2 (weight 1x): full-field media rankings — LALAS, BR, YAH, SPNET, ATH (when filled)
  T3 (weight 0):  partial/compare-only — ESPN (top 15 by design), OPTA (partial)
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from name_map import normalize, CANONICAL

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources")

T1 = {"PELE": 3.0, "ELO": 3.0, "FIFA": 3.0}
T2 = {"LALAS": 1.0, "BR": 1.0, "YAH": 1.0, "SPNET": 1.0, "ATH": 1.0}
T3 = {"ESPN", "OPTA"}
FILES = {
    "PELE": "pele.json", "ELO": "elo.json", "FIFA": "fifa.json",
    "LALAS": "foxlalas.json", "BR": "bleacher.json", "YAH": "yahoo.json",
    "SPNET": "sportsnet.json", "ATH": "athletic.json",
    "ESPN": "espn.json", "OPTA": "opta.json",
}


def load(fname):
    with open(os.path.join(SRC, fname)) as f:
        return json.load(f)


def zscores(values):
    """values: {team: number}; returns {team: z} standardized over given teams."""
    xs = list(values.values())
    mean = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / len(xs))
    return {t: (v - mean) / sd for t, v in values.items()}


def system_values(data):
    """Extract {canonical_team: comparable_value} where higher = better."""
    vals = {}
    for entry in data.get("teams", []):
        team = normalize(entry["team"])
        if team is None:
            continue
        if "value" in entry:
            vals[team] = float(entry["value"])
        elif "rank" in entry:
            vals[team] = -float(entry["rank"])  # invert: rank 1 is best
    return vals


def main():
    teams_meta = load("teams.json")["teams"]
    groups = {t["team"]: t["group"] for t in teams_meta}
    assert len(groups) == 48

    sys_z = {}        # system -> {team: z}
    sys_rank = {}     # system -> {team: ordinal rank within the 48}
    coverage = {}
    for sysname, fname in FILES.items():
        data = load(fname)
        vals = system_values(data)
        coverage[sysname] = len(vals)
        if len(vals) == 0:
            continue
        complete = set(vals) >= set(CANONICAL)
        if sysname in T3 or not complete:
            # compare-only: still compute ranks over whatever coverage exists
            ordered = sorted(vals, key=lambda t: -vals[t])
            sys_rank[sysname] = {t: i + 1 for i, t in enumerate(ordered)}
            if sysname not in T3:
                print(f"WARN: {sysname} incomplete ({len(vals)}/48) — demoted to compare-only")
            continue
        z = zscores(vals)
        sys_z[sysname] = z
        ordered = sorted(vals, key=lambda t: -vals[t])
        sys_rank[sysname] = {t: i + 1 for i, t in enumerate(ordered)}

    weights = {**T1, **T2}
    x = {}
    for team in CANONICAL:
        num, den = 0.0, 0.0
        for s, z in sys_z.items():
            w = weights[s]
            num += w * z[team]
            den += w
        x[team] = num / den

    ordered = sorted(CANONICAL, key=lambda t: -x[t])
    xrank = {t: i + 1 for i, t in enumerate(ordered)}

    # rows: [team, group, xscore, xrank, best, worst, {system: rank-or-null}]
    weighted_systems = [s for s in FILES if s in sys_z]
    compare_systems = [s for s in FILES if s in sys_rank and s not in sys_z]
    rows = []
    for t in ordered:
        ranks = {s: sys_rank[s].get(t) for s in weighted_systems + compare_systems}
        have = [r for s, r in ranks.items() if r is not None and s in weighted_systems]
        rows.append({
            "team": t, "group": groups[t], "x": round(x[t], 4), "xr": xrank[t],
            "best": min(have), "worst": max(have), "ranks": ranks,
        })

    # fixtures with X-Spread + win probability
    # SPREAD_K calibrated against opening bookmaker goal lines (see METHODOLOGY)
    SPREAD_K = 0.9
    WIN_K = 0.95
    fixtures = []
    fx_path = os.path.join(SRC, "fixtures_raw.json")
    # optional live snapshot: live.json = {"matches":[{"n":9,"hs":0,"as":1,"clock":"43'"}]}
    live = {}
    live_path = os.path.join(SRC, "live.json")
    if os.path.exists(live_path):
        with open(live_path) as f:
            for lm in json.load(f).get("matches", []):
                live[lm["n"]] = lm

    if os.path.exists(fx_path):
        with open(fx_path) as f:
            raw_fx = json.load(f)
        for m in raw_fx:
            if not m.get("Group"):
                continue
            h, a = normalize(m["HomeTeam"]), normalize(m["AwayTeam"])
            zd = x[h] - x[a]
            spread = round(zd * SPREAD_K * 2) / 2.0  # to nearest half-goal
            pwin = 1.0 / (1.0 + math.exp(-WIN_K * zd))
            n = m["MatchNumber"]
            hs, as_ = m.get("HomeTeamScore"), m.get("AwayTeamScore")
            status, clock = "", ""
            if hs is not None and as_ is not None:
                status = "FT"
            elif n in live:
                status, hs, as_ = "LIVE", live[n].get("hs"), live[n].get("as")
                clock = live[n].get("clock", "")
            fixtures.append({
                "n": n, "rd": m["RoundNumber"], "date": m["DateUtc"],
                "loc": m["Location"], "h": h, "a": a, "g": m["Group"][-1],
                "spread": spread, "hwin": round(pwin * 100),
                "hs": hs, "as": as_, "status": status, "clock": clock,
            })

    # group standings + prediction accuracy from completed (FT) matches
    standings = {g: {t: {"team": t, "p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}
                     for t in CANONICAL if groups[t] == g} for g in sorted(set(groups.values()))}
    correct = total = 0
    for f in fixtures:
        if f["status"] != "FT":
            continue
        g, h, a, hs, as_ = f["g"], f["h"], f["a"], f["hs"], f["as"]
        for t, gf, ga in ((h, hs, as_), (a, as_, hs)):
            s = standings[g][t]
            s["p"] += 1; s["gf"] += gf; s["ga"] += ga
            if gf > ga: s["w"] += 1; s["pts"] += 3
            elif gf == ga: s["d"] += 1; s["pts"] += 1
            else: s["l"] += 1
        # accuracy: did the X-Score favorite avoid losing? (spread sign vs result)
        total += 1
        if hs == as_:
            correct += 1 if abs(f["spread"]) < 0.75 else 0
        else:
            fav_home = f["spread"] > 0
            home_won = hs > as_
            correct += 1 if fav_home == home_won else 0
    for g in standings:
        table = sorted(standings[g].values(), key=lambda s: (-s["pts"], -(s["gf"] - s["ga"]), -s["gf"]))
        for s in table:
            s["gd"] = s["gf"] - s["ga"]
        standings[g] = table

    out = {
        "computed": "2026-06-13",
        "weighted": weighted_systems,
        "compare": compare_systems,
        "tier": {s: (1 if s in T1 else 2) for s in weighted_systems} | {s: 3 for s in compare_systems},
        "coverage": coverage,
        "rows": rows,
        "fixtures": fixtures,
        "standings": standings,
        "accuracy": {"correct": correct, "total": total},
    }
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "xscore.json"), "w") as f:
        json.dump(out, f, indent=1)
    with open(os.path.join(here, "data.js"), "w") as f:
        f.write("// Generated by compute_xscore.py — do not edit by hand\n")
        f.write("const WCX=" + json.dumps(out) + ";\n")
    print(f"weighted: {weighted_systems}")
    print(f"compare:  {compare_systems}")
    print(f"coverage: {coverage}")
    print("\nTop 10:")
    for r in rows[:10]:
        print(f"  {r['xr']:>2}. {r['team']:<22} X={r['x']:+.3f}  (grp {r['group']})")
    print("\nBottom 5:")
    for r in rows[-5:]:
        print(f"  {r['xr']:>2}. {r['team']:<22} X={r['x']:+.3f}  (grp {r['group']})")


if __name__ == "__main__":
    main()
