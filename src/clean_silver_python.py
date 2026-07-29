"""
Silver Layer Cleaning - Python / pandas

This script reads raw JSON payloads from the Bronze layer stored in
SQL Server, cleans and transforms the data, then writes the Silver
layer outputs to both parquet files and SQL Server tables.

Author: Your Name
Project: TMDB Movie Intelligence
"""

# ==========================================
# Standard Library Imports
# ==========================================

import os
import json
from pathlib import Path

# ==========================================
# Third-party Imports
# ==========================================
import numpy as np
import pandas as pd
import pyodbc
from dotenv import load_dotenv

# ==========================================
# Load environment variables
# ==========================================

# Read variables from the .env file
load_dotenv()

# Read SQL Server connection string
SQLSERVER_CONN = os.getenv("SQLSERVER_CONN")

# Validate that the connection string exists
if not SQLSERVER_CONN:
    raise ValueError(
        "SQLSERVER_CONN was not found. Check your .env file."
    )

# ==========================================
# Silver output directory
# ==========================================

# Directory where cleaned parquet files will be stored
SILVER_DIR = Path("data/silver")

# Create the directory if it doesn't exist
SILVER_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ==========================================
# SQL Server Connection
# ==========================================

def get_connection():
    """
    Create and return a SQL Server connection.

    Returns
    -------
    pyodbc.Connection
        Active SQL Server connection.
    """

    connection = pyodbc.connect(
        SQLSERVER_CONN
    )

    print("Connected to SQL Server.")

    return connection

# ==========================================
# Read Bronze data
# ==========================================

def read_movie_records(connection):
    """
    Read all movie endpoints used to build the Silver movies table.
    """

    query = """
    SELECT
        movie_id,
        source_endpoint,
        payload,
        ingested_at
    FROM bronze.raw_movies
    WHERE source_endpoint IN (
        'details',
        'discover',
        'popular',
        'trending'
    )
    """

    df = pd.read_sql(query, connection)

    print(f"Loaded {len(df)} movie records.")

    return df


def read_credits(connection):
    """
    Read movie credits from the Bronze layer.

    Returns
    -------
    pandas.DataFrame
        Movie credits with raw JSON payload.
    """

    query = """
    SELECT
        movie_id,
        payload,
        ingested_at
    FROM bronze.raw_movies
    WHERE source_endpoint = 'credits'
    """

    df = pd.read_sql(
        query,
        connection
    )

    print(f"Loaded {len(df)} movie credits.")

    return df


def read_genres(connection):
    """
    Read genre lookup from the Bronze layer.

    Returns
    -------
    pandas.DataFrame
        Genre lookup payload.
    """

    query = """
    SELECT
        payload,
        ingested_at
    FROM bronze.raw_movies
    WHERE source_endpoint = 'genres'
    """

    df = pd.read_sql(
        query,
        connection
    )

    print(f"Loaded {len(df)} genre lookup record(s).")

    return df

# ==========================================
# Clean movie details
# ==========================================

def clean_movies(raw_df):
    """
    Clean and transform movie data from the Bronze layer.

    Parameters
    ----------
    raw_df : pandas.DataFrame
        Raw movie records from Bronze.

    Returns
    -------
    pandas.DataFrame
        Clean Silver movies dataframe.
    """

    # --------------------------------------
    # Convert JSON strings to dictionaries
    # --------------------------------------

    raw_df = raw_df.copy()

    raw_df["payload"] = raw_df["payload"].apply(json.loads)

    # --------------------------------------
    # Flatten JSON
    # --------------------------------------

    movies_df = pd.json_normalize(raw_df["payload"])

    # Preserve Bronze metadata
    movies_df["source_endpoint"] = raw_df["source_endpoint"].values
    movies_df["ingested_at"] = raw_df["ingested_at"].values

    # --------------------------------------
    # Keep required columns
    # --------------------------------------

    columns = [
        "id",
        "title",
        "original_title",
        "original_language",
        "release_date",
        "budget",
        "revenue",
        "runtime",
        "vote_average",
        "vote_count",
        "popularity",
        "adult",
        "overview",
        "genres",
        "production_companies",
        "spoken_languages"
    ]

    for column in columns:
        if column not in movies_df.columns:
            movies_df[column] = pd.NA

    movies_df = movies_df[
        columns + [
            "source_endpoint",
            "ingested_at"
        ]
    ]

    # --------------------------------------
    # Rename columns
    # --------------------------------------

    movies_df = movies_df.rename(
        columns={
            "id": "movie_id",
            "adult": "is_adult"
        }
    )

    # --------------------------------------
    # Replace sentinel zeros
    # --------------------------------------

    movies_df["budget"] = movies_df["budget"].replace(0, pd.NA)
    movies_df["revenue"] = movies_df["revenue"].replace(0, pd.NA)
    movies_df["runtime"] = movies_df["runtime"].replace(0, pd.NA)

    # --------------------------------------
    # Parse release date
    # --------------------------------------

    movies_df["release_date"] = pd.to_datetime(
        movies_df["release_date"],
        errors="coerce"
    )

    movies_df["release_year"] = movies_df["release_date"].dt.year

    # --------------------------------------
    # Fix invalid ratings
    # --------------------------------------

    movies_df.loc[
        movies_df["vote_count"] == 0,
        "vote_average"
    ] = pd.NA

    # --------------------------------------
    # Standardize text
    # --------------------------------------

    movies_df["title"] = (
        movies_df["title"]
        .fillna("")
        .str.strip()
    )

    movies_df["original_title"] = (
        movies_df["original_title"]
        .fillna("")
        .str.strip()
    )

    movies_df["original_language"] = (
        movies_df["original_language"]
        .fillna("")
        .str.upper()
        .str.strip()
    )

    # --------------------------------------
    # Empty overview flag
    # --------------------------------------

    movies_df["overview_is_empty"] = (
        movies_df["overview"]
        .fillna("")
        .str.strip()
        .eq("")
    )

    # --------------------------------------
    # Convert data types
    # --------------------------------------

    movies_df["movie_id"] = movies_df["movie_id"].astype("Int64")
    movies_df["budget"] = movies_df["budget"].astype("Int64")
    movies_df["revenue"] = movies_df["revenue"].astype("Int64")
    movies_df["runtime"] = movies_df["runtime"].astype("Int64")
    movies_df["vote_count"] = movies_df["vote_count"].astype("Int64")
    movies_df["release_year"] = movies_df["release_year"].astype("Int64")
    movies_df["is_adult"] = movies_df["is_adult"].fillna(False).astype(bool)
    print("\nAfter astype:")
    print(movies_df[["budget", "revenue", "runtime"]].dtypes)
    # --------------------------------------
    # Completeness score
    # --------------------------------------

    movies_df["completeness_score"] = (
        movies_df["budget"].notna().astype(int)
        + movies_df["revenue"].notna().astype(int)
        + movies_df["runtime"].notna().astype(int)
        + movies_df["genres"].notna().astype(int)
        + movies_df["production_companies"].notna().astype(int)
        + movies_df["spoken_languages"].notna().astype(int)
    )

    # --------------------------------------
    # Endpoint priority
    # --------------------------------------

    endpoint_priority = {
        "details": 4,
        "discover": 3,
        "popular": 2,
        "trending": 1
    }

    movies_df["endpoint_priority"] = (
        movies_df["source_endpoint"]
        .map(endpoint_priority)
        .fillna(0)
    )

    # --------------------------------------
    # Deduplicate
    # --------------------------------------
    print(f"Rows before deduplication: {len(movies_df)}")
    print(f"Unique movie IDs before deduplication: {movies_df['movie_id'].nunique()}")
    movies_df = (
        movies_df
        .sort_values(
            by=[
                "movie_id",
                "completeness_score",
                "endpoint_priority",
                "ingested_at"
            ],
            ascending=[
                True,
                False,
                False,
                False
            ]
        )
        .drop_duplicates(
            subset="movie_id",
            keep="first"
        )
    )
    print(f"Rows after deduplication: {len(movies_df)}")
    print(f"Unique movie IDs after deduplication: {movies_df['movie_id'].nunique()}")
    # --------------------------------------
    # Remove helper columns
    # --------------------------------------

    movies_df = movies_df.drop(
        columns=[
            "completeness_score",
            "endpoint_priority",
            "source_endpoint"
        ]
    )

    return movies_df

# ==========================================
# Build genres lookup table
# ==========================================

def build_genres(genres_df):
    """
    Build the Silver genres lookup table.

    Parameters
    ----------
    genres_df : pandas.DataFrame
        Raw Bronze genres endpoint.

    Returns
    -------
    pandas.DataFrame
        Genre lookup table.
    """

    # Convert JSON string to dictionary
    genres_df["payload"] = genres_df["payload"].apply(
        json.loads
    )

    # Extract list of genres
    genre_list = genres_df.iloc[0]["payload"]["genres"]

    # Convert list to DataFrame
    genres = pd.DataFrame(genre_list)

    # Rename columns
    genres = genres.rename(
        columns={
            "id": "genre_id",
            "name": "genre_name"
        }
    )

    # Remove duplicates
    genres = genres.drop_duplicates()

    return genres

# ==========================================
# Build movie_genres bridge table
# ==========================================

def build_movie_genres(movies_df):
    """
    Build the Silver movie_genres bridge table.

    Parameters
    ----------
    movies_df : pandas.DataFrame
        Clean movies dataframe.

    Returns
    -------
    pandas.DataFrame
        Movie to genre bridge table.
    """

    movie_genres = movies_df[
        ["movie_id", "genres"]
    ].copy()

    # One row per genre
    movie_genres = movie_genres.explode(
        "genres"
    )

    # Remove movies without genres
    movie_genres = movie_genres.dropna(
        subset=["genres"]
    )

    # Extract genre_id
    movie_genres["genre_id"] = (
        movie_genres["genres"]
        .apply(lambda x: x["id"])
    )

    # Keep only required columns
    movie_genres = movie_genres[
        [
            "movie_id",
            "genre_id"
        ]
    ]

    # Remove duplicates
    movie_genres = movie_genres.drop_duplicates()

    return movie_genres

# ==========================================
# Build movie_companies bridge table
# ==========================================

def build_movie_companies(movies_df):
    """
    Build the Silver movie_companies bridge table.

    Parameters
    ----------
    movies_df : pandas.DataFrame
        Clean movies dataframe.

    Returns
    -------
    pandas.DataFrame
        Movie to production company bridge table.
    """

    movie_companies = movies_df[
        ["movie_id", "production_companies"]
    ].copy()

    # One row per company
    movie_companies = movie_companies.explode(
        "production_companies"
    )

    # Remove movies without companies
    movie_companies = movie_companies.dropna(
        subset=["production_companies"]
    )

    # Extract company name
    movie_companies["company_name"] = (
        movie_companies["production_companies"]
        .apply(lambda x: x["name"])
    )

    # Keep only required columns
    movie_companies = movie_companies[
        [
            "movie_id",
            "company_name"
        ]
    ]

    # Remove duplicates
    movie_companies = movie_companies.drop_duplicates()

    return movie_companies

# ==========================================
# Build movie_cast table
# ==========================================

def build_movie_cast(credits_df):
    """
    Build the Silver movie_cast table.

    Parameters
    ----------
    credits_df : pandas.DataFrame
        Raw Bronze credits dataframe.

    Returns
    -------
    pandas.DataFrame
        Top cast members and director for each movie.
    """

    # Convert JSON string to dictionary
    credits_df["payload"] = credits_df["payload"].apply(
        json.loads
    )

    records = []

    for payload in credits_df["payload"]:

        movie_id = payload["id"]

        # -------------------------------
        # Top 5 cast members
        # -------------------------------

        cast = payload.get("cast", [])

        for person in cast:

            if person.get("order", 999) <= 4:

                records.append({
                    "movie_id": movie_id,
                    "person_name": person.get("name"),
                    "role_type": "Cast",
                    "character_name": person.get("character"),
                    "cast_order": person.get("order")
                })

        # -------------------------------
        # Director
        # -------------------------------

        crew = payload.get("crew", [])

        for person in crew:

            if person.get("job") == "Director":

                records.append({
                    "movie_id": movie_id,
                    "person_name": person.get("name"),
                    "role_type": "Director",
                    "character_name": None,
                    "cast_order": None
                })

    movie_cast = pd.DataFrame(records)
    
    movie_cast = movie_cast.drop_duplicates()

    return movie_cast

# ==========================================
# Save Silver tables to Parquet
# ==========================================

def save_to_parquet(
    movies_df,
    genres_df,
    movie_genres_df,
    movie_companies_df,
    movie_cast_df
):
    """
    Save Silver tables as Parquet files.
    """

    output_dir = Path("data/silver")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Movies table (remove nested columns)
    movies_output = movies_df.drop(
        columns=[
            "genres",
            "production_companies",
            "spoken_languages"
        ]
    )

    movies_output.to_parquet(
        output_dir / "movies.parquet",
        index=False
    )

    genres_df.to_parquet(
        output_dir / "genres.parquet",
        index=False
    )

    movie_genres_df.to_parquet(
        output_dir / "movie_genres.parquet",
        index=False
    )

    movie_companies_df.to_parquet(
        output_dir / "movie_companies.parquet",
        index=False
    )

    movie_cast_df.to_parquet(
        output_dir / "movie_cast.parquet",
        index=False
    )

    print("\nSilver Parquet files saved.")

def python_value(value):
    """
    Convert pandas / NumPy values to native Python types
    that pyodbc understands.
    """

    if pd.isna(value):
        return None

    # Pandas Timestamp
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    # NumPy integer
    if isinstance(value, np.integer):
        return int(value)

    # NumPy float
    if isinstance(value, np.floating):
        return float(value)

    # NumPy bool
    if isinstance(value, np.bool_):
        return bool(value)

    return value

def load_movies_to_sql(connection, movies_df):
    """
    Load the Silver movies table into SQL Server.
    """

    cursor = connection.cursor()

    # Remove existing data
    cursor.execute("TRUNCATE TABLE silver_python.movies")

    insert_query = """
    INSERT INTO silver_python.movies
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
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    columns = [
    "movie_id",
    "title",
    "original_title",
    "original_language",
    "release_date",
    "release_year",
    "budget",
    "revenue",
    "runtime",
    "vote_average",
    "vote_count",
    "popularity",
    "is_adult",
    "overview_is_empty",
    "ingested_at"
]

    rows = [
    tuple(python_value(v) for v in row)
    for row in movies_df[columns].itertuples(index=False, name=None)
]
    cursor.fast_executemany = True

    cursor.executemany(insert_query, rows)

    connection.commit()

    print(f"{len(rows)} rows inserted into silver_python.movies.")

def load_dataframe_to_sql(
    connection,
    dataframe,
    table_name,
    columns
):
    """
    Load any DataFrame into a SQL Server table.
    """

    cursor = connection.cursor()

    cursor.execute(f"TRUNCATE TABLE {table_name}")

    placeholders = ", ".join(["?"] * len(columns))

    insert_query = f"""
    INSERT INTO {table_name}
    ({", ".join(columns)})
    VALUES ({placeholders})
    """

    rows = [
        tuple(python_value(v) for v in row)
        for row in dataframe[columns].itertuples(index=False, name=None)
    ]

    cursor.fast_executemany = True

    cursor.executemany(insert_query, rows)

    connection.commit()

    print(f"{len(rows)} rows inserted into {table_name}.")

def main():

    connection = get_connection()

    try:

        # Read Bronze data
        raw_df = read_movie_records(connection)
        genres_df = read_genres(connection)
        credits_df = read_credits(connection)

        # Build Silver DataFrames
        movies_df = clean_movies(raw_df)
        genres = build_genres(genres_df)
        movie_genres = build_movie_genres(movies_df)
        movie_companies = build_movie_companies(movies_df)
        movie_cast = build_movie_cast(credits_df)
        save_to_parquet(
    movies_df,
    genres,
    movie_genres,
    movie_companies,
    movie_cast
)
        load_movies_to_sql(connection, movies_df)
        # Display summary
        print("\nSilver tables created successfully.\n")

        load_dataframe_to_sql(
    connection=connection,
    dataframe=genres,
    table_name="silver_python.genres",
    columns=[
        "genre_id",
        "genre_name",
    ],
)
        load_dataframe_to_sql(
    connection=connection,
    dataframe=movie_genres,
    table_name="silver_python.movie_genres",
    columns=[
        "movie_id",
        "genre_id",
    ],
)
        load_dataframe_to_sql(
    connection=connection,
    dataframe=movie_companies,
    table_name="silver_python.movie_companies",
    columns=[
        "movie_id",
        "company_name",
    ],
)
        load_dataframe_to_sql(
    connection=connection,
    dataframe=movie_cast,
    table_name="silver_python.movie_cast",
    columns=[
        "movie_id",
        "person_name",
        "role_type",
        "character_name",
        "cast_order",
    ],
)
        print(f"movies: {len(movies_df)}")
        print(f"genres: {len(genres)}")
        print(f"movie_genres: {len(movie_genres)}")
        print(f"movie_companies: {len(movie_companies)}")
        print(f"movie_cast: {len(movie_cast)}")

    finally:

        connection.close()

        print("\nConnection closed.")


if __name__ == "__main__":
    main()