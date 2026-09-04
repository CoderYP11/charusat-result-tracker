"""Canonical, stable keys for a discovered (institute, degree, semester,
exam) result.

Why this exists: the original code joined names with "|" into a single
string (`f"{inst_name}|{degree_name}|{sem_id}|{exam_name}"`) and later
split it back apart with `item.split("|", 3)`. Two problems with that:

1. Any institute/degree name that itself contains "|" silently
   corrupts the split.
2. Keying on *names* means a portal-side rename (even a spacing/case
   change) makes the diff logic think every exam under that
   institute/degree is a brand-new result — a mass false alert.

This module keys on IDs wherever the portal gives us a stable one
(institute, degree, semester all have dropdown `value`s that are
IDs). The exam dropdown does not expose a separate ID in the markup
this project scrapes, so the exam name is kept — but as a JSON field,
never concatenated, so there's no delimiter to collide with.

NOTE ON MIGRATION: `known_results.json` in the repo today is keyed
with the *old* pipe-joined name format. Switching key formats is a
breaking change — see `migrate_keys.py` for a one-time converter, and
run it (or accept a one-time "everything looks new" alert burst) when
deploying this change.
"""

import json


def make_key(inst_id, inst_name, degree_id, degree_name, sem_id, exam_name):
    payload = {
        "inst_id": inst_id,
        "inst_name": inst_name,
        "degree_id": degree_id,
        "degree_name": degree_name,
        "sem_id": sem_id,
        "exam_name": exam_name,
    }
    # sort_keys makes the string deterministic so it can be used as a
    # set/dict key and compared run-to-run.
    return json.dumps(payload, sort_keys=True)


def parse_key(key):
    """Best-effort parse. Falls back to a stub dict for legacy
    pipe-joined keys so old entries don't crash formatting — they'll
    just display less richly until migrated."""
    try:
        return json.loads(key)
    except (json.JSONDecodeError, TypeError):
        return {
            "inst_name": key,
            "degree_name": "",
            "sem_id": "",
            "exam_name": "",
        }


def format_for_display(key):
    data = parse_key(key)
    return (
        f"🏫 Institute : {data.get('inst_name', '?')}\n"
        f"📚 Course    : {data.get('degree_name', '?')}\n"
        f"🎓 Semester  : {data.get('sem_id', '?')}\n"
        f"📄 Exam      : {data.get('exam_name', '?')}"
    )
