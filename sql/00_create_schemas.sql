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

