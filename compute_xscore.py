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
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from name_map import normalize, CANONICAL


def simulate_futures(x, groups, fixtures, n_sims=20000, spread_k=0.74):
    """Monte Carlo: P(win group), P(advance to KO32), P(win cup).

    Conditioned on completed (FT) results; remaining matches simulated from X-Score
    via twin-Poisson scorelines. Knockouts use a seeded re-bracket approximation
    (exact WC bracket lands when the group stage finalizes).
    """
    random.seed(42)  # stable numbers between refreshes until results change
    teams_by_group = {}
    for t, g in groups.items():
        teams_by_group.setdefault(g, []).append(t)
    grp_fx = [f for f in fixtures if f["rd"] in (1, 2, 3)]
    # banked points/gd/gf from FT matches
    base = {t: {"pts": 0, "gd": 0, "gf": 0} for t in groups}
    remaining = []
    for f in grp_fx:
        if f["status"] == "FT" and f["hs"] is not None:
            for t, gf, ga in ((f["h"], f["hs"], f["as"]), (f["a"], f["as"], f["hs"])):
                base[t]["gf"] += gf; base[t]["gd"] += gf - ga
                base[t]["pts"] += 3 if gf > ga else 1 if gf == ga else 0
        else:
            remaining.append(f)

    def sim_score(h, a):
        mu = (x[h] - x[a]) * spread_k
        hx = max(0.15, (2.6 + mu) / 2); ax = max(0.15, (2.6 - mu) / 2)
        return _pois(hx), _pois(ax)

    win_group = {t: 0 for t in groups}
    advance = {t: 0 for t in groups}
    champ = {t: 0 for t in groups}
    for _ in range(n_sims):
        st = {t: dict(base[t]) for t in groups}
        for f in remaining:
            hs, as_ = sim_score(f["h"], f["a"])
            for t, gf, ga in ((f["h"], hs, as_), (f["a"], as_, hs)):
                st[t]["gf"] += gf; st[t]["gd"] += gf - ga
                st[t]["pts"] += 3 if gf > ga else 1 if gf == ga else 0
        qualifiers, thirds = [], []
        for g, ts in teams_by_group.items():
            table = sorted(ts, key=lambda t: (st[t]["pts"], st[t]["gd"], st[t]["gf"], random.random()), reverse=True)
            win_group[table[0]] += 1
            qualifiers += table[:2]; advance[table[0]] += 1; advance[table[1]] += 1
            thirds.append(table[2])
        best_thirds = sorted(thirds, key=lambda t: (st[t]["pts"], st[t]["gd"], st[t]["gf"], random.random()), reverse=True)[:8]
        for t in best_thirds:
            advance[t] += 1
        bracket = sorted(qualifiers + best_thirds, key=lambda t: x[t], reverse=True)
        while len(bracket) > 1:
            nxt = []
            for i in range(len(bracket) // 2):
                a, b = bracket[i], bracket[-1 - i]
                p = 1.0 / (1.0 + math.exp(-0.95 * (x[a] - x[b])))
                nxt.append(a if random.random() < p else b)
            bracket = sorted(nxt, key=lambda t: x[t], reverse=True)
        champ[bracket[0]] += 1

    return {t: {"grp": round(100 * win_group[t] / n_sims, 1),
                "ko": round(100 * advance[t] / n_sims, 1),
                "cup": round(100 * champ[t] / n_sims, 1)} for t in groups}


def _pois(lam):
    # Knuth's algorithm — small lambdas, fine for goal counts
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        k += 1; p *= random.random()
        if p <= L:
            return k - 1

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources")

# Tier 1 = core models Chris trusts most (heavy). Tier 2 = FIFA + media (×1).
# Chris's own rankings will join T1 at 4.0 once provided.
T1 = {"PELE": 4.0, "ELO": 4.0}
T2 = {"FIFA": 1.0, "LALAS": 1.0, "BR": 1.0, "YAH": 1.0, "SPNET": 1.0, "ATH": 1.0}
T3 = {"ESPN"}  # OPTA dropped: only ~6 of 48 ratings public, so the column was misleading
FILES = {
    "PELE": "pele.json", "ELO": "elo.json", "FIFA": "fifa.json",
    "LALAS": "foxlalas.json", "BR": "bleacher.json", "YAH": "yahoo.json",
    "SPNET": "sportsnet.json", "ATH": "athletic.json",
    "ESPN": "espn.json",
}


def load(fname):
    with open(os.path.join(SRC, fname)) as f:
        return json.load(f)


def zscores(values):
    """values: {team: number}; returns {team: z} standardized over given teams."""
    xs = list(values.values())
    mean = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / len(xs))
    if sd == 0:  # degenerate source (all identical) — avoid divide-by-zero
        return {t: 0.0 for t in values}
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
    if not sys_z:
        raise SystemExit("FATAL: no complete weighted systems — refusing to publish empty X-Score")
    x = {}
    for team in CANONICAL:
        num, den = 0.0, 0.0
        for s, z in sys_z.items():
            w = weights[s]
            num += w * z[team]
            den += w
        x[team] = num / den if den else 0.0

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
    # SPREAD_K=0.74 fitted to DraftKings Asian-handicap lines across 65 fixtures
    # (RMSE 0.47 goals; see calibrate.py). Market mean total ~2.56 ≈ our 2.6.
    SPREAD_K = 0.74
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
        # accuracy: X-Score "called" the match — the favorite won outright; a draw
        # counts only when the projected line was essentially even (< 0.75 goals).
        total += 1
        if hs == as_:
            correct += 1 if abs(f["spread"]) < 0.75 else 0
        else:
            correct += 1 if (f["spread"] > 0) == (hs > as_) else 0

    # FIFA group ordering: overall pts -> GD -> GF; then head-to-head among teams
    # still level; then X-rank as the drawing-of-lots proxy. Teams sharing overall
    # pts/GD/GF are flagged "tied" so the UI can show a tiebreak-pending hint.
    ft = [f for f in fixtures if f["status"] == "FT"]
    for g in standings:
        for s in standings[g].values():
            s["gd"] = s["gf"] - s["ga"]

        def h2h(cluster):
            cs = set(cluster)
            tab = {t: {"pts": 0, "gd": 0, "gf": 0} for t in cluster}
            for f in ft:
                if f["g"] == g and f["h"] in cs and f["a"] in cs:
                    for t, gf, ga in ((f["h"], f["hs"], f["as"]), (f["a"], f["as"], f["hs"])):
                        tab[t]["gf"] += gf; tab[t]["gd"] += gf - ga
                        tab[t]["pts"] += 3 if gf > ga else 1 if gf == ga else 0
            return tab

        base = sorted(standings[g].values(), key=lambda s: (-s["pts"], -s["gd"], -s["gf"]))
        out, i = [], 0
        while i < len(base):
            j = i
            while j < len(base) and (base[j]["pts"], base[j]["gd"], base[j]["gf"]) == \
                    (base[i]["pts"], base[i]["gd"], base[i]["gf"]):
                j += 1
            cluster = base[i:j]
            if len(cluster) > 1 and base[i]["p"] > 0:  # genuine tie among teams that have played
                ht = h2h([s["team"] for s in cluster])
                cluster = sorted(cluster, key=lambda s: (-ht[s["team"]]["pts"], -ht[s["team"]]["gd"],
                                                         -ht[s["team"]]["gf"], -x[s["team"]]))
                for s in cluster:
                    s["tied"] = True
            out.extend(cluster)
            i = j
        standings[g] = out

    futures = simulate_futures(x, groups, fixtures)

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
        "futures": futures,
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
