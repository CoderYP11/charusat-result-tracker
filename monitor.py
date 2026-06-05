from crawler import discover_all_results
from github_state import (
    load_known_results,
    load_structure,
    save_known_results,
)
from telegram_utils import send

try:
    known_results = load_known_results()

    # Load the pre-built structure so the crawler skips dropdown discovery.
    structure = load_structure()

    current_results = discover_all_results(structure=structure)

    if not known_results:
        save_known_results(current_results)
        send(
            f"✅ Tracker initialized\n\n"
            f"Stored {len(current_results)} results"
        )
        raise SystemExit

    new_results = set(current_results) - set(known_results)

    if new_results:
        formatted = []
        for item in sorted(new_results):
            try:
                inst, course, sem, exam = item.split("|", 3)
                formatted.append(
                    f"🏫 {inst}\n"
                    f"📚 {course}\n"
                    f"🎓 Semester {sem}\n"
                    f"📄 {exam}"
                )
            except Exception:
                formatted.append(item)

        message = (
            f"🚨 {len(new_results)} NEW RESULT(S) DETECTED 🚨\n\n"
            + "\n\n".join(formatted)
        )
        send(message[:3900])

        known_results.update(current_results)
        save_known_results(known_results)

except Exception as e:
    send("⚠️ TRACKER ERROR ⚠️\n\n" + str(e))
    raise
print(f"TOTAL RESULTS: {len(current_results)}")
