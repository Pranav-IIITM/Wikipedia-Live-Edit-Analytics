-- Bronze -> Silver: parse raw JSON, type-cast, derive columns.
-- Input table:  bronze(event_id, wiki, event_time, raw_json, ingested_at)
-- Output table: parsed (every bronze row, with an is_valid flag)

CREATE OR REPLACE TABLE parsed AS
WITH extracted AS (
    SELECT
        event_id,
        raw_json,
        ingested_at,
        json_extract_string(raw_json, '$.type')                              AS change_type,
        json_extract_string(raw_json, '$.wiki')                              AS wiki,
        json_extract_string(raw_json, '$.title')                             AS title,
        TRY_CAST(json_extract_string(raw_json, '$.namespace') AS INTEGER)    AS namespace,
        json_extract_string(raw_json, '$.user')                              AS user_name,
        json_extract_string(raw_json, '$.bot') = 'true'                      AS bot_flag,
        json_extract_string(raw_json, '$.minor') = 'true'                    AS minor_flag,
        TRY_CAST(json_extract_string(raw_json, '$.length.old') AS BIGINT)    AS length_old,
        TRY_CAST(json_extract_string(raw_json, '$.length.new') AS BIGINT)    AS length_new,
        TRY_CAST(json_extract_string(raw_json, '$.revision.new') AS BIGINT)  AS revision_id,
        TRY_CAST(json_extract_string(raw_json, '$.timestamp') AS BIGINT)     AS ts_epoch
    FROM bronze
)
SELECT
    event_id,
    change_type,
    wiki,
    title,
    namespace,
    user_name,
    coalesce(bot_flag, false)                                  AS is_bot,
    coalesce(minor_flag, false)                                AS is_minor,
    regexp_matches(coalesce(user_name, ''), '{anon_regex}')    AS is_anonymous,
    coalesce(length_new, 0) - coalesce(length_old, 0)          AS bytes_changed,
    revision_id,
    to_timestamp(ts_epoch)                                     AS event_time,
    ingested_at,
    epoch(ingested_at) - ts_epoch                              AS ingest_lag_sec,
    raw_json,
    (event_id IS NOT NULL AND ts_epoch IS NOT NULL
        AND title IS NOT NULL AND wiki IS NOT NULL)            AS is_valid
FROM extracted;

-- Silver: valid rows, one per event_id.
CREATE OR REPLACE TABLE silver AS
SELECT * EXCLUDE (raw_json, is_valid),
       CAST(event_time AS DATE) AS event_date
FROM parsed
WHERE is_valid
QUALIFY row_number() OVER (PARTITION BY event_id ORDER BY ingested_at DESC) = 1;

-- Quarantine: rows we could not use, kept for inspection.
CREATE OR REPLACE TABLE quarantine AS
SELECT event_id, raw_json, ingested_at, 'missing_required_fields' AS reason
FROM parsed
WHERE NOT is_valid;
