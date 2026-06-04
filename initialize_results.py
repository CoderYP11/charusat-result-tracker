import json

from crawler import discover_all_results

results = discover_all_results()

with open("known_results.json", "w") as f:
    json.dump(
        results,
        f,
        indent=2
    )

print(
    f"known_results.json initialized with "
    f"{len(results)} results"
)
