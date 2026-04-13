#!/bin/sh
set -e

cd /app

echo "=== Running Pokemon scraper ==="
scrapy crawl pokemondb_pokemon --nolog -L WARNING
echo "=== Pokemon data synced ==="

echo "=== Running Egg Move Parents scraper ==="
scrapy crawl pokemondb_egg_moves --nolog -L WARNING
echo "=== Egg move parents synced ==="

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

echo "=== Running Berries scraper ==="
scrapy crawl pokemondb_berries --nolog -L WARNING
echo "=== Berry data synced ==="

echo "=== Running Trainers scraper ==="
scrapy crawl pokemondb_trainers --nolog -L WARNING
echo "=== Trainer data synced ==="

echo "=== Running Z-Moves scraper ==="
scrapy crawl pokemondb_zmoves --nolog -L WARNING
echo "=== Z-Moves data synced ==="

echo "=== Running Pokemon GO scraper ==="
scrapy crawl pokemondb_go --nolog -L WARNING
echo "=== Pokemon GO data synced ==="

echo "=== Running Contest Stats scraper ==="
scrapy crawl pokemondb_contest --nolog -L WARNING
echo "=== Contest stats synced ==="

echo "=== Running Battle Facilities scraper ==="
scrapy crawl pokemondb_battle_facilities --nolog -L WARNING
echo "=== Battle facilities synced ==="

echo "=== Running Bulbapedia supplemental scrapers ==="
scrapy crawl bulbapedia_classification --nolog -L WARNING
scrapy crawl bulbapedia_ingame_trades --nolog -L WARNING
scrapy crawl bulbapedia_events --nolog -L WARNING
scrapy crawl bulbapedia_outbreaks --nolog -L WARNING
scrapy crawl bulbapedia_version_exclusives --nolog -L WARNING
scrapy crawl bulbapedia_move_tutors --nolog -L WARNING
echo "=== Bulbapedia supplemental data synced ==="

echo "=== Running Tera Raid scraper ==="
scrapy crawl game8_raids --nolog -L WARNING
echo "=== Raid data synced ==="

echo "=== All spiders complete ==="
