import logging
import os
import time

import requests
from dotenv import load_dotenv

from database import (
    add_subscriber,
    get_active_subscribers,
    get_result_count,
    get_subscriber_count,
    get_telegram_offset,
    is_subscribed,
    log_event,
    remove_subscriber,
    save_telegram_offset,
)

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["CHAT_ID"])

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

POLL_TIMEOUT = 25
ERROR_RETRY_DELAY = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("telegram_bot")


# ============================================================
# TELEGRAM API
# ============================================================

def send_message(chat_id, text):
    """Send a Telegram message."""

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


def get_updates(offset):
    """Receive Telegram updates using long polling."""

    response = requests.get(
        f"{BASE_URL}/getUpdates",
        params={
            "offset": offset,
            "timeout": POLL_TIMEOUT,
        },
        timeout=POLL_TIMEOUT + 10,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        raise RuntimeError(
            f"Telegram API error: {data}"
        )

    return data.get("result", [])


# ============================================================
# COMMANDS
# ============================================================

def handle_start(chat_id, user):
    """Subscribe the user."""

    add_subscriber(
        chat_id=chat_id,
        username=user.get("username"),
        first_name=user.get("first_name"),
    )

    send_message(
        chat_id,
        "✅ You are now subscribed!\n\n"
        "You will receive notifications when new "
        "CHARUSAT results are detected.\n\n"
        "Use /stop anytime to unsubscribe.",
    )

    logger.info(
        "➕ Subscriber added: %s",
        chat_id,
    )


def handle_stop(chat_id):
    """Unsubscribe the user."""

    remove_subscriber(chat_id)

    send_message(
        chat_id,
        "🛑 You have been unsubscribed.\n\n"
        "You will no longer receive result alerts.\n\n"
        "Use /start anytime to subscribe again.",
    )

    logger.info(
        "➖ Subscriber removed: %s",
        chat_id,
    )


def handle_status(chat_id):
    """Show the user's subscription status."""

    subscribed = is_subscribed(chat_id)

    if subscribed:
        message = (
            "🟢 Subscription Status\n\n"
            "You are currently subscribed. ✅\n\n"
            "You will receive new result alerts."
        )
    else:
        message = (
            "⚪ Subscription Status\n\n"
            "You are currently not subscribed.\n\n"
            "Use /start to subscribe."
        )

    send_message(
        chat_id,
        message,
    )


def handle_help(chat_id):
    """Show available commands."""

    send_message(
        chat_id,
        "🤖 CHARUSAT Result Tracker\n\n"
        "/start - Subscribe to result alerts\n"
        "/stop - Unsubscribe from alerts\n"
        "/status - Check subscription status\n"
        "/help - Show this help message",
    )


# ============================================================
# ADMIN COMMANDS
# ============================================================

def is_admin(chat_id):
    return chat_id == ADMIN_CHAT_ID


def handle_subscribers(chat_id):
    """Admin-only subscriber count."""

    if not is_admin(chat_id):
        send_message(
            chat_id,
            "⛔ Admin only command.",
        )
        return

    count = get_subscriber_count()

    send_message(
        chat_id,
        "👥 Subscriber Statistics\n\n"
        f"Active subscribers: {count}",
    )


def handle_stats(chat_id):
    """Admin-only tracker statistics."""

    if not is_admin(chat_id):
        send_message(
            chat_id,
            "⛔ Admin only command.",
        )
        return

    subscribers = get_subscriber_count()
    results = get_result_count()

    send_message(
        chat_id,
        "📊 CHARUSAT Tracker Stats\n\n"
        f"👥 Subscribers: {subscribers}\n"
        f"📄 Results stored: {results}",
    )


# ============================================================
# UPDATE PROCESSING
# ============================================================

def process_update(update):
    """Process one Telegram update."""

    message = update.get("message")

    if not message:
        return

    chat = message.get("chat", {})
    user = message.get("from", {})

    chat_id = chat.get("id")

    if not chat_id:
        return

    text = message.get("text", "").strip()

    if not text:
        return

    command = text.split()[0].lower()

    # Remove bot username from commands such as:
    # /start@charusat_result_alert_bot
    if "@" in command:
        command = command.split("@", 1)[0]

    logger.info(
        "📩 Command %s from %s",
        command,
        chat_id,
    )

    if command == "/start":
        handle_start(chat_id, user)

    elif command == "/stop":
        handle_stop(chat_id)

    elif command == "/status":
        handle_status(chat_id)

    elif command == "/help":
        handle_help(chat_id)

    elif command == "/subscribers":
        handle_subscribers(chat_id)

    elif command == "/stats":
        handle_stats(chat_id)

    else:
        send_message(
            chat_id,
            "🤖 Unknown command.\n\n"
            "Use /help to see available commands.",
        )


# ============================================================
# MAIN POLLING LOOP
# ============================================================

def main():

    logger.info("=" * 60)
    logger.info("🤖 CHARUSAT TELEGRAM BOT")
    logger.info("=" * 60)

    logger.info(
        "👥 Subscribers in DB: %d",
        get_subscriber_count(),
    )

    logger.info(
        "📄 Results in DB: %d",
        get_result_count(),
    )

    offset = get_telegram_offset()

    logger.info(
        "📌 Starting Telegram offset: %d",
        offset,
    )

    log_event(
        "INFO",
        "telegram_start",
        f"Telegram bot started with offset {offset}",
    )

    while True:

        try:

            updates = get_updates(offset)

            for update in updates:

                update_id = update.get(
                    "update_id"
                )

                if update_id is None:
                    continue

                # ------------------------------------------------
                # Process update
                # ------------------------------------------------

                try:
                    process_update(update)

                except Exception as e:

                    logger.error(
                        "❌ Error processing update %s: %s",
                        update_id,
                        e,
                    )

                # ------------------------------------------------
                # Advance offset AFTER processing
                # ------------------------------------------------

                offset = update_id + 1

                save_telegram_offset(
                    offset
                )

            if updates:
                logger.info(
                    "📥 Processed %d update(s)",
                    len(updates),
                )

        except requests.RequestException as e:

            logger.error(
                "🌐 Telegram network error: %s",
                e,
            )

            time.sleep(
                ERROR_RETRY_DELAY
            )

        except Exception as e:

            logger.error(
                "❌ Telegram bot error: %s",
                e,
            )

            time.sleep(
                ERROR_RETRY_DELAY
            )


if __name__ == "__main__":
    main()