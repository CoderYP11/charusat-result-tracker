-- ============================================
-- CHARUSAT RESULT TRACKER DATABASE
-- ============================================

-- Institutes
CREATE TABLE IF NOT EXISTS institutes (
    id VARCHAR(100) PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- Degrees / Courses
CREATE TABLE IF NOT EXISTS degrees (
    id VARCHAR(100) PRIMARY KEY,
    institute_id VARCHAR(100) NOT NULL
        REFERENCES institutes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (institute_id, id)
);


-- Semesters
CREATE TABLE IF NOT EXISTS semesters (
    id VARCHAR(100) NOT NULL,
    degree_id VARCHAR(100) NOT NULL
        REFERENCES degrees(id) ON DELETE CASCADE,
    name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (degree_id, id)
);


-- Discovered results
CREATE TABLE IF NOT EXISTS results (
    id BIGSERIAL PRIMARY KEY,

    institute_id VARCHAR(100) NOT NULL,
    degree_id VARCHAR(100) NOT NULL,
    semester_id VARCHAR(100) NOT NULL,
    exam_name TEXT NOT NULL,

    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_result_institute
        FOREIGN KEY (institute_id)
        REFERENCES institutes(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_result_degree
        FOREIGN KEY (degree_id)
        REFERENCES degrees(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_result_semester
        FOREIGN KEY (degree_id, semester_id)
        REFERENCES semesters(degree_id, id)
        ON DELETE CASCADE,

    UNIQUE (
        institute_id,
        degree_id,
        semester_id,
        exam_name
    )
);


-- Telegram subscribers
CREATE TABLE IF NOT EXISTS subscribers (
    chat_id BIGINT PRIMARY KEY,

    username TEXT,
    first_name TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- Telegram polling state
CREATE TABLE IF NOT EXISTS telegram_state (
    id SMALLINT PRIMARY KEY DEFAULT 1,

    update_offset BIGINT NOT NULL DEFAULT 0,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT telegram_state_single_row
        CHECK (id = 1)
);


-- Tracker logs
CREATE TABLE IF NOT EXISTS tracker_logs (
    id BIGSERIAL PRIMARY KEY,

    level VARCHAR(20) NOT NULL,
    event_type VARCHAR(100),

    message TEXT,

    failed_institutes JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================
-- Useful indexes
-- ============================================

CREATE INDEX IF NOT EXISTS idx_degrees_institute
    ON degrees(institute_id);

CREATE INDEX IF NOT EXISTS idx_semesters_degree
    ON semesters(degree_id);

CREATE INDEX IF NOT EXISTS idx_results_institute
    ON results(institute_id);

CREATE INDEX IF NOT EXISTS idx_results_degree
    ON results(degree_id);

CREATE INDEX IF NOT EXISTS idx_results_last_seen
    ON results(last_seen_at);

CREATE INDEX IF NOT EXISTS idx_logs_created_at
    ON tracker_logs(created_at DESC);


CREATE TABLE IF NOT EXISTS notification_queue (
    id BIGSERIAL PRIMARY KEY,

    result_id BIGINT NOT NULL
        REFERENCES results(id)
        ON DELETE CASCADE,

    chat_id BIGINT NOT NULL
        REFERENCES subscribers(chat_id)
        ON DELETE CASCADE,

    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    attempts INTEGER NOT NULL DEFAULT 0,

    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    last_error TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    sent_at TIMESTAMPTZ,

    UNIQUE (result_id, chat_id),

    CONSTRAINT notification_status_check
        CHECK (status IN ('pending', 'sending', 'sent', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_notification_queue_pending
    ON notification_queue(status, next_attempt_at);

CREATE INDEX IF NOT EXISTS idx_notification_queue_result
    ON notification_queue(result_id);

CREATE INDEX IF NOT EXISTS idx_notification_queue_chat
    ON notification_queue(chat_id);

-- ============================================================
-- CHARUSAT RESULT TRACKER
-- ADMIN CONTROL PANEL - DATABASE FOUNDATION
-- ============================================================

BEGIN;


-- ============================================================
-- 1. SETTINGS
-- Dashboard-controlled runtime configuration
-- ============================================================

CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(150) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(100)
);


-- ============================================================
-- 2. CRAWL RUNS
-- One row = one crawler execution
-- ============================================================

CREATE TABLE IF NOT EXISTS crawl_runs (
    id BIGSERIAL PRIMARY KEY,

    status VARCHAR(20) NOT NULL DEFAULT 'running',

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    duration_ms BIGINT,

    workers INTEGER,
    institutes_total INTEGER NOT NULL DEFAULT 0,
    institutes_completed INTEGER NOT NULL DEFAULT 0,
    institutes_failed INTEGER NOT NULL DEFAULT 0,

    results_discovered INTEGER NOT NULL DEFAULT 0,
    results_new INTEGER NOT NULL DEFAULT 0,

    error_message TEXT,

    triggered_by VARCHAR(100) NOT NULL DEFAULT 'system',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT crawl_runs_status_check
        CHECK (
            status IN (
                'running',
                'success',
                'failed',
                'cancelled'
            )
        ),

    CONSTRAINT crawl_runs_workers_check
        CHECK (workers IS NULL OR workers > 0)
);

CREATE INDEX IF NOT EXISTS idx_crawl_runs_started_at
    ON crawl_runs(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_crawl_runs_status
    ON crawl_runs(status);


-- ============================================================
-- 3. ACTIVITY / AUDIT LOGS
-- Every important admin/system action
-- ============================================================

CREATE TABLE IF NOT EXISTS activity_logs (
    id BIGSERIAL PRIMARY KEY,

    level VARCHAR(20) NOT NULL DEFAULT 'INFO',

    actor VARCHAR(100) NOT NULL DEFAULT 'system',

    action VARCHAR(150) NOT NULL,

    target VARCHAR(255),

    message TEXT,

    details JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT activity_logs_level_check
        CHECK (
            level IN (
                'DEBUG',
                'INFO',
                'SUCCESS',
                'WARN',
                'ERROR'
            )
        )
);

CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at
    ON activity_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_activity_logs_level
    ON activity_logs(level);

CREATE INDEX IF NOT EXISTS idx_activity_logs_actor
    ON activity_logs(actor);


-- ============================================================
-- 4. ADMIN USERS
-- Real dashboard authentication
-- ============================================================

CREATE TABLE IF NOT EXISTS admin_users (
    id BIGSERIAL PRIMARY KEY,

    username VARCHAR(100) UNIQUE NOT NULL,

    password_hash TEXT NOT NULL,

    display_name VARCHAR(150),

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    last_login_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_users_active
    ON admin_users(is_active);


-- ============================================================
-- 5. DEFAULT SETTINGS
-- ============================================================

INSERT INTO settings (
    key,
    value,
    description
)
VALUES

(
    'crawler.enabled',
    'true',
    'Enable or disable automatic crawler execution'
),

(
    'crawler.interval_minutes',
    '30',
    'Automatic crawler interval in minutes'
),

(
    'crawler.workers',
    '11',
    'Number of crawler worker threads'
),

(
    'crawler.retry_count',
    '3',
    'Number of crawler retries'
),

(
    'crawler.retry_delay_seconds',
    '5',
    'Delay between crawler retries'
),

(
    'crawler.request_timeout_seconds',
    '30',
    'HTTP request timeout for crawler'
),

(
    'notifications.enabled',
    'true',
    'Enable notification worker'
),

(
    'notifications.poll_interval_seconds',
    '30',
    'Notification queue polling interval'
),

(
    'notifications.batch_size',
    '20',
    'Maximum notifications processed per batch'
),

(
    'notifications.retry_delay_seconds',
    '300',
    'Delay before retrying failed notifications'
),

(
    'notifications.max_attempts',
    '5',
    'Maximum notification delivery attempts'
),

(
    'telegram.enabled',
    'true',
    'Enable Telegram integration'
),

(
    'telegram.notifications_enabled',
    'true',
    'Enable new-result Telegram notifications'
),

(
    'telegram.admin_chat_id',
    '0',
    'Telegram administrator chat ID'
),

(
    'system.maintenance_mode',
    'false',
    'Put the tracker into maintenance mode'
),

(
    'system.timezone',
    '"Asia/Kolkata"',
    'Application timezone'
),

(
    'system.log_retention_days',
    '90',
    'Number of days to retain activity logs'
)

ON CONFLICT (key) DO NOTHING;


COMMIT;