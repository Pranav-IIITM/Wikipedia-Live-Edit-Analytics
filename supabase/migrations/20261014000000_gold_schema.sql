-- WikiPulse gold layer: tables served to the website, plus pipeline state and run log.

-- ---------------------------------------------------------------- pipeline internals
create table public.pipeline_state (
    key         text primary key,
    value       text,
    updated_at  timestamptz not null default now()
);

create table public.pipeline_runs (
    run_id          text primary key,
    job             text not null,                 -- 'pipeline' | 'daily'
    started_at      timestamptz not null,
    finished_at     timestamptz,
    status          text not null,                 -- 'success' | 'failed' | 'failed_quality'
    events_seen     integer,
    events_kept     integer,
    silver_rows     integer,
    quarantined     integer,
    trending_rows   integer,
    caught_up       boolean,
    max_event_time  timestamptz,
    checks          jsonb,
    error           text
);
create index pipeline_runs_started_idx on public.pipeline_runs (job, started_at desc);

-- ---------------------------------------------------------------- activity
-- One row per article per 15-minute bucket. Counts are added up across runs;
-- editors holds distinct human usernames so editor counts stay exact.
create table public.page_activity_15m (
    wiki            text not null,
    title           text not null,
    bucket_start    timestamptz not null,
    edits           integer not null default 0,
    human_edits     integer not null default 0,
    bot_edits       integer not null default 0,
    new_pages       integer not null default 0,
    bytes_changed   bigint not null default 0,
    editors         text[] not null default '{}',
    primary key (wiki, title, bucket_start)
);
create index page_activity_15m_bucket_idx on public.page_activity_15m (bucket_start);

create table public.wiki_activity_hourly (
    wiki            text not null,
    hour_start      timestamptz not null,
    edits           integer not null default 0,
    human_edits     integer not null default 0,
    bot_edits       integer not null default 0,
    anon_edits      integer not null default 0,
    new_pages       integer not null default 0,
    bytes_changed   bigint not null default 0,
    bytes_added     bigint not null default 0,
    primary key (wiki, hour_start)
);
create index wiki_activity_hourly_hour_idx on public.wiki_activity_hourly (hour_start);

-- ---------------------------------------------------------------- trending
create table public.trending_now (
    wiki            text not null,
    title           text not null,
    rank            integer not null,
    human_edits     integer not null,
    total_edits     integer not null,
    editors         integer not null,
    bytes_changed   bigint not null,
    baseline        numeric not null,              -- avg human edits per 30 min over previous 24 h
    spike_score     numeric not null,
    is_breaking     boolean not null,
    window_start    timestamptz not null,
    computed_at     timestamptz not null,
    primary key (wiki, title)
);

create table public.breaking_alerts (
    wiki                text not null,
    title               text not null,
    alert_date          date not null,
    first_detected_at   timestamptz not null,
    last_seen_at        timestamptz not null,
    peak_spike_score    numeric not null,
    peak_human_edits    integer not null,
    peak_editors        integer not null,
    primary key (wiki, title, alert_date)
);
create index breaking_alerts_seen_idx on public.breaking_alerts (last_seen_at desc);

-- ---------------------------------------------------------------- enrichment + daily
create table public.page_summaries (
    wiki            text not null,
    title           text not null,
    display_title   text,
    description     text,
    extract         text,
    thumbnail_url   text,
    page_url        text,
    fetched_at      timestamptz not null default now(),
    primary key (wiki, title)
);

create table public.daily_top_read (
    wiki    text not null,
    day     date not null,
    rank    integer not null,
    title   text not null,
    views   bigint not null,
    primary key (wiki, day, rank)
);
create index daily_top_read_title_idx on public.daily_top_read (wiki, title);

create table public.daily_digest (
    wiki            text not null,
    day             date not null,
    rank            integer not null,
    title           text not null,
    human_edits     integer not null,
    total_edits     integer not null,
    editors         integer not null,
    bytes_changed   bigint not null,
    primary key (wiki, day, rank)
);
create index daily_digest_day_idx on public.daily_digest (day desc);

-- ---------------------------------------------------------------- trending refresh
-- Window = current 15-minute bucket + the previous one (15-30 minutes of data).
-- spike_score = human edits in the window / average per 30 min over the previous 24 h (floor 1).
-- Thresholds mirror pipeline/rules.py.
create or replace function public.refresh_trending(p_now timestamptz)
returns integer
language plpgsql
set search_path = public
as $$
declare
    v_window_start   timestamptz := date_bin('15 minutes', p_now, timestamptz '2000-01-01 00:00+00')
                                    - interval '15 minutes';
    v_baseline_start timestamptz := v_window_start - interval '24 hours';
    v_count          integer;
begin
    delete from public.trending_now where true;

    insert into public.trending_now
        (wiki, title, rank, human_edits, total_edits, editors, bytes_changed,
         baseline, spike_score, is_breaking, window_start, computed_at)
    with recent as (
        select wiki, title,
               sum(human_edits)::int   as human_edits,
               sum(edits)::int         as total_edits,
               sum(bytes_changed)      as bytes_changed
        from public.page_activity_15m
        where bucket_start >= v_window_start
        group by wiki, title
        having sum(human_edits) >= 2
    ),
    recent_editors as (
        select p.wiki, p.title, count(distinct e)::int as editors
        from public.page_activity_15m p
        cross join lateral unnest(p.editors) as e
        where p.bucket_start >= v_window_start
        group by p.wiki, p.title
    ),
    baseline as (
        select wiki, title, sum(human_edits)::numeric / 48 as per_30m
        from public.page_activity_15m
        where bucket_start >= v_baseline_start and bucket_start < v_window_start
        group by wiki, title
    ),
    scored as (
        select r.wiki, r.title, r.human_edits, r.total_edits, r.bytes_changed,
               coalesce(e.editors, 0)                                         as editors,
               round(coalesce(b.per_30m, 0), 3)                               as baseline,
               round(r.human_edits / greatest(coalesce(b.per_30m, 0), 1), 2)  as spike_score
        from recent r
        left join recent_editors e using (wiki, title)
        left join baseline b using (wiki, title)
    ),
    ranked as (
        select s.*,
               row_number() over (partition by s.wiki
                                  order by s.editors desc, s.human_edits desc, s.title) as rnk
        from scored s
    )
    select wiki, title, rnk, human_edits, total_edits, editors, bytes_changed, baseline, spike_score,
           (spike_score >= 5 and human_edits >= 8 and editors >= 3),
           v_window_start, p_now
    from ranked
    where rnk <= 30;

    get diagnostics v_count = row_count;

    insert into public.breaking_alerts as a
        (wiki, title, alert_date, first_detected_at, last_seen_at,
         peak_spike_score, peak_human_edits, peak_editors)
    select wiki, title, (p_now at time zone 'utc')::date, p_now, p_now,
           spike_score, human_edits, editors
    from public.trending_now
    where is_breaking
    on conflict (wiki, title, alert_date) do update set
        last_seen_at     = excluded.last_seen_at,
        peak_spike_score = greatest(a.peak_spike_score, excluded.peak_spike_score),
        peak_human_edits = greatest(a.peak_human_edits, excluded.peak_human_edits),
        peak_editors     = greatest(a.peak_editors, excluded.peak_editors);

    return v_count;
end;
$$;

revoke execute on function public.refresh_trending(timestamptz) from public, anon, authenticated;

-- ---------------------------------------------------------------- access
-- The website uses the publishable (anon) key: read-only access to gold tables.
-- The pipeline connects as the postgres role and bypasses RLS.
alter table public.pipeline_state       enable row level security;
alter table public.pipeline_runs        enable row level security;
alter table public.page_activity_15m    enable row level security;
alter table public.wiki_activity_hourly enable row level security;
alter table public.trending_now         enable row level security;
alter table public.breaking_alerts      enable row level security;
alter table public.page_summaries       enable row level security;
alter table public.daily_top_read       enable row level security;
alter table public.daily_digest         enable row level security;

revoke all on public.pipeline_state from anon, authenticated;

do $$
declare
    t text;
begin
    foreach t in array array[
        'pipeline_runs', 'page_activity_15m', 'wiki_activity_hourly', 'trending_now',
        'breaking_alerts', 'page_summaries', 'daily_top_read', 'daily_digest'
    ] loop
        execute format('revoke all on public.%I from anon, authenticated', t);
        execute format('grant select on public.%I to anon, authenticated', t);
        execute format('create policy "public read" on public.%I for select to anon, authenticated using (true)', t);
    end loop;
end $$;
