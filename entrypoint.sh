#!/bin/sh
set -e

echo "=== Running Pokemon scraper ==="
cd /app/pokemondb_scraper
scrapy crawl pokemondb_pokemon --nolog -L WARNING
echo "=== Pokemon data synced ==="

echo "=== Running Regional Dex scraper ==="
scrapy crawl pokemondb_regional_dex --nolog -L WARNING
echo "=== Regional dex data synced ==="

echo "=== Starting API server ==="
cd /app
exec ./pokedex-api
