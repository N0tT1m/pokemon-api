package db

import (
	"context"
	"fmt"
	"sort"
	"strconv"
	"strings"

	"github.com/N0tT1m/pokemon-api/models"
)

// GetPokemonByName resolves a Pokemon by its stored name or by its PokeAPI
// slug. Names are scraped verbatim, so the database holds "Farfetch'd",
// "Mr. Mime" and "Type: Null" while callers ask for "farfetchd", "mr-mime" and
// "type-null". The second WHERE branch strips the punctuation that does not
// survive slugification, and the ORDER BY keeps an exact name match ahead of a
// slug match. The two Nidoran are not recoverable this way and are mapped
// explicitly by the caller.
//
// REPLACE and LOWER behave the same on Postgres and SQLite, so this needs no
// dialect branch.
func GetPokemonByName(ctx context.Context, name string) (*models.Pokemon, error) {
	p := &models.Pokemon{}
	err := Pool.QueryRow(ctx, `
		SELECT name, url, national_no, types, species, height, weight,
			abilities, ev_yield, catch_rate, base_friendship, base_exp,
			growth_rate, egg_groups, gender_ratio, egg_cycles,
			hp, attack, defense, sp_atk, sp_def, speed, total
		FROM pokemon
		WHERE LOWER(name) = LOWER($1)
		   OR LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
		        name, '''', ''), '.', ''), ':', ''), 'é', 'e'), ' ', '-')) = LOWER($1)
		ORDER BY CASE WHEN LOWER(name) = LOWER($1) THEN 0 ELSE 1 END
		LIMIT 1
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

// RegionalDexEntryWithNo is a regional dex entry carrying the species' national
// dex number, resolved in the same query so callers don't need a per-entry
// lookup. NationalNo is 0 when the species has no matching pokemon row.
type RegionalDexEntryWithNo struct {
	DexNumber   int
	PokemonName string
	NationalNo  int
}

// GetRegionalDexWithNationalNo returns a game's regional dex joined to the
// pokemon table so each entry carries its national number in one round-trip.
func GetRegionalDexWithNationalNo(ctx context.Context, game string) ([]RegionalDexEntryWithNo, error) {
	rows, err := Pool.Query(ctx, `
		SELECT rd.dex_number, rd.pokemon_name, p.national_no
		FROM regional_dex rd
		LEFT JOIN pokemon p ON LOWER(p.name) = LOWER(rd.pokemon_name)
		WHERE rd.game = $1
		ORDER BY rd.dex_number
	`, game)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var entries []RegionalDexEntryWithNo
	for rows.Next() {
		var e RegionalDexEntryWithNo
		var nationalNo *string
		if err := rows.Scan(&e.DexNumber, &e.PokemonName, &nationalNo); err != nil {
			return nil, err
		}
		if nationalNo != nil {
			trimmed := strings.TrimLeft(*nationalNo, "0")
			if trimmed != "" {
				e.NationalNo, _ = strconv.Atoi(trimmed)
			}
		}
		entries = append(entries, e)
	}
	return entries, nil
}

// GetPokemonByNationalNoRange returns list entries whose national number falls
// within [start, end] inclusive, filtered and ordered in SQL. national_no is
// stored as text, so it is cast to an integer for the comparison.
func GetPokemonByNationalNoRange(ctx context.Context, start, end int) ([]models.PokemonListEntry, error) {
	rows, err := Pool.Query(ctx, `
		SELECT name, national_no, types
		FROM pokemon
		WHERE CAST(national_no AS INTEGER) BETWEEN $1 AND $2
		ORDER BY CAST(national_no AS INTEGER)
	`, start, end)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var entries []models.PokemonListEntry
	for rows.Next() {
		var e models.PokemonListEntry
		if err := rows.Scan(&e.Name, &e.NationalNo, &e.Types); err != nil {
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

func GetAllPokemonCompetitive(ctx context.Context) ([]models.CompetitivePokemon, error) {
	rows, err := Pool.Query(ctx, `
		SELECT name, national_no, types, abilities, hp, attack, defense, sp_atk, sp_def, speed, total
		FROM pokemon ORDER BY national_no
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var entries []models.CompetitivePokemon
	for rows.Next() {
		var p models.CompetitivePokemon
		if err := rows.Scan(&p.Name, &p.NationalNo, &p.Types, &p.Abilities,
			&p.HP, &p.Attack, &p.Defense, &p.SpAtk, &p.SpDef, &p.Speed, &p.Total); err != nil {
			return nil, err
		}
		entries = append(entries, p)
	}
	return entries, nil
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

// MovesByVersionGroup returns the learnset for a Pokemon (kebab-case
// identifier) in a given PokeAPI version-group slug. Joins on moves_canonical
// for type/damage_class/power/accuracy — both tables are PokeAPI-identifier-
// keyed, so the join is exact.
func MovesByVersionGroup(ctx context.Context, pokemonIdentifier, versionGroup string) ([]models.Move, error) {
	rows, err := Pool.Query(ctx, fmt.Sprintf(`
		SELECT m.learn_method, COALESCE(%s, ''), m.move_identifier,
		       mc.type, mc.damage_class, mc.power, mc.accuracy
		FROM pokemon_moves_vg m
		LEFT JOIN moves_canonical mc ON mc.move_identifier = m.move_identifier
		WHERE m.pokemon_identifier = $1 AND m.version_group = $2
		ORDER BY m.learn_method, m.level NULLS LAST, m.move_order NULLS LAST, m.move_identifier
	`, CastText("m.level")), pokemonIdentifier, versionGroup)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var moves []models.Move
	for rows.Next() {
		var m models.Move
		var levelStr string
		var moveType, damageClass *string
		if err := rows.Scan(&m.LearnMethod, &levelStr, &m.Name, &moveType, &damageClass, &m.Power, &m.Accuracy); err != nil {
			return nil, err
		}
		m.LevelOrTM = levelStr
		if moveType != nil {
			m.Type = *moveType
		}
		if damageClass != nil {
			m.Category = *damageClass
		}
		moves = append(moves, m)
	}
	return moves, nil
}

// ItemExtra holds PokeAPI-CSV-sourced fling/baby-trigger metadata.
type ItemExtra struct {
	FlingPower     *int    `json:"fling_power"`
	FlingEffect    *string `json:"fling_effect"`
	BabyTriggerFor *string `json:"baby_trigger_for"`
}

// GetItemExtra returns nil if the item has no extra data on file.
func GetItemExtra(ctx context.Context, identifier string) (*ItemExtra, error) {
	e := &ItemExtra{}
	err := Pool.QueryRow(ctx, `
		SELECT fling_power, fling_effect, baby_trigger_for FROM item_extra
		WHERE item_identifier = $1
	`, identifier).Scan(&e.FlingPower, &e.FlingEffect, &e.BabyTriggerFor)
	if err != nil {
		return nil, err
	}
	return e, nil
}

// GetItemAttributes returns the attribute identifiers for an item (e.g.
// "holdable", "consumable", "usable-in-battle").
func GetItemAttributes(ctx context.Context, identifier string) ([]string, error) {
	rows, err := Pool.Query(ctx, `
		SELECT attribute FROM item_attributes
		WHERE item_identifier = $1 ORDER BY attribute
	`, identifier)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var attrs []string
	for rows.Next() {
		var a string
		if err := rows.Scan(&a); err != nil {
			return nil, err
		}
		attrs = append(attrs, a)
	}
	return attrs, nil
}

// GetLocalizedNames returns (language, localized_name) pairs for the given
// entity. The table argument is whitelisted to one of the *_names tables.
func GetLocalizedNames(ctx context.Context, table, identifier string) ([]models.PokemonName, error) {
	pkCol := map[string]string{
		"item_names":    "item_identifier",
		"move_names":    "move_identifier",
		"ability_names": "ability_identifier",
		"type_names":    "type_identifier",
	}[table]
	if pkCol == "" {
		return nil, fmt.Errorf("invalid names table: %s", table)
	}
	q := fmt.Sprintf(`
		SELECT language, localized_name FROM %s
		WHERE %s = $1
		ORDER BY language
	`, table, pkCol)
	rows, err := Pool.Query(ctx, q, identifier)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []models.PokemonName
	for rows.Next() {
		var n models.PokemonName
		if err := rows.Scan(&n.Language, &n.LocalizedName); err != nil {
			return nil, err
		}
		out = append(out, n)
	}
	return out, nil
}

// GetPastTypes returns past type assignments grouped by generation, ordered by
// slot. The pokemonIdentifier is kebab-case (matches PokeAPI's CSV).
func GetPastTypes(ctx context.Context, pokemonIdentifier string) ([]models.PastTypeEntry, error) {
	rows, err := Pool.Query(ctx, `
		SELECT generation, slot, type FROM pokemon_past_types
		WHERE pokemon_identifier = $1
		ORDER BY generation, slot
	`, pokemonIdentifier)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	byGen := map[int][]string{}
	gens := []int{}
	for rows.Next() {
		var gen, slot int
		var typeName string
		if err := rows.Scan(&gen, &slot, &typeName); err != nil {
			return nil, err
		}
		if _, ok := byGen[gen]; !ok {
			gens = append(gens, gen)
		}
		byGen[gen] = append(byGen[gen], typeName)
	}
	out := make([]models.PastTypeEntry, 0, len(gens))
	for _, g := range gens {
		out = append(out, models.PastTypeEntry{Generation: g, Types: byGen[g]})
	}
	return out, nil
}

// GetPastAbilities returns past ability assignments grouped by generation.
func GetPastAbilities(ctx context.Context, pokemonIdentifier string) ([]models.PastAbilityEntry, error) {
	rows, err := Pool.Query(ctx, `
		SELECT generation, slot, ability, is_hidden FROM pokemon_past_abilities
		WHERE pokemon_identifier = $1
		ORDER BY generation, slot
	`, pokemonIdentifier)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	byGen := map[int][]models.PastAbilityAbility{}
	gens := []int{}
	for rows.Next() {
		var gen, slot int
		var ability *string
		var isHidden bool
		if err := rows.Scan(&gen, &slot, &ability, &isHidden); err != nil {
			return nil, err
		}
		if _, ok := byGen[gen]; !ok {
			gens = append(gens, gen)
		}
		byGen[gen] = append(byGen[gen], models.PastAbilityAbility{
			Slot: slot, Ability: ability, IsHidden: isHidden,
		})
	}
	out := make([]models.PastAbilityEntry, 0, len(gens))
	for _, g := range gens {
		out = append(out, models.PastAbilityEntry{Generation: g, Abilities: byGen[g]})
	}
	return out, nil
}

// GetMoveMeta fetches move_meta for a move identifier (kebab-case lowercase).
// Returns (nil, sql.ErrNoRows) if missing — callers should treat that as
// "no meta available" rather than an error.
func GetMoveMeta(ctx context.Context, identifier string) (*models.MoveMeta, error) {
	m := &models.MoveMeta{}
	err := Pool.QueryRow(ctx, `
		SELECT ailment, ailment_chance, flinch_chance, crit_rate, drain, healing,
		       stat_chance, min_hits, max_hits, min_turns, max_turns, category
		FROM move_meta WHERE move_identifier = $1
	`, identifier).Scan(&m.Ailment, &m.AilmentChance, &m.FlinchChance, &m.CritRate,
		&m.Drain, &m.Healing, &m.StatChance, &m.MinHits, &m.MaxHits,
		&m.MinTurns, &m.MaxTurns, &m.Category)
	if err != nil {
		return nil, err
	}
	return m, nil
}

// GetMoveStatChanges returns stat changes (e.g. Swords Dance: +2 attack) for
// a move identifier.
func GetMoveStatChanges(ctx context.Context, identifier string) ([]models.MoveStatChange, error) {
	rows, err := Pool.Query(ctx, `
		SELECT stat, change FROM move_stat_changes
		WHERE move_identifier = $1 ORDER BY stat
	`, identifier)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []models.MoveStatChange
	for rows.Next() {
		var s models.MoveStatChange
		if err := rows.Scan(&s.Stat, &s.Change); err != nil {
			return nil, err
		}
		out = append(out, s)
	}
	return out, nil
}

// MoveFilter holds optional filters for GetAllMoveDetails. Empty fields are
// ignored.
type MoveFilter struct {
	Type       string
	Category   string
	Generation int // 0 = no filter
}

func GetAllMoveDetails(ctx context.Context, limit, offset int, filter MoveFilter) ([]models.MoveDetail, int, error) {
	conditions := []string{}
	args := []any{}
	if filter.Type != "" {
		args = append(args, filter.Type)
		conditions = append(conditions, fmt.Sprintf("LOWER(type) = LOWER($%d)", len(args)))
	}
	if filter.Category != "" {
		args = append(args, filter.Category)
		conditions = append(conditions, fmt.Sprintf("LOWER(category) = LOWER($%d)", len(args)))
	}
	if filter.Generation > 0 {
		args = append(args, filter.Generation)
		conditions = append(conditions, fmt.Sprintf("generation_introduced = $%d", len(args)))
	}
	where := ""
	if len(conditions) > 0 {
		where = " WHERE " + strings.Join(conditions, " AND ")
	}

	var total int
	if err := Pool.QueryRow(ctx, "SELECT COUNT(*) FROM move_details"+where, args...).Scan(&total); err != nil {
		return nil, 0, err
	}

	args = append(args, limit, offset)
	q := fmt.Sprintf(`
		SELECT name, type, category, power, accuracy, pp, effect, effect_chance, priority, target,
		       generation_introduced, z_move_equivalent, max_move_equivalent, contest_type, flags
		FROM move_details%s ORDER BY name LIMIT $%d OFFSET $%d
	`, where, len(args)-1, len(args))
	rows, err := Pool.Query(ctx, q, args...)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()
	var moves []models.MoveDetail
	for rows.Next() {
		var m models.MoveDetail
		if err := rows.Scan(&m.Name, &m.Type, &m.Category, &m.Power, &m.Accuracy, &m.PP, &m.Effect, &m.EffectChance, &m.Priority, &m.Target,
			&m.GenerationIntroduced, &m.ZMoveEquivalent, &m.MaxMoveEquivalent, &m.ContestType, &m.Flags); err != nil {
			return nil, 0, err
		}
		moves = append(moves, m)
	}
	return moves, total, nil
}

func GetMoveDetailByName(ctx context.Context, name string) (*models.MoveDetail, error) {
	m := &models.MoveDetail{}
	err := Pool.QueryRow(ctx, `
		SELECT name, type, category, power, accuracy, pp, effect, effect_chance, priority, target,
		       generation_introduced, z_move_equivalent, max_move_equivalent, contest_type, flags
		FROM move_details WHERE LOWER(name) = LOWER($1)
	`, name).Scan(&m.Name, &m.Type, &m.Category, &m.Power, &m.Accuracy, &m.PP, &m.Effect, &m.EffectChance, &m.Priority, &m.Target,
		&m.GenerationIntroduced, &m.ZMoveEquivalent, &m.MaxMoveEquivalent, &m.ContestType, &m.Flags)
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
	rows, err := Pool.Query(ctx, fmt.Sprintf(
		`SELECT DISTINCT region FROM location_encounters WHERE %s ORDER BY region`,
		ArrayContains("games", "$1"),
	), game)
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
	rows, err := Pool.Query(ctx, fmt.Sprintf(`
		SELECT DISTINCT route_name FROM location_encounters
		WHERE LOWER(region) = LOWER($1) AND %s
		ORDER BY route_name
	`, ArrayContains("games", "$2")), region, game)
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
	rows, err := Pool.Query(ctx, fmt.Sprintf(`
		SELECT region, route_name, pokemon_name, games, encounter_method, rarity, level_range, time_of_day
		FROM location_encounters
		WHERE LOWER(region) = LOWER($1) AND LOWER(route_name) = LOWER($2) AND %s
		ORDER BY pokemon_name
	`, ArrayContains("games", "$3")), region, routeName, game)
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
	rows, err := Pool.Query(ctx, ArrayDistinct("location_encounters", "games"))
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
	rows, err := Pool.Query(ctx, fmt.Sprintf(`
		SELECT id, pokemon_name, tera_type, star_rating, event_start, event_end, is_active, source_url, %s
		FROM raid_events
		ORDER BY is_active DESC, scraped_at DESC
	`, UTCTimestamp("scraped_at")))
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
	rows, err := Pool.Query(ctx, fmt.Sprintf(`
		SELECT id, pokemon_name, tera_type, star_rating, event_start, event_end, is_active, source_url, %s
		FROM raid_events
		WHERE is_active = TRUE
		ORDER BY star_rating DESC, pokemon_name
	`, UTCTimestamp("scraped_at")))
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
	rows, err := Pool.Query(ctx, fmt.Sprintf(`
		SELECT id, pokemon_name, tera_type, star_rating, event_start, event_end, is_active, source_url, %s
		FROM raid_events
		WHERE LOWER(pokemon_name) = LOWER($1)
		ORDER BY scraped_at DESC
	`, UTCTimestamp("scraped_at")), pokemonName)
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
	rows, err := Pool.Query(ctx, fmt.Sprintf(`
		SELECT name FROM pokemon
		WHERE %s
		ORDER BY name
	`, ArrayContainsFold("types", "$1")), typeName)
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

// GetAllTypes returns the canonical list of types from the type_matchups table.
func GetAllTypes(ctx context.Context) ([]string, error) {
	rows, err := Pool.Query(ctx, `
		SELECT DISTINCT attacking_type FROM type_matchups ORDER BY attacking_type
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var types []string
	for rows.Next() {
		var t string
		if err := rows.Scan(&t); err != nil {
			return nil, err
		}
		types = append(types, t)
	}
	return types, nil
}

// TypeDamageRelations groups defending types by multiplier bucket relative
// to the given attacker.
type TypeDamageRelations struct {
	DoubleDamageTo   []string
	HalfDamageTo     []string
	NoDamageTo       []string
	DoubleDamageFrom []string
	HalfDamageFrom   []string
	NoDamageFrom     []string
}

// GetTypeDamageRelations returns offensive (attacker = typeName) and defensive
// (defender = typeName) buckets read from type_matchups. Missing rows imply a
// 1.0 multiplier.
func GetTypeDamageRelations(ctx context.Context, typeName string) (*TypeDamageRelations, error) {
	rels := &TypeDamageRelations{
		DoubleDamageTo:   []string{},
		HalfDamageTo:     []string{},
		NoDamageTo:       []string{},
		DoubleDamageFrom: []string{},
		HalfDamageFrom:   []string{},
		NoDamageFrom:     []string{},
	}

	offensiveRows, err := Pool.Query(ctx, `
		SELECT defending_type, multiplier FROM type_matchups
		WHERE LOWER(attacking_type) = LOWER($1)
		ORDER BY defending_type
	`, typeName)
	if err != nil {
		return nil, err
	}
	for offensiveRows.Next() {
		var defendingType string
		var multiplier float32
		if err := offensiveRows.Scan(&defendingType, &multiplier); err != nil {
			offensiveRows.Close()
			return nil, err
		}
		switch multiplier {
		case 2.0:
			rels.DoubleDamageTo = append(rels.DoubleDamageTo, defendingType)
		case 0.5:
			rels.HalfDamageTo = append(rels.HalfDamageTo, defendingType)
		case 0.0:
			rels.NoDamageTo = append(rels.NoDamageTo, defendingType)
		}
	}
	offensiveRows.Close()

	defensiveRows, err := Pool.Query(ctx, `
		SELECT attacking_type, multiplier FROM type_matchups
		WHERE LOWER(defending_type) = LOWER($1)
		ORDER BY attacking_type
	`, typeName)
	if err != nil {
		return nil, err
	}
	defer defensiveRows.Close()
	for defensiveRows.Next() {
		var attackingType string
		var multiplier float32
		if err := defensiveRows.Scan(&attackingType, &multiplier); err != nil {
			return nil, err
		}
		switch multiplier {
		case 2.0:
			rels.DoubleDamageFrom = append(rels.DoubleDamageFrom, attackingType)
		case 0.5:
			rels.HalfDamageFrom = append(rels.HalfDamageFrom, attackingType)
		case 0.0:
			rels.NoDamageFrom = append(rels.NoDamageFrom, attackingType)
		}
	}
	return rels, nil
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

// --- Classification queries ---

// classificationDistinct returns distinct non-null values from one of the
// pokemon_classification text columns. The column name is interpolated, so
// callers must pass a whitelisted value.
func classificationDistinct(ctx context.Context, column string) ([]string, error) {
	allowed := map[string]bool{"color": true, "shape": true, "habitat": true}
	if !allowed[column] {
		return nil, fmt.Errorf("invalid column: %s", column)
	}
	q := fmt.Sprintf(`
		SELECT DISTINCT %s FROM pokemon_classification
		WHERE %s IS NOT NULL AND %s <> ''
		ORDER BY %s
	`, column, column, column, column)
	rows, err := Pool.Query(ctx, q)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []string
	for rows.Next() {
		var v string
		if err := rows.Scan(&v); err != nil {
			return nil, err
		}
		out = append(out, v)
	}
	return out, nil
}

// pokemonByClassification returns Pokemon names where the given column
// matches the provided value (case-insensitive).
func pokemonByClassification(ctx context.Context, column, value string) ([]string, error) {
	allowed := map[string]bool{"color": true, "shape": true, "habitat": true}
	if !allowed[column] {
		return nil, fmt.Errorf("invalid column: %s", column)
	}
	q := fmt.Sprintf(`
		SELECT pokemon_name FROM pokemon_classification
		WHERE LOWER(%s) = LOWER($1)
		ORDER BY pokemon_name
	`, column)
	rows, err := Pool.Query(ctx, q, value)
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

func GetAllPokemonColors(ctx context.Context) ([]string, error) {
	return classificationDistinct(ctx, "color")
}

func GetAllPokemonShapes(ctx context.Context) ([]string, error) {
	return classificationDistinct(ctx, "shape")
}

func GetAllPokemonHabitats(ctx context.Context) ([]string, error) {
	return classificationDistinct(ctx, "habitat")
}

func GetPokemonByColor(ctx context.Context, color string) ([]string, error) {
	return pokemonByClassification(ctx, "color", color)
}

func GetPokemonByShape(ctx context.Context, shape string) ([]string, error) {
	return pokemonByClassification(ctx, "shape", shape)
}

func GetPokemonByHabitat(ctx context.Context, habitat string) ([]string, error) {
	return pokemonByClassification(ctx, "habitat", habitat)
}

// GetAllEggGroups returns distinct egg groups from pokemon.egg_groups.
func GetAllEggGroups(ctx context.Context) ([]string, error) {
	rows, err := Pool.Query(ctx, ArrayDistinct("pokemon", "egg_groups"))
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []string
	for rows.Next() {
		var g string
		if err := rows.Scan(&g); err != nil {
			return nil, err
		}
		out = append(out, g)
	}
	return out, nil
}

// GetPokemonByEggGroup returns Pokemon whose egg_groups contains the given
// group (case-insensitive).
func GetPokemonByEggGroup(ctx context.Context, group string) ([]string, error) {
	rows, err := Pool.Query(ctx, fmt.Sprintf(`
		SELECT name FROM pokemon
		WHERE %s
		ORDER BY name
	`, ArrayContainsFold("egg_groups", "$1")), group)
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

func GetPokemonClassification(ctx context.Context, pokemonName string) (*models.PokemonClassification, error) {
	c := &models.PokemonClassification{}
	err := Pool.QueryRow(ctx, `
		SELECT pokemon_name, generation_introduced, is_legendary, is_mythical, is_ultra_beast, is_baby, is_paradox, color, shape, habitat
		FROM pokemon_classification WHERE LOWER(pokemon_name) = LOWER($1)
	`, pokemonName).Scan(&c.PokemonName, &c.GenerationIntroduced, &c.IsLegendary, &c.IsMythical, &c.IsUltraBeast, &c.IsBaby, &c.IsParadox, &c.Color, &c.Shape, &c.Habitat)
	if err != nil {
		return nil, err
	}
	return c, nil
}

// --- Z-Move queries ---

func GetAllZMoves(ctx context.Context) ([]models.ZMove, error) {
	rows, err := Pool.Query(ctx, `
		SELECT name, type, power, effect, base_move, category FROM z_moves ORDER BY name
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var moves []models.ZMove
	for rows.Next() {
		var z models.ZMove
		if err := rows.Scan(&z.Name, &z.Type, &z.Power, &z.Effect, &z.BaseMove, &z.Category); err != nil {
			return nil, err
		}
		moves = append(moves, z)
	}
	return moves, nil
}

func GetZMoveByName(ctx context.Context, name string) (*models.ZMove, error) {
	z := &models.ZMove{}
	err := Pool.QueryRow(ctx, `
		SELECT name, type, power, effect, base_move, category FROM z_moves WHERE LOWER(name) = LOWER($1)
	`, name).Scan(&z.Name, &z.Type, &z.Power, &z.Effect, &z.BaseMove, &z.Category)
	if err != nil {
		return nil, err
	}
	return z, nil
}

// --- In-game trade queries ---

func GetAllInGameTrades(ctx context.Context, game string) ([]models.InGameTrade, error) {
	query := `SELECT game, location, offered_pokemon, offered_level, offered_item, requested_pokemon, npc_name, notes FROM in_game_trades`
	args := []any{}
	if game != "" {
		query += " WHERE LOWER(game) = LOWER($1)"
		args = append(args, game)
	}
	query += " ORDER BY game, offered_pokemon"
	rows, err := Pool.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var trades []models.InGameTrade
	for rows.Next() {
		var t models.InGameTrade
		if err := rows.Scan(&t.Game, &t.Location, &t.OfferedPokemon, &t.OfferedLevel, &t.OfferedItem, &t.RequestedPokemon, &t.NpcName, &t.Notes); err != nil {
			return nil, err
		}
		trades = append(trades, t)
	}
	return trades, nil
}

// --- Contest stat queries ---

func GetContestStats(ctx context.Context, pokemonName string) ([]models.ContestStat, error) {
	rows, err := Pool.Query(ctx, `
		SELECT pokemon_name, contest_type, appeal, jam FROM contest_stats WHERE LOWER(pokemon_name) = LOWER($1) ORDER BY contest_type
	`, pokemonName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var stats []models.ContestStat
	for rows.Next() {
		var s models.ContestStat
		if err := rows.Scan(&s.PokemonName, &s.ContestType, &s.Appeal, &s.Jam); err != nil {
			return nil, err
		}
		stats = append(stats, s)
	}
	return stats, nil
}

// --- Event Pokemon queries ---

func GetAllEventPokemon(ctx context.Context, name, game string) ([]models.EventPokemon, error) {
	query := `SELECT name, game, year, level, held_item, moves, ot_name, distribution_method, notes FROM event_pokemon`
	args := []any{}
	conditions := []string{}
	if name != "" {
		args = append(args, name)
		conditions = append(conditions, fmt.Sprintf("LOWER(name) = LOWER($%d)", len(args)))
	}
	if game != "" {
		args = append(args, game)
		conditions = append(conditions, fmt.Sprintf("LOWER(game) = LOWER($%d)", len(args)))
	}
	if len(conditions) > 0 {
		query += " WHERE " + strings.Join(conditions, " AND ")
	}
	query += " ORDER BY name, year"
	rows, err := Pool.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var events []models.EventPokemon
	for rows.Next() {
		var e models.EventPokemon
		if err := rows.Scan(&e.Name, &e.Game, &e.Year, &e.Level, &e.HeldItem, &e.Moves, &e.OtName, &e.DistributionMethod, &e.Notes); err != nil {
			return nil, err
		}
		events = append(events, e)
	}
	return events, nil
}

// --- Mass outbreak queries ---

func GetAllMassOutbreaks(ctx context.Context, game, region string) ([]models.MassOutbreak, error) {
	query := `SELECT game, region, location, pokemon_name, notes FROM mass_outbreaks`
	args := []any{}
	conditions := []string{}
	if game != "" {
		args = append(args, game)
		conditions = append(conditions, fmt.Sprintf("LOWER(game) = LOWER($%d)", len(args)))
	}
	if region != "" {
		args = append(args, region)
		conditions = append(conditions, fmt.Sprintf("LOWER(region) = LOWER($%d)", len(args)))
	}
	if len(conditions) > 0 {
		query += " WHERE " + strings.Join(conditions, " AND ")
	}
	query += " ORDER BY game, region, pokemon_name"
	rows, err := Pool.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var outbreaks []models.MassOutbreak
	for rows.Next() {
		var o models.MassOutbreak
		if err := rows.Scan(&o.Game, &o.Region, &o.Location, &o.PokemonName, &o.Notes); err != nil {
			return nil, err
		}
		outbreaks = append(outbreaks, o)
	}
	return outbreaks, nil
}

// --- Pokemon GO queries ---

func GetPokemonGo(ctx context.Context, pokemonName string) (*models.PokemonGo, error) {
	g := &models.PokemonGo{}
	err := Pool.QueryRow(ctx, `
		SELECT pokemon_name, max_cp, buddy_distance_km, base_attack, base_defense, base_stamina, shiny_available, shadow_available
		FROM pokemon_go WHERE LOWER(pokemon_name) = LOWER($1)
	`, pokemonName).Scan(&g.PokemonName, &g.MaxCP, &g.BuddyDistanceKm, &g.BaseAttack, &g.BaseDefense, &g.BaseStamina, &g.ShinyAvailable, &g.ShadowAvailable)
	if err != nil {
		return nil, err
	}
	return g, nil
}

// --- Battle facility queries ---

func GetAllBattleFacilities(ctx context.Context, game string) ([]models.BattleFacility, error) {
	query := `SELECT name, game, region, facility_type, description, currency FROM battle_facilities`
	args := []any{}
	if game != "" {
		query += " WHERE LOWER(game) = LOWER($1)"
		args = append(args, game)
	}
	query += " ORDER BY game, name"
	rows, err := Pool.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var facilities []models.BattleFacility
	for rows.Next() {
		var f models.BattleFacility
		if err := rows.Scan(&f.Name, &f.Game, &f.Region, &f.FacilityType, &f.Description, &f.Currency); err != nil {
			return nil, err
		}
		facilities = append(facilities, f)
	}
	return facilities, nil
}

// --- Move tutor queries ---

func GetAllMoveTutorLocations(ctx context.Context, game, moveName string) ([]models.MoveTutorLocation, error) {
	query := `SELECT move_name, game, location, cost FROM move_tutor_locations`
	args := []any{}
	conditions := []string{}
	if game != "" {
		args = append(args, game)
		conditions = append(conditions, fmt.Sprintf("LOWER(game) = LOWER($%d)", len(args)))
	}
	if moveName != "" {
		args = append(args, moveName)
		conditions = append(conditions, fmt.Sprintf("LOWER(move_name) = LOWER($%d)", len(args)))
	}
	if len(conditions) > 0 {
		query += " WHERE " + strings.Join(conditions, " AND ")
	}
	query += " ORDER BY move_name, game"
	rows, err := Pool.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var tutors []models.MoveTutorLocation
	for rows.Next() {
		var t models.MoveTutorLocation
		if err := rows.Scan(&t.MoveName, &t.Game, &t.Location, &t.Cost); err != nil {
			return nil, err
		}
		tutors = append(tutors, t)
	}
	return tutors, nil
}

// --- Version exclusive queries ---

func GetAllVersionExclusives(ctx context.Context, game, gamePair string) ([]models.VersionExclusive, error) {
	query := `SELECT pokemon_name, game, game_pair FROM version_exclusives`
	args := []any{}
	conditions := []string{}
	if game != "" {
		args = append(args, game)
		conditions = append(conditions, fmt.Sprintf("LOWER(game) = LOWER($%d)", len(args)))
	}
	if gamePair != "" {
		args = append(args, gamePair)
		conditions = append(conditions, fmt.Sprintf("LOWER(game_pair) = LOWER($%d)", len(args)))
	}
	if len(conditions) > 0 {
		query += " WHERE " + strings.Join(conditions, " AND ")
	}
	query += " ORDER BY game_pair, game, pokemon_name"
	rows, err := Pool.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var exclusives []models.VersionExclusive
	for rows.Next() {
		var v models.VersionExclusive
		if err := rows.Scan(&v.PokemonName, &v.Game, &v.GamePair); err != nil {
			return nil, err
		}
		exclusives = append(exclusives, v)
	}
	return exclusives, nil
}

// --- Trainer queries ---

func GetAllTrainers(ctx context.Context, game, role string) ([]models.Trainer, error) {
	query := `SELECT name, game, role, specialty_type, location, battle_variant FROM trainers`
	args := []any{}
	conditions := []string{}
	if game != "" {
		args = append(args, game)
		conditions = append(conditions, fmt.Sprintf("LOWER(game) = LOWER($%d)", len(args)))
	}
	if role != "" {
		args = append(args, role)
		conditions = append(conditions, fmt.Sprintf("LOWER(role) = LOWER($%d)", len(args)))
	}
	if len(conditions) > 0 {
		query += " WHERE " + strings.Join(conditions, " AND ")
	}
	query += " ORDER BY game, name, battle_variant"
	rows, err := Pool.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var trainers []models.Trainer
	for rows.Next() {
		var t models.Trainer
		if err := rows.Scan(&t.Name, &t.Game, &t.Role, &t.SpecialtyType, &t.Location, &t.BattleVariant); err != nil {
			return nil, err
		}
		trainers = append(trainers, t)
	}
	return trainers, nil
}

func GetTrainerPokemon(ctx context.Context, trainerName, game, battleVariant string) ([]models.TrainerPokemon, error) {
	query := `SELECT trainer_name, game, battle_variant, pokemon_name, level, held_item, ability, moves, team_order
	          FROM trainer_pokemon WHERE LOWER(trainer_name) = LOWER($1)`
	args := []any{trainerName}
	if game != "" {
		args = append(args, game)
		query += fmt.Sprintf(" AND LOWER(game) = LOWER($%d)", len(args))
	}
	if battleVariant != "" {
		args = append(args, battleVariant)
		query += fmt.Sprintf(" AND LOWER(battle_variant) = LOWER($%d)", len(args))
	}
	query += " ORDER BY game, battle_variant, team_order"
	rows, err := Pool.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var pokemon []models.TrainerPokemon
	for rows.Next() {
		var p models.TrainerPokemon
		if err := rows.Scan(&p.TrainerName, &p.Game, &p.BattleVariant, &p.PokemonName, &p.Level, &p.HeldItem, &p.Ability, &p.Moves, &p.TeamOrder); err != nil {
			return nil, err
		}
		pokemon = append(pokemon, p)
	}
	return pokemon, nil
}

// EVTarget represents a Pokemon that yields EVs in a given stat, with location info.
type EVTarget struct {
	PokemonName string  `json:"pokemon_name"`
	EVYield     string  `json:"ev_yield"`
	YieldAmount int     `json:"yield_amount"`
	Game        string  `json:"game"`
	Location    string  `json:"location"`
	Method      *string `json:"method"`
}

// GetEVTargetsByStat returns Pokemon that yield EVs in the given stat,
// optionally filtered by game. stat values: "hp","attack","defense","sp-atk","sp-def","speed".
func GetEVTargetsByStat(ctx context.Context, stat string, game string) ([]EVTarget, error) {
	statKeywords := map[string]string{
		"hp":      "HP",
		"attack":  "Attack",
		"defense": "Defense",
		"sp-atk":  "Sp. Atk",
		"sp-def":  "Sp. Def",
		"speed":   "Speed",
	}
	keyword, ok := statKeywords[strings.ToLower(stat)]
	if !ok {
		return nil, fmt.Errorf("unknown stat: %s", stat)
	}

	var rows Rows
	var err error

	// Order is applied in Go after fetching: SQL's split_part-based sort
	// only sees the first comma-separated yield, so a Pokemon with
	// "1 HP, 2 Speed" filtered by stat=Speed would sort by 1 instead of 2.
	if game != "" {
		rows, err = Pool.Query(ctx, fmt.Sprintf(`
			SELECT p.name, p.ev_yield, gl.game, gl.location, gl.method
			FROM pokemon p
			JOIN pokemon_game_locations gl ON LOWER(gl.pokemon_name) = LOWER(p.name)
			WHERE %s
			  AND gl.game = $2
		`, LikeFold("p.ev_yield", "$1")), "%"+keyword+"%", game)
	} else {
		rows, err = Pool.Query(ctx, fmt.Sprintf(`
			SELECT p.name, p.ev_yield, gl.game, gl.location, gl.method
			FROM pokemon p
			JOIN pokemon_game_locations gl ON LOWER(gl.pokemon_name) = LOWER(p.name)
			WHERE %s
		`, LikeFold("p.ev_yield", "$1")), "%"+keyword+"%")
	}
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	parseYield := func(evYield string) int {
		for _, part := range strings.Split(evYield, ",") {
			part = strings.TrimSpace(part)
			if !strings.Contains(strings.ToLower(part), strings.ToLower(keyword)) {
				continue
			}
			fields := strings.Fields(part)
			if len(fields) >= 1 {
				var n int
				if _, scanErr := fmt.Sscan(fields[0], &n); scanErr == nil {
					return n
				}
			}
		}
		return 1
	}

	var targets []EVTarget
	for rows.Next() {
		var t EVTarget
		if scanErr := rows.Scan(&t.PokemonName, &t.EVYield, &t.Game, &t.Location, &t.Method); scanErr != nil {
			return nil, scanErr
		}
		t.YieldAmount = parseYield(t.EVYield)
		targets = append(targets, t)
	}

	// Sort by yield amount for the requested stat (descending), then by name,
	// game, location for stable output.
	sort.SliceStable(targets, func(i, j int) bool {
		if targets[i].YieldAmount != targets[j].YieldAmount {
			return targets[i].YieldAmount > targets[j].YieldAmount
		}
		if targets[i].PokemonName != targets[j].PokemonName {
			return targets[i].PokemonName < targets[j].PokemonName
		}
		if targets[i].Game != targets[j].Game {
			return targets[i].Game < targets[j].Game
		}
		return targets[i].Location < targets[j].Location
	})
	return targets, nil
}
