import logging
import os

import requests
from dotenv import load_dotenv
from database import get_setting

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["CHAT_ID"])

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

logger = logging.getLogger("telegram_db")


def send_message(chat_id, text):
    """
    Send a Telegram message to one chat.

    Respects the global Telegram enable/disable setting.
    """

    if not bool(get_setting("telegram.enabled", True)):
        logger.info(
            "⏸️ Telegram is disabled. Message not sent."
        )
        return {
            "ok": False,
            "disabled": True,
        }

    response = requests.post(
        f"{BASE_URL}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(
            f"Telegram API error: {data}"
        )

    return data


def send_admin_message(text):
    """
    Send a message to the configured admin chat.
    """

    return send_message(
        ADMIN_CHAT_ID,
        text,
    )