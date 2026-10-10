-- One-time migration: identify a result by the portal's exam dropdown
-- value, so same-named exams (e.g. re-assessment results declared
-- within the same month) are stored as separate results.
--
-- Safe to run more than once.

BEGIN;

ALTER TABLE results
    ADD COLUMN IF NOT EXISTS exam_value VARCHAR(100);

-- Drop the old UNIQUE (institute_id, degree_id, semester_id, exam_name)
-- (its auto-generated name is looked up instead of assumed)
DO $$
DECLARE
    c RECORD;
BEGIN
    FOR c IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'results'::regclass
          AND contype = 'u'
    LOOP
        EXECUTE format('ALTER TABLE results DROP CONSTRAINT %I', c.conname);
    END LOOP;
END $$;

-- Existing rows keep exam_value = NULL until the baseline crawl
-- fills them in. NULLs never conflict, so this index is safe now.
CREATE UNIQUE INDEX IF NOT EXISTS results_exam_identity_key
    ON results (institute_id, degree_id, semester_id, exam_value);

COMMIT;
