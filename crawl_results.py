import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from database import get_connection
from scraper import (
    fetch_home,
    get_viewstate,
    get_viewstate_generator,
    iter_options,
    new_session,
    postback,
)

MAX_WORKERS = int(os.environ.get("CRAWLER_WORKERS", "11"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("crawl_results")


# ============================================================
# DATABASE
# ============================================================

def get_institutes_from_db():
    """Load all seeded institutes from PostgreSQL."""

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name
                FROM institutes
                ORDER BY name
                """
            )

            return cur.fetchall()

    finally:
        conn.close()


def save_results_bulk(results):
    """
    Insert all discovered results in one PostgreSQL transaction.

    For genuinely NEW results:
        1. Insert result
        2. Create Telegram notification queue entries
           for all active subscribers

    Both operations happen inside the same transaction.

    Returns:
        List of genuinely NEW result tuples:
        [
            (institute_id, degree_id, semester_id, exam_name),
            ...
        ]
    """

    if not results:
        return []

    # Remove duplicates returned by the portal
    results = list(dict.fromkeys(results))

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            # ------------------------------------------------
            # 1. Insert new results
            # ------------------------------------------------

            values_sql = ", ".join(
                ["(%s, %s, %s, %s)"] * len(results)
            )

            params = []

            for row in results:
                params.extend(row)

            insert_query = f"""
                INSERT INTO results (
                    institute_id,
                    degree_id,
                    semester_id,
                    exam_name
                )
                VALUES {values_sql}

                ON CONFLICT (
                    institute_id,
                    degree_id,
                    semester_id,
                    exam_name
                )
                DO NOTHING

                RETURNING
                    id,
                    institute_id,
                    degree_id,
                    semester_id,
                    exam_name
            """

            cur.execute(
                insert_query,
                params,
            )

            inserted_rows = cur.fetchall()

            # Convert database rows back to the format
            # expected by the rest of crawl_results.py
            new_results = [
                (
                    row[1],  # institute_id
                    row[2],  # degree_id
                    row[3],  # semester_id
                    row[4],  # exam_name
                )
                for row in inserted_rows
            ]

            # ------------------------------------------------
            # 2. Create notification queue
            # ------------------------------------------------

            if inserted_rows:

                result_ids = [
                    row[0]
                    for row in inserted_rows
                ]

                queue_values_sql = ", ".join(
                    ["(%s)"] * len(result_ids)
                )

                queue_query = f"""
                    INSERT INTO notification_queue (
                        result_id,
                        chat_id
                    )
                    SELECT
                        v.result_id,
                        s.chat_id
                    FROM (
                        VALUES {queue_values_sql}
                    ) AS v(result_id)

                    CROSS JOIN subscribers s

                    WHERE s.is_active = TRUE

                    ON CONFLICT (result_id, chat_id)
                    DO NOTHING
                """

                cur.execute(
                    queue_query,
                    result_ids,
                )

            # ------------------------------------------------
            # 3. Update last_seen_at
            # ------------------------------------------------

            update_values_sql = ", ".join(
                ["(%s, %s, %s, %s)"] * len(results)
            )

            update_params = []

            for row in results:
                update_params.extend(row)

            update_query = f"""
                UPDATE results AS r

                SET last_seen_at = NOW()

                FROM (
                    VALUES {update_values_sql}
                ) AS incoming (
                    institute_id,
                    degree_id,
                    semester_id,
                    exam_name
                )

                WHERE r.institute_id = incoming.institute_id
                  AND r.degree_id = incoming.degree_id
                  AND r.semester_id = incoming.semester_id
                  AND r.exam_name = incoming.exam_name
            """

            cur.execute(
                update_query,
                update_params,
            )

        # ------------------------------------------------
        # 4. Commit everything together
        # ------------------------------------------------

        conn.commit()

        return new_results

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def get_db_result_count():
    """Return total unique results currently stored."""

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM results"
            )

            return cur.fetchone()[0]

    finally:
        conn.close()


# ============================================================
# CRAWLER
# ============================================================

def process_institute(institute_id, institute_name):
    """
    Crawl one complete institute.

    Institute
        -> Degree
            -> Semester
                -> Exam

    Returns:
        (institute_name, results)

    results is a list of database rows.
    """

    session = new_session()

    results = []

    logger.info(
        "🏫 Starting: %s [%s]",
        institute_name,
        institute_id,
    )

    # --------------------------------------------------------
    # Homepage
    # --------------------------------------------------------

    soup = fetch_home(session)

    generator = get_viewstate_generator(
        soup,
        context=institute_name,
    )

    viewstate = get_viewstate(
        soup,
        context=institute_name,
    )

    # --------------------------------------------------------
    # Institute
    # --------------------------------------------------------

    soup1 = postback(
        session,
        event_target="ddlInst",
        viewstate=viewstate,
        generator=generator,
        ddlInst=institute_id,
    )

    degree_select = soup1.find(
        id="ddlDegree"
    )

    if not degree_select:
        raise RuntimeError(
            f"ddlDegree not found for {institute_name}"
        )

    degrees = list(
        iter_options(degree_select)
    )

    logger.info(
        "📚 %s -> %d degrees",
        institute_name,
        len(degrees),
    )

    # --------------------------------------------------------
    # Degrees
    # --------------------------------------------------------

    for degree_id, degree_name in degrees:

        viewstate = get_viewstate(
            soup1,
            context=(
                f"{institute_name}/"
                f"{degree_name}"
            ),
        )

        soup2 = postback(
            session,
            event_target="ddlDegree",
            viewstate=viewstate,
            generator=generator,
            ddlInst=institute_id,
            ddlDegree=degree_id,
        )

        semester_select = soup2.find(
            id="ddlSem"
        )

        if not semester_select:
            logger.warning(
                "⚠️ No semesters: %s -> %s",
                institute_name,
                degree_name,
            )
            continue

        semesters = list(
            iter_options(semester_select)
        )

        # ----------------------------------------------------
        # Semesters
        # ----------------------------------------------------

        for semester_id, semester_name in semesters:

            viewstate = get_viewstate(
                soup2,
                context=(
                    f"{institute_name}/"
                    f"{degree_name}/"
                    f"{semester_name}"
                ),
            )

            soup3 = postback(
                session,
                event_target="ddlSem",
                viewstate=viewstate,
                generator=generator,
                ddlInst=institute_id,
                ddlDegree=degree_id,
                ddlSem=semester_id,
            )

            exam_select = soup3.find(
                id="ddlScheduleExam"
            )

            if not exam_select:
                continue

            exams = list(
                iter_options(exam_select)
            )

            # ------------------------------------------------
            # Exams / Results
            # ------------------------------------------------

            for _exam_value, exam_name in exams:

                results.append(
                    (
                        institute_id,
                        degree_id,
                        semester_id,
                        exam_name,
                    )
                )

    logger.info(
        "✅ Completed: %s | Results found: %d",
        institute_name,
        len(results),
    )

    return institute_name, results


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info("=" * 60)
    logger.info("🚀 CHARUSAT RESULT CRAWLER")
    logger.info("=" * 60)

    logger.info(
        "⚙️ Workers: %d",
        MAX_WORKERS,
    )

    # --------------------------------------------------------
    # Load institutes
    # --------------------------------------------------------

    institutes = get_institutes_from_db()

    if not institutes:
        raise RuntimeError(
            "No institutes found in PostgreSQL. "
            "Run seed_structure.py first."
        )

    logger.info(
        "🏫 Institutes loaded from PostgreSQL: %d",
        len(institutes),
    )

    # --------------------------------------------------------
    # Parallel crawling
    # --------------------------------------------------------

    total_discovered = 0
    total_saved = 0
    total_new = 0
    all_new_results = []
    failed = []

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        future_to_institute = {
            executor.submit(
                process_institute,
                institute_id,
                institute_name,
            ): (
                institute_id,
                institute_name,
            )
            for institute_id, institute_name in institutes
        }

        for future in as_completed(
            future_to_institute
        ):

            institute_id, institute_name = (
                future_to_institute[future]
            )

            try:

                name, results = future.result()

                total_discovered += len(results)

                new_results = save_results_bulk(results)

                total_saved += len(results)
                total_new += len(new_results)

                all_new_results.extend(new_results)
                

                logger.info(
                    "💾 Saved to PostgreSQL: %s | %d rows | 🆕 New: %d",
                    name,
                    len(results),
                    len(new_results),
                )
            except Exception as e:

                failed.append(institute_name)

                logger.error(
                    "❌ Failed: %s [%s] -> %s",
                    institute_name,
                    institute_id,
                    e,
                )

    # --------------------------------------------------------
    # Final DB count
    # --------------------------------------------------------

    db_result_count = get_db_result_count()

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ CRAWL COMPLETE")
    logger.info("=" * 60)

    logger.info(
        "🔎 Results discovered this run : %d",
        total_discovered,
    )

    logger.info(
        "💾 Rows processed into DB      : %d",
        total_saved,
    )

    logger.info(
        "📊 Unique results currently DB : %d",
        db_result_count,
    )

    logger.info(
        "🏫 Failed institutes            : %d/%d",
        len(failed),
        len(institutes),
    )

    logger.info(
        "🆕 New results this run       : %d",
        total_new,
    )

    # --------------------------------------------------------
# Send Telegram notifications
# --------------------------------------------------------

    if all_new_results:
        logger.info("")
        logger.info("🆕 NEW RESULTS:")

        for (
            institute_id,
            degree_id,
            semester_id,
            exam_name,
        ) in all_new_results:

            logger.info(
                "   %s | %s | %s | %s",
                institute_id,
                degree_id,
                semester_id,
                exam_name,
            )

    if failed:
        logger.warning(
            "⚠️ Failed: %s",
            ", ".join(failed),
        )

    logger.info("=" * 60)


if __name__ == "__main__":
    main()