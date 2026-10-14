-- Silver -> Gold aggregates for this run. They are merged into Postgres by publish.py,
-- where counts are added to existing buckets and editor lists are unioned.

-- Per article, per 15-minute bucket.
CREATE OR REPLACE TABLE gold_page_15m AS
SELECT
    wiki,
    title,
    CAST(time_bucket(INTERVAL '{bucket_minutes} minutes', event_time) AS TIMESTAMP) AS bucket_start,
    count(*)                                              AS edits,
    count(*) FILTER (WHERE NOT is_bot)                    AS human_edits,
    count(*) FILTER (WHERE is_bot)                        AS bot_edits,
    count(*) FILTER (WHERE change_type = 'new')           AS new_pages,
    sum(bytes_changed)                                    AS bytes_changed,
    coalesce(
        list_sort(list(DISTINCT user_name) FILTER (WHERE NOT is_bot AND user_name IS NOT NULL)),
        []
    )                                                     AS editors
FROM silver
GROUP BY ALL;

-- Per wiki, per hour.
CREATE OR REPLACE TABLE gold_wiki_hourly AS
SELECT
    wiki,
    CAST(date_trunc('hour', event_time) AS TIMESTAMP)     AS hour_start,
    count(*)                                              AS edits,
    count(*) FILTER (WHERE NOT is_bot)                    AS human_edits,
    count(*) FILTER (WHERE is_bot)                        AS bot_edits,
    count(*) FILTER (WHERE is_anonymous)                  AS anon_edits,
    count(*) FILTER (WHERE change_type = 'new')           AS new_pages,
    sum(bytes_changed)                                    AS bytes_changed,
    sum(greatest(bytes_changed, 0))                       AS bytes_added
FROM silver
GROUP BY ALL;
