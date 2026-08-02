-- to check data inserted
SELECT TOP (10) *
FROM bronze.raw_movies;

--record count
SELECT
    COUNT(*) AS record_count
FROM bronze.raw_movies
-- counting by endpoints
SELECT
    source_endpoint,
    COUNT(*) AS record_count
FROM bronze.raw_movies
GROUP BY source_endpoint
ORDER BY source_endpoint;

-- only popular endpoint data
SELECT *
FROM bronze.raw_movies
where source_endpoint ='popular';

-- counting how many records each movie have, seeing dublicates
SELECT 
    movie_id,
    COUNT(*) AS appearances
FROM bronze.raw_movies
WHERE movie_id IS NOT NULL
GROUP BY movie_id
HAVING COUNT(*) > 1
ORDER BY appearances DESC;

SELECT COUNT(*) FROM silver_python.movies;
SELECT COUNT(*) FROM silver.movies;

SELECT COUNT(*) FROM silver_python.movie_genres;
SELECT COUNT(*) FROM silver.movie_genres;

SELECT COUNT(*) FROM silver_python.movie_companies;
SELECT COUNT(*) FROM silver.movie_companies;

SELECT COUNT(*) FROM silver_python.movie_cast;
SELECT COUNT(*) FROM silver.movie_cast;

select * from gold.dim_date

select * from gold.dim_genre

select * from gold.fact_movie

select * from gold.kpi_by_genre_year

select * from gold.kpi_studio_performance