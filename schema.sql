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