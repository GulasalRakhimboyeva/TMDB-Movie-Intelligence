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
SILVER_DIR = Path("data/silver/python")

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