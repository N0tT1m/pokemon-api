#!/bin/sh
set -e

cd /app

echo "=== Running Pokemon scraper ==="
scrapy crawl pokemondb_pokemon --nolog -L WARNING
echo "=== Pokemon data synced ==="

echo "=== Running Regional Dex scraper ==="
scrapy crawl pokemondb_regional_dex --nolog -L WARNING
echo "=== Regional dex data synced ==="

echo "=== Running Locations scraper ==="
scrapy crawl pokemondb_locations --nolog -L WARNING
echo "=== Location data synced ==="

echo "=== Running Abilities scraper ==="
scrapy crawl pokemondb_abilities --nolog -L WARNING
echo "=== Abilities data synced ==="

echo "=== Running Items scraper ==="
scrapy crawl pokemondb_items --nolog -L WARNING
echo "=== Items data synced ==="

echo "=== Running Moves scraper ==="
scrapy crawl pokemondb_moves --nolog -L WARNING
echo "=== Moves data synced ==="

echo "=== Running Natures scraper ==="
scrapy crawl pokemondb_natures --nolog -L WARNING
echo "=== Natures data synced ==="

echo "=== Running Bulbapedia scrapers ==="
scrapy crawl bulbapedia_item_locations --nolog -L WARNING
scrapy crawl bulbapedia_tm_locations --nolog -L WARNING
scrapy crawl bulbapedia_pokemon --nolog -L WARNING
scrapy crawl bulbapedia_pokemon_locations --nolog -L WARNING
echo "=== Bulbapedia data synced ==="

echo "=== Running Tera Raid scraper ==="
scrapy crawl game8_raids --nolog -L WARNING
echo "=== Raid data synced ==="

echo "=== All spiders complete ==="
