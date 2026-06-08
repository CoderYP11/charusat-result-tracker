import os
import json
import requests
from github_state import (
    download_file,
    upload_file
)

BOT_TOKEN = os.environ["BOT_TOKEN"]

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

SUBSCRIBERS_FILE = "subscribers.json"
STATE_FILE = "telegram_state.json"


def load_json(filename, default):

    try:

        content = download_file(
            filename
        )

        return json.loads(
            content
        )

    except:

        return default


def save_json(filename, data):

    upload_file(
        filename,
        json.dumps(
            data,
            indent=2
        )
    )


subscribers = load_json(
    SUBSCRIBERS_FILE,
    []
)

state = load_json(
    STATE_FILE,
    {"offset": 0}
)

offset = state["offset"]

updates = requests.get(
    f"{BASE_URL}/getUpdates",
    params={
        "offset": offset
    },
    timeout=30
).json()

for update in updates.get(
    "result",
    []
):

    offset = (
        update["update_id"]
        + 1
    )

    if "message" not in update:

        continue

    chat_id = update[
        "message"
    ]["chat"]["id"]

    text = update[
        "message"
    ].get(
        "text",
        ""
    )

    if text == "/start":

        if chat_id not in subscribers:

            subscribers.append(
                chat_id
            )

            requests.get(
                f"{BASE_URL}/sendMessage",
                params={
                    "chat_id": chat_id,
                    "text":
                    "✅ Subscription activated.\n\nYou will receive CHARUSAT result alerts."
                },
                timeout=30
            )

    elif text == "/stop":

        if chat_id in subscribers:

            subscribers.remove(
                chat_id
            )

            requests.get(
                f"{BASE_URL}/sendMessage",
                params={
                    "chat_id": chat_id,
                    "text":
                    "❌ Subscription removed."
                },
                timeout=30
            )

save_json(
    SUBSCRIBERS_FILE,
    subscribers
)

save_json(
    STATE_FILE,
    {
        "offset": offset
    }
)
