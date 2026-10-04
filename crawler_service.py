import logging
import os
import subprocess
import sys
import time

from database import get_setting, set_setting

# crawl_results is intentionally NOT imported here any more: each crawl
# runs in its own child process (see run_crawler_isolated), so
#   * a hung crawl can be killed, which frees its DB lock instantly,
#   * every crawl re-reads the dashboard settings on start.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("crawler_service")


CHECK_INTERVAL_SECONDS = 10

# Hard ceiling for one crawl. A healthy run finishes far sooner; if the
# child is still alive after this it is hung and gets SIGKILLed.
MAX_RUN_SECONDS = 20 * 60

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CRAWLER_SCRIPT = os.path.join(_BASE_DIR, "crawl_results.py")

EXIT_OK = 0
EXIT_BUSY = 2


def run_crawler_isolated(triggered_by):
    """
    Run one crawl in a child process with a hard timeout.

    Returns "ok", "busy" (another crawl holds the lock), "timeout"
    or "failed". When the child is killed, PostgreSQL releases its
    advisory lock immediately because its connection dies with it, and
    the next crawl marks the orphaned run as cancelled.
    """
    try:
        proc = subprocess.run(
            [sys.executable, _CRAWLER_SCRIPT, triggered_by],
            cwd=_BASE_DIR,
            timeout=MAX_RUN_SECONDS,
        )

    except subprocess.TimeoutExpired:
        logger.error(
            "⏱️ Crawl exceeded %d seconds and was killed",
            MAX_RUN_SECONDS,
        )
        return "timeout"

    if proc.returncode == EXIT_OK:
        return "ok"

    if proc.returncode == EXIT_BUSY:
        return "busy"

    logger.error(
        "❌ Crawler process exited with code %s",
        proc.returncode,
    )
    return "failed"

def check_manual_trigger():
    """
    Check whether a manual crawl has been requested
    from the dashboard.
    """

    triggered = bool(
        get_setting("crawler.manual_trigger", False)
    )

    if not triggered:
        return False

    logger.info("🖱️ Manual crawl trigger received from dashboard")

    # Consume the trigger before starting the crawl so that
    # the same request cannot be executed repeatedly.
    set_setting(
        "crawler.manual_trigger",
        False,
        updated_by="crawler_service",
    )

    return True


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

        if check_manual_trigger():
            logger.info(
                "▶️ Starting manual crawl"
            )

            outcome = run_crawler_isolated("manual")

            if outcome == "ok":
                logger.info(
                    "✅ Manual crawl finished"
                )

            elif outcome == "busy":
                # Another crawl holds the lock. Put the request back so
                # it runs as soon as the lock is free, instead of being
                # silently dropped.
                logger.warning(
                    "⏭️ Manual crawl postponed: another crawl is running"
                )

                set_setting(
                    "crawler.manual_trigger",
                    True,
                    updated_by="crawler_service",
                )

                time.sleep(CHECK_INTERVAL_SECONDS)

            continue

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

            outcome = run_crawler_isolated("scheduled")

            if outcome == "ok":
                logger.info(
                    "✅ Scheduled crawl finished"
                )

            elif outcome == "busy":
                logger.warning(
                    "⏭️ Scheduled crawl skipped: another crawl is running"
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