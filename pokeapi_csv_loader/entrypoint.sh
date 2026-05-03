#!/bin/sh
set -e

cd /app

echo "=== Loading PokeAPI CSV data ==="
python -m pokeapi_csv_loader
echo "=== PokeAPI CSV data synced ==="
