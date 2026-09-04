import logging
import os

import requests
from dotenv import load_dotenv

from database import (
    get_active_subscribers,
)

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

MAX_MESSAGE_LENGTH = 3900

logger = logging.getLogger("telegram_notifier")


def send_message(chat_id, text):
    """Send one Telegram message."""

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


def format_result(
    institute_name,
    degree_name,
    semester_name,
    exam_name,
):
    """Format one result notification."""

    return (
        "🆕 NEW CHARUSAT RESULT\n\n"
        f"🏫 Institute: {institute_name}\n"
        f"📚 Degree: {degree_name}\n"
        f"🎓 Semester: {semester_name}\n"
        f"📄 Exam: {exam_name}"
    )


def send_new_result_notifications(new_results):
    """
    Send notifications for newly discovered results.

    new_results must contain:
        (
            institute_id,
            degree_id,
            semester_id,
            exam_name
        )
    """

    if not new_results:
        logger.info(
            "📭 No new results to notify."
        )
        return 0

    subscribers = get_active_subscribers()

    if not subscribers:
        logger.info(
            "📭 No active Telegram subscribers."
        )
        return 0

    sent = 0

    for result in new_results:

        (
            institute_id,
            degree_id,
            semester_id,
            exam_name,
        ) = result

        # ----------------------------------------------------
        # Get human-readable names from PostgreSQL
        # ----------------------------------------------------

        from database import get_connection

        conn = get_connection()

        try:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT
                        i.name,
                        d.name,
                        s.name
                    FROM institutes i
                    JOIN degrees d
                        ON d.institute_id = i.id
                    JOIN semesters s
                        ON s.degree_id = d.id
                       AND s.id = %s
                    WHERE i.id = %s
                      AND d.id = %s
                    """,
                    (
                        semester_id,
                        institute_id,
                        degree_id,
                    ),
                )

                row = cur.fetchone()

        finally:
            conn.close()

        if not row:
            logger.warning(
                "⚠️ Could not resolve result names: %s",
                result,
            )
            continue

        institute_name, degree_name, semester_name = row

        message = format_result(
            institute_name,
            degree_name,
            semester_name,
            exam_name,
        )

        if len(message) > MAX_MESSAGE_LENGTH:
            message = message[:MAX_MESSAGE_LENGTH]

        # ----------------------------------------------------
        # Send to every active subscriber
        # ----------------------------------------------------

        for subscriber in subscribers:

            # database.py currently returns chat IDs
            # for active subscribers.
            chat_id = subscriber

            try:

                send_message(
                    chat_id,
                    message,
                )

                sent += 1

                logger.info(
                    "📨 Notification sent: %s -> %s",
                    exam_name,
                    chat_id,
                )

            except requests.RequestException as e:

                logger.error(
                    "❌ Telegram send failed: %s -> %s",
                    chat_id,
                    e,
                )

            except Exception as e:

                logger.error(
                    "❌ Notification error: %s -> %s",
                    chat_id,
                    e,
                )

    return sent