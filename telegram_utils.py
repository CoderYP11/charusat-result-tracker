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

    except Exception as e:

        print(
            f"Failed to load subscribers: {e}"
        )
    
        return []


def send_to_chat(chat_id, msg):

    response = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        params={
            "chat_id": chat_id,
            "text": msg[:4000]
        },
        timeout=30
    )

    response.raise_for_status()


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

        msg = str(msg)

        if "Status: 502" in msg:

            msg = (
                "GitHub API Error (502 Bad Gateway)\n\n"
                "GitHub server temporarily unavailable.\n"
                "The tracker will automatically retry on the next scheduled run."
            )

        elif "Status: 500" in msg:

            msg = (
                "GitHub API Error (500 Internal Server Error)\n\n"
                "Temporary GitHub server issue."
            )

        elif "Status: 409" in msg:

            msg = (
                "GitHub API Error (409 Conflict)\n\n"
                "Repository update conflict occurred."
            )

        elif "Status: 503" in msg:

            msg = (
                "GitHub API Error (503 Service Unavailable)\n\n"
                "GitHub service is temporarily unavailable."
            )
        
        elif "Status: 504" in msg:
        
            msg = (
                "GitHub API Error (504 Gateway Timeout)\n\n"
                "GitHub API did not respond in time."
            )

        elif len(msg) > 1000:

            msg = (
                msg[:1000]
                + "\n\n...(truncated)"
            )

        send_to_chat(
            ADMIN_CHAT_ID,
            f"⚠️ CHARUSAT Tracker Error\n\n{msg}"
        )

    except Exception as e:

        print(
            f"Admin notification failed: {e}"
        )
