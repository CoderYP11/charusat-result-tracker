from parallel_crawler_v1 import discover_all_results
from github_state import (
    load_known_results,
    save_known_results
)
from telegram_utils import (
    send,
    send_error
)

try:

    known_results = load_known_results()

    current_results = discover_all_results()

    if known_results is None:

        save_known_results(current_results)

        send(
            f"✅ Tracker initialized\n\n"
            f"Stored {len(current_results)} results"
        )

        raise SystemExit

    new_results = (
        set(current_results)
        - set(known_results)
    )

    if new_results:

        formatted = []

        for item in sorted(new_results):

            try:

                inst, course, sem, exam = (
                    item.split("|", 3)
                )

                formatted.append(
                    f"🏫 Institute : {inst}\n"
                    f"📚 Course    : {course}\n"
                    f"🎓 Semester  : {sem}\n"
                    f"📄 Exam      : {exam}"
                )

            except Exception:

                formatted.append(item)

        message = (
            "🚨 CHARUSAT RESULT UPDATE 🚨\n\n"
            f"📊 New Results Found: {len(new_results)}\n\n"
            + "\n\n".join(formatted)
            + "\n\n🌐 Check Result:\n"
              "https://support.charusat.edu.in/Uniexamresult/"
        )

        send(message[:3900])

        known_results.update(current_results)

        save_known_results(
            known_results
        )

except Exception as e:

    send_error(
        f"{type(e).__name__}: {e}"
    )

    raise
