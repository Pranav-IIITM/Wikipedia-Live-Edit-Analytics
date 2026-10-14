-- Private Storage bucket for the lake (bronze / silver / quarantine Parquet files).
-- The pipeline writes to it through the S3-compatible endpoint with S3 access keys.
do $$
begin
    if to_regclass('storage.buckets') is not null then
        insert into storage.buckets (id, name, public, file_size_limit)
        values ('lake', 'lake', false, 52428800)
        on conflict (id) do nothing;
    end if;
end $$;
