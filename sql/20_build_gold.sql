USE movies;
GO

IF NOT EXISTS
(
    SELECT *
    FROM sys.schemas
    WHERE name = 'gold'
)
BEGIN
    EXEC('CREATE SCHEMA gold');
END
GO

DROP TABLE IF EXISTS gold.dim_date;
GO

CREATE TABLE gold.dim_date
(
    date_key INT PRIMARY KEY,

    full_date DATE,

    calendar_year INT,

    calendar_quarter INT,

    calendar_month INT,

    month_name VARCHAR(20)
);
GO

INSERT INTO gold.dim_date
(
    date_key,
    full_date,
    calendar_year,
    calendar_quarter,
    calendar_month,
    month_name
)
SELECT DISTINCT

    YEAR(release_date) * 10000
    + MONTH(release_date) * 100
    + DAY(release_date),

    release_date,

    YEAR(release_date),

    DATEPART(QUARTER, release_date),

    MONTH(release_date),

    DATENAME(MONTH, release_date)

FROM silver.movies

WHERE release_date IS NOT NULL;

DROP TABLE IF EXISTS gold.dim_language;
GO

CREATE TABLE gold.dim_language
(
    language_key INT IDENTITY(1,1) PRIMARY KEY,

    language_code VARCHAR(10) UNIQUE
);
GO

INSERT INTO gold.dim_language
(
    language_code
)
SELECT DISTINCT
    original_language
FROM silver.movies
WHERE original_language IS NOT NULL
ORDER BY original_language;

DROP TABLE IF EXISTS gold.dim_genre;
GO

CREATE TABLE gold.dim_genre
(
    genre_key INT IDENTITY(1,1) PRIMARY KEY,

    genre_id INT UNIQUE,

    genre_name NVARCHAR(100)
);
GO

INSERT INTO gold.dim_genre
(
    genre_id,
    genre_name
)
SELECT

    genre_id,

    genre_name

FROM silver.genres

ORDER BY genre_name;

DROP TABLE IF EXISTS gold.dim_movie;
GO

CREATE TABLE gold.dim_movie
(
    movie_key INT IDENTITY(1,1) PRIMARY KEY,

    movie_id INT UNIQUE,

    title NVARCHAR(500),

    original_title NVARCHAR(500),

    original_language VARCHAR(10),

    release_date DATE,

    release_year INT,

    runtime INT,

    is_adult BIT,

    overview_is_empty BIT
);
GO

INSERT INTO gold.dim_movie
(
    movie_id,
    title,
    original_title,
    original_language,
    release_date,
    release_year,
    runtime,
    is_adult,
    overview_is_empty
)

SELECT

    movie_id,

    title,

    original_title,

    original_language,

    release_date,

    release_year,

    runtime,

    is_adult,

    overview_is_empty

FROM silver.movies

ORDER BY movie_id;

DROP TABLE IF EXISTS gold.fact_movie;
GO

CREATE TABLE gold.fact_movie
(
    movie_key INT PRIMARY KEY,

    date_key INT NULL,

    language_key INT NULL,

    budget BIGINT NULL,

    revenue BIGINT NULL,

    profit BIGINT NULL,

    roi FLOAT NULL,

    runtime INT NULL,

    vote_average FLOAT NULL,

    vote_count INT,

    popularity FLOAT
);
GO

INSERT INTO gold.fact_movie
(
    movie_key,
    date_key,
    language_key,
    budget,
    revenue,
    profit,
    roi,
    runtime,
    vote_average,
    vote_count,
    popularity
)

SELECT

    dm.movie_key,

    dd.date_key,

    dl.language_key,

    s.budget,

    s.revenue,

    CASE
        WHEN s.budget IS NULL
          OR s.revenue IS NULL
        THEN NULL
        ELSE s.revenue - s.budget
    END AS profit,

    CASE
        WHEN s.budget IS NULL
          OR s.revenue IS NULL
        THEN NULL
        ELSE CAST(s.revenue - s.budget AS FLOAT)
             / NULLIF(s.budget,0)
    END AS roi,

    s.runtime,

    s.vote_average,

    s.vote_count,

    s.popularity

FROM silver.movies s

INNER JOIN gold.dim_movie dm
ON s.movie_id = dm.movie_id

LEFT JOIN gold.dim_date dd
ON s.release_date = dd.full_date

LEFT JOIN gold.dim_language dl
ON s.original_language = dl.language_code;

DROP TABLE IF EXISTS gold.bridge_movie_genre;
GO

CREATE TABLE gold.bridge_movie_genre
(
    movie_key INT NOT NULL,

    genre_key INT NOT NULL
);
GO

INSERT INTO gold.bridge_movie_genre
(
    movie_key,
    genre_key
)

SELECT

    dm.movie_key,

    dg.genre_key

FROM silver.movie_genres mg

INNER JOIN gold.dim_movie dm
ON mg.movie_id = dm.movie_id

INNER JOIN gold.dim_genre dg
ON mg.genre_id = dg.genre_id;


CREATE OR ALTER VIEW gold.kpi_by_genre_year
AS

SELECT

    dd.calendar_year,

    dg.genre_name,

    COUNT(*) AS movie_count,

    AVG(f.vote_average) AS average_rating,

    SUM(f.revenue) AS total_revenue

FROM gold.fact_movie f

INNER JOIN gold.dim_date dd
ON f.date_key = dd.date_key

INNER JOIN gold.bridge_movie_genre b
ON f.movie_key = b.movie_key

INNER JOIN gold.dim_genre dg
ON b.genre_key = dg.genre_key

GROUP BY

    dd.calendar_year,

    dg.genre_name;
GO

CREATE OR ALTER VIEW gold.kpi_studio_performance
AS

SELECT

    mc.company_name,

    COUNT(*) AS movie_count,

    SUM(f.revenue) AS total_revenue,

    AVG(f.vote_average) AS average_rating

FROM silver.movie_companies mc

INNER JOIN gold.dim_movie dm
ON mc.movie_id = dm.movie_id

INNER JOIN gold.fact_movie f
ON dm.movie_key = f.movie_key

GROUP BY

    mc.company_name;
GO