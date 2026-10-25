CREATE INDEX IF NOT EXISTS idx_obs_source_crawler
     ON listing_observation (source, crawled_at DESC);