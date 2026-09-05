import logging
import time

from database import get_setting
from crawl_results import main as run_crawler


logger = logging.getLogger("crawler_service")


CHECK_INTERVAL_SECONDS = 10


def get_crawler_settings():
    """
    Read crawler runtime settings from PostgreSQL.
    """

    enabled = bool(
        get_setting("crawler.enabled", True)
    )

    interval_minutes = int(
        get_setting("crawler.interval_minutes", 30)
    )

    if interval_minutes < 1:
        interval_minutes = 1

    return enabled, interval_minutes


def wait_with_dynamic_settings():
    """
    Wait for the configured interval while continuously checking
    PostgreSQL so that enable/disable and interval changes take
    effect without restarting the service.
    """

    elapsed = 0

    while True:

        enabled, interval_minutes = get_crawler_settings()

        if not enabled:
            logger.info(
                "⏸️ Crawler disabled. Waiting for it to be enabled..."
            )

            time.sleep(CHECK_INTERVAL_SECONDS)
            elapsed = 0
            continue

        target_seconds = interval_minutes * 60

        if elapsed >= target_seconds:
            return

        remaining = target_seconds - elapsed

        logger.info(
            "⏳ Next crawl in approximately %d seconds "
            "(interval=%d minutes)",
            remaining,
            interval_minutes,
        )

        sleep_seconds = min(
            CHECK_INTERVAL_SECONDS,
            remaining,
        )

        time.sleep(sleep_seconds)

        elapsed += sleep_seconds


def main():

    logger.info("=" * 60)
    logger.info("🚀 CHARUSAT CRAWLER SERVICE")
    logger.info("=" * 60)

    logger.info(
        "🔄 Dynamic scheduler started"
    )

    while True:

        try:

            enabled, interval_minutes = (
                get_crawler_settings()
            )

            if not enabled:

                logger.info(
                    "⏸️ Crawler is disabled in PostgreSQL"
                )

                time.sleep(
                    CHECK_INTERVAL_SECONDS
                )

                continue

            logger.info(
                "▶️ Starting scheduled crawl "
                "(interval=%d minutes)",
                interval_minutes,
            )

            run_crawler()

            logger.info(
                "✅ Scheduled crawl finished"
            )

        except KeyboardInterrupt:

            logger.info(
                "🛑 Crawler service stopped by user"
            )

            break

        except Exception:

            logger.exception(
                "❌ Scheduled crawler failed"
            )

            logger.info(
                "🔁 Service will continue running"
            )

        wait_with_dynamic_settings()


if __name__ == "__main__":
    main()