import logging
import time

from database import (
    get_connection,
    get_pending_notifications,
    mark_notification_sent,
    mark_notification_failed,
    get_setting,
)
from redaction import redact_secrets
from telegram_db import send_message
from telegram_notifier import format_result


# Default values used only if PostgreSQL settings are unavailable.
DEFAULT_POLL_INTERVAL = 30
DEFAULT_BATCH_SIZE = 20
DEFAULT_RETRY_DELAY = 300
DEFAULT_MAX_ATTEMPTS = 5


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("notification_worker")


# Outcomes returned by process_notification().
OUTCOME_SENT = "sent"          # delivered; row marked 'sent'
OUTCOME_RETRY = "retry"        # failed; row 'failed', will be retried later
OUTCOME_FAILED = "failed"      # failed; attempts exhausted, row is TERMINAL
OUTCOME_DEFERRED = "deferred"  # Telegram disabled; row left untouched


class TelegramDisabled(Exception):
    """telegram.enabled is false: nothing was (or may be) delivered."""


def get_notification_settings():
    """
    Read notification worker settings from PostgreSQL.
    """

    enabled = bool(
        get_setting(
            "notifications.enabled",
            True,
        )
    )

    telegram_notifications_enabled = bool(
        get_setting(
            "telegram.notifications_enabled",
            True,
        )
    )

    poll_interval = int(
        get_setting(
            "notifications.poll_interval_seconds",
            DEFAULT_POLL_INTERVAL,
        )
    )

    batch_size = int(
        get_setting(
            "notifications.batch_size",
            DEFAULT_BATCH_SIZE,
        )
    )

    retry_delay = int(
        get_setting(
            "notifications.retry_delay_seconds",
            DEFAULT_RETRY_DELAY,
        )
    )

    max_attempts = int(
        get_setting(
            "notifications.max_attempts",
            DEFAULT_MAX_ATTEMPTS,
        )
    )

    # Safety limits
    poll_interval = max(1, poll_interval)
    batch_size = max(1, min(batch_size, 100))
    retry_delay = max(1, retry_delay)
    max_attempts = max(1, max_attempts)

    return (
        enabled,
        telegram_notifications_enabled,
        poll_interval,
        batch_size,
        retry_delay,
        max_attempts,
    )


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


def process_notification(
    notification,
    retry_delay_seconds,
    max_attempts,
):
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

        # Send Telegram message.
        response = send_message(
            chat_id,
            message,
        )

        # telegram_db.send_message() returns {"ok": False, "disabled": True}
        # (it does not raise) when telegram.enabled is false. That means
        # NOTHING was delivered: leave the row exactly as it is (still
        # pending/failed, no attempt consumed) so it is delivered once
        # Telegram is re-enabled.
        if isinstance(response, dict) and response.get("disabled"):
            raise TelegramDisabled()

        # Only an explicit confirmation from Telegram counts as delivered.
        if not (isinstance(response, dict) and response.get("ok") is True):
            raise RuntimeError(
                "Telegram did not confirm delivery"
            )

        # Mark as successfully delivered
        mark_notification_sent(
            notification_id
        )

        logger.info(
            "✅ Notification #%s sent successfully",
            notification_id,
        )

        return OUTCOME_SENT

    except TelegramDisabled:

        logger.info(
            "⏸️ Telegram disabled; notification #%s deferred "
            "(not sent, attempt not consumed)",
            notification_id,
        )

        return OUTCOME_DEFERRED

    except Exception as e:

        # Exception text from `requests` contains the request URL, which
        # contains the bot token. Never log or store it unredacted.
        error_message = redact_secrets(e)

        logger.error(
            "❌ Notification #%s failed: %s",
            notification_id,
            error_message,
        )

        current_attempt = attempts + 1

        if current_attempt >= max_attempts:
            logger.error(
                "🛑 Notification #%s reached maximum attempts (%d); "
                "marked permanently failed",
                notification_id,
                max_attempts,
            )

            # Terminal: status 'failed' with attempts >= max_attempts.
            # get_pending_notifications(max_attempts=...) never selects it
            # again; the error text is kept for troubleshooting.
            mark_notification_failed(
                notification_id,
                f"Permanent failure after {current_attempt} "
                f"attempt(s): {error_message}",
                retry_minutes=0,
            )

            return OUTCOME_FAILED

        retry_minutes = retry_delay_seconds / 60

        logger.warning(
            "🔁 Notification #%s will retry in %d seconds "
            "(attempt %d/%d)",
            notification_id,
            retry_delay_seconds,
            current_attempt,
            max_attempts,
        )

        mark_notification_failed(
            notification_id,
            error_message,
            retry_minutes=retry_minutes,
        )

        return OUTCOME_RETRY


def process_queue(
    batch_size,
    retry_delay_seconds,
    max_attempts,
):
    """
    Process one batch of pending notifications.
    """

    notifications = get_pending_notifications(
        limit=batch_size,
        max_attempts=max_attempts,
    )

    if not notifications:
        return 0

    logger.info(
        "📬 Found %d pending notification(s)",
        len(notifications),
    )

    processed = 0

    for notification in notifications:

        outcome = process_notification(
            notification,
            retry_delay_seconds,
            max_attempts,
        )

        if outcome == OUTCOME_DEFERRED:
            # Telegram was switched off mid-batch: stop here, the remaining
            # rows stay queued untouched.
            break

        processed += 1

    return processed


def main():

    logger.info("=" * 60)
    logger.info("📨 TELEGRAM NOTIFICATION WORKER")
    logger.info("=" * 60)

    logger.info("🔄 Dynamic settings enabled")

    while True:

        try:

            (
                enabled,
                telegram_notifications_enabled,
                poll_interval,
                batch_size,
                retry_delay,
                max_attempts,
            ) = get_notification_settings()

            if not enabled:

                logger.info(
                    "⏸️ Notification worker disabled. "
                    "Waiting for it to be enabled..."
                )

                time.sleep(10)
                continue

            if not telegram_notifications_enabled:

                logger.info(
                    "⏸️ Telegram result notifications disabled. "
                    "Waiting..."
                )

                time.sleep(poll_interval)
                continue

            if not bool(get_setting("telegram.enabled", True)):

                # Rows stay queued (status unchanged, no attempts used) and
                # are delivered once the integration is re-enabled.
                logger.info(
                    "⏸️ Telegram integration disabled "
                    "(telegram.enabled=false). Notifications stay queued."
                )

                time.sleep(poll_interval)
                continue

            logger.info(
                "⚙️ Notification settings | "
                "telegram_notifications=%s | "
                "poll=%ds | batch=%d | retry=%ds | max_attempts=%d",
                telegram_notifications_enabled,
                poll_interval,
                batch_size,
                retry_delay,
                max_attempts,
            )

            process_queue(
                batch_size=batch_size,
                retry_delay_seconds=retry_delay,
                max_attempts=max_attempts,
            )

            # Sleep using the current PostgreSQL value.
            # Settings will be re-read after this interval.
            time.sleep(poll_interval)

        except KeyboardInterrupt:

            logger.info(
                "🛑 Notification worker stopped by user"
            )

            break

        except Exception as e:

            logger.exception(
                "⚠️ Notification worker error: %s",
                e,
            )

            # Don't let a temporary DB/API error kill the worker.
            time.sleep(10)

if __name__ == "__main__":
    main()