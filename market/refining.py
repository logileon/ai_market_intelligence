"""Indicative spot cracks: same-day observations only, no forward filling."""
import pandas as pd

CRACKS = {"Gasoline crack": ("DGASUSGULF",), "ULSD crack": ("DDFUELUSGULF",), "3:2:1": ("DGASUSGULF", "DDFUELUSGULF")}

def crack_series(prices, crude="DCOILWTICO"):
    if crude not in ("DCOILWTICO", "DCOILBRENTEU"):
        raise ValueError("Unsupported crude benchmark")
    columns = ["date", "spread", "value", "crude"]
    if prices.empty:
        return pd.DataFrame(columns=columns)
    wide = prices.pivot(index="date", columns="series", values="value").sort_index()
    output = []
    for name, products in CRACKS.items():
        if not {crude, *products}.issubset(wide.columns):
            continue
        aligned = wide[[crude, *products]].dropna()
        value = (42 * aligned[products[0]] - aligned[crude] if len(products) == 1 else
                 42 * (2 * aligned[products[0]] + aligned[products[1]]) / 3 - aligned[crude])
        for date, val in value.items():
            output.append(dict(date=pd.to_datetime(date, utc=True), spread=name, value=float(val), crude=crude))
    return pd.DataFrame(output, columns=columns).sort_values(["date", "spread"]).reset_index(drop=True)

def chronology(fig, periods):
    return fig.update_xaxes(type="category", categoryorder="array", categoryarray=sorted(set(periods)))

def scenario_balance(supply, demand, supply_shock, demand_shock, days):
    balance = supply + supply_shock - demand - demand_shock
    return balance, balance * days
