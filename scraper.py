"""Shared ASP.NET postback client for the CHARUSAT result portal.

Both `parallel_crawler_v1.py` and `build_structure.py` drive the same
Institute -> Degree -> Semester -> Exam postback chain against
support.charusat.edu.in. Previously that chain was implemented twice
(~80% duplicated code) — any change to the site's markup meant fixing
it in two places. It now lives here once.

This module also owns "politeness": the portal is shared university
infrastructure, and 11 threads firing postbacks back-to-back risks a
block that would silently kill the tracker with no error visible
anywhere. A small randomized delay is added before every request.
"""

import logging
import os
import random
import time

import requests
from bs4 import BeautifulSoup

URL = "https://support.charusat.edu.in/Uniexamresult/"

USER_AGENT = (
    "Mozilla/5.0 (compatible; CharusatResultTracker/1.0; "
    "+https://github.com/CoderYP11/charusat-result-tracker)"
)

# Delay range (seconds) inserted before every GET/POST, per worker.
# Overridable via env vars so this can be tuned without a code change.
DELAY_MIN = float(os.environ.get("CRAWLER_DELAY_MIN", "0.05"))
DELAY_MAX = float(os.environ.get("CRAWLER_DELAY_MAX", "0.10"))

REQUEST_TIMEOUT = 30
RETRY_COUNT = 3
RETRY_DELAY = 5

RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}

logger = logging.getLogger("scraper")

def configure_request_settings(
    retry_count=3,
    retry_delay_seconds=5,
    request_timeout_seconds=30,
):
    """
    Configure scraper request behavior at runtime.

    Values are loaded from PostgreSQL by the crawler and applied
    before worker threads are started.
    """
    global RETRY_COUNT
    global RETRY_DELAY
    global REQUEST_TIMEOUT

    RETRY_COUNT = max(0, int(retry_count))
    RETRY_DELAY = max(0, float(retry_delay_seconds))
    REQUEST_TIMEOUT = max(1, float(request_timeout_seconds))

    logger.info(
        "⚙️ Request settings | retries=%d | retry_delay=%ss | timeout=%ss",
        RETRY_COUNT,
        RETRY_DELAY,
        REQUEST_TIMEOUT,
    )


class PortalLayoutError(Exception):
    """Raised when an expected form control is missing from the HTML.

    This almost always means the portal's page layout changed, not a
    transient network issue — it's raised instead of a raw KeyError so
    callers can log/alert on it distinctly.
    """


def new_session():
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def _sleep_politely():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

def _request_with_retry(session, method, **kwargs):
    """
    Execute an HTTP request with configurable retries.

    RETRY_COUNT means the number of retries AFTER the initial attempt.
    Therefore retry_count=3 allows up to 4 total attempts.
    """

    kwargs.setdefault("timeout", REQUEST_TIMEOUT)

    total_attempts = RETRY_COUNT + 1

    for attempt in range(total_attempts):
        try:
            response = session.request(
                method,
                URL,
                **kwargs,
            )

            if response.status_code not in RETRYABLE_STATUS_CODES:
                response.raise_for_status()
                return response

            if attempt >= RETRY_COUNT:
                response.raise_for_status()

            logger.warning(
                "⚠️ HTTP %s on attempt %d/%d; retrying in %ss",
                response.status_code,
                attempt + 1,
                total_attempts,
                RETRY_DELAY,
            )

        except requests.exceptions.RequestException as exc:

            if attempt >= RETRY_COUNT:
                raise

            logger.warning(
                "⚠️ Request failed on attempt %d/%d: %s; retrying in %ss",
                attempt + 1,
                total_attempts,
                exc,
                RETRY_DELAY,
            )

        time.sleep(RETRY_DELAY)

    raise RuntimeError("Request retry loop exited unexpectedly")


def get_viewstate(soup, context=""):
    node = soup.find(id="__VIEWSTATE")
    if node is None or not node.get("value"):
        suffix = f" ({context})" if context else ""
        raise PortalLayoutError(f"__VIEWSTATE missing{suffix} — portal markup may have changed")
    return node["value"]


def get_viewstate_generator(soup, context=""):
    node = soup.find(id="__VIEWSTATEGENERATOR")
    if node is None or not node.get("value"):
        suffix = f" ({context})" if context else ""
        raise PortalLayoutError(f"__VIEWSTATEGENERATOR missing{suffix}")
    return node["value"]


def fetch_home(session):
    """GET the landing page once. Callers must not re-GET it per loop
    iteration just to refresh __VIEWSTATE — a single fetch is enough,
    and the VIEWSTATE returned by each subsequent postback response
    should be used for the next postback in that chain instead.
    """
    _sleep_politely()

    response = _request_with_retry(
        session,
        "GET",
    )

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


def postback(session, event_target, viewstate, generator, **fields):
    """Submit one ASP.NET postback and return the parsed response.

    `fields` should supply whichever of ddlInst/ddlDegree/ddlSem are
    relevant to this step; anything not passed defaults to "0".
    """
    payload = {
        "__EVENTTARGET": event_target,
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": viewstate,
        "__VIEWSTATEGENERATOR": generator,
        "ddlInst": "0",
        "ddlDegree": "0",
        "ddlSem": "0",
        "txtEnrNo": "",
    }
    payload.update(fields)

    _sleep_politely()

    response = _request_with_retry(
        session,
        "POST",
        data=payload,
    )

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


def iter_options(select_tag):
    """Yield (value, text) for real options in a <select>, skipping
    blank values and the "0" placeholder used throughout this portal
    (previously each dropdown had its own ad-hoc, slightly different
    filter — e.g. the exam dropdown matched on the label text
    "Select..." instead, which breaks if that label is ever localized
    or reworded).
    """
    if select_tag is None:
        return
    for option in select_tag.find_all("option"):
        value = option.get("value", "").strip()
        text = option.text.strip()
        if not value or value == "0":
            continue
        yield value, text
