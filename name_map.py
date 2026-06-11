# WorldCupX — national team name normalization
# Canonical names = sources/teams.json (FIFA final draw spelling, ASCII-simplified)

CANONICAL = [
    "Czechia", "Mexico", "South Africa", "South Korea",
    "Bosnia and Herzegovina", "Canada", "Qatar", "Switzerland",
    "Brazil", "Haiti", "Morocco", "Scotland",
    "Australia", "Paraguay", "Turkey", "United States",
    "Curacao", "Ecuador", "Germany", "Ivory Coast",
    "Japan", "Netherlands", "Sweden", "Tunisia",
    "Belgium", "Egypt", "Iran", "New Zealand",
    "Cape Verde", "Saudi Arabia", "Spain", "Uruguay",
    "France", "Iraq", "Norway", "Senegal",
    "Algeria", "Argentina", "Austria", "Jordan",
    "Colombia", "DR Congo", "Portugal", "Uzbekistan",
    "Croatia", "England", "Ghana", "Panama",
]

ALIASES = {
    # Turkey
    "turkiye": "Turkey", "türkiye": "Turkey",
    # South Korea
    "korea republic": "South Korea", "korea, south": "South Korea", "s. korea": "South Korea",
    "republic of korea": "South Korea",
    # USA
    "usa": "United States", "united states of america": "United States", "usmnt": "United States",
    # Ivory Coast
    "cote d'ivoire": "Ivory Coast", "côte d'ivoire": "Ivory Coast", "cote divoire": "Ivory Coast",
    # DR Congo
    "congo dr": "DR Congo", "dem. rep. congo": "DR Congo", "democratic republic of the congo": "DR Congo",
    "dr congo": "DR Congo", "congo-kinshasa": "DR Congo", "dem rep congo": "DR Congo",
    # Bosnia
    "bosnia-herzegovina": "Bosnia and Herzegovina", "bosnia/herzegovina": "Bosnia and Herzegovina",
    "bosnia": "Bosnia and Herzegovina", "bosnia & herzegovina": "Bosnia and Herzegovina",
    "bosnia and hezergovina": "Bosnia and Herzegovina",  # Sportsnet typo
    # Cape Verde
    "cabo verde": "Cape Verde", "cape verde islands": "Cape Verde",
    # Curacao
    "curaçao": "Curacao",
    # Czechia
    "czech republic": "Czechia",
    # Iran
    "ir iran": "Iran", "iran ir": "Iran", "islamic republic of iran": "Iran",
    # Misc spellings
    "holland": "Netherlands", "the netherlands": "Netherlands",
    "rep. ireland": "Republic of Ireland",  # not qualified; here so lookups fail loudly elsewhere
    "saudiarabia": "Saudi Arabia", "ksa": "Saudi Arabia",
    "new zeland": "New Zealand",
}


def normalize(name):
    """Return canonical team name, or None if not one of the 48."""
    n = " ".join(name.replace(" ", " ").strip().split())
    if n in CANONICAL:
        return n
    n_l = n.lower()
    if n_l in ALIASES:
        a = ALIASES[n_l]
        return a if a in CANONICAL else None
    # title-case match (e.g. "SPAIN" from Sportsnet)
    for c in CANONICAL:
        if c.lower() == n_l:
            return c
    return None
