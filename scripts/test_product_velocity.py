"""Smoke test for classify_product_velocity against the GearWrench account."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from ads_mcp.client import get_client
from ads_mcp.reporting.product_velocity import classify_product_velocity

CUSTOMER_ID = "5327742235"  # Gearwrench Shop

def main():
    print(f"Running product velocity classification for GearWrench ({CUSTOMER_ID})...")
    client = get_client()
    result = classify_product_velocity(client, CUSTOMER_ID, "LAST_30_DAYS")

    print(f"\nDate range:  {result['current_date_range']}")
    print(f"Prior range: {result['prior_date_range']}")
    print(f"Account target ROAS: {result['account_target_roas']:.2f}x")

    s = result["summary"]
    print(f"\nSummary:")
    print(f"  New Winners:      {s['new_winners']}")
    print(f"  Turning Losers:   {s['turning_losers']}")
    print(f"  Consistent Losers:{s['consistent_losers']}")
    print(f"  On Track:         {s['on_track']}")

    def _print_tier(label, rows, limit=10):
        if not rows:
            return
        print(f"\n--- {label} (top {min(limit, len(rows))} of {len(rows)}) ---")
        for r in rows[:limit]:
            price_str = f"${r['estimated_price']:.2f}" if r['estimated_price'] else "unknown"
            print(
                f"  [{r['product_id']}] {r['title'][:60]}"
                f"\n    Est. price: {price_str}"
                f"\n    Current: ${r['current_cost']:.2f} spend, {r['current_roas']:.2f}x ROAS"
                f"\n    Prior:   ${r['prior_cost']:.2f} spend, {r['prior_roas']:.2f}x ROAS"
                f"\n    Delta:   {r['roas_delta']:+.2f}x ROAS"
                f"\n    Action:  {r['action']}"
            )

    _print_tier("NEW WINNERS", result["new_winners"])
    _print_tier("TURNING LOSERS", result["turning_losers"])
    _print_tier("CONSISTENT LOSERS", result["consistent_losers"])

    print("\nDone.")

if __name__ == "__main__":
    main()
