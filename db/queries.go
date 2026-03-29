package db

import (
	"context"
	"fmt"
	"strings"

	"github.com/pokedex-api/models"
)

func GetPokemonByName(ctx context.Context, name string) (*models.Pokemon, error) {
	p := &models.Pokemon{}
	err := Pool.QueryRow(ctx, `
		SELECT name, url, national_no, types, species, height, weight,
			abilities, ev_yield, catch_rate, base_friendship, base_exp,
			growth_rate, egg_groups, gender_ratio, egg_cycles,
			hp, attack, defense, sp_atk, sp_def, speed, total
		FROM pokemon WHERE LOWER(name) = LOWER($1)
	`, name).Scan(
		&p.Name, &p.URL, &p.NationalNo, &p.Types, &p.Species,
		&p.Height, &p.Weight, &p.Abilities, &p.EVYield, &p.CatchRate,
		&p.BaseFriendship, &p.BaseExp, &p.GrowthRate, &p.EggGroups,
		&p.GenderRatio, &p.EggCycles, &p.HP, &p.Attack, &p.Defense,
		&p.SpAtk, &p.SpDef, &p.Speed, &p.Total,
	)
	if err != nil {
		return nil, err
	}
	return p, nil
}

func GetPokemonByNationalNo(ctx context.Context, no int) (*models.Pokemon, error) {
	p := &models.Pokemon{}
	// national_no is stored as text, try both padded and unpadded forms
	noStr := fmt.Sprintf("%04d", no)
	noStrTrimmed := strings.TrimLeft(noStr, "0")
	if noStrTrimmed == "" {
		noStrTrimmed = "0"
	}
	err := Pool.QueryRow(ctx, `
		SELECT name, url, national_no, types, species, height, weight,
			abilities, ev_yield, catch_rate, base_friendship, base_exp,
			growth_rate, egg_groups, gender_ratio, egg_cycles,
			hp, attack, defense, sp_atk, sp_def, speed, total
		FROM pokemon WHERE national_no = $1 OR national_no = $2
		LIMIT 1
	`, noStr, noStrTrimmed).Scan(
		&p.Name, &p.URL, &p.NationalNo, &p.Types, &p.Species,
		&p.Height, &p.Weight, &p.Abilities, &p.EVYield, &p.CatchRate,
		&p.BaseFriendship, &p.BaseExp, &p.GrowthRate, &p.EggGroups,
		&p.GenderRatio, &p.EggCycles, &p.HP, &p.Attack, &p.Defense,
		&p.SpAtk, &p.SpDef, &p.Speed, &p.Total,
	)
	if err != nil {
		return nil, err
	}
	return p, nil
}

func GetTypeDefenses(ctx context.Context, pokemonName string) ([]models.TypeDefense, error) {
	rows, err := Pool.Query(ctx, `
		SELECT type_name, multiplier
		FROM type_defenses WHERE pokemon_name = $1
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var defenses []models.TypeDefense
	for rows.Next() {
		var d models.TypeDefense
		if err := rows.Scan(&d.TypeName, &d.Multiplier); err != nil {
			return nil, err
		}
		defenses = append(defenses, d)
	}
	return defenses, nil
}

func GetEvolutions(ctx context.Context, pokemonName string) ([]models.Evolution, error) {
	rows, err := Pool.Query(ctx, `
		SELECT number, evo_name, evo_url, types, evolves_via, evolves_from, chain_order
		FROM evolutions WHERE pokemon_name = $1
		ORDER BY chain_order
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var evos []models.Evolution
	for rows.Next() {
		var e models.Evolution
		if err := rows.Scan(&e.Number, &e.Name, &e.URL, &e.Types, &e.EvolvesVia, &e.EvolvesFrom, &e.ChainOrder); err != nil {
			return nil, err
		}
		evos = append(evos, e)
	}
	return evos, nil
}

func GetMoves(ctx context.Context, pokemonName string) ([]models.Move, error) {
	rows, err := Pool.Query(ctx, `
		SELECT learn_method, level_or_tm, move_name, type, category, power, accuracy
		FROM moves WHERE pokemon_name = $1
		ORDER BY learn_method, level_or_tm
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var moves []models.Move
	for rows.Next() {
		var m models.Move
		if err := rows.Scan(&m.LearnMethod, &m.LevelOrTM, &m.Name, &m.Type, &m.Category, &m.Power, &m.Accuracy); err != nil {
			return nil, err
		}
		moves = append(moves, m)
	}
	return moves, nil
}

func GetLocations(ctx context.Context, pokemonName string) ([]models.Location, error) {
	rows, err := Pool.Query(ctx, `
		SELECT games, locations
		FROM locations WHERE pokemon_name = $1
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var locs []models.Location
	for rows.Next() {
		var l models.Location
		if err := rows.Scan(&l.Games, &l.Locations); err != nil {
			return nil, err
		}
		locs = append(locs, l)
	}
	return locs, nil
}

func GetRegionalDex(ctx context.Context, game string) ([]models.RegionalDexEntry, error) {
	rows, err := Pool.Query(ctx, `
		SELECT dex_number, pokemon_name, types
		FROM regional_dex WHERE game = $1
		ORDER BY dex_number
	`, game)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var entries []models.RegionalDexEntry
	for rows.Next() {
		var e models.RegionalDexEntry
		if err := rows.Scan(&e.DexNumber, &e.PokemonName, &e.Types); err != nil {
			return nil, err
		}
		entries = append(entries, e)
	}
	return entries, nil
}

func GetGameNationalDex(ctx context.Context, game string) ([]models.NationalDexEntry, error) {
	rows, err := Pool.Query(ctx, `
		SELECT national_no, pokemon_name
		FROM game_national_dex WHERE game = $1
		ORDER BY national_no
	`, game)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var entries []models.NationalDexEntry
	for rows.Next() {
		var e models.NationalDexEntry
		if err := rows.Scan(&e.NationalNo, &e.PokemonName); err != nil {
			return nil, err
		}
		entries = append(entries, e)
	}
	return entries, nil
}

func GetAllGames(ctx context.Context) ([]string, error) {
	rows, err := Pool.Query(ctx, `
		SELECT DISTINCT game FROM regional_dex ORDER BY game
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var games []string
	for rows.Next() {
		var g string
		if err := rows.Scan(&g); err != nil {
			return nil, err
		}
		games = append(games, g)
	}
	return games, nil
}

func GetAllPokemon(ctx context.Context, limit, offset int) ([]models.PokemonListEntry, int, error) {
	var total int
	err := Pool.QueryRow(ctx, `SELECT COUNT(*) FROM pokemon`).Scan(&total)
	if err != nil {
		return nil, 0, err
	}

	rows, err := Pool.Query(ctx, `
		SELECT name, national_no, types
		FROM pokemon ORDER BY national_no
		LIMIT $1 OFFSET $2
	`, limit, offset)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var entries []models.PokemonListEntry
	for rows.Next() {
		var e models.PokemonListEntry
		if err := rows.Scan(&e.Name, &e.NationalNo, &e.Types); err != nil {
			return nil, 0, err
		}
		entries = append(entries, e)
	}
	return entries, total, nil
}
