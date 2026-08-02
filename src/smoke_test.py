import os
import requests
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

# Read API key
api_key = os.getenv("TMDB_API_KEY")

if not api_key:
    raise ValueError("TMDB_API_KEY not found in .env")

# Call TMDB API
response = requests.get(
    "https://api.themoviedb.org/3/movie/550",
    params={"api_key": api_key},
    timeout=30
)

# Print the result
print("Status Code:", response.status_code)

if response.status_code == 200:
    data = response.json()
    print("Movie Title:", data["title"])
else:
    print(response.text)

