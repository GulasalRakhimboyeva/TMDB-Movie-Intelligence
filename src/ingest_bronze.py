"""
Bronze Layer Ingestion Script

This script downloads raw movie data from the TMDB API and stores it
without modification. The raw JSON files become the Bronze layer of the
Medallion Architecture.

Author: Your Name
Project: TMDB Movie Intelligence
"""

# ==============================
# Standard Library Imports
# ==============================

import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone

# ==============================
# Third-party Imports
# ==============================

import requests
from dotenv import load_dotenv

# ==========================================
# Load environment variables
# ==========================================

# Read variables from the .env file
load_dotenv()

# Read the TMDB API key from the environment
API_KEY = os.getenv("TMDB_API_KEY")

# Validate that the API key exists
if not API_KEY:
    raise ValueError(
        "TMDB_API_KEY was not found. Check your .env file."
    )

# Base URL used for every TMDB endpoint
BASE_URL = "https://api.themoviedb.org/3"

# Directory where raw JSON files will be stored
BRONZE_DIR = Path("data/bronze")

# Create the directory if it does not exist.
# exist_ok=True makes the script idempotent.
BRONZE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ==========================================
# Reusable function for calling TMDB API
# ==========================================

def make_request(endpoint, params=None, max_retries=3):
    """
    Send a GET request to the TMDB API.

    Parameters
    ----------
    endpoint : str
        API endpoint (example: '/movie/popular').

    params : dict
        Optional query parameters.

    max_retries : int
        Maximum number of retry attempts for transient failures.

    Returns
    -------
    dict
        JSON response from the API.
    """

    # Create a dictionary if no parameters were provided
    if params is None:
        params = {}

    # Always include the API key
    params["api_key"] = API_KEY

    # Build the complete request URL
    url = f"{BASE_URL}{endpoint}"

    # Retry loop
    for attempt in range(max_retries):

        try:
            response = requests.get(
                url,
                params=params,
                timeout=30
            )

            # -------------------------------
            # Rate limit (HTTP 429)
            # -------------------------------
            if response.status_code == 429:

                retry_after = int(
                    response.headers.get("Retry-After", 5)
                )

                print(
                    f"Rate limit reached. Waiting {retry_after} seconds..."
                )

                time.sleep(retry_after)

                continue

            # Raise an exception for HTTP errors
            response.raise_for_status()

            # Small delay to avoid hitting the API too aggressively
            time.sleep(0.25)

            return response.json()

        except requests.exceptions.HTTPError as e:

            # Retry only server-side errors
            if response.status_code >= 500:

                wait = 2 ** attempt

                print(
                    f"Server error {response.status_code}. "
                    f"Retrying in {wait} seconds..."
                )

                time.sleep(wait)

                continue

            raise

        except requests.exceptions.RequestException as e:

            wait = 2 ** attempt

            print(
                f"Request failed: {e}"
            )

            print(
                f"Retrying in {wait} seconds..."
            )

            time.sleep(wait)

    raise Exception(
        f"Request failed after {max_retries} attempts."
    )
# ==========================================
# Save raw API response to Bronze layer
# ==========================================

def save_raw_json(data, endpoint, filename):
    """
    Save the raw API response into the appropriate Bronze folder.

    Parameters
    ----------
    data : dict
        Raw JSON returned by the API.

    endpoint : str
        Endpoint name (discover, details, credits, etc.)

    filename : str
        JSON file name.
    """

    # Create endpoint folder if it doesn't exist
    endpoint_dir = BRONZE_DIR / endpoint
    endpoint_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # Full file path
    file_path = endpoint_dir / filename

    # Save JSON exactly as returned by the API
    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(f"Saved: {file_path}")

# ==========================================
# Create Bronze metadata
# ==========================================

def create_metadata(movie_id, endpoint, payload):
    """
    Create metadata for a Bronze record.

    Parameters
    ----------
    movie_id : int | None
        Movie ID if available.

    endpoint : str
        Source endpoint.

    payload : dict
        Original API response.

    Returns
    -------
    dict
        Metadata dictionary.
    """

    return {

        "movie_id": movie_id,

        "source_endpoint": endpoint,

        "ingested_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "payload": payload
    }

# ==========================================
# Get movie IDs from Discover endpoint
# ==========================================

def discover_movies(
    start_year=2018,
    end_year=2023,
    pages_per_year=9
):
    """
    Collect movie IDs from the Discover endpoint.

    Parameters
    ----------
    start_year : int
        First release year.

    end_year : int
        Last release year.

    pages_per_year : int
        Number of pages to request for each year.

    Returns
    -------
    list
        List of discovered movie IDs.
    """

    movie_ids = []

    for year in range(start_year, end_year + 1):

        print(f"\nProcessing year {year}")

        for page in range(1, pages_per_year + 1):

            print(f"  Page {page}")

            data = make_request(
                "/discover/movie",
                params={
                    "primary_release_year": year,
                    "page": page,
                    "sort_by": "popularity.desc"
                }
            )

            # Save the raw Discover response
            save_raw_json(
                data,
                "discover",
                f"discover_{year}_page_{page}.json"
            )

            results = data.get("results", [])

            for movie in results:

                movie_ids.append(movie["id"])

             #   metadata = create_metadata(
             #   movie["id"],
             #   "discover",
              #  movie
             #   )

    return movie_ids

# ==========================================
# Get detailed information for each movie
# ==========================================

def get_movie_details(movie_ids):
    """
    Download detailed information for each movie.

    Parameters
    ----------
    movie_ids : list
        List of TMDB movie IDs.
    """

    print("\nDownloading movie details...")

    for movie_id in movie_ids:

        print(f"Movie ID: {movie_id}")

        data = make_request(
            f"/movie/{movie_id}"
        )

        save_raw_json(
            data,
            "details",
            f"movie_{movie_id}.json"
        )

# ==========================================
# Get movie credits (cast and crew)
# ==========================================

def get_movie_credits(movie_ids):
    """
    Download cast and crew information for each movie.

    Parameters
    ----------
    movie_ids : list
        List of TMDB movie IDs.
    """

    print("\nDownloading movie credits...")

    for movie_id in movie_ids:

        print(f"Movie ID: {movie_id}")

        data = make_request(
            f"/movie/{movie_id}/credits"
        )

        save_raw_json(
            data,
            "credits",
            f"credits_{movie_id}.json"
        )
# ==========================================
# Get weekly trending movies
# ==========================================

def get_trending_movies():
    """
    Download the weekly trending movies.
    """

    print("\nDownloading trending movies...")

    data = make_request(
        "/trending/movie/week"
    )

    save_raw_json(
        data,
        "trending",
        "trending_week.json"
    )

# ==========================================
# Get popular movies
# ==========================================

def get_popular_movies():
    """
    Download the current popular movies.
    """

    print("\nDownloading popular movies...")

    data = make_request(
        "/movie/popular"
    )

    save_raw_json(
        data,
        "popular",
        "popular_movies.json"
    )

# ==========================================
# Get movie genres
# ==========================================

def get_movie_genres():
    """
    Download the movie genre lookup table.
    """

    print("\nDownloading movie genres...")

    data = make_request(
        "/genre/movie/list"
    )

    save_raw_json(
        data,
        "genres",
        "movie_genres.json"
    )

if __name__ == "__main__":

    movie_ids = discover_movies()

    movie_ids = list(dict.fromkeys(movie_ids))

    print(f"\nCollected {len(movie_ids)} unique movie IDs")

    get_movie_details(movie_ids)

    get_movie_credits(movie_ids)

    get_trending_movies()

    get_popular_movies()

    get_movie_genres()