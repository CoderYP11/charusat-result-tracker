import json

from crawler import discover_all_results
from telegram_utils import send

results = discover_all_results()

with open("current_results.json", "w") as f:
    json.dump(results, f, indent=2)

sample = list(results.keys())[:20]

send(
    "FULL SCAN COMPLETE\n\n"
    f"TOTAL RESULTS: {len(results)}\n\n"
    + "\n".join(sample)
)
