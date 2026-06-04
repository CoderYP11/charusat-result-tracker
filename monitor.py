from github_state import (
    load_known_results,
    save_known_results
)

from telegram_utils import send

data = load_known_results()

data["TEST_ENTRY"] = True

save_known_results(data)

send(
    "GitHub save test successful ✅"
)
