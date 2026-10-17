
CREATE TABLE crawler_configs (
    site_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    enabled BOOLEAN NOT NULL,
    config_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT ck_crawler_configs_site_id_nonblank
        CHECK (length(trim(site_id)) > 0),

    CONSTRAINT ck_crawler_configs_name_nonblank
        CHECK (length(trim(name)) > 0),

    CONSTRAINT ck_crawler_configs_json_object
        CHECK (jsonb_typeof(config_json) = 'object'),

    CONSTRAINT ck_crawler_configs_json_site_id
        CHECK (config_json ->> 'site_id' = site_id),

    CONSTRAINT ck_crawler_configs_json_name
        CHECK (config_json ->> 'name' = name),

    CONSTRAINT ck_crawler_configs_json_enabled
        CHECK (
            jsonb_typeof(config_json -> 'enabled') = 'boolean'
            AND (config_json ->> 'enabled')::boolean = enabled
        )
);
