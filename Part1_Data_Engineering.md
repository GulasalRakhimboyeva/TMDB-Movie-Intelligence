# Part 1 — Data Engineering: Build the Medallion Pipeline


---

## Learning objectives

By the end of Part 1 you can:

1. Call a paginated REST API responsibly (auth, rate limits, retries).
2. Design a Bronze/Silver/Gold medallion pipeline.
3. Identify and fix real data-quality problems (nulls, sentinels, duplicates,
   nested structures, bad types, inconsistent categories).
4. Express the *same* transformation in both **pandas** and **T-SQL**, and
   explain the trade-offs.
5. Model a **star schema** (facts + dimensions) suitable for BI.

---

## 0. Setup

1. Get your TMDB API key (see README).
2. Create `.env` from `.env.example`:
   ```
   TMDB_API_KEY=your_key_here
   SQLSERVER_CONN=Driver={ODBC Driver 18 for SQL Server};Server=localhost;Database=movies;Trusted_Connection=yes;Encrypt=no;
   ```
3. Create a `movies` database in SQL Server.
4. Confirm you can call the API. Quick smoke test:
   ```python
   import os, requests
   key = os.environ["TMDB_API_KEY"]
   r = requests.get("https://api.themoviedb.org/3/movie/550",
                    params={"api_key": key})
   print(r.status_code, r.json()["title"])   # 200 Fight Club
   ```

---

## 1. Bronze — ingest raw, keep everything

**Objective:** pull ~1,000 movies plus their details and land the **raw JSON
untouched**. Bronze is your safety net: if you get cleaning wrong, you re-derive
from Bronze without re-hitting the API.

### What to pull

You must combine **multiple endpoints** — this is deliberate, because merging
sources is where duplicates and inconsistencies are born.

| Endpoint | Purpose | Notes |
|---|---|---|
| `GET /discover/movie` | Backbone list of movies | Paginate. Filter e.g. `primary_release_year` across a few years to reach ~1,000. 20 results/page. |
| `GET /movie/{id}` | Full details per movie | budget, revenue, runtime, genres, production_companies, spoken_languages |
| `GET /movie/{id}/credits` | Cast & crew | keep top cast + director |
| `GET /trending/movie/week` | Extra rows that **overlap** with discover | intentionally creates duplicates |
| `GET /movie/popular` | More overlapping rows | more duplicates |
| `GET /genre/movie/list` | Genre id → name lookup | small reference table |

### Requirements

- [ ] Pull ~1,000 distinct movies via `/discover/movie` across a few release
      years (e.g. 2018–2023). Also pull `/trending` and `/popular` **without**
      pre-deduping — let the duplicates land.
- [ ] For each movie id, fetch `/movie/{id}` and `/movie/{id}/credits`.
- [ ] Store raw responses **as-is**. Two acceptable landing targets (do both):
  - **Files:** one JSON file (or JSON-lines) per endpoint in `data/bronze/`.
  - **SQL Server:** a `bronze.raw_movies` table holding the raw JSON string.
- [ ] Add **ingestion metadata** to every record: `source_endpoint`,
      `ingested_at` (UTC), `movie_id`, and the raw `payload`.

Suggested Bronze table:

```sql
CREATE TABLE bronze.raw_movies (
    raw_id         BIGINT IDENTITY PRIMARY KEY,
    movie_id       INT          NULL,
    source_endpoint VARCHAR(50) NOT NULL,
    ingested_at    DATETIME2    NOT NULL,
    payload        NVARCHAR(MAX) NOT NULL   -- the raw JSON, verbatim
);
```

### Responsible API usage (required)

- [ ] Read the key from env, **never hardcode** it.
- [ ] Handle rate limiting: on HTTP `429`, back off and retry (respect
      `Retry-After` if present). Add a small delay between calls.
- [ ] Retry transient errors (5xx) a few times with backoff.
- [ ] Be idempotent-ish: you should be able to re-run ingestion without crashing.

---

## 2. Silver — clean it (TWICE: Python AND T-SQL)

**Objective:** produce a clean, typed, deduplicated, flattened dataset. You will
implement this **two ways** and prove they agree.

> The Silver layer is where you earn your keep. Do the *same* logic in
> `clean_silver_python.py` (pandas) and `sql/10_clean_silver_tsql.sql` (T-SQL,
> using `OPENJSON` to parse the Bronze payloads).

### The data-quality issues you WILL find (and must handle)

| # | Problem | What's wrong | Required fix |
|---|---|---|---|
| 1 | **Sentinel zeros** | `budget` / `revenue` / `runtime` = `0` | Convert `0` → `NULL` (0 means "unknown", not "free movie") |
| 2 | **Missing dates** | `release_date` is `""` or `null` | Parse to real date; null out invalid/empty |
| 3 | **Duplicates** | Same movie from discover + trending + popular | Deduplicate on `movie_id`, keep the most complete record |
| 4 | **Nested arrays** | `genres`, `spoken_languages`, `production_companies` are arrays of objects | Flatten/explode into bridge tables |
| 5 | **Type inconsistency** | numbers as strings, bools, mixed | Cast to correct types |
| 6 | **Fake ratings** | `vote_average` > 0 while `vote_count` = 0 (or both 0) | Treat as no rating (null the average when `vote_count` = 0) |
| 7 | **Inconsistent text** | `original_language` codes, casing in titles, whitespace | Standardize (trim, uppercase codes, keep a clean `title`) |
| 8 | **Free text** | `overview` empty / multi-language | Keep, but flag empties; do not fabricate |
| 9 | **Outliers** | absurd runtimes, revenue < budget oddities | Detect and document; decide keep vs flag |

### Silver deliverables (both cohorts)

Produce these conformed Silver tables (same shape from both the Python and SQL
paths):

- `silver.movies` — one row per distinct movie, cleaned & typed.
- `silver.movie_genres` — bridge: `movie_id`, `genre_id` (exploded).
- `silver.genres` — `genre_id`, `genre_name` (from the lookup endpoint).
- `silver.movie_companies` — bridge: `movie_id`, `company_name`.
- `silver.movie_cast` — top N cast + the director per movie.

Suggested `silver.movies` columns:

```
movie_id (PK), title, original_title, original_language,
release_date (date), release_year (int),
budget (nullable int), revenue (nullable int), runtime (nullable int),
vote_average (nullable float), vote_count (int), popularity (float),
is_adult (bit), overview_is_empty (bit), ingested_at
```

### Two implementations — the core requirement

**A) Python / pandas path** (`src/clean_silver_python.py`)
- Read from Bronze (files or SQL).
- Use pandas: `replace(0, NA)`, `to_datetime(errors="coerce")`, `drop_duplicates`,
  `explode` for nested lists, `astype`, string methods for standardization.
- Write Silver to `data/silver/` (parquet or csv) **and** to `silver.*` tables.

**B) T-SQL path** (`sql/10_clean_silver_tsql.sql`)
- Parse Bronze JSON with **`OPENJSON`** + `JSON_VALUE` / `CROSS APPLY`.
- Apply the same rules with `NULLIF(x, 0)`, `TRY_CONVERT`, `ROW_NUMBER()` window
  for dedup, `CROSS APPLY OPENJSON(...)` to explode arrays.
- Write into `silver.*` tables.

Sketch of the T-SQL flavor (students complete it):

```sql
-- 0 -> NULL, safe date parse, dedup keep-most-complete
WITH parsed AS (
    SELECT
        JSON_VALUE(payload,'$.id')                        AS movie_id,
        JSON_VALUE(payload,'$.title')                     AS title,
        NULLIF(TRY_CONVERT(BIGINT, JSON_VALUE(payload,'$.budget')), 0)  AS budget,
        NULLIF(TRY_CONVERT(BIGINT, JSON_VALUE(payload,'$.revenue')),0)  AS revenue,
        TRY_CONVERT(DATE, NULLIF(JSON_VALUE(payload,'$.release_date'),'')) AS release_date,
        TRY_CONVERT(INT, JSON_VALUE(payload,'$.vote_count'))            AS vote_count,
        TRY_CONVERT(FLOAT, JSON_VALUE(payload,'$.vote_average'))        AS vote_average_raw,
        ingested_at
    FROM bronze.raw_movies
    WHERE source_endpoint = 'movie_details'
),
ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY movie_id
            ORDER BY (CASE WHEN budget IS NOT NULL THEN 1 ELSE 0 END)
                   + (CASE WHEN revenue IS NOT NULL THEN 1 ELSE 0 END) DESC,
                     ingested_at DESC
        ) AS rn
    FROM parsed
)
SELECT
    movie_id, title, budget, revenue, release_date, vote_count,
    CASE WHEN vote_count = 0 THEN NULL ELSE vote_average_raw END AS vote_average
INTO silver.movies_stage
FROM ranked
WHERE rn = 1;
```

### Prove the two paths agree (required)

- [ ] Row counts of `silver.movies` match between Python and T-SQL (±0 ideally;
      document any justified difference).
- [ ] Spot-check 5 movies across both outputs — same budget/revenue/date/rating.
- [ ] Write a short **comparison note**: where was pandas easier? where was SQL
      easier? which nulls/edge cases did each surface differently?

---

## 3. Gold — model the star schema (T-SQL)

**Objective:** turn Silver into a **business-ready star schema** and pre-computed
aggregates that Power BI can consume directly. This is the **contract** for Part 2.

Build in `sql/20_build_gold.sql`.

### Dimensions and facts

```
                 ┌───────────────┐
                 │  dim_date     │  (date_key, year, quarter, month, month_name)
                 └───────┬───────┘
                         │
   ┌────────────┐  ┌─────┴──────────────┐  ┌─────────────┐
   │ dim_genre  │──│  fact_movie        │──│ dim_language│
   └────────────┘  │  (grain: 1 movie)  │  └─────────────┘
                   │  movie_key,        │
                   │  date_key,         │
                   │  budget, revenue,  │
                   │  profit, roi,      │
                   │  runtime,          │
                   │  vote_average,     │
                   │  vote_count,       │
                   │  popularity        │
                   └────────────────────┘
```

### Requirements

- [ ] `dim_movie` (title, original_language, is_adult, etc.).
- [ ] `dim_genre`, `dim_date`, `dim_language`.
- [ ] `fact_movie` at one-row-per-movie grain with **derived measures**:
  - `profit = revenue - budget`
  - `roi = (revenue - budget) / NULLIF(budget, 0)`
  - guard every division with `NULLIF` to avoid divide-by-zero.
- [ ] A genre bridge (`bridge_movie_genre`) because a movie has many genres.
- [ ] At least **two Gold aggregate views** for KPIs, e.g.:
  - `gold.kpi_by_genre_year` — avg rating, total revenue, movie count.
  - `gold.kpi_studio_performance` — revenue & count by production company.
- [ ] Expose Gold as **views or tables** that Power BI connects to.

---

## 4. Deliverables checklist (Part 1)

- [ ] `src/ingest_bronze.py` — reproducible API ingestion with retries/rate limits.
- [ ] `data/bronze/` raw JSON **and** `bronze.raw_movies` populated.
- [ ] `src/clean_silver_python.py` — pandas Silver path.
- [ ] `sql/10_clean_silver_tsql.sql` — T-SQL Silver path.
- [ ] Silver tables populated; **Python vs SQL comparison note** written.
- [ ] `sql/20_build_gold.sql` — star schema + KPI views.
- [ ] Updated `README` in your repo with: how to run, the reflections above, and
      a data-quality issues log (what you found, how you fixed it).
- [ ] `.env` **not** committed; `.gitignore` covers secrets and `data/`.

### Acceptance criteria

1. Deleting Silver + Gold and re-running your scripts rebuilds them from Bronze.
2. No sentinel `0` budgets/revenues survive into Silver.
3. No duplicate `movie_id` in `silver.movies`.
4. Nested genres are correctly exploded and joinable.
5. Gold `roi`/`profit` never throw divide-by-zero and are null-safe.
6. Python and T-SQL Silver outputs reconcile.

---

