"""Builds a snapshot of Institute -> Degree -> Semesters and saves it
as structure.json.

STATUS: nothing else in this project currently reads structure.json —
the crawler (`parallel_crawler_v1.py`) derives everything live on
every run instead. This script is kept because it's cheap and useful
for two things that *aren't* wired in yet:

  1. A future crawl-shortcut/pruning source (skip re-walking degrees
     you already know a given institute has).
  2. Detecting institute/degree renames between runs, which is exactly
     the situation that produces false "new result" alerts under a
     name-keyed diff (see result_keys.py's docstring).

If neither of those gets built, delete this file — don't let it keep
existing just because it once did.
"""

import logging

from github_state import save_structure
from scraper import fetch_home, get_viewstate, get_viewstate_generator, iter_options, new_session, postback

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("build_structure")


def build_structure():
    session = new_session()
    soup = fetch_home(session)  # single GET — the original re-fetched this inside every institute loop

    generator = get_viewstate_generator(soup)
    inst_select = soup.find(id="ddlInst")

    structure = {}

    for inst_id, inst_name in iter_options(inst_select):
        viewstate = get_viewstate(soup, context=inst_name)

        soup1 = postback(
            session,
            event_target="ddlInst",
            viewstate=viewstate,
            generator=generator,
            ddlInst=inst_id,
        )

        structure[inst_id] = {"name": inst_name, "degrees": {}}

        degree_select = soup1.find(id="ddlDegree")

        for degree_id, degree_name in iter_options(degree_select):
            viewstate = get_viewstate(soup1, context=f"{inst_name}/{degree_name}")

            soup2 = postback(
                session,
                event_target="ddlDegree",
                viewstate=viewstate,
                generator=generator,
                ddlInst=inst_id,
                ddlDegree=degree_id,
            )

            semester_select = soup2.find(id="ddlSem")
            semesters = [sem_id for sem_id, _ in iter_options(semester_select)]

            structure[inst_id]["degrees"][degree_id] = {
                "name": degree_name,
                "semesters": semesters,
            }

    return structure


def main():
    structure = build_structure()
    saved_ok = save_structure(structure)

    total_degrees = sum(len(inst["degrees"]) for inst in structure.values())
    total_semesters = sum(
        len(degree["semesters"])
        for inst in structure.values()
        for degree in inst["degrees"].values()
    )

    logger.info("Institutions: %d", len(structure))
    logger.info("Degrees: %d", total_degrees)
    logger.info("Semesters: %d", total_semesters)
    logger.info("structure.json %s", "saved to GitHub" if saved_ok else "save FAILED — see errors above")


if __name__ == "__main__":
    main()
