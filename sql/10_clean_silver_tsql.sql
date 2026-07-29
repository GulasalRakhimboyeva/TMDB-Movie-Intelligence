CREATE TABLE silver.movies
(
    movie_id INT PRIMARY KEY,

    title NVARCHAR(500),
    original_title NVARCHAR(500),

    original_language VARCHAR(10),

    release_date DATE,
    release_year INT,

    budget BIGINT NULL,
    revenue BIGINT NULL,
    runtime INT NULL,

    vote_average FLOAT NULL,
    vote_count INT,

    popularity FLOAT,

    is_adult BIT,

    overview_is_empty BIT,

    ingested_at DATETIME2
);

CREATE TABLE silver.genres
(
    genre_id INT PRIMARY KEY,
    genre_name NVARCHAR(100)
);

CREATE TABLE silver.movie_genres
(
    movie_id INT,
    genre_id INT
);

CREATE TABLE silver.movie_companies
(
    movie_id INT,
    company_name NVARCHAR(300)
);

CREATE TABLE silver.movie_cast
(
    movie_id INT,

    person_name NVARCHAR(200),

    role_type VARCHAR(20),

    character_name NVARCHAR(300),

    cast_order INT
);

SELECT 
    TABLE_SCHEMA,
    TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'silver';

CREATE TABLE silver_python.movies
(
    movie_id INT PRIMARY KEY,

    title NVARCHAR(500),
    original_title NVARCHAR(500),

    original_language VARCHAR(10),

    release_date DATE,
    release_year INT,

    budget BIGINT NULL,
    revenue BIGINT NULL,
    runtime INT NULL,

    vote_average FLOAT NULL,
    vote_count INT,

    popularity FLOAT,

    is_adult BIT,

    overview_is_empty BIT,

    ingested_at DATETIME2
);

CREATE TABLE silver_python.genres
(
    genre_id INT PRIMARY KEY,
    genre_name NVARCHAR(100)
);

CREATE TABLE silver_python.movie_genres
(
    movie_id INT,
    genre_id INT
);

CREATE TABLE silver_python.movie_companies
(
    movie_id INT,
    company_name NVARCHAR(300)
);

CREATE TABLE silver_python.movie_cast
(
    movie_id INT,

    person_name NVARCHAR(200),

    role_type VARCHAR(20),

    character_name NVARCHAR(300),

    cast_order INT
);

SELECT 
    TABLE_SCHEMA,
    TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'silver_python';