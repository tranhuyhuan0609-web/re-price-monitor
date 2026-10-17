CREATE TABLE IF NOT EXISTS crawl_runs (
    crawl_run_id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    items_scraped INTEGER NOT NULL DEFAULT 0,
    request_failures INTEGER NOT NULL DEFAULT 0,
    finish_reason TEXT,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_crawl_runs_status
        CHECK (status IN ('success', 'partial', 'failed')),
    CONSTRAINT ck_crawl_runs_times
        CHECK (finished_at >= started_at),
    CONSTRAINT ck_crawl_runs_counts
        CHECK (items_scraped >= 0 AND request_failures >= 0),
    CONSTRAINT ck_crawl_runs_failed_error
        CHECK (status <> 'failed' OR error IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_crawl_runs_site_started
    ON crawl_runs (site_id, started_at DESC);
