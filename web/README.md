# WikiPulse website

Next.js 16 site that reads the pipeline's gold tables from Supabase (read-only, publishable key).

```bash
cp .env.example .env.local   # Supabase URL + publishable key
npm install
npm run dev                  # http://localhost:3000
```

| Route | Data |
|---|---|
| `/` | `trending_now`, `page_summaries`, `page_activity_15m` (sparklines), `breaking_alerts`, `daily_top_read` |
| `/topic/[wiki]/[title]` | one article across all gold tables |
| `/india`, `/stats` | `wiki_activity_hourly` (last 7 days) |
| `/digest`, `/digest/[date]` | `daily_digest` |

Data loaders live in `lib/data.ts`. They use `"use cache"` with a 5-minute revalidation, so pages are
pre-rendered and refreshed in the background rather than querying the database on every visit.
