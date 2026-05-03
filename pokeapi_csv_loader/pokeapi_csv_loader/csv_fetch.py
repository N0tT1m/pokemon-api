"""Read PokeAPI CSVs.

The Docker image is built with prefetch.py snapshotting every CSV listed in
its CSVS into /app/csv_data/. fetch_csv() reads from there first, then falls
back to a live HTTP fetch if the file is missing (useful for adding a new CSV
without rebuilding the image during development).
"""
from __future__ import annotations

import csv
import io
import os
from typing import Iterable

import requests

BASE_URL = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv"
LOCAL_DIR = os.environ.get("CSV_DATA_DIR", "/app/csv_data")


def fetch_csv(name: str) -> list[dict[str, str]]:
    """Fetch a single CSV by basename (no extension) and return parsed rows.

    Reads /app/csv_data/{name}.csv if present; otherwise downloads from
    PokeAPI's GitHub raw URL.
    """
    local_path = os.path.join(LOCAL_DIR, f"{name}.csv")
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        url = f"{BASE_URL}/{name}.csv"
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        text = resp.content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def index_by(rows: Iterable[dict], key: str) -> dict[str, dict]:
    """Return {row[key]: row} mapping."""
    return {row[key]: row for row in rows}
