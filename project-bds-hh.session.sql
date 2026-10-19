UPDATE crawler_configs
SET
    enabled = false;
    config_json = jsonb_set(
        config_json,
        '{enabled}',
        'false'
    ),
    updated_at = now();