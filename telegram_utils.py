import requests
import os
import json

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_CHAT_ID = os.environ["CHAT_ID"]

SUBSCRIBERS_FILE = "subscribers.json"


def load_subscribers():

    try:

        with open(
            SUBSCRIBERS_FILE,
            "r"
        ) as f:

            return json.load(f)

    except:

        return []


def send_to_chat(chat_id, msg):

    requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        params={
            "chat_id": chat_id,
            "text": msg[:4000]
        },
        timeout=30
    )


def send(msg):

    subscribers = load_subscribers()

    for chat_id in subscribers:

        try:

            send_to_chat(
                chat_id,
                msg
            )

        except Exception as e:

            print(
                f"Telegram error {chat_id}: {e}"
            )


def send_error(msg):

    try:

        send_to_chat(
            ADMIN_CHAT_ID,
            f"⚠️ CHARUSAT Tracker Error\n\n{msg[:3500]}"
        )

    except Exception as e:

        print(
            f"Admin notification failed: {e}"
        )
