"""Load the latest seven EIA STEO monthly releases; keep all earlier local versions."""
import argparse
import json
from market.steo import update_steo

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', type=int, default=7, help='Latest monthly releases to check; old versions are never removed')
    args = parser.parse_args()
    if not 1 <= args.history <= 36: parser.error('--history must be between 1 and 36')
    results = update_steo(history=args.history)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if any(r['status'] == 'error' for r in results): raise SystemExit(1)
