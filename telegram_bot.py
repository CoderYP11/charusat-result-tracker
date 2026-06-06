import json
import os
import requests
import time

BOT_TOKEN = os.environ["BOT_TOKEN"]

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

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


def save_subscribers(data):

    with open(
        SUBSCRIBERS_FILE,
        "w"
    ) as f:

        json.dump(
            data,
            f,
            indent=2
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


offset = 0

print("Bot Started...")


while True:

    try:

        updates = requests.get(
            f"{BASE_URL}/getUpdates",
            params={
                "offset": offset,
                "timeout": 30
            },
            timeout=35
        ).json()

        for update in updates["result"]:

            offset = update["update_id"] + 1

            if "message" not in update:
                continue

            chat_id = update["message"]["chat"]["id"]

            text = update["message"].get(
                "text",
                ""
            )

            subscribers = load_subscribers()

            if text == "/start":

                if chat_id not in subscribers:

                    subscribers.append(chat_id)

                    save_subscribers(
                        subscribers
                    )

                send_message(
                    chat_id,
                    "✅ Subscribed to CHARUSAT Result Alerts"
                )

            elif text == "/stop":

                if chat_id in subscribers:

                    subscribers.remove(
                        chat_id
                    )

                    save_subscribers(
                        subscribers
                    )

                send_message(
                    chat_id,
                    "❌ Unsubscribed"
                )

            elif text == "/status":

                if chat_id in subscribers:

                    send_message(
                        chat_id,
                        "✅ Subscription Active"
                    )

                else:

                    send_message(
                        chat_id,
                        "❌ Not Subscribed\nUse /start"
                    )

        time.sleep(2)

    except Exception as e:

        print(e)

        time.sleep(10)
