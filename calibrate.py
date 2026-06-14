#!/usr/bin/env python3
"""Calibrate the X-Spread factor against real bookmaker lines (ESPN/DraftKings).

For each upcoming match we pull the 3-way moneyline + total, de-vig to true
probabilities, invert a twin-Poisson model to recover the market's goal
supremacy, then regress market supremacy against our X-Score differential (zd)
to get the best-fit goals-per-z-unit. Read-only: prints a recommendation.
"""
import json, math, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from name_map import normalize

ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
DATES = [f"202606{d:02d}" for d in range(14, 28)]
UA = {"User-Agent": "Mozilla/5.0"}


def get(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read())


def ml_to_prob(ml):
    return (-ml) / (-ml + 100) if ml < 0 else 100 / (ml + 100)


def poisson_pmf(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def outcome_probs(total, sup):
    hx, ax = max(0.05, (total + sup) / 2), max(0.05, (total - sup) / 2)
    ph = pd = pa = 0.0
    for i in range(11):
        for j in range(11):
            p = poisson_pmf(i, hx) * poisson_pmf(j, ax)
            if i > j: ph += p
            elif i == j: pd += p
            else: pa += p
    return ph, pd, pa


def market_supremacy(total, p_home, p_away):
    # binary search supremacy so model (phw - paw) matches market
    target = p_home - p_away
    lo, hi = -5.0, 5.0
    for _ in range(40):
        mid = (lo + hi) / 2
        ph, _, pa = outcome_probs(total, mid)
        if ph - pa < target: lo = mid
        else: hi = mid
    return (lo + hi) / 2


def spread_line(o):
    """Return home goal-supremacy from the Asian handicap (open line preferred)."""
    ps = (o.get("pointSpread") or {}).get("home") or {}
    for phase in ("open", "close", "current"):
        ln = (ps.get(phase) or {}).get("line")
        if ln not in (None, ""):
            try:
                return -float(str(ln).replace("+", ""))  # -handicap = supremacy
            except ValueError:
                pass
    return None


def main():
    x = {r["team"]: r["x"] for r in json.load(open(os.path.join(os.path.dirname(__file__), "xscore.json")))["rows"]}
    pts = []  # (zd, market_sup, total)
    seen = set()
    for dt in DATES:
        try:
            d = get(f"{ESPN}?dates={dt}")
        except Exception:
            continue
        for ev in d.get("events", []):
            c = ev["competitions"][0]
            o = (c.get("odds") or [None])[0]
            if not o:
                continue
            cs = c["competitors"]
            hc = next((t for t in cs if t["homeAway"] == "home"), None)
            ac = next((t for t in cs if t["homeAway"] == "away"), None)
            if not hc or not ac:
                continue
            h, a = normalize(hc["team"]["displayName"]), normalize(ac["team"]["displayName"])
            if not h or not a or (h, a) in seen:
                continue
            sup = spread_line(o)
            ou = o.get("overUnder") or 2.6
            if sup is None or h not in x or a not in x:
                continue
            zd = x[h] - x[a]
            pts.append((zd, sup, ou))
            seen.add((h, a))
    if not pts:
        print("No odds found.")
        return
    # regress sup = k * zd through origin
    num = sum(zd * sup for zd, sup, _ in pts)
    den = sum(zd * zd for zd, sup, _ in pts)
    k = num / den
    mean_total = sum(t for _, _, t in pts) / len(pts)
    # current model error vs market at k=0.9 and at fitted k
    def rmse(kk):
        return math.sqrt(sum((kk * zd - sup) ** 2 for zd, sup, _ in pts) / len(pts))
    print(f"matches with odds: {len(pts)}")
    print(f"current SPREAD_K=0.9  -> RMSE {rmse(0.9):.3f} goals")
    print(f"fitted  SPREAD_K={k:.3f} -> RMSE {rmse(k):.3f} goals")
    print(f"market mean total goals (current model uses 2.6): {mean_total:.2f}")
    print("\nsample (zd -> market supremacy):")
    for zd, sup, t in sorted(pts, key=lambda p: -abs(p[0]))[:8]:
        print(f"  zd={zd:+.2f}  market_sup={sup:+.2f}  (0.9*zd={0.9*zd:+.2f}, {k:.2f}*zd={k*zd:+.2f})")


if __name__ == "__main__":
    main()
