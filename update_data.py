import json
from market.collect import update
from market.steo import update_steo

if __name__ == "__main__":
    market_results = update()
    steo_results = update_steo()
    results = market_results + steo_results
    print(json.dumps(results, ensure_ascii=False, indent=2))
    # STEO failures block publication; partial RSS/FRED outages remain visible.
    if all(r["status"] in ("error", "skipped") for r in market_results) or any(r["status"] == "error" for r in steo_results):
        raise SystemExit(1)
