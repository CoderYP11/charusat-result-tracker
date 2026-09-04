import logging
import time

from database import (
    get_connection,
    get_pending_notifications,
    mark_notification_sent,
    mark_notification_failed,
)
from telegram_db import send_message
from telegram_notifier import format_result


# How often the worker checks PostgreSQL
POLL_INTERVAL = 30

# Maximum notifications processed in one batch
BATCH_SIZE = 20


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("notification_worker")


def get_result_names(
    institute_id,
    degree_id,
    semester_id,
):
    """
    Get human-readable institute, degree and semester names.
    """

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

            if not row:
                raise RuntimeError(
                    "Could not find result hierarchy: "
                    f"{institute_id}/{degree_id}/{semester_id}"
                )

            return row

    finally:
        conn.close()


def process_notification(notification):
    """
    Send one queued notification.
    """

    (
        notification_id,
        result_id,
        chat_id,
        attempts,
        institute_id,
        degree_id,
        semester_id,
        exam_name,
    ) = notification

    logger.info(
        "📨 Processing notification #%s | "
        "Result #%s | Chat %s | Attempt %s",
        notification_id,
        result_id,
        chat_id,
        attempts + 1,
    )

    try:
        # Get human-readable names
        (
            institute_name,
            degree_name,
            semester_name,
        ) = get_result_names(
            institute_id,
            degree_id,
            semester_id,
        )

        # Build Telegram message
        message = format_result(
            institute_name,
            degree_name,
            semester_name,
            exam_name,
        )

        # Send Telegram message
        send_message(
            chat_id,
            message,
        )

        # Mark as successfully delivered
        mark_notification_sent(
            notification_id
        )

        logger.info(
            "✅ Notification #%s sent successfully",
            notification_id,
        )

    except Exception as e:

        error_message = str(e)

        logger.error(
            "❌ Notification #%s failed: %s",
            notification_id,
            error_message,
        )

        # Keep it in queue and retry later
        mark_notification_failed(
            notification_id,
            error_message,
            retry_minutes=5,
        )


def process_queue():
    """
    Process one batch of pending notifications.
    """

    notifications = get_pending_notifications(
        limit=BATCH_SIZE
    )

    if not notifications:
        return 0

    logger.info(
        "📬 Found %d pending notification(s)",
        len(notifications),
    )

    processed = 0

    for notification in notifications:

        process_notification(
            notification
        )

        processed += 1

    return processed


def main():

    logger.info("=" * 60)
    logger.info("📨 TELEGRAM NOTIFICATION WORKER")
    logger.info("=" * 60)

    logger.info(
        "⏱️ Poll interval: %d seconds",
        POLL_INTERVAL,
    )

    logger.info(
        "📦 Batch size: %d",
        BATCH_SIZE,
    )

    logger.info("🚀 Worker started")

    while True:

        try:

            process_queue()

        except Exception as e:

            logger.error(
                "⚠️ Queue processing error: %s",
                e,
            )

        time.sleep(
            POLL_INTERVAL
        )


if __name__ == "__main__":
    main()