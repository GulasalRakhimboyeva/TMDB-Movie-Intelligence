# Part 2 — BI & Dashboard: Build the Movie Intelligence Report

---

## Learning objectives

By the end of Part 2 you can:

1. Connect Power BI to SQL Server and import a star schema.
2. Build a correct **data model** (relationships, star schema, hidden keys).
3. Write **DAX** measures for KPIs.
4. Design a clean, multi-page report that tells a story.
5. Apply BI best practices: single source of truth, no raw-data wrangling in the
   report, performance-aware modeling.

---

## The golden rule

> **Do not clean data in Power BI.** All cleaning happened in Part 1. Power BI
> connects to **Gold** only. 


---

## 1. Connect to the Gold layer

1. **Get Data → SQL Server.**
2. Server: your instance (e.g. `localhost`), Database: `movies`.
3. Choose **Import** mode (fine for ~1,000 movies; use DirectQuery only as a
   stretch goal).
4. Select the **Gold** objects only:
   - `gold.dim_movie`, `gold.dim_genre`, `gold.dim_date`, `gold.dim_language`
   - `gold.fact_movie`, `gold.bridge_movie_genre`
   - the KPI views (`gold.kpi_by_genre_year`, etc.) if useful.


---

## 2. Build the data model

- [ ] Create relationships: `fact_movie` → each dimension via keys.
- [ ] Genres are many-to-many via `bridge_movie_genre` — model the bridge
      correctly (movie → bridge → genre).
- [ ] Mark `dim_date` as a **Date table** (Table tools → Mark as date table).
- [ ] **Hide** surrogate/foreign keys from the report view.
- [ ] Rename fields to human-friendly names (e.g. `vote_average` → "Avg Rating").
- [ ] Verify the model is a clean **star** — no unnecessary cross-filters.

---

## 3. DAX measures (build at least these)

Create explicit measures (don't drag raw columns into visuals):

- [ ] `Total Revenue = SUM(fact_movie[revenue])`
- [ ] `Total Budget = SUM(fact_movie[budget])`
- [ ] `Total Profit = [Total Revenue] - [Total Budget]`
- [ ] `Avg ROI = AVERAGE(fact_movie[roi])` (already null-safe from Gold)
- [ ] `Movie Count = DISTINCTCOUNT(fact_movie[movie_key])`
- [ ] `Avg Rating = AVERAGE(fact_movie[vote_average])` (nulls excluded correctly)
- [ ] `Revenue YoY %` — year-over-year growth using the date table.
- [ ] One measure of your own that answers a real question.


---

## 4. The report — required pages

Design a clean, **3-page** report. Consistent colors, clear titles, and every
visual must answer a question.

### Page 1 — Executive Overview
- [ ] KPI cards: Total Revenue, Total Profit, Movie Count, Avg Rating.
- [ ] Revenue & movie count **trend over time** (line/column by year).
- [ ] Revenue **by genre** (bar).
- [ ] A slicer for **release year** and **genre**.

### Page 2 — Genre & Studio Deep Dive
- [ ] Avg rating vs revenue **by genre** (scatter or matrix).
- [ ] Top production companies by revenue / movie count.
- [ ] Budget vs revenue relationship (scatter, watch for the null handling).

### Page 3 — Movie Explorer
- [ ] A detailed, sortable table: title, year, genre, budget, revenue, ROI,
      rating.
- [ ] Drill-through from a genre/year to the movies behind it.
- [ ] Top/bottom performers (highest ROI, highest rated with enough votes).

### Design requirements
- [ ] Consistent theme/colors; readable fonts; titles on every visual.
- [ ] No broken/blank visuals; no raw key columns shown.
- [ ] At least one **interaction** (slicer cross-filtering, drill-through).
- [ ] A short "Data as of / source" note (TMDB, ingestion date).

---

## 5. Business questions your dashboard must answer

Your report should let a non-technical producer answer these in a few clicks:

1. Which genres generate the most revenue, and which are most *profitable*
   (ROI, not just gross)?
2. How have ratings and revenue trended over the years?
3. Which studios/production companies are the strongest performers?
4. Is there a relationship between budget and revenue? Do big budgets pay off?
5. What are the top and bottom performers, and what do they have in common?


---

## 6. Deliverables checklist (Part 2)

- [ ] `powerbi/movie_dashboard.pbix` connected to Gold (not to raw/Silver).
- [ ] Clean star-schema model with correct relationships and a marked date table.
- [ ] The required DAX measures.
- [ ] 3-page report meeting the requirements above.
- [ ] Insight summary paragraph.

### Acceptance criteria

1. The report connects to **Gold only** — no cleaning in Power Query.
2. KPIs are correct and null-safe (unknown budgets aren't counted as 0).
3. Genre many-to-many is modeled through the bridge, not faked.
4. All five business questions are answerable from the report.
5. The report is readable and professional — something you'd show an investor.
