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
DELAY_MIN = float(os.environ.get("CRAWLER_DELAY_MIN", "0.15"))
DELAY_MAX = float(os.environ.get("CRAWLER_DELAY_MAX", "0.45"))

logger = logging.getLogger("scraper")


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
    response = session.get(URL, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


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
    response = session.post(URL, data=payload, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


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
