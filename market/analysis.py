"""Deterministic bilingual rules. Signals are mentions, not price forecasts."""
import re

TOPICS = {
    "Crude oil: prices & differentials": ["crude", "brent", "wti", "urals", "dubai", '\u043d\u0435\u0444\u0442'],
    "OPEC+ & quotas": ["opec", '\u043e\u043f\u0435\u043a', "quota", '\u043a\u0432\u043e\u0442'],
    "Production & supply": ["production", "supply", "upstream", '\u0434\u043e\u0431\u044b\u0447', '\u043f\u043e\u0441\u0442\u0430\u0432\u043a'],
    "Refinery runs & maintenance": ["refinery", "refineries", "refining", '\u043d\u043f\u0437', '\u043f\u0435\u0440\u0435\u0440\u0430\u0431\u043e\u0442', "turnaround"],
    "Gasoline & blending components": ["gasoline", "rbob", "naphtha", '\u0431\u0435\u043d\u0437\u0438\u043d', '\u043d\u0430\u0444\u0442\u0430'],
    "Diesel & gasoil": ["diesel", "gasoil", "ulsd", '\u0434\u0438\u0437\u0435\u043b', '\u0433\u0430\u0437\u043e\u0439\u043b'],
    "Jet fuel": ["jet fuel", "aviation fuel", '\u043a\u0435\u0440\u043e\u0441\u0438\u043d', '\u0430\u0432\u0438\u0430\u0442\u043e\u043f\u043b\u0438\u0432'],
    "Fuel oil & bunkers": ["fuel oil", "bunker", '\u043c\u0430\u0437\u0443\u0442', '\u0431\u0443\u043d\u043a\u0435\u0440'],
    "LPG & petrochemicals": ["propane", "butane", "lpg", "petrochem", '\u043f\u0440\u043e\u043f\u0430\u043d', '\u0431\u0443\u0442\u0430\u043d', '\u0441\u0443\u0433', '\u043d\u0435\u0444\u0442\u0435\u0445\u0438\u043c'],
    "Crack spreads & refining margins": ["crack spread", "refining margin", '\u043a\u0440\u044d\u043a', '\u043a\u0440\u0435\u043a\u0438\u043d\u0433-\u0441\u043f\u0440\u0435\u0434', '\u043c\u0430\u0440\u0436\u0430 \u043d\u043f\u0437'],
    "Tankers & freight": ["tanker", "freight", "shipping", '\u0442\u0430\u043d\u043a\u0435\u0440', '\u0444\u0440\u0430\u0445\u0442'],
    "Pipelines & terminals": ["pipeline", "terminal", '\u043d\u0435\u0444\u0442\u0435\u043f\u0440\u043e\u0432\u043e\u0434', '\u0442\u0435\u0440\u043c\u0438\u043d\u0430\u043b'],
    "Demand & seasonality": ["demand", "winter", "cold", "heatwave", "driving season", '\u0441\u043f\u0440\u043e\u0441', '\u0437\u0438\u043c', '\u043c\u043e\u0440\u043e\u0437'],
    "Inventories & SPR": ["storage", "inventories", "stockpile", "spr", '\u0445\u0440\u0430\u043d\u0438\u043b\u0438\u0449', '\u0437\u0430\u043f\u0430\u0441'],
    "Sanctions & trade flows": ["sanction", "embargo", "export", "import", '\u0441\u0430\u043d\u043a\u0446\u0438', '\u044d\u043a\u0441\u043f\u043e\u0440\u0442', '\u0438\u043c\u043f\u043e\u0440\u0442'],
    "Regulation & emissions": ["permit", "regulation", "emissions", '\u0440\u0430\u0437\u0440\u0435\u0448\u0435\u043d', '\u0432\u044b\u0431\u0440\u043e\u0441'],
    "Investment & projects": ["contract", "investment", "fid", "capex", '\u043a\u043e\u043d\u0442\u0440\u0430\u043a\u0442', '\u0438\u043d\u0432\u0435\u0441\u0442\u0438\u0446'],
}
REGIONS = {
    "United States": ["u.s.", "united states", "wti", "cushing", "texas", "louisiana", '\u0441\u0448\u0430'],
    "Europe": ["europe", "european", "germany", "norway", '\u0435\u0432\u0440\u043e\u043f', '\u043d\u043e\u0440\u0432\u0435\u0433'],
    "Asia": ["china", "japan", "korea", "india", "asia", '\u043a\u0438\u0442\u0430\u0439', '\u044f\u043f\u043e\u043d\u0438', '\u0430\u0437\u0438'],
    "Middle East": ["saudi", "iraq", "iran", "uae", "hormuz", '\u0441\u0430\u0443\u0434\u043e\u0432', '\u0438\u0440\u0430\u043a', '\u0438\u0440\u0430\u043d', '\u043e\u0440\u043c\u0443\u0437'],
    "Russia": ["russia", "gazprom", "novatek", '\u0440\u043e\u0441\u0441\u0438', '\u0433\u0430\u0437\u043f\u0440\u043e\u043c', '\u043d\u043e\u0432\u0430\u0442\u044d\u043a'],
    "Australia": ["australia", "woodside", '\u0430\u0432\u0441\u0442\u0440\u0430\u043b\u0438'],
}
RISK = ["outage", "disruption", "shutdown", "sanction", "shortage", '\u0430\u0432\u0430\u0440\u0438', '\u0434\u0435\u0444\u0438\u0446\u0438\u0442', '\u0441\u0430\u043d\u043a\u0446\u0438']
SUPPLY = ["expansion", "new capacity", "startup", "start-up", "commissioning", '\u0440\u0430\u0441\u0448\u0438\u0440\u0435\u043d', '\u0432\u0432\u043e\u0434 \u043c\u043e\u0449\u043d\u043e\u0441\u0442']

def matches(text, terms):
    # English short words use boundaries: LNG must not match an unrelated substring.
    return [t for t in terms if (re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", text)
            if t.isascii() and len(t) <= 4 and t.isalpha() else t in text)]

def relevant(text):
    return bool(matches(text.lower(), ["crude", "oil", "petroleum", "brent", "wti", "opec", "refinery", "refineries", "gasoline", "diesel", "gasoil", "jet fuel", '\u043d\u0435\u0444\u0442', '\u043e\u043f\u0435\u043a', '\u043d\u043f\u0437', '\u0431\u0435\u043d\u0437\u0438\u043d', '\u0434\u0438\u0437\u0435\u043b', '\u043c\u0430\u0437\u0443\u0442', "propane", "butane", "lpg", "naphtha", "petrochem", "bunker", '\u043a\u0435\u0440\u043e\u0441\u0438\u043d', '\u0441\u0443\u0433', '\u043d\u0435\u0444\u0442\u0435\u0445\u0438\u043c']))

def analyze(title, summary=""):
    text = (title + " " + summary).lower()
    topics = [k for k, words in TOPICS.items() if matches(text, words)]
    regions = [k for k, words in REGIONS.items() if matches(text, words)]
    risk, supply = matches(text, RISK), matches(text, SUPPLY)
    signal = "Mixed mentions" if risk and supply else "Risk mention" if risk else "Expansion mention" if supply else "No explicit signal"
    evidence = sorted(set(risk + supply))
    return {"topics": "; ".join(topics) or "Other", "regions": "; ".join(regions) or "Unspecified",
            "signal": signal, "evidence": ", ".join(evidence)}
