-- to check data inserted
SELECT TOP (10) *
FROM bronze.raw_movies;

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