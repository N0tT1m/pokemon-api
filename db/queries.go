package db

import (
	"context"
	"fmt"
	"strings"

	"github.com/N0tT1m/pokemon-api/models"
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

// --- Item queries ---

func GetAllItems(ctx context.Context, limit, offset int) ([]models.ItemDetail, int, error) {
	var total int
	err := Pool.QueryRow(ctx, `SELECT COUNT(*) FROM item_details`).Scan(&total)
	if err != nil {
		return nil, 0, err
	}
	rows, err := Pool.Query(ctx, `
		SELECT name, category, effect, sprite_url, buy_price, sell_price
		FROM item_details ORDER BY name LIMIT $1 OFFSET $2
	`, limit, offset)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()
	var items []models.ItemDetail
	for rows.Next() {
		var i models.ItemDetail
		if err := rows.Scan(&i.Name, &i.Category, &i.Effect, &i.SpriteURL, &i.BuyPrice, &i.SellPrice); err != nil {
			return nil, 0, err
		}
		items = append(items, i)
	}
	return items, total, nil
}

func GetItemByName(ctx context.Context, name string) (*models.ItemDetail, error) {
	i := &models.ItemDetail{}
	err := Pool.QueryRow(ctx, `
		SELECT name, category, effect, sprite_url, buy_price, sell_price
		FROM item_details WHERE LOWER(name) = LOWER($1)
	`, name).Scan(&i.Name, &i.Category, &i.Effect, &i.SpriteURL, &i.BuyPrice, &i.SellPrice)
	if err != nil {
		return nil, err
	}
	return i, nil
}

// --- Move queries ---

func GetAllMoveDetails(ctx context.Context, limit, offset int) ([]models.MoveDetail, int, error) {
	var total int
	err := Pool.QueryRow(ctx, `SELECT COUNT(*) FROM move_details`).Scan(&total)
	if err != nil {
		return nil, 0, err
	}
	rows, err := Pool.Query(ctx, `
		SELECT name, type, category, power, accuracy, pp, effect, effect_chance, priority, target
		FROM move_details ORDER BY name LIMIT $1 OFFSET $2
	`, limit, offset)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()
	var moves []models.MoveDetail
	for rows.Next() {
		var m models.MoveDetail
		if err := rows.Scan(&m.Name, &m.Type, &m.Category, &m.Power, &m.Accuracy, &m.PP, &m.Effect, &m.EffectChance, &m.Priority, &m.Target); err != nil {
			return nil, 0, err
		}
		moves = append(moves, m)
	}
	return moves, total, nil
}

func GetMoveDetailByName(ctx context.Context, name string) (*models.MoveDetail, error) {
	m := &models.MoveDetail{}
	err := Pool.QueryRow(ctx, `
		SELECT name, type, category, power, accuracy, pp, effect, effect_chance, priority, target
		FROM move_details WHERE LOWER(name) = LOWER($1)
	`, name).Scan(&m.Name, &m.Type, &m.Category, &m.Power, &m.Accuracy, &m.PP, &m.Effect, &m.EffectChance, &m.Priority, &m.Target)
	if err != nil {
		return nil, err
	}
	return m, nil
}

func GetPokemonForms(ctx context.Context, pokemonName string) ([]models.PokemonForm, error) {
	rows, err := Pool.Query(ctx, `
		SELECT pokemon_name, form_name, types, abilities, height, weight,
		       hp, attack, defense, sp_atk, sp_def, speed, total
		FROM pokemon_forms WHERE LOWER(pokemon_name) = LOWER($1)
		ORDER BY form_name
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var forms []models.PokemonForm
	for rows.Next() {
		var f models.PokemonForm
		if err := rows.Scan(&f.PokemonName, &f.FormName, &f.Types, &f.Abilities, &f.Height, &f.Weight,
			&f.HP, &f.Attack, &f.Defense, &f.SpAtk, &f.SpDef, &f.Speed, &f.Total); err != nil {
			return nil, err
		}
		forms = append(forms, f)
	}
	return forms, nil
}

func GetEggMoveParents(ctx context.Context, pokemonName, moveName string) ([]models.EggMoveParent, error) {
	rows, err := Pool.Query(ctx, `
		SELECT pokemon_name, move_name, parent_name
		FROM egg_move_parents
		WHERE LOWER(pokemon_name) = LOWER($1) AND LOWER(move_name) = LOWER($2)
		ORDER BY parent_name
	`, pokemonName, moveName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var parents []models.EggMoveParent
	for rows.Next() {
		var p models.EggMoveParent
		if err := rows.Scan(&p.PokemonName, &p.MoveName, &p.ParentName); err != nil {
			return nil, err
		}
		parents = append(parents, p)
	}
	return parents, nil
}

func GetAllEggMoveParents(ctx context.Context, pokemonName string) ([]models.EggMoveParent, error) {
	rows, err := Pool.Query(ctx, `
		SELECT pokemon_name, move_name, parent_name
		FROM egg_move_parents
		WHERE LOWER(pokemon_name) = LOWER($1)
		ORDER BY move_name, parent_name
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var parents []models.EggMoveParent
	for rows.Next() {
		var p models.EggMoveParent
		if err := rows.Scan(&p.PokemonName, &p.MoveName, &p.ParentName); err != nil {
			return nil, err
		}
		parents = append(parents, p)
	}
	return parents, nil
}

// GetPokemonByMove returns Pokemon names that learn a given move
func GetPokemonByMove(ctx context.Context, moveName string) ([]map[string]string, error) {
	rows, err := Pool.Query(ctx, `
		SELECT DISTINCT pokemon_name, learn_method FROM moves
		WHERE LOWER(move_name) = LOWER($1)
		ORDER BY pokemon_name
	`, moveName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var results []map[string]string
	for rows.Next() {
		var pname, method string
		if err := rows.Scan(&pname, &method); err != nil {
			return nil, err
		}
		results = append(results, map[string]string{"pokemon_name": pname, "learn_method": method})
	}
	return results, nil
}

// --- Ability queries ---

func GetAllAbilities(ctx context.Context, limit, offset int) ([]models.AbilityDetail, int, error) {
	var total int
	err := Pool.QueryRow(ctx, `SELECT COUNT(*) FROM ability_details`).Scan(&total)
	if err != nil {
		return nil, 0, err
	}
	rows, err := Pool.Query(ctx, `
		SELECT name, description, generation FROM ability_details ORDER BY name LIMIT $1 OFFSET $2
	`, limit, offset)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()
	var abilities []models.AbilityDetail
	for rows.Next() {
		var a models.AbilityDetail
		if err := rows.Scan(&a.Name, &a.Description, &a.Generation); err != nil {
			return nil, 0, err
		}
		abilities = append(abilities, a)
	}
	return abilities, total, nil
}

func GetAbilityByName(ctx context.Context, name string) (*models.AbilityDetail, error) {
	a := &models.AbilityDetail{}
	err := Pool.QueryRow(ctx, `
		SELECT name, description, generation FROM ability_details WHERE LOWER(name) = LOWER($1)
	`, name).Scan(&a.Name, &a.Description, &a.Generation)
	if err != nil {
		return nil, err
	}
	return a, nil
}

func GetAbilityPokemon(ctx context.Context, abilityName string) ([]models.AbilityPokemon, error) {
	rows, err := Pool.Query(ctx, `
		SELECT pokemon_name, is_hidden FROM ability_pokemon WHERE LOWER(ability_name) = LOWER($1) ORDER BY pokemon_name
	`, abilityName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var pokemon []models.AbilityPokemon
	for rows.Next() {
		var p models.AbilityPokemon
		if err := rows.Scan(&p.PokemonName, &p.IsHidden); err != nil {
			return nil, err
		}
		pokemon = append(pokemon, p)
	}
	return pokemon, nil
}

// --- Pokedex entries (flavor text) ---

func GetPokedexEntries(ctx context.Context, pokemonName string) ([]models.PokedexEntry, error) {
	rows, err := Pool.Query(ctx, `
		SELECT game_version, flavor_text FROM pokedex_entries WHERE pokemon_name = $1 ORDER BY game_version
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var entries []models.PokedexEntry
	for rows.Next() {
		var e models.PokedexEntry
		if err := rows.Scan(&e.GameVersion, &e.FlavorText); err != nil {
			return nil, err
		}
		entries = append(entries, e)
	}
	return entries, nil
}

// --- Natures ---

func GetAllNatures(ctx context.Context) ([]models.Nature, error) {
	rows, err := Pool.Query(ctx, `SELECT name, increased_stat, decreased_stat FROM natures ORDER BY name`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var natures []models.Nature
	for rows.Next() {
		var n models.Nature
		if err := rows.Scan(&n.Name, &n.IncreasedStat, &n.DecreasedStat); err != nil {
			return nil, err
		}
		natures = append(natures, n)
	}
	return natures, nil
}

// --- Location encounters ---

func GetLocationEncounters(ctx context.Context, region, routeName string) ([]models.LocationEncounter, error) {
	rows, err := Pool.Query(ctx, `
		SELECT region, route_name, pokemon_name, games, encounter_method, rarity, level_range, time_of_day
		FROM location_encounters WHERE LOWER(region) = LOWER($1) AND LOWER(route_name) = LOWER($2)
		ORDER BY pokemon_name
	`, region, routeName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var encounters []models.LocationEncounter
	for rows.Next() {
		var e models.LocationEncounter
		if err := rows.Scan(&e.Region, &e.RouteName, &e.PokemonName, &e.Games, &e.EncounterMethod, &e.Rarity, &e.LevelRange, &e.TimeOfDay); err != nil {
			return nil, err
		}
		encounters = append(encounters, e)
	}
	return encounters, nil
}

func GetAllRegions(ctx context.Context) ([]string, error) {
	rows, err := Pool.Query(ctx, `SELECT DISTINCT region FROM location_encounters ORDER BY region`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var regions []string
	for rows.Next() {
		var r string
		if err := rows.Scan(&r); err != nil {
			return nil, err
		}
		regions = append(regions, r)
	}
	return regions, nil
}

func GetRegionsByGame(ctx context.Context, game string) ([]string, error) {
	rows, err := Pool.Query(ctx, `SELECT DISTINCT region FROM location_encounters WHERE $1 = ANY(games) ORDER BY region`, game)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var regions []string
	for rows.Next() {
		var r string
		if err := rows.Scan(&r); err != nil {
			return nil, err
		}
		regions = append(regions, r)
	}
	return regions, nil
}

func GetEncountersByPokemon(ctx context.Context, pokemonName string) ([]models.LocationEncounter, error) {
	rows, err := Pool.Query(ctx, `
		SELECT region, route_name, pokemon_name, games, encounter_method, rarity, level_range, time_of_day
		FROM location_encounters WHERE LOWER(pokemon_name) = LOWER($1)
		ORDER BY region, route_name
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var encounters []models.LocationEncounter
	for rows.Next() {
		var e models.LocationEncounter
		if err := rows.Scan(&e.Region, &e.RouteName, &e.PokemonName, &e.Games, &e.EncounterMethod, &e.Rarity, &e.LevelRange, &e.TimeOfDay); err != nil {
			return nil, err
		}
		encounters = append(encounters, e)
	}
	return encounters, nil
}

func GetRoutesByRegion(ctx context.Context, region string) ([]string, error) {
	rows, err := Pool.Query(ctx, `
		SELECT DISTINCT route_name FROM location_encounters WHERE LOWER(region) = LOWER($1) ORDER BY route_name
	`, region)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var routes []string
	for rows.Next() {
		var r string
		if err := rows.Scan(&r); err != nil {
			return nil, err
		}
		routes = append(routes, r)
	}
	return routes, nil
}

func GetRoutesByRegionAndGame(ctx context.Context, region, game string) ([]string, error) {
	rows, err := Pool.Query(ctx, `
		SELECT DISTINCT route_name FROM location_encounters
		WHERE LOWER(region) = LOWER($1) AND $2 = ANY(games)
		ORDER BY route_name
	`, region, game)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var routes []string
	for rows.Next() {
		var r string
		if err := rows.Scan(&r); err != nil {
			return nil, err
		}
		routes = append(routes, r)
	}
	return routes, nil
}

func GetLocationEncountersByGame(ctx context.Context, region, routeName, game string) ([]models.LocationEncounter, error) {
	rows, err := Pool.Query(ctx, `
		SELECT region, route_name, pokemon_name, games, encounter_method, rarity, level_range, time_of_day
		FROM location_encounters
		WHERE LOWER(region) = LOWER($1) AND LOWER(route_name) = LOWER($2) AND $3 = ANY(games)
		ORDER BY pokemon_name
	`, region, routeName, game)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var encounters []models.LocationEncounter
	for rows.Next() {
		var e models.LocationEncounter
		if err := rows.Scan(&e.Region, &e.RouteName, &e.PokemonName, &e.Games, &e.EncounterMethod, &e.Rarity, &e.LevelRange, &e.TimeOfDay); err != nil {
			return nil, err
		}
		encounters = append(encounters, e)
	}
	return encounters, nil
}

func GetAllEncounterGames(ctx context.Context) ([]string, error) {
	rows, err := Pool.Query(ctx, `SELECT DISTINCT unnest(games) AS game FROM location_encounters ORDER BY game`)
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

// --- Berry queries ---

func GetAllBerries(ctx context.Context) ([]models.Berry, error) {
	rows, err := Pool.Query(ctx, `
		SELECT name, natural_gift_type, natural_gift_power, size_mm, firmness, effect, growth_time
		FROM berries ORDER BY name
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var berries []models.Berry
	for rows.Next() {
		var b models.Berry
		if err := rows.Scan(&b.Name, &b.NaturalGiftType, &b.NaturalGiftPower, &b.SizeMM, &b.Firmness, &b.Effect, &b.GrowthTime); err != nil {
			return nil, err
		}
		berries = append(berries, b)
	}
	return berries, nil
}

func GetBerryByName(ctx context.Context, name string) (*models.Berry, error) {
	b := &models.Berry{}
	err := Pool.QueryRow(ctx, `
		SELECT name, natural_gift_type, natural_gift_power, size_mm, firmness, effect, growth_time
		FROM berries WHERE LOWER(name) = LOWER($1)
	`, name).Scan(&b.Name, &b.NaturalGiftType, &b.NaturalGiftPower, &b.SizeMM, &b.Firmness, &b.Effect, &b.GrowthTime)
	if err != nil {
		return nil, err
	}
	return b, nil
}

func GetBerryFlavors(ctx context.Context, berryName string) ([]models.BerryFlavor, error) {
	rows, err := Pool.Query(ctx, `
		SELECT flavor, potency FROM berry_flavors WHERE LOWER(berry_name) = LOWER($1) ORDER BY flavor
	`, berryName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var flavors []models.BerryFlavor
	for rows.Next() {
		var f models.BerryFlavor
		if err := rows.Scan(&f.Flavor, &f.Potency); err != nil {
			return nil, err
		}
		flavors = append(flavors, f)
	}
	return flavors, nil
}

// --- Item location queries ---

func GetItemLocations(ctx context.Context, itemName string) ([]models.ItemLocation, error) {
	rows, err := Pool.Query(ctx, `
		SELECT item_name, game, location, method FROM item_locations WHERE LOWER(item_name) = LOWER($1) ORDER BY game
	`, itemName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var locations []models.ItemLocation
	for rows.Next() {
		var l models.ItemLocation
		if err := rows.Scan(&l.ItemName, &l.Game, &l.Location, &l.Method); err != nil {
			return nil, err
		}
		locations = append(locations, l)
	}
	return locations, nil
}

func GetPokemonNames(ctx context.Context, pokemonName string) ([]models.PokemonName, error) {
	rows, err := Pool.Query(ctx, `
		SELECT language, localized_name FROM pokemon_names WHERE pokemon_name = $1 ORDER BY language
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var names []models.PokemonName
	for rows.Next() {
		var n models.PokemonName
		if err := rows.Scan(&n.Language, &n.LocalizedName); err != nil {
			return nil, err
		}
		names = append(names, n)
	}
	return names, nil
}

func GetPokemonSprites(ctx context.Context, pokemonName string) ([]models.PokemonSprite, error) {
	rows, err := Pool.Query(ctx, `
		SELECT sprite_type, generation, url FROM pokemon_sprites WHERE pokemon_name = $1 ORDER BY generation, sprite_type
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var sprites []models.PokemonSprite
	for rows.Next() {
		var s models.PokemonSprite
		if err := rows.Scan(&s.SpriteType, &s.Generation, &s.URL); err != nil {
			return nil, err
		}
		sprites = append(sprites, s)
	}
	return sprites, nil
}

// --- TM location queries ---

func GetTmLocations(ctx context.Context, game string) ([]models.TmLocation, error) {
	rows, err := Pool.Query(ctx, `
		SELECT tm_number, move_name, game, location FROM tm_locations WHERE game = $1 ORDER BY tm_number
	`, game)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var locs []models.TmLocation
	for rows.Next() {
		var l models.TmLocation
		if err := rows.Scan(&l.TmNumber, &l.MoveName, &l.Game, &l.Location); err != nil {
			return nil, err
		}
		locs = append(locs, l)
	}
	return locs, nil
}

func GetAllTmGames(ctx context.Context) ([]string, error) {
	rows, err := Pool.Query(ctx, `
		SELECT DISTINCT game FROM tm_locations ORDER BY game
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

// GetItemLocationsByGame returns all item locations for a given game.
func GetItemLocationsByGame(ctx context.Context, game string) ([]models.ItemLocation, error) {
	rows, err := Pool.Query(ctx, `
		SELECT item_name, game, location, method FROM item_locations WHERE game = $1 ORDER BY item_name
	`, game)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var locations []models.ItemLocation
	for rows.Next() {
		var l models.ItemLocation
		if err := rows.Scan(&l.ItemName, &l.Game, &l.Location, &l.Method); err != nil {
			return nil, err
		}
		locations = append(locations, l)
	}
	return locations, nil
}

// GetAllItemLocationGames returns all distinct games that have item location data.
func GetAllItemLocationGames(ctx context.Context) ([]string, error) {
	rows, err := Pool.Query(ctx, `SELECT DISTINCT game FROM item_locations ORDER BY game`)
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

// --- Wild held item queries ---

// GetWildHeldItemsByPokemon returns all items that a given Pokemon can hold in the wild.
func GetWildHeldItemsByPokemon(ctx context.Context, pokemonName string) ([]models.WildHeldItem, error) {
	rows, err := Pool.Query(ctx, `
		SELECT pokemon_name, game, item_name, rarity
		FROM wild_held_items WHERE LOWER(pokemon_name) = LOWER($1)
		ORDER BY game, item_name
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var items []models.WildHeldItem
	for rows.Next() {
		var w models.WildHeldItem
		if err := rows.Scan(&w.PokemonName, &w.Game, &w.ItemName, &w.Rarity); err != nil {
			return nil, err
		}
		items = append(items, w)
	}
	return items, nil
}

// GetWildHeldItemsByItem returns all Pokemon that hold a given item in the wild.
func GetWildHeldItemsByItem(ctx context.Context, itemName string) ([]models.WildHeldItem, error) {
	rows, err := Pool.Query(ctx, `
		SELECT pokemon_name, game, item_name, rarity
		FROM wild_held_items WHERE LOWER(item_name) = LOWER($1)
		ORDER BY pokemon_name, game
	`, itemName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var items []models.WildHeldItem
	for rows.Next() {
		var w models.WildHeldItem
		if err := rows.Scan(&w.PokemonName, &w.Game, &w.ItemName, &w.Rarity); err != nil {
			return nil, err
		}
		items = append(items, w)
	}
	return items, nil
}

// --- Pokemon game location queries ---

func GetPokemonGameLocations(ctx context.Context, pokemonName string) ([]models.PokemonGameLocation, error) {
	rows, err := Pool.Query(ctx, `
		SELECT pokemon_name, game, location, method
		FROM pokemon_game_locations
		WHERE LOWER(pokemon_name) = LOWER($1)
		ORDER BY game, location
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var locs []models.PokemonGameLocation
	for rows.Next() {
		var l models.PokemonGameLocation
		if err := rows.Scan(&l.PokemonName, &l.Game, &l.Location, &l.Method); err != nil {
			return nil, err
		}
		locs = append(locs, l)
	}
	return locs, nil
}

// --- Raid queries ---

func GetAllRaidEvents(ctx context.Context) ([]models.RaidEvent, error) {
	rows, err := Pool.Query(ctx, `
		SELECT id, pokemon_name, tera_type, star_rating, event_start, event_end, is_active, source_url,
		       to_char(scraped_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
		FROM raid_events
		ORDER BY is_active DESC, scraped_at DESC
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var events []models.RaidEvent
	for rows.Next() {
		var e models.RaidEvent
		if err := rows.Scan(&e.ID, &e.PokemonName, &e.TeraType, &e.StarRating, &e.EventStart, &e.EventEnd, &e.IsActive, &e.SourceURL, &e.ScrapedAt); err != nil {
			return nil, err
		}
		events = append(events, e)
	}
	return events, nil
}

func GetActiveRaidEvents(ctx context.Context) ([]models.RaidEvent, error) {
	rows, err := Pool.Query(ctx, `
		SELECT id, pokemon_name, tera_type, star_rating, event_start, event_end, is_active, source_url,
		       to_char(scraped_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
		FROM raid_events
		WHERE is_active = TRUE
		ORDER BY star_rating DESC, pokemon_name
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var events []models.RaidEvent
	for rows.Next() {
		var e models.RaidEvent
		if err := rows.Scan(&e.ID, &e.PokemonName, &e.TeraType, &e.StarRating, &e.EventStart, &e.EventEnd, &e.IsActive, &e.SourceURL, &e.ScrapedAt); err != nil {
			return nil, err
		}
		events = append(events, e)
	}
	return events, nil
}

func GetRaidEventsByPokemon(ctx context.Context, pokemonName string) ([]models.RaidEvent, error) {
	rows, err := Pool.Query(ctx, `
		SELECT id, pokemon_name, tera_type, star_rating, event_start, event_end, is_active, source_url,
		       to_char(scraped_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
		FROM raid_events
		WHERE LOWER(pokemon_name) = LOWER($1)
		ORDER BY scraped_at DESC
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var events []models.RaidEvent
	for rows.Next() {
		var e models.RaidEvent
		if err := rows.Scan(&e.ID, &e.PokemonName, &e.TeraType, &e.StarRating, &e.EventStart, &e.EventEnd, &e.IsActive, &e.SourceURL, &e.ScrapedAt); err != nil {
			return nil, err
		}
		events = append(events, e)
	}
	return events, nil
}

func GetRaidCounters(ctx context.Context, pokemonName string, teraType string) ([]models.RaidCounter, error) {
	query := `
		SELECT pokemon_name, tera_type, counter_pokemon, rank, notes
		FROM raid_counters
		WHERE LOWER(pokemon_name) = LOWER($1)
		ORDER BY rank NULLS LAST, counter_pokemon
	`
	args := []any{pokemonName}
	if teraType != "" {
		query = `
			SELECT pokemon_name, tera_type, counter_pokemon, rank, notes
			FROM raid_counters
			WHERE LOWER(pokemon_name) = LOWER($1) AND LOWER(COALESCE(tera_type, '')) = LOWER($2)
			ORDER BY rank NULLS LAST, counter_pokemon
		`
		args = append(args, teraType)
	}
	rows, err := Pool.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var counters []models.RaidCounter
	for rows.Next() {
		var c models.RaidCounter
		if err := rows.Scan(&c.PokemonName, &c.TeraType, &c.CounterPokemon, &c.Rank, &c.Notes); err != nil {
			return nil, err
		}
		counters = append(counters, c)
	}
	return counters, nil
}

// --- Type queries ---

// GetPokemonByType returns all Pokemon names that have the given type (case-insensitive).
func GetPokemonByType(ctx context.Context, typeName string) ([]string, error) {
	rows, err := Pool.Query(ctx, `
		SELECT name FROM pokemon
		WHERE EXISTS (SELECT 1 FROM UNNEST(types) t WHERE LOWER(t) = LOWER($1))
		ORDER BY name
	`, typeName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var names []string
	for rows.Next() {
		var n string
		if err := rows.Scan(&n); err != nil {
			return nil, err
		}
		names = append(names, n)
	}
	return names, nil
}

// --- Pokemon biology queries ---

func GetPokemonBiologyText(ctx context.Context, pokemonName string) (*models.PokemonBiology, error) {
	b := &models.PokemonBiology{}
	err := Pool.QueryRow(ctx, `
		SELECT pokemon_name, biology FROM pokemon_biology WHERE LOWER(pokemon_name) = LOWER($1)
	`, pokemonName).Scan(&b.PokemonName, &b.Biology)
	if err != nil {
		return nil, err
	}
	return b, nil
}
