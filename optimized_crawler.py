"""
optimized_crawler.py
~~~~~~~~~~~~~~~~~~~~~
Faster replacement for crawler.py.

Key improvements over the original:
  1. Uses the pre-built structure.json so we never re-crawl the
     inst / degree dropdown tree – that alone saves ~N_degrees * 2
     round-trips per run.
  2. Fetches the page ONCE at startup to grab __VIEWSTATE and
     __VIEWSTATEGENERATOR, then reuses them.  ASP.NET ViewState is
     only needed for the *next* postback; once we have the exam
     dropdown we don't POST again, so a single baseline state is
     enough for all parallel workers.
  3. Probes inst→degree→sem in parallel with a ThreadPoolExecutor.
     Each worker does the minimum two POSTs required to reach the
     exam dropdown (ddlDegree POST, then ddlSem POST) and extracts
     exam names – no extra GETs.
  4. Removes the fixed sleep; a configurable per-thread delay
     (default 0 s) plus connection pooling via requests.Session
     shared across threads keeps the server happy while maximising
     throughput.
"""

from __future__ import annotations

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import requests
from bs4 import BeautifulSoup

URL = "https://support.charusat.edu.in/Uniexamresult/"

# How many threads to use.  The site is a single IIS box; keep this
# conservative to avoid triggering rate-limiting.  12–16 is a sweet
# spot in practice.
MAX_WORKERS = 12

# Optional per-request delay (seconds) inside each worker.
WORKER_DELAY = 0.0

# ---------------------------------------------------------------------------
# Thread-safe session pool
# ---------------------------------------------------------------------------

_local = threading.local()


def _get_session() -> requests.Session:
    """Return a per-thread Session (created lazily)."""
    if not hasattr(_local, "session"):
        s = requests.Session()
        # Increase pool size so threads don't block waiting for a socket.
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=MAX_WORKERS,
            pool_maxsize=MAX_WORKERS,
            max_retries=2,
        )
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        _local.session = s
    return _local.session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_base_state() -> tuple[str, str]:
    """
    Do ONE GET to the result page and return (viewstate, generator).
    Both values are static across the entire crawl because we never
    need to submit a form that changes page structure – we only read
    the exam dropdown which is populated by a POST that returns its
    own fresh viewstate we throw away after reading.
    """
    html = requests.get(URL, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")
    viewstate  = soup.find(id="__VIEWSTATE")["value"]
    generator  = soup.find(id="__VIEWSTATEGENERATOR")["value"]
    return viewstate, generator


def _post(
    session: requests.Session,
    payload: dict,
    retries: int = 2,
) -> Optional[BeautifulSoup]:
    """POST and return a BeautifulSoup, or None on persistent failure."""
    for attempt in range(retries + 1):
        try:
            resp = session.post(URL, data=payload, timeout=30)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception:
            if attempt == retries:
                return None
            time.sleep(0.5 * (attempt + 1))
    return None


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

def _probe_semester(
    inst_id: str,
    inst_name: str,
    degree_id: str,
    degree_name: str,
    sem_id: str,
    viewstate: str,
    generator: str,
) -> list[str]:
    """
    Execute the two POSTs needed to reach the exam dropdown for one
    (inst, degree, sem) combination and return a list of result keys.

    POST 1 – select degree  → gives us a new viewstate + ddlSem
    POST 2 – select sem     → gives us ddlScheduleExam

    We only need POST 1 when inst+degree hasn't been fetched yet, but
    since threads are independent it's simpler (and still fast) to
    always do both.  The cost is one extra POST per semester vs the
    original sequential code – which required the same two POSTs plus
    an initial GET.
    """
    session = _get_session()

    if WORKER_DELAY:
        time.sleep(WORKER_DELAY)

    # ── POST 1: select the degree ──────────────────────────────────────────
    payload1 = {
        "__EVENTTARGET":        "ddlDegree",
        "__EVENTARGUMENT":      "",
        "__VIEWSTATE":          viewstate,
        "__VIEWSTATEGENERATOR": generator,
        "ddlInst":              inst_id,
        "ddlDegree":            degree_id,
        "txtEnrNo":             "",
    }
    soup1 = _post(session, payload1)
    if soup1 is None:
        return []

    vs1_tag = soup1.find(id="__VIEWSTATE")
    if vs1_tag is None:
        return []
    viewstate1 = vs1_tag["value"]

    # ── POST 2: select the semester ────────────────────────────────────────
    payload2 = {
        "__EVENTTARGET":        "ddlSem",
        "__EVENTARGUMENT":      "",
        "__VIEWSTATE":          viewstate1,
        "__VIEWSTATEGENERATOR": generator,
        "ddlInst":              inst_id,
        "ddlDegree":            degree_id,
        "ddlSem":               sem_id,
        "txtEnrNo":             "",
    }
    soup2 = _post(session, payload2)
    if soup2 is None:
        return []

    exam_select = soup2.find(id="ddlScheduleExam")
    if not exam_select:
        return []

    keys: list[str] = []
    for opt in exam_select.find_all("option"):
        exam_name = opt.text.strip()
        if exam_name and exam_name != "Select...":
            keys.append(
                f"{inst_name}|{degree_name}|{sem_id}|{exam_name}"
            )

    return keys


# ---------------------------------------------------------------------------
# Public API  (same signature as the original crawler)
# ---------------------------------------------------------------------------

def discover_all_results(structure: dict | None = None) -> dict:
    """
    Return a dict mapping result-key → True for every exam currently
    visible on the CHARUSAT result portal.

    Parameters
    ----------
    structure : dict, optional
        Pre-loaded structure.json content.  When supplied the function
        skips the dropdown-tree discovery phase entirely and goes
        straight to probing semesters – this is the fast path used by
        monitor.py.  When omitted the function falls back to the
        original full-crawl behaviour (useful for build_structure.py).
    """
    results: dict[str, bool] = {}

    # ── One-time baseline state ────────────────────────────────────────────
    viewstate, generator = _fetch_base_state()

    if structure:
        # ── Fast path: structure already known ────────────────────────────
        tasks: list[tuple] = []
        for inst_id, inst_data in structure.items():
            inst_name = inst_data["name"]
            for degree_id, degree_data in inst_data["degrees"].items():
                degree_name = degree_data["name"]
                for sem_id in degree_data["semesters"]:
                    tasks.append(
                        (inst_id, inst_name, degree_id, degree_name, sem_id)
                    )

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(
                    _probe_semester,
                    inst_id, inst_name, degree_id, degree_name, sem_id,
                    viewstate, generator,
                ): (inst_name, degree_name, sem_id)
                for inst_id, inst_name, degree_id, degree_name, sem_id in tasks
            }
            for future in as_completed(futures):
                for key in future.result():
                    results[key] = True

    else:
        # ── Fallback: discover structure on the fly ────────────────────────
        # This replicates the original crawler logic but still uses the
        # thread pool for the innermost (semester) loop.
        session = _get_session()

        html = session.get(URL, timeout=30).text
        soup = BeautifulSoup(html, "html.parser")

        inst_select = soup.find(id="ddlInst")
        if not inst_select:
            return results

        for inst_option in inst_select.find_all("option"):
            inst_id   = inst_option.get("value", "").strip()
            inst_name = inst_option.text.strip()
            if not inst_id or inst_id == "0":
                continue

            # Refresh page to get a clean viewstate for this inst
            html = session.get(URL, timeout=30).text
            soup = BeautifulSoup(html, "html.parser")
            vs   = soup.find(id="__VIEWSTATE")["value"]

            payload_inst = {
                "__EVENTTARGET":        "ddlInst",
                "__EVENTARGUMENT":      "",
                "__VIEWSTATE":          vs,
                "__VIEWSTATEGENERATOR": generator,
                "ddlInst":              inst_id,
                "ddlDegree":            "0",
                "txtEnrNo":             "",
            }
            soup1 = _post(session, payload_inst)
            if soup1 is None:
                continue

            degree_select = soup1.find(id="ddlDegree")
            if not degree_select:
                continue

            vs1 = soup1.find(id="__VIEWSTATE")["value"]

            tasks_for_inst: list[tuple] = []
            for deg_option in degree_select.find_all("option"):
                degree_id   = deg_option.get("value", "").strip()
                degree_name = deg_option.text.strip()
                if not degree_id or degree_id == "0":
                    continue

                payload_deg = {
                    "__EVENTTARGET":        "ddlDegree",
                    "__EVENTARGUMENT":      "",
                    "__VIEWSTATE":          vs1,
                    "__VIEWSTATEGENERATOR": generator,
                    "ddlInst":              inst_id,
                    "ddlDegree":            degree_id,
                    "txtEnrNo":             "",
                }
                soup2 = _post(session, payload_deg)
                if soup2 is None:
                    continue

                sem_select = soup2.find(id="ddlSem")
                if not sem_select:
                    continue

                vs2 = soup2.find(id="__VIEWSTATE")["value"]
                for sem_option in sem_select.find_all("option"):
                    sem_id = sem_option.get("value", "").strip()
                    if not sem_id or sem_id == "0":
                        continue
                    tasks_for_inst.append(
                        (inst_id, inst_name, degree_id, degree_name, sem_id, vs2)
                    )

            # Submit all semesters for this institution concurrently
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                futures = {
                    pool.submit(
                        _probe_semester,
                        inst_id, inst_name, degree_id, degree_name, sem_id,
                        sem_vs, generator,
                    ): sem_id
                    for inst_id, inst_name, degree_id, degree_name, sem_id, sem_vs
                    in tasks_for_inst
                }
                for future in as_completed(futures):
                    for key in future.result():
                        results[key] = True

    return results

if __name__ == "__main__":

    try:
        from github_state import load_structure

        structure = load_structure()

        results = discover_all_results(
            structure=structure
        )

        print(
            f"TOTAL RESULTS: {len(results)}"
        )

    except Exception as e:

        print(
            f"ERROR: {e}"
        )
