from crawler import discover_all_results
from github_state import (
    load_known_results,
    save_known_results
)
from telegram_utils import send

known_results = load_known_results()

current_results = discover_all_results()

if not known_results:

    save_known_results(current_results)

    send(
        f"Tracker initialized ✅\n\n"
        f"Stored {len(current_results)} results"
    )

    raise SystemExit

new_results = set(current_results) - set(known_results)

if new_results:

    message = (
        "🚨 NEW CHARUSAT RESULTS DETECTED 🚨\n\n"
        + "\n".join(
            sorted(new_results)
        )[:3500]
    )

    send(message)

    known_results.update(current_results)

    save_known_results(
        known_results
    )

else:

    send(
        f"No new results\n\n"
        f"Tracked Results: {len(current_results)}"
    )
