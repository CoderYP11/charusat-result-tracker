import os
from contextlib import contextmanager

import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv


load_dotenv()


# ============================================================
# Database connection
# ============================================================

def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


@contextmanager
def get_db():
    conn = get_connection()

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ============================================================
# Institutes
# ============================================================

def upsert_institute(inst_id, inst_name):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO institutes (id, name)
                VALUES (%s, %s)
                ON CONFLICT (id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    updated_at = NOW()
                """,
                (str(inst_id), inst_name),
            )


# ============================================================
# Degrees
# ============================================================

def upsert_degree(degree_id, institute_id, degree_name):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO degrees (id, institute_id, name)
                VALUES (%s, %s, %s)
                ON CONFLICT (id)
                DO UPDATE SET
                    institute_id = EXCLUDED.institute_id,
                    name = EXCLUDED.name,
                    updated_at = NOW()
                """,
                (
                    str(degree_id),
                    str(institute_id),
                    degree_name,
                ),
            )


# ============================================================
# Semesters
# ============================================================

def upsert_semester(semester_id, degree_id, semester_name=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO semesters (id, degree_id, name)
                VALUES (%s, %s, %s)
                ON CONFLICT (degree_id, id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    updated_at = NOW()
                """,
                (
                    str(semester_id),
                    str(degree_id),
                    semester_name,
                ),
            )


# ============================================================
# Results
# ============================================================

def result_exists(
    institute_id,
    degree_id,
    semester_id,
    exam_name,
):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM results
                WHERE institute_id = %s
                  AND degree_id = %s
                  AND semester_id = %s
                  AND exam_name = %s
                LIMIT 1
                """,
                (
                    str(institute_id),
                    str(degree_id),
                    str(semester_id),
                    exam_name,
                ),
            )

            return cur.fetchone() is not None


def insert_result(
    institute_id,
    degree_id,
    semester_id,
    exam_name,
):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO results (
                    institute_id,
                    degree_id,
                    semester_id,
                    exam_name
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (
                    institute_id,
                    degree_id,
                    semester_id,
                    exam_name
                )
                DO UPDATE SET
                    last_seen_at = NOW()
                RETURNING id
                """,
                (
                    str(institute_id),
                    str(degree_id),
                    str(semester_id),
                    exam_name,
                ),
            )

            row = cur.fetchone()
            return row[0] if row else None


def get_all_results():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    institute_id,
                    degree_id,
                    semester_id,
                    exam_name
                FROM results
                """
            )

            return cur.fetchall()


def get_result_count():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM results")
            return cur.fetchone()[0]


# ============================================================
# Subscribers
# ============================================================

def add_subscriber(chat_id, username=None, first_name=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO subscribers (
                    chat_id,
                    username,
                    first_name,
                    is_active
                )
                VALUES (%s, %s, %s, TRUE)
                ON CONFLICT (chat_id)
                DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    is_active = TRUE,
                    updated_at = NOW()
                """,
                (
                    int(chat_id),
                    username,
                    first_name,
                ),
            )


def remove_subscriber(chat_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE subscribers
                SET
                    is_active = FALSE,
                    updated_at = NOW()
                WHERE chat_id = %s
                """,
                (int(chat_id),),
            )


def set_subscriber_status(chat_id, is_active):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE subscribers
                SET
                    is_active = %s,
                    updated_at = NOW()
                WHERE chat_id = %s
                """,
                (
                    bool(is_active),
                    int(chat_id),
                ),
            )

            return cur.rowcount > 0


def get_active_subscribers():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT chat_id
                FROM subscribers
                WHERE is_active = TRUE
                ORDER BY created_at
                """
            )

            return [row[0] for row in cur.fetchall()]


def get_all_subscribers():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    chat_id,
                    username,
                    first_name,
                    is_active,
                    created_at,
                    updated_at
                FROM subscribers
                ORDER BY created_at
                """
            )

            return cur.fetchall()


def is_subscribed(chat_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM subscribers
                WHERE chat_id = %s
                  AND is_active = TRUE
                LIMIT 1
                """,
                (int(chat_id),),
            )

            return cur.fetchone() is not None


def get_subscriber_count():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM subscribers
                WHERE is_active = TRUE
                """
            )

            return cur.fetchone()[0]


def get_total_subscriber_count():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM subscribers
                """
            )

            return cur.fetchone()[0]


# ============================================================
# Telegram State
# ============================================================

def get_telegram_offset():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT update_offset
                FROM telegram_state
                WHERE id = 1
                """
            )

            row = cur.fetchone()

            if row is None:
                return 0

            return row[0]


def save_telegram_offset(offset):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO telegram_state (
                    id,
                    update_offset
                )
                VALUES (1, %s)
                ON CONFLICT (id)
                DO UPDATE SET
                    update_offset = EXCLUDED.update_offset,
                    updated_at = NOW()
                """,
                (int(offset),),
            )


# ============================================================
# Application Settings
# ============================================================

def get_setting(key, default=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT value
                FROM settings
                WHERE key = %s
                LIMIT 1
                """,
                (key,),
            )

            row = cur.fetchone()

            if row is None:
                return default

            return row[0]


def get_settings(prefix=None):
    with get_db() as conn:
        with conn.cursor() as cur:

            if prefix:
                cur.execute(
                    """
                    SELECT key, value
                    FROM settings
                    WHERE key LIKE %s
                    ORDER BY key
                    """,
                    (f"{prefix}%",),
                )
            else:
                cur.execute(
                    """
                    SELECT key, value
                    FROM settings
                    ORDER BY key
                    """
                )

            return {
                row[0]: row[1]
                for row in cur.fetchall()
            }


def set_setting(key, value, updated_by=None):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO settings (
                    key,
                    value,
                    updated_at,
                    updated_by
                )
                VALUES (%s, %s, NOW(), %s)
                ON CONFLICT (key)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = NOW(),
                    updated_by = EXCLUDED.updated_by
                RETURNING key, value
                """,
                (
                    key,
                    Jsonb(value),
                    updated_by,
                ),
            )

            return cur.fetchone()


def set_settings(settings, updated_by=None):
    if not settings:
        return

    with get_db() as conn:
        with conn.cursor() as cur:

            for key, value in settings.items():
                cur.execute(
                    """
                    INSERT INTO settings (
                        key,
                        value,
                        updated_at,
                        updated_by
                    )
                    VALUES (%s, %s, NOW(), %s)
                    ON CONFLICT (key)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = NOW(),
                        updated_by = EXCLUDED.updated_by
                    """,
                    (
                        key,
                        Jsonb(value),
                        updated_by,
                    ),
                )


def delete_setting(key):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM settings
                WHERE key = %s
                """,
                (key,),
            )

            return cur.rowcount > 0


# ============================================================
# Crawl Runs
# ============================================================

def create_crawl_run(
    triggered_by=None,
    workers=None,
    institutes_total=0,
):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO crawl_runs (
                    status,
                    started_at,
                    triggered_by,
                    workers,
                    institutes_total
                )
                VALUES (
                    'running',
                    NOW(),
                    %s,
                    %s,
                    %s
                )
                RETURNING id
                """,
                (
                    triggered_by,
                    workers,
                    institutes_total,
                ),
            )

            return cur.fetchone()[0]


def update_crawl_run(
    run_id,
    status=None,
    completed_at=None,
    duration_ms=None,
    institutes_completed=None,
    institutes_failed=None,
    results_discovered=None,
    results_new=None,
    error_message=None,
):
    updates = []
    params = []

    values = {
        "status": status,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "institutes_completed": institutes_completed,
        "institutes_failed": institutes_failed,
        "results_discovered": results_discovered,
        "results_new": results_new,
        "error_message": error_message,
    }

    for field, value in values.items():
        if value is not None:
            updates.append(f"{field} = %s")
            params.append(value)

    if not updates:
        return False

    params.append(run_id)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE crawl_runs
                SET {", ".join(updates)}
                WHERE id = %s
                """,
                params,
            )

            return cur.rowcount > 0


def get_crawl_run(run_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    status,
                    started_at,
                    completed_at,
                    duration_ms,
                    workers,
                    institutes_total,
                    institutes_completed,
                    institutes_failed,
                    results_discovered,
                    results_new,
                    error_message,
                    triggered_by
                FROM crawl_runs
                WHERE id = %s
                """,
                (run_id,),
            )

            return cur.fetchone()


def get_latest_crawl_run():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    status,
                    started_at,
                    completed_at,
                    duration_ms,
                    workers,
                    institutes_total,
                    institutes_completed,
                    institutes_failed,
                    results_discovered,
                    results_new,
                    error_message,
                    triggered_by
                FROM crawl_runs
                ORDER BY id DESC
                LIMIT 1
                """
            )

            return cur.fetchone()


def get_running_crawl_run():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    status,
                    started_at,
                    completed_at,
                    duration_ms,
                    workers,
                    institutes_total,
                    institutes_completed,
                    institutes_failed,
                    results_discovered,
                    results_new,
                    error_message,
                    triggered_by
                FROM crawl_runs
                WHERE status = 'running'
                ORDER BY id DESC
                LIMIT 1
                """
            )

            return cur.fetchone()


def get_crawl_runs(limit=50, offset=0):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    status,
                    started_at,
                    completed_at,
                    duration_ms,
                    workers,
                    institutes_total,
                    institutes_completed,
                    institutes_failed,
                    results_discovered,
                    results_new,
                    error_message,
                    triggered_by
                FROM crawl_runs
                ORDER BY id DESC
                LIMIT %s
                OFFSET %s
                """,
                (
                    int(limit),
                    int(offset),
                ),
            )

            return cur.fetchall()


# ============================================================
# Activity / Audit Logs
# ============================================================

def log_activity(
    level,
    action,
    message,
    actor=None,
    target=None,
    details=None,
):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO activity_logs (
                    level,
                    actor,
                    action,
                    target,
                    message,
                    details
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    level,
                    actor,
                    action,
                    target,
                    message,
                    Jsonb(details) if details is not None else None,
                ),
            )

            return cur.fetchone()[0]


def get_activity_logs(
    limit=100,
    offset=0,
    level=None,
    action=None,
    actor=None,
):
    with get_db() as conn:
        with conn.cursor() as cur:

            conditions = []
            params = []

            if level:
                conditions.append("level = %s")
                params.append(level)

            if action:
                conditions.append("action = %s")
                params.append(action)

            if actor:
                conditions.append("actor = %s")
                params.append(actor)

            where_clause = ""

            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            params.extend([
                int(limit),
                int(offset),
            ])

            cur.execute(
                f"""
                SELECT
                    id,
                    level,
                    actor,
                    action,
                    target,
                    message,
                    details,
                    created_at
                FROM activity_logs
                {where_clause}
                ORDER BY id DESC
                LIMIT %s
                OFFSET %s
                """,
                params,
            )

            return cur.fetchall()

def get_activity_log_count(
    level=None,
    action=None,
):
    with get_db() as conn:
        with conn.cursor() as cur:

            conditions = []
            params = []

            if level:
                conditions.append("level = %s")
                params.append(level)

            if action:
                conditions.append("action = %s")
                params.append(action)

            where_clause = ""

            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM activity_logs
                {where_clause}
                """,
                params,
            )

            return cur.fetchone()[0]


def log_event(
    level,
    event_type,
    message,
    failed_institutes=None,
    actor="system",
):
    """
    Backward-compatible logging wrapper.

    Existing crawler/bot code can continue using log_event().
    Logs are stored in activity_logs.
    """

    details = None

    if failed_institutes is not None:
        details = {
            "failed_institutes": failed_institutes
        }

    return log_activity(
        level=level,
        action=event_type,
        message=message,
        details=details,
        actor=actor,
    )


# ============================================================
# Admin Users
# ============================================================

def create_admin_user(
    username,
    password_hash,
    display_name=None,
):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO admin_users (
                    username,
                    password_hash,
                    display_name,
                    active
                )
                VALUES (%s, %s, %s, TRUE)
                RETURNING id
                """,
                (
                    username,
                    password_hash,
                    display_name,
                ),
            )

            return cur.fetchone()[0]


def get_admin_users():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    username,
                    password_hash,
                    is_active,
                    created_at,
                    updated_at,
                    last_login_at
                FROM admin_users
                ORDER BY id
                """
            )

            return cur.fetchall()

def get_admin_user(username):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    username,
                    password_hash,
                    is_active,
                    created_at,
                    updated_at,
                    last_login_at
                FROM admin_users
                WHERE username = %s
                LIMIT 1
                """,
                (username,),
            )

            return cur.fetchone()

def get_admin_user_by_id(user_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    username,
                    password_hash,
                    display_name,
                    active,
                    created_at,
                    updated_at,
                    last_login_at
                FROM admin_users
                WHERE id = %s
                LIMIT 1
                """,
                (user_id,),
            )

            return cur.fetchone()


def get_admin_users():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    username,
                    password_hash,
                    is_active,
                    created_at,
                    updated_at,
                    last_login_at
                FROM admin_users
                ORDER BY id
                """
            )

            return cur.fetchall()


def get_admin_user(username):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    username,
                    password_hash,
                    is_active,
                    created_at,
                    updated_at,
                    last_login_at
                FROM admin_users
                WHERE username = %s
                LIMIT 1
                """,
                (username,),
            )

            return cur.fetchone()


def set_admin_user_status(
    user_id,
    active,
):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE admin_users
                SET
                    active = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    bool(active),
                    user_id,
                ),
            )

            return cur.rowcount > 0


def update_admin_last_login(user_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE admin_users
                SET
                    last_login_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (user_id,),
            )

            return cur.rowcount > 0


# ============================================================
# Notification Queue
# ============================================================

def create_notification_queue(
    result_id,
    chat_ids,
):
    """
    Create pending notification entries for a newly discovered result.
    Duplicate entries are ignored.
    """

    chat_ids = list(set(chat_ids))

    if not chat_ids:
        return 0

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            values_sql = ", ".join(
                ["(%s, %s)"] * len(chat_ids)
            )

            params = []

            for chat_id in chat_ids:
                params.extend([
                    result_id,
                    chat_id,
                ])

            query = f"""
                INSERT INTO notification_queue (
                    result_id,
                    chat_id
                )
                VALUES {values_sql}
                ON CONFLICT (result_id, chat_id)
                DO NOTHING
            """

            cur.execute(
                query,
                params,
            )

            created = cur.rowcount

        conn.commit()

        return created

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_pending_notifications(limit=20):
    """
    Get notifications that are ready to be sent.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    nq.id,
                    nq.result_id,
                    nq.chat_id,
                    nq.attempts,
                    r.institute_id,
                    r.degree_id,
                    r.semester_id,
                    r.exam_name
                FROM notification_queue nq
                JOIN results r
                    ON r.id = nq.result_id
                WHERE nq.status IN ('pending', 'failed')
                  AND nq.next_attempt_at <= NOW()
                ORDER BY nq.id
                LIMIT %s
                """,
                (limit,),
            )

            return cur.fetchall()

    finally:
        conn.close()


def mark_notification_sent(notification_id):
    """
    Mark a notification as successfully delivered.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE notification_queue
                SET
                    status = 'sent',
                    sent_at = NOW(),
                    last_error = NULL
                WHERE id = %s
                """,
                (notification_id,),
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def mark_notification_failed(
    notification_id,
    error_message,
    retry_minutes=5,
):
    """
    Mark notification as failed and schedule a retry.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE notification_queue
                SET
                    status = 'failed',
                    attempts = attempts + 1,
                    last_error = %s,
                    next_attempt_at =
                        NOW() + (%s * INTERVAL '1 minute')
                WHERE id = %s
                """,
                (
                    error_message,
                    retry_minutes,
                    notification_id,
                ),
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_notification_queue_count(
    status=None,
):
    """
    Return number of notifications in the queue.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            if status:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM notification_queue
                    WHERE status = %s
                    """,
                    (status,),
                )
            else:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM notification_queue
                    """
                )

            return cur.fetchone()[0]

    finally:
        conn.close()


def get_notification_queue_counts():
    """
    Return notification counts grouped by status.

    Always returns all known queue statuses, even when
    there are currently zero notifications.
    """
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    status,
                    COUNT(*)
                FROM notification_queue
                GROUP BY status
                """
            )

            counts = {
                "pending": 0,
                "sending": 0,
                "sent": 0,
                "failed": 0,
            }

            for status, count in cur.fetchall():
                if status in counts:
                    counts[status] = count

            return counts