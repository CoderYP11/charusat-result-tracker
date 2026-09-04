import logging

from database import (
    upsert_degree,
    upsert_institute,
    upsert_semester,
)
from scraper import (
    fetch_home,
    get_viewstate,
    get_viewstate_generator,
    iter_options,
    new_session,
    postback,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logger = logging.getLogger("seed_structure")


def seed_structure():
    logger.info("🌐 Fetching CHARUSAT portal...")

    session = new_session()

    soup = fetch_home(session)

    generator = get_viewstate_generator(
        soup,
        context="structure",
    )

    inst_select = soup.find(id="ddlInst")

    if not inst_select:
        raise RuntimeError(
            "Portal layout error: ddlInst not found."
        )

    institutes = list(iter_options(inst_select))

    logger.info(
        "🏫 Institutes discovered: %d",
        len(institutes),
    )

    total_degrees = 0
    total_semesters = 0

    for inst_id, inst_name in institutes:

        logger.info(
            "\n🏫 %s [%s]",
            inst_name,
            inst_id,
        )

        # Save institute
        upsert_institute(
            inst_id,
            inst_name,
        )

        # Get fresh viewstate
        viewstate = get_viewstate(
            soup,
            context=inst_name,
        )

        # Select institute
        soup1 = postback(
            session,
            event_target="ddlInst",
            viewstate=viewstate,
            generator=generator,
            ddlInst=inst_id,
        )

        degree_select = soup1.find(
            id="ddlDegree"
        )

        if not degree_select:
            logger.warning(
                "   ⚠️ No degrees found."
            )
            continue

        degrees = list(
            iter_options(degree_select)
        )

        for degree_id, degree_name in degrees:

            total_degrees += 1

            logger.info(
                "   📚 %s [%s]",
                degree_name,
                degree_id,
            )

            # Save degree
            upsert_degree(
                degree_id,
                inst_id,
                degree_name,
            )

            viewstate = get_viewstate(
                soup1,
                context=f"{inst_name}/{degree_name}",
            )

            # Select degree
            soup2 = postback(
                session,
                event_target="ddlDegree",
                viewstate=viewstate,
                generator=generator,
                ddlInst=inst_id,
                ddlDegree=degree_id,
            )

            semester_select = soup2.find(
                id="ddlSem"
            )

            if not semester_select:
                logger.warning(
                    "      ⚠️ No semesters found."
                )
                continue

            semesters = list(
                iter_options(semester_select)
            )

            for sem_id, sem_name in semesters:

                total_semesters += 1

                logger.info(
                    "      🎓 %s [%s]",
                    sem_name,
                    sem_id,
                )

                upsert_semester(
                    sem_id,
                    degree_id,
                    sem_name,
                )

    logger.info("\n" + "=" * 50)
    logger.info("✅ STRUCTURE SEED COMPLETE")
    logger.info("=" * 50)
    logger.info(
        "🏫 Institutes : %d",
        len(institutes),
    )
    logger.info(
        "📚 Degrees    : %d",
        total_degrees,
    )
    logger.info(
        "🎓 Semesters  : %d",
        total_semesters,
    )


if __name__ == "__main__":
    seed_structure()