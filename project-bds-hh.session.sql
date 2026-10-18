UPDATE crawler_configs
SET
    config_json = jsonb_set(
        config_json,
        '{schedule_interval_seconds}',
        '300'
    ),
    updated_at = now();