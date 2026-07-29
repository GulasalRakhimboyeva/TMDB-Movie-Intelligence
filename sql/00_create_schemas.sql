-- ==========================================
-- Create Database
-- ==========================================

IF DB_ID('movies') IS NULL
BEGIN
    CREATE DATABASE movies;
END;
GO

USE movies;
GO

-- ==========================================
-- Create Schemas
-- ==========================================

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'bronze')
BEGIN
    EXEC('CREATE SCHEMA bronze');
END;
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'silver')
BEGIN
    EXEC('CREATE SCHEMA silver');
END;
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'gold')
BEGIN
    EXEC('CREATE SCHEMA gold');
END;
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'silver_python')
BEGIN
    EXEC('CREATE SCHEMA silver_python');
END;
GO

-- ==========================================
-- Create Bronze Table
-- ==========================================

IF OBJECT_ID('bronze.raw_movies', 'U') IS NOT NULL
    DROP TABLE bronze.raw_movies;
GO

CREATE TABLE bronze.raw_movies
(
    raw_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    movie_id INT NULL,
    source_endpoint VARCHAR(50) NOT NULL,
    ingested_at DATETIME2 NOT NULL,
    payload NVARCHAR(MAX) NOT NULL
);
GO


-- ==========================================
-- Create Silver Tables for TSQL
-- ==========================================
IF OBJECT_ID('silver.movies', 'U') IS NOT NULL
    DROP TABLE silver.movies;
GO
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
IF OBJECT_ID('silver.genres', 'U') IS NOT NULL
    DROP TABLE silver.genres;

CREATE TABLE silver.genres
(
    genre_id INT PRIMARY KEY,
    genre_name NVARCHAR(100)
);
IF OBJECT_ID('silver.movie_genres', 'U') IS NOT NULL
    DROP TABLE silver.movie_genres;
CREATE TABLE silver.movie_genres
(
    movie_id INT,
    genre_id INT
);
IF OBJECT_ID('silver.movie_companies', 'U') IS NOT NULL
    DROP TABLE silver.movie_companies;
CREATE TABLE silver.movie_companies
(
    movie_id INT,
    company_name NVARCHAR(300)
);
IF OBJECT_ID('silver.movie_cast', 'U') IS NOT NULL
    DROP TABLE silver.movie_cast;
CREATE TABLE silver.movie_cast
(
    movie_id INT,

    person_name NVARCHAR(200),

    role_type VARCHAR(20),

    character_name NVARCHAR(300),

    cast_order INT
);



-- ==========================================
-- Create Silver Tables for Python
-- ==========================================
IF OBJECT_ID('silver_python.movies', 'U') IS NOT NULL
    DROP TABLE silver_python.movies;
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
IF OBJECT_ID('silver_python.genres', 'U') IS NOT NULL
    DROP TABLE silver_python.genres;
CREATE TABLE silver_python.genres
(
    genre_id INT PRIMARY KEY,
    genre_name NVARCHAR(100)
);
IF OBJECT_ID('silver_python.movie_genres', 'U') IS NOT NULL
    DROP TABLE silver_python.movie_genres;
CREATE TABLE silver_python.movie_genres
(
    movie_id INT,
    genre_id INT
);
IF OBJECT_ID('silver_python.movie_companies', 'U') IS NOT NULL
    DROP TABLE silver_python.movie_companies;
CREATE TABLE silver_python.movie_companies
(
    movie_id INT,
    company_name NVARCHAR(300)
);

IF OBJECT_ID('silver_python.movie_cast', 'U') IS NOT NULL
    DROP TABLE silver_python.movie_cast;

CREATE TABLE silver_python.movie_cast
(
    movie_id INT,
    person_name NVARCHAR(255),
    role_type NVARCHAR(20),
    character_name NVARCHAR(255),
    cast_order INT NULL
);
GO


