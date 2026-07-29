TRUNCATE TABLE silver.movies;

WITH parsed AS
(
    SELECT

        TRY_CONVERT(INT, JSON_VALUE(payload, '$.id')) AS movie_id,

        JSON_VALUE(payload, '$.title') AS title,

        JSON_VALUE(payload, '$.original_title') AS original_title,

        UPPER(LTRIM(RTRIM(JSON_VALUE(payload, '$.original_language'))))
            AS original_language,

        TRY_CONVERT(
            DATE,
            NULLIF(JSON_VALUE(payload, '$.release_date'), '')
        ) AS release_date,

        NULLIF(
            TRY_CONVERT(BIGINT, JSON_VALUE(payload, '$.budget')),
            0
        ) AS budget,

        NULLIF(
            TRY_CONVERT(BIGINT, JSON_VALUE(payload, '$.revenue')),
            0
        ) AS revenue,

        NULLIF(
            TRY_CONVERT(INT, JSON_VALUE(payload, '$.runtime')),
            0
        ) AS runtime,

        TRY_CONVERT(
            FLOAT,
            JSON_VALUE(payload, '$.vote_average')
        ) AS vote_average_raw,

        TRY_CONVERT(
            INT,
            JSON_VALUE(payload, '$.vote_count')
        ) AS vote_count,

        TRY_CONVERT(
            FLOAT,
            JSON_VALUE(payload, '$.popularity')
        ) AS popularity,

        TRY_CONVERT(
            BIT,
            JSON_VALUE(payload, '$.adult')
        ) AS is_adult,

        CASE
            WHEN NULLIF(
                    LTRIM(RTRIM(JSON_VALUE(payload, '$.overview'))),
                    ''
                 ) IS NULL
            THEN 1
            ELSE 0
        END AS overview_is_empty,

        ingested_at,

        payload

    FROM bronze.raw_movies

    WHERE source_endpoint IN
    (
        'details',
        'discover',
        'popular',
        'trending'
    )
),
ranked AS
(
    SELECT
        *,

        (
            CASE WHEN budget IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN revenue IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN runtime IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN JSON_QUERY(payload, '$.genres') IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN JSON_QUERY(payload, '$.production_companies') IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN JSON_QUERY(payload, '$.spoken_languages') IS NOT NULL THEN 1 ELSE 0 END
        ) AS completeness_score,

        ROW_NUMBER() OVER
        (
            PARTITION BY movie_id

            ORDER BY

            (
                CASE WHEN budget IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN revenue IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN runtime IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN JSON_QUERY(payload, '$.genres') IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN JSON_QUERY(payload, '$.production_companies') IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN JSON_QUERY(payload, '$.spoken_languages') IS NOT NULL THEN 1 ELSE 0 END
            ) DESC,

            ingested_at DESC

        ) AS rn

    FROM parsed
)
INSERT INTO silver.movies
(
    movie_id,
    title,
    original_title,
    original_language,
    release_date,
    release_year,
    budget,
    revenue,
    runtime,
    vote_average,
    vote_count,
    popularity,
    is_adult,
    overview_is_empty,
    ingested_at
)

SELECT

    movie_id,

    title,

    original_title,

    original_language,

    release_date,

    YEAR(release_date),

    budget,

    revenue,

    runtime,

    CASE
        WHEN vote_count = 0
        THEN NULL
        ELSE vote_average_raw
    END,

    vote_count,

    popularity,

    is_adult,

    overview_is_empty,

    ingested_at

FROM ranked

WHERE rn = 1;

--SELECT count(*)
--FROM silver.movies;
--SELECT count(*)
--FROM silver_python.movies;

--SELECT DB_NAME() AS CurrentDatabase;

TRUNCATE TABLE silver.genres;

INSERT INTO silver.genres
(
    genre_id,
    genre_name
)
SELECT
    TRY_CONVERT(INT, JSON_VALUE(g.value, '$.id')) AS genre_id,
    JSON_VALUE(g.value, '$.name') AS genre_name
FROM bronze.raw_movies b
CROSS APPLY OPENJSON(b.payload, '$.genres') g
WHERE b.source_endpoint = 'genres';

TRUNCATE TABLE silver.movie_genres;

INSERT INTO silver.movie_genres
(
    movie_id,
    genre_id
)
SELECT

    TRY_CONVERT(INT, JSON_VALUE(b.payload,'$.id')) AS movie_id,

    TRY_CONVERT(INT, JSON_VALUE(g.value,'$.id')) AS genre_id

FROM bronze.raw_movies b

CROSS APPLY OPENJSON(b.payload,'$.genres') g

WHERE b.source_endpoint = 'details';


TRUNCATE TABLE silver.movie_companies;

INSERT INTO silver.movie_companies
(
    movie_id,
    company_name
)
SELECT

    TRY_CONVERT(INT, JSON_VALUE(b.payload,'$.id')),

    JSON_VALUE(c.value,'$.name')

FROM bronze.raw_movies b

CROSS APPLY OPENJSON(
    b.payload,
    '$.production_companies'
) c

WHERE b.source_endpoint='details';


TRUNCATE TABLE silver.movie_cast;

-- Top 5 cast
INSERT INTO silver.movie_cast
(
    movie_id,
    person_name,
    role_type,
    character_name,
    cast_order
)
SELECT

    TRY_CONVERT(INT, JSON_VALUE(b.payload,'$.id')),

    JSON_VALUE(c.value,'$.name'),

    'Cast',

    JSON_VALUE(c.value,'$.character'),

    TRY_CONVERT(INT, JSON_VALUE(c.value,'$.order'))

FROM bronze.raw_movies b

CROSS APPLY OPENJSON(b.payload,'$.cast') c

WHERE
    b.source_endpoint='credits'
    AND TRY_CONVERT(INT, JSON_VALUE(c.value,'$.order')) <= 4;


-- Director
INSERT INTO silver.movie_cast
(
    movie_id,
    person_name,
    role_type,
    character_name,
    cast_order
)
SELECT

    TRY_CONVERT(INT, JSON_VALUE(b.payload,'$.id')),

    JSON_VALUE(c.value,'$.name'),

    'Director',

    NULL,

    NULL

FROM bronze.raw_movies b

CROSS APPLY OPENJSON(b.payload,'$.crew') c

WHERE
    b.source_endpoint='credits'
    AND JSON_VALUE(c.value,'$.job')='Director';