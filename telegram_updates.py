import os
import json
import requests
from github_state import (
    download_file,
    upload_file
)

ADMIN_CHAT_ID = int(
    os.environ["CHAT_ID"]
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

    except Exception as e:

        raise Exception(
            f"Failed loading {filename}: {e}"
        )


def save_json(filename, data):

    upload_file(
        filename,
        json.dumps(
            data,
            indent=2
        )
    )


def send_message(chat_id, text):

    requests.get(
        f"{BASE_URL}/sendMessage",
        params={
            "chat_id": chat_id,
            "text": text
        },
        timeout=30
    )


subscribers = load_json(
    SUBSCRIBERS_FILE,
    []
)

state = load_json(
    STATE_FILE,
    {"offset": 0}
)

known_results = load_json(
    "known_results.json",
    {}
)

offset = state["offset"]

if (
    len(subscribers) == 0
    and offset > 0
):
    raise Exception(
        "Subscribers list unexpectedly empty."
    )

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
    ).strip().lower()

    if text == "/start":

        if chat_id in subscribers:

            send_message(
                chat_id,
                "ℹ️ You are already subscribed to CHARUSAT result alerts."
            )

        else:

            subscribers.append(
                chat_id
            )

            send_message(
                chat_id,
                "🎓 CHARUSAT Result Alerts\n\n"
                "✅ Subscription Activated\n\n"
                "You will now receive automatic result notifications."
            )

    elif text == "/stop":

        if chat_id in subscribers:

            subscribers.remove(
                chat_id
            )

            send_message(
                chat_id,
                "🔕 Subscription Removed\n\n"
                "You will no longer receive result alerts.\n\n"
                "Use /start anytime to subscribe again."
            )

        else:

            send_message(
                chat_id,
                "ℹ️ You are not currently subscribed."
            )

    elif text == "/status":

        if chat_id in subscribers:

            send_message(
                chat_id,
                f"📊 Subscription Status\n\n"
                f"✅ Active\n"
                f"🆔 Chat ID: {chat_id}"
            )

        else:

            send_message(
                chat_id,
                "📊 Subscription Status\n\n"
                "❌ Not Subscribed\n\n"
                "Use /start to subscribe."
            )

    elif text == "/help":

        send_message(
            chat_id,
            "🎓 CHARUSAT Result Alerts\n\n"
            "Available Commands:\n\n"
            "/start - Subscribe to result alerts\n"
            "/stop - Unsubscribe from alerts\n"
            "/status - Check subscription status\n"
            "/help - Show this help message"
        )

    elif text == "/subscribers":

        if chat_id != ADMIN_CHAT_ID:

            send_message(
                chat_id,
                "⛔ Admin only command"
            )

        else:

            send_message(
                chat_id,
                f"👥 Subscribers\n\n"
                f"Total Subscribers: {len(subscribers)}"
            )

    elif text == "/stats":

        if chat_id != ADMIN_CHAT_ID:

            send_message(
                chat_id,
                "⛔ Admin only command"
            )

        else:

            send_message(
                chat_id,
                "📊 CHARUSAT Tracker Stats\n\n"
                f"👥 Subscribers : {len(subscribers)}\n"
                f"📄 Known Results : {len(known_results)}\n\n"
                "🟢 Status : Running"
            )

    elif text == "/health":

        if chat_id != ADMIN_CHAT_ID:

            send_message(
                chat_id,
                "⛔ Admin only command"
            )

        else:

            send_message(
                chat_id,
                "🟢 Tracker Health\n\n"
                f"👥 Subscribers : {len(subscribers)}\n"
                f"📄 Results Stored : {len(known_results)}\n"
                "✅ GitHub Actions Active"
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
