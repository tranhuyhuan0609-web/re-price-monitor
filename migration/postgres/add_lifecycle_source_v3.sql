BEGIN;
SET LOCAL TIME ZONE 'UTC';

-- listing_key has the form '<source>:url:<sha256>'; store the
-- source separately
-- so the lifecycle updater can filter with an indexed equality instead of a
-- LIKE prefix scan.
ALTER TABLE listing_lifecycle
    ADD COLUMN IF NOT EXISTS source TEXT;

UPDATE listing_lifecycle
SET source = split_part(listing_key, ':url:', 1)
WHERE source IS NULL;

ALTER TABLE listing_lifecycle
    ALTER COLUMN source SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_lc_source'
    ) THEN
        ALTER TABLE listing_lifecycle
            ADD CONSTRAINT chk_lc_source
            CHECK (
                length(btrim(source)) > 0 AND source = lower(btrim(source))
            );
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_lifecycle_source_status
    ON listing_lifecycle (source, status);

COMMIT;