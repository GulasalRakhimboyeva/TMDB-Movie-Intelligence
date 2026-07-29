"""
Bronze Layer Loader

This script reads raw JSON files from the Bronze folder
and loads them into SQL Server without modification.

Author: Gulasal Rakhimboeva
Project: TMDB Movie Intelligence
"""

# ==============================
# Standard Library Imports
# ==============================

import os
import json
from pathlib import Path
from datetime import datetime, timezone

# ==============================
# Third-party Imports
# ==============================

import pyodbc
from dotenv import load_dotenv

# ==========================================
# Load Environment Variables
# ==========================================

load_dotenv()

SQL_CONN = os.getenv("SQLSERVER_CONN")

if not SQL_CONN:
    raise ValueError(
        "SQLSERVER_CONN was not found in the .env file."
    )

# Bronze folder location
BRONZE_DIR = Path("data/bronze")

# ==========================================
# Connect to SQL Server
# ==========================================

def connect_to_sqlserver():
    """
    Create a connection to SQL Server.

    Returns
    -------
    pyodbc.Connection
        SQL Server connection object.
    """

    connection = pyodbc.connect(SQL_CONN)

    print("Connected to SQL Server.")

    return connection

# ==========================================
# Insert one record into Bronze table
# ==========================================

def insert_record(
    connection,
    movie_id,
    source_endpoint,
    payload
):
    """
    Insert one Bronze record into SQL Server.

    Parameters
    ----------
    connection : pyodbc.Connection
        SQL Server connection.

    movie_id : int | None
        TMDB movie ID.

    source_endpoint : str
        Source endpoint (discover, details, credits, etc.)

    payload : dict
        Raw JSON payload.
    """

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO bronze.raw_movies
        (
            movie_id,
            source_endpoint,
            ingested_at,
            payload
        )
        VALUES (?, ?, ?, ?)
        """,
        movie_id,
        source_endpoint,
        datetime.now(timezone.utc),
        json.dumps(payload)
    )

    connection.commit()

# ==========================================
# Find all Bronze JSON files
# ==========================================

def get_json_files():
    """
    Return a list of all JSON files in the Bronze folder.
    """

    json_files = list(BRONZE_DIR.rglob("*.json"))

    print(f"Found {len(json_files)} JSON files.")

    return json_files

# ==========================================
# Load JSON files into SQL Server
# ==========================================

def load_json_files(connection):
    """
    Read all Bronze JSON files and load them into SQL Server.
    """

    json_files = get_json_files()

    for file_path in json_files:

        print(f"Processing: {file_path.name}")

        # Read JSON file
        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        # Endpoint is the parent folder name
        source_endpoint = file_path.parent.name

        # ----------------------------------
        # Discover endpoint
        # ----------------------------------
        # ----------------------------------
# List endpoints
# discover, popular, trending
# ----------------------------------

        if source_endpoint in [
            "discover",
            "popular",
            "trending"
        ]:

            for movie in data.get("results", []):

                insert_record(
                    connection=connection,
                    movie_id=movie.get("id"),
                    source_endpoint=source_endpoint,
                    payload=movie
                )


        # ----------------------------------
        # Single movie endpoints
        # details, credits
        # ----------------------------------

        else:

            insert_record(
                connection=connection,
                movie_id=data.get("id"),
                source_endpoint=source_endpoint,
                payload=data
            )

    print("All JSON files have been loaded.")

if __name__ == "__main__":

    connection = connect_to_sqlserver()

    load_json_files(connection)

    connection.close()

    print("Connection closed.")