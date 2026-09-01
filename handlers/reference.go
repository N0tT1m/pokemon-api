package handlers

import (
	"net/http"
	"strconv"
	"strings"

	"github.com/N0tT1m/pokemon-api/db"
	"github.com/N0tT1m/pokemon-api/models"
	"github.com/go-chi/chi/v5"
)

// --- Items ---

// GET /api/v2/item?limit=N&offset=N
func ListItems(w http.ResponseWriter, r *http.Request) {
	limit := queryLimit(r, 2000, 10000)
	offset := queryInt(r, "offset", 0)

	items, total, err := db.GetAllItems(r.Context(), limit, offset)
	if err != nil {
		writeServerError(w, r, err)
		return
	}

	results := make([]map[string]any, len(items))
	for i, item := range items {
		apiName := strings.ToLower(strings.ReplaceAll(item.Name, " ", "-"))
		results[i] = map[string]any{
			"name": apiName,
			"url":  "/api/v2/item/" + apiName + "/",
		}
	}

	writeJSON(w, 200, map[string]any{
		"count":   total,
		"results": results,
	})
}

// GET /api/v2/item/{identifier}
func GetItem(w http.ResponseWriter, r *http.Request) {
	identifier := chi.URLParam(r, "identifier")
	// Convert kebab-case back to display name for lookup
	displayName := strings.ReplaceAll(identifier, "-", " ")

	item, err := db.GetItemByName(r.Context(), displayName)
	if err != nil {
		// Try exact identifier
		item, err = db.GetItemByName(r.Context(), identifier)
		if err != nil {
			writeError(w, 404, "Item not found")
			return
		}
	}

	apiName := strings.ToLower(strings.ReplaceAll(item.Name, " ", "-"))
	category := ""
	if item.Category != nil {
		category = *item.Category
	}
	effect := ""
	if item.Effect != nil {
		effect = *item.Effect
	}
	spriteURL := ""
	if item.SpriteURL != nil {
		spriteURL = *item.SpriteURL
	}

	// Get game locations for this item
	locations, _ := db.GetItemLocations(r.Context(), item.Name)
	gameLocations := make([]map[string]any, 0)
	if locations != nil {
		for _, loc := range locations {
			method := ""
			if loc.Method != nil {
				method = *loc.Method
			}
			gameLocations = append(gameLocations, map[string]any{
				"game":     loc.Game,
				"location": loc.Location,
				"method":   method,
			})
		}
	}

	// Get Pokemon that hold this item in the wild
	holders, _ := db.GetWildHeldItemsByItem(r.Context(), item.Name)
	heldByPokemon := make([]map[string]any, 0)
	if holders != nil {
		for _, h := range holders {
			heldByPokemon = append(heldByPokemon, map[string]any{
				"pokemon": map[string]any{
					"name": strings.ToLower(h.PokemonName),
					"url":  "/api/v2/pokemon/" + strings.ToLower(h.PokemonName) + "/",
				},
				"game":   h.Game,
				"rarity": h.Rarity,
			})
		}
	}

	attributes, _ := db.GetItemAttributes(r.Context(), apiName)
	if attributes == nil {
		attributes = []string{}
	}
	extra, _ := db.GetItemExtra(r.Context(), apiName)

	attributeRefs := make([]map[string]any, len(attributes))
	for i, a := range attributes {
		attributeRefs[i] = map[string]any{"name": a}
	}

	resp := map[string]any{
		"id":         0,
		"name":       apiName,
		"cost":       item.BuyPrice,
		"buy_price":  item.BuyPrice,
		"sell_price": item.SellPrice,
		"category": map[string]any{
			"name": strings.ToLower(strings.ReplaceAll(category, " ", "-")),
		},
		"effect_entries": []map[string]any{
			{
				"short_effect": effect,
				"effect":       effect,
				"language":     map[string]string{"name": "en"},
			},
		},
		"flavor_text_entries": []map[string]any{
			{
				"text":     effect,
				"language": map[string]string{"name": "en"},
			},
		},
		"sprites": map[string]any{
			"default": spriteURL,
		},
		"held_by_pokemon": heldByPokemon,
		"game_locations":  gameLocations,
		"attributes":      attributeRefs,
	}
	if extra != nil {
		resp["fling_power"] = extra.FlingPower
		resp["fling_effect"] = extra.FlingEffect
		resp["baby_trigger_for"] = extra.BabyTriggerFor
	}

	writeJSON(w, 200, resp)
}

// GET /api/v2/item-locations?game={game}
func ListItemLocationsByGame(w http.ResponseWriter, r *http.Request) {
	game := r.URL.Query().Get("game")
	if game == "" {
		writeError(w, 400, "game query parameter is required")
		return
	}

	locs, err := db.GetItemLocationsByGame(r.Context(), game)
	if err != nil || locs == nil {
		locs = []models.ItemLocation{}
	}

	results := make([]map[string]any, len(locs))
	for i, l := range locs {
		method := ""
		if l.Method != nil {
			method = *l.Method
		}
		results[i] = map[string]any{
			"item_name": l.ItemName,
			"game":      l.Game,
			"location":  l.Location,
			"method":    method,
		}
	}

	writeJSON(w, 200, map[string]any{
		"game":    game,
		"count":   len(results),
		"results": results,
	})
}

// GET /api/v2/item-locations/games
func ListItemLocationGames(w http.ResponseWriter, r *http.Request) {
	games, err := db.GetAllItemLocationGames(r.Context())
	if err != nil || games == nil {
		games = []string{}
	}
	writeJSON(w, 200, map[string]any{"games": games})
}

// GET /api/v2/item/{identifier}/locations
func GetItemLocations(w http.ResponseWriter, r *http.Request) {
	identifier := chi.URLParam(r, "identifier")
	displayName := strings.ReplaceAll(identifier, "-", " ")

	locations, err := db.GetItemLocations(r.Context(), displayName)
	if err != nil {
		locations, err = db.GetItemLocations(r.Context(), identifier)
		if err != nil {
			writeJSON(w, 200, []any{})
			return
		}
	}

	result := make([]map[string]any, 0)
	if locations != nil {
		for _, loc := range locations {
			method := ""
			if loc.Method != nil {
				method = *loc.Method
			}
			result = append(result, map[string]any{
				"game":     loc.Game,
				"location": loc.Location,
				"method":   method,
			})
		}
	}

	writeJSON(w, 200, result)
}

// --- Types ---

// GET /api/v2/type
func ListTypes(w http.ResponseWriter, r *http.Request) {
	types, err := db.GetAllTypes(r.Context())
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if types == nil {
		types = []string{}
	}
	results := make([]map[string]any, len(types))
	for i, t := range types {
		results[i] = map[string]any{
			"name": t,
			"url":  "/api/v2/type/" + t + "/",
		}
	}
	writeJSON(w, 200, map[string]any{
		"count":   len(results),
		"results": results,
	})
}

// GET /api/v2/type/{identifier}
func GetType(w http.ResponseWriter, r *http.Request) {
	identifier := strings.ToLower(chi.URLParam(r, "identifier"))

	names, err := db.GetPokemonByType(r.Context(), identifier)
	if err != nil || names == nil {
		names = []string{}
	}

	pokemon := make([]map[string]any, len(names))
	for i, n := range names {
		apiName := strings.ToLower(n)
		pokemon[i] = map[string]any{
			"pokemon": map[string]any{
				"name": apiName,
				"url":  "/api/v2/pokemon/" + apiName + "/",
			},
			"slot": 1,
		}
	}

	rels, _ := db.GetTypeDamageRelations(r.Context(), identifier)
	if rels == nil {
		rels = &db.TypeDamageRelations{}
	}

	writeJSON(w, 200, map[string]any{
		"name":             identifier,
		"pokemon":          pokemon,
		"damage_relations": typeDamageRelationsJSON(rels),
	})
}

func typeDamageRelationsJSON(r *db.TypeDamageRelations) map[string]any {
	bucket := func(types []string) []map[string]any {
		out := make([]map[string]any, len(types))
		for i, t := range types {
			out[i] = map[string]any{
				"name": t,
				"url":  "/api/v2/type/" + t + "/",
			}
		}
		return out
	}
	return map[string]any{
		"double_damage_to":   bucket(r.DoubleDamageTo),
		"half_damage_to":     bucket(r.HalfDamageTo),
		"no_damage_to":       bucket(r.NoDamageTo),
		"double_damage_from": bucket(r.DoubleDamageFrom),
		"half_damage_from":   bucket(r.HalfDamageFrom),
		"no_damage_from":     bucket(r.NoDamageFrom),
	}
}

// --- Moves ---

// GET /api/v2/move?limit=N&offset=N&type=fire&category=physical&generation=3
func ListMoves(w http.ResponseWriter, r *http.Request) {
	limit := queryLimit(r, 1000, 10000)
	offset := queryInt(r, "offset", 0)
	gen := queryInt(r, "generation", 0)
	filter := db.MoveFilter{
		Type:       r.URL.Query().Get("type"),
		Category:   r.URL.Query().Get("category"),
		Generation: gen,
	}

	moves, total, err := db.GetAllMoveDetails(r.Context(), limit, offset, filter)
	if err != nil {
		writeServerError(w, r, err)
		return
	}

	results := make([]map[string]any, len(moves))
	for i, m := range moves {
		apiName := strings.ToLower(strings.ReplaceAll(m.Name, " ", "-"))
		results[i] = map[string]any{
			"name": apiName,
			"url":  "/api/v2/move/" + apiName + "/",
		}
	}

	writeJSON(w, 200, map[string]any{
		"count":   total,
		"results": results,
	})
}

// GET /api/v2/move/{identifier}
func GetMove(w http.ResponseWriter, r *http.Request) {
	identifier := chi.URLParam(r, "identifier")
	displayName := strings.ReplaceAll(identifier, "-", " ")

	m, err := db.GetMoveDetailByName(r.Context(), displayName)
	if err != nil {
		m, err = db.GetMoveDetailByName(r.Context(), identifier)
		if err != nil {
			writeError(w, 404, "Move not found")
			return
		}
	}

	apiName := strings.ToLower(strings.ReplaceAll(m.Name, " ", "-"))

	moveType := ""
	if m.Type != nil {
		moveType = strings.ToLower(*m.Type)
	}
	category := ""
	if m.Category != nil {
		category = strings.ToLower(*m.Category)
	}
	effect := ""
	if m.Effect != nil {
		effect = *m.Effect
	}

	// Get Pokemon that learn this move
	learners, _ := db.GetPokemonByMove(r.Context(), m.Name)
	learnedBy := make([]map[string]any, 0)
	if learners != nil {
		for _, l := range learners {
			learnedBy = append(learnedBy, map[string]any{
				"pokemon": map[string]any{
					"name": strings.ToLower(l["pokemon_name"]),
					"url":  "/api/v2/pokemon/" + strings.ToLower(l["pokemon_name"]) + "/",
				},
				"version_group_details": []map[string]any{
					{"move_learn_method": map[string]string{"name": l["learn_method"]}},
				},
			})
		}
	}

	target := ""
	if m.Target != nil {
		target = *m.Target
	}

	// Move meta + stat changes (PokeAPI CSV-sourced; may be absent)
	meta, _ := db.GetMoveMeta(r.Context(), apiName)
	statChanges, _ := db.GetMoveStatChanges(r.Context(), apiName)
	if statChanges == nil {
		statChanges = []models.MoveStatChange{}
	}

	resp := map[string]any{
		"id":       0,
		"name":     apiName,
		"accuracy": m.Accuracy,
		"power":    m.Power,
		"pp":       m.PP,
		"priority": m.Priority,
		"target":   target,
		"type": map[string]any{
			"name": moveType,
			"url":  "/api/v2/type/" + moveType + "/",
		},
		"damage_class": map[string]any{
			"name": category,
		},
		"effect_entries": []map[string]any{
			{
				"short_effect": effect,
				"effect":       effect,
				"language":     map[string]string{"name": "en"},
			},
		},
		"effect_chance": m.EffectChance,
		"flavor_text_entries": []map[string]any{
			{
				"flavor_text": effect,
				"language":    map[string]string{"name": "en"},
			},
		},
		"learned_by_pokemon": learnedBy,
		"machines":           []any{},
		"meta":               meta,
		"stat_changes":       statChanges,
	}

	writeJSON(w, 200, resp)
}

// --- Abilities ---

// GET /api/v2/ability?limit=N&offset=N
func ListAbilities(w http.ResponseWriter, r *http.Request) {
	limit := queryLimit(r, 400, 10000)
	offset := queryInt(r, "offset", 0)

	abilities, total, err := db.GetAllAbilities(r.Context(), limit, offset)
	if err != nil {
		writeServerError(w, r, err)
		return
	}

	results := make([]map[string]any, len(abilities))
	for i, a := range abilities {
		apiName := strings.ToLower(strings.ReplaceAll(a.Name, " ", "-"))
		results[i] = map[string]any{
			"name": apiName,
			"url":  "/api/v2/ability/" + apiName + "/",
		}
	}

	writeJSON(w, 200, map[string]any{
		"count":   total,
		"results": results,
	})
}

// GET /api/v2/ability/{identifier}
func GetAbility(w http.ResponseWriter, r *http.Request) {
	identifier := chi.URLParam(r, "identifier")
	displayName := strings.ReplaceAll(identifier, "-", " ")

	a, err := db.GetAbilityByName(r.Context(), displayName)
	if err != nil {
		a, err = db.GetAbilityByName(r.Context(), identifier)
		if err != nil {
			writeError(w, 404, "Ability not found")
			return
		}
	}

	apiName := strings.ToLower(strings.ReplaceAll(a.Name, " ", "-"))
	desc := ""
	if a.Description != nil {
		desc = *a.Description
	}
	gen := 0
	if a.Generation != nil {
		gen = *a.Generation
	}

	// Get Pokemon with this ability
	pokemon, _ := db.GetAbilityPokemon(r.Context(), a.Name)
	pokemonList := make([]map[string]any, 0)
	if pokemon != nil {
		for _, p := range pokemon {
			pokemonList = append(pokemonList, map[string]any{
				"is_hidden": p.IsHidden,
				"pokemon": map[string]any{
					"name": strings.ToLower(p.PokemonName),
					"url":  "/api/v2/pokemon/" + strings.ToLower(p.PokemonName) + "/",
				},
			})
		}
	}

	resp := map[string]any{
		"id":   0,
		"name": apiName,
		"generation": map[string]any{
			"name": "generation-" + strings.ToLower(romanNumeral(gen)),
			"url":  "/api/v2/generation/" + strconv.Itoa(gen) + "/",
		},
		"effect_entries": []map[string]any{
			{
				"short_effect": desc,
				"effect":       desc,
				"language":     map[string]string{"name": "en"},
			},
		},
		"flavor_text_entries": []map[string]any{
			{
				"flavor_text": desc,
				"language":    map[string]string{"name": "en"},
			},
		},
		"pokemon": pokemonList,
	}

	writeJSON(w, 200, resp)
}

// --- Natures ---

// GET /api/v2/nature
func ListNatures(w http.ResponseWriter, r *http.Request) {
	natures, err := db.GetAllNatures(r.Context())
	if err != nil {
		writeServerError(w, r, err)
		return
	}

	results := make([]map[string]any, len(natures))
	for i, n := range natures {
		increased := ""
		if n.IncreasedStat != nil {
			increased = *n.IncreasedStat
		}
		decreased := ""
		if n.DecreasedStat != nil {
			decreased = *n.DecreasedStat
		}
		results[i] = map[string]any{
			"name":           strings.ToLower(n.Name),
			"increased_stat": increased,
			"decreased_stat": decreased,
		}
	}

	writeJSON(w, 200, map[string]any{
		"count":   len(natures),
		"results": results,
	})
}

// --- Berries ---

// GET /api/v2/berry
func ListBerries(w http.ResponseWriter, r *http.Request) {
	berries, err := db.GetAllBerries(r.Context())
	if err != nil {
		writeServerError(w, r, err)
		return
	}

	results := make([]map[string]any, len(berries))
	for i, b := range berries {
		apiName := strings.ToLower(strings.ReplaceAll(b.Name, " ", "-"))
		results[i] = map[string]any{
			"name": apiName,
			"url":  "/api/v2/berry/" + apiName + "/",
		}
	}

	writeJSON(w, 200, map[string]any{
		"count":   len(berries),
		"results": results,
	})
}

// GET /api/v2/berry/{identifier}
func GetBerry(w http.ResponseWriter, r *http.Request) {
	identifier := chi.URLParam(r, "identifier")
	displayName := strings.ReplaceAll(identifier, "-", " ")

	b, err := db.GetBerryByName(r.Context(), displayName)
	if err != nil {
		b, err = db.GetBerryByName(r.Context(), identifier)
		if err != nil {
			writeError(w, 404, "Berry not found")
			return
		}
	}

	flavors, _ := db.GetBerryFlavors(r.Context(), b.Name)
	flavorList := make([]map[string]any, 0)
	if flavors != nil {
		for _, f := range flavors {
			flavorList = append(flavorList, map[string]any{
				"flavor":  map[string]string{"name": f.Flavor},
				"potency": f.Potency,
			})
		}
	}

	effect := ""
	if b.Effect != nil {
		effect = *b.Effect
	}
	firmness := ""
	if b.Firmness != nil {
		firmness = *b.Firmness
	}
	giftType := ""
	if b.NaturalGiftType != nil {
		giftType = *b.NaturalGiftType
	}

	resp := map[string]any{
		"id":                 0,
		"name":               strings.ToLower(strings.ReplaceAll(b.Name, " ", "-")),
		"natural_gift_type":  giftType,
		"natural_gift_power": b.NaturalGiftPower,
		"size":               b.SizeMM,
		"firmness":           map[string]string{"name": firmness},
		"growth_time":        b.GrowthTime,
		"effect":             effect,
		"flavors":            flavorList,
	}

	writeJSON(w, 200, resp)
}

// --- Location encounters ---

// GET /api/v2/location/regions?game={game}
func ListRegions(w http.ResponseWriter, r *http.Request) {
	game := r.URL.Query().Get("game")
	var regions []string
	var err error
	if game != "" {
		regions, err = db.GetRegionsByGame(r.Context(), game)
	} else {
		regions, err = db.GetAllRegions(r.Context())
	}
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	writeJSON(w, 200, map[string]any{"regions": regions})
}

// GET /api/v2/location/pokemon/{name}
func GetPokemonLocationEncounters(w http.ResponseWriter, r *http.Request) {
	name := chi.URLParam(r, "name")
	encounters, err := db.GetEncountersByPokemon(r.Context(), name)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if encounters == nil {
		encounters = []models.LocationEncounter{}
	}
	writeJSON(w, 200, map[string]any{
		"pokemon_name": name,
		"encounters":   encounters,
	})
}

// GET /api/v2/location/games
func ListEncounterGames(w http.ResponseWriter, r *http.Request) {
	abbreviations, err := db.GetAllEncounterGames(r.Context())
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if abbreviations == nil {
		abbreviations = []string{}
	}

	gameNames := map[string]string{
		"AS":  "Alpha Sapphire",
		"B":   "Blue / Black",
		"B2":  "Black 2",
		"BD":  "Brilliant Diamond",
		"C":   "Crystal",
		"D":   "Diamond",
		"E":   "Emerald",
		"FR":  "FireRed",
		"G":   "Gold",
		"HG":  "HeartGold",
		"LA":  "Legends: Arceus",
		"LG":  "LeafGreen",
		"LGE": "Let's Go Eevee",
		"LGP": "Let's Go Pikachu",
		"M":   "Moon",
		"OR":  "Omega Ruby",
		"P":   "Pearl",
		"Pt":  "Platinum",
		"R":   "Red / Ruby",
		"S":   "Silver / Sun / Scarlet",
		"Sh":  "Shield",
		"SP":  "Shining Pearl",
		"SS":  "SoulSilver",
		"Sw":  "Sword",
		"UM":  "Ultra Moon",
		"US":  "Ultra Sun",
		"V":   "Violet",
		"W":   "White",
		"W2":  "White 2",
		"X":   "X",
		"Y":   "Yellow / Y",
	}

	results := make([]map[string]any, len(abbreviations))
	for i, abbr := range abbreviations {
		name := abbr
		if display, ok := gameNames[abbr]; ok {
			name = display
		}
		results[i] = map[string]any{
			"abbreviation": abbr,
			"name":         name,
		}
	}

	writeJSON(w, 200, map[string]any{"games": results})
}

// GET /api/v2/location/region/{region}/routes?game={game}
func ListRoutes(w http.ResponseWriter, r *http.Request) {
	region := chi.URLParam(r, "region")
	game := r.URL.Query().Get("game")

	var routes []string
	var err error
	if game != "" {
		routes, err = db.GetRoutesByRegionAndGame(r.Context(), region, game)
	} else {
		routes, err = db.GetRoutesByRegion(r.Context(), region)
	}
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	writeJSON(w, 200, map[string]any{"region": region, "routes": routes})
}

// GET /api/v2/location/region/{region}/route/{route}?game={game}
func GetRouteEncounters(w http.ResponseWriter, r *http.Request) {
	region := chi.URLParam(r, "region")
	route := chi.URLParam(r, "route")
	game := r.URL.Query().Get("game")

	var encounters []models.LocationEncounter
	var err error
	if game != "" {
		encounters, err = db.GetLocationEncountersByGame(r.Context(), region, route, game)
	} else {
		encounters, err = db.GetLocationEncounters(r.Context(), region, route)
	}
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if encounters == nil {
		encounters = []models.LocationEncounter{}
	}

	writeJSON(w, 200, map[string]any{
		"region":     region,
		"route":      route,
		"encounters": encounters,
	})
}

// --- Pokedex entries (flavor text) ---

// GET /api/v2/pokemon/{identifier}/flavor-text
func GetPokemonFlavorText(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}

	entries, _ := db.GetPokedexEntries(r.Context(), p.Name)
	if entries == nil {
		entries = []models.PokedexEntry{}
	}

	result := make([]map[string]any, len(entries))
	for i, e := range entries {
		result[i] = map[string]any{
			"flavor_text": e.FlavorText,
			"version":     map[string]string{"name": e.GameVersion},
			"language":    map[string]string{"name": "en"},
		}
	}

	writeJSON(w, 200, result)
}

// GET /api/v2/pokemon/{identifier}/names
func GetPokemonNames(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}
	names, _ := db.GetPokemonNames(r.Context(), p.Name)
	if names == nil {
		names = []models.PokemonName{}
	}
	writeJSON(w, 200, names)
}

// GET /api/v2/pokemon/{identifier}/sprites-all
func GetPokemonSprites(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}
	sprites, _ := db.GetPokemonSprites(r.Context(), p.Name)
	if sprites == nil {
		sprites = []models.PokemonSprite{}
	}
	writeJSON(w, 200, sprites)
}

// --- TM locations ---

// GET /api/v2/tm?game={game}
func ListTmLocations(w http.ResponseWriter, r *http.Request) {
	game := r.URL.Query().Get("game")
	if game == "" {
		writeError(w, 400, "game query parameter is required")
		return
	}

	locs, err := db.GetTmLocations(r.Context(), game)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if locs == nil {
		locs = []models.TmLocation{}
	}

	writeJSON(w, 200, map[string]any{
		"game":    game,
		"count":   len(locs),
		"results": locs,
	})
}

// GET /api/v2/tm/games
func ListTmGames(w http.ResponseWriter, r *http.Request) {
	games, err := db.GetAllTmGames(r.Context())
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if games == nil {
		games = []string{}
	}
	writeJSON(w, 200, map[string]any{"games": games})
}

// --- Pokemon game locations ---

// GET /api/v2/pokemon/{identifier}/game-locations
func GetPokemonGameLocationsHandler(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}

	locs, _ := db.GetPokemonGameLocations(r.Context(), p.Name)
	if locs == nil {
		locs = []models.PokemonGameLocation{}
	}

	result := make([]map[string]any, len(locs))
	for i, l := range locs {
		method := ""
		if l.Method != nil {
			method = *l.Method
		}
		result[i] = map[string]any{
			"game":     l.Game,
			"location": l.Location,
			"method":   method,
		}
	}

	writeJSON(w, 200, map[string]any{
		"pokemon_name": p.Name,
		"locations":    result,
	})
}

// --- Wild held items ---

// GET /api/v2/pokemon/{identifier}/held-items
func GetPokemonHeldItems(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}

	items, _ := db.GetWildHeldItemsByPokemon(r.Context(), p.Name)
	if items == nil {
		items = []models.WildHeldItem{}
	}

	result := make([]map[string]any, len(items))
	for i, h := range items {
		result[i] = map[string]any{
			"item":   map[string]string{"name": strings.ToLower(h.ItemName)},
			"game":   h.Game,
			"rarity": h.Rarity,
		}
	}

	writeJSON(w, 200, map[string]any{
		"pokemon_name": p.Name,
		"held_items":   result,
	})
}

// --- Pokemon biology ---

// GET /api/v2/pokemon/{identifier}/biology
func GetPokemonBiologyHandler(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}

	bio, err := db.GetPokemonBiologyText(r.Context(), p.Name)
	if err != nil {
		writeJSON(w, 200, map[string]any{"pokemon_name": p.Name, "biology": ""})
		return
	}

	writeJSON(w, 200, map[string]any{
		"pokemon_name": bio.PokemonName,
		"biology":      bio.Biology,
	})
}

// --- Pokemon forms ---

// GET /api/v2/pokemon/{identifier}/forms
func GetPokemonForms(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}

	forms, _ := db.GetPokemonForms(r.Context(), p.Name)
	if forms == nil {
		forms = []models.PokemonForm{}
	}

	writeJSON(w, 200, map[string]any{
		"pokemon_name": p.Name,
		"forms":        forms,
	})
}

// --- Egg move parents ---

// GET /api/v2/pokemon/{identifier}/egg-move-parents
// Optional query: ?move={move_name} to filter to a specific egg move.
func GetEggMoveParents(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}

	moveName := r.URL.Query().Get("move")
	var parents []models.EggMoveParent
	if moveName != "" {
		parents, _ = db.GetEggMoveParents(r.Context(), p.Name, moveName)
	} else {
		parents, _ = db.GetAllEggMoveParents(r.Context(), p.Name)
	}
	if parents == nil {
		parents = []models.EggMoveParent{}
	}

	writeJSON(w, 200, map[string]any{
		"pokemon_name": p.Name,
		"parents":      parents,
	})
}

// --- Classification ---

// GET /api/v2/pokemon/{identifier}/classification
func GetPokemonClassification(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}
	c, err := db.GetPokemonClassification(r.Context(), p.Name)
	if err != nil {
		writeError(w, 404, "Classification not found")
		return
	}
	writeJSON(w, 200, c)
}

// --- Localized names (PokeAPI CSV-sourced) ---

func writeLocalizedNames(w http.ResponseWriter, r *http.Request, table, paramName string) {
	identifier := strings.ToLower(chi.URLParam(r, paramName))
	names, err := db.GetLocalizedNames(r.Context(), table, identifier)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if names == nil {
		names = []models.PokemonName{}
	}
	writeJSON(w, 200, names)
}

// GET /api/v2/item/{identifier}/names
func GetItemNames(w http.ResponseWriter, r *http.Request) {
	writeLocalizedNames(w, r, "item_names", "identifier")
}

// GET /api/v2/move/{identifier}/names
func GetMoveNames(w http.ResponseWriter, r *http.Request) {
	writeLocalizedNames(w, r, "move_names", "identifier")
}

// GET /api/v2/ability/{identifier}/names
func GetAbilityNames(w http.ResponseWriter, r *http.Request) {
	writeLocalizedNames(w, r, "ability_names", "identifier")
}

// GET /api/v2/type/{identifier}/names
func GetTypeNames(w http.ResponseWriter, r *http.Request) {
	writeLocalizedNames(w, r, "type_names", "identifier")
}

// --- Classification (color / shape / habitat / egg-group) listing ---

// classificationListResponse formats a list of values as PokeAPI-style results.
func classificationListResponse(values []string, baseURL string) map[string]any {
	results := make([]map[string]any, len(values))
	for i, v := range values {
		slug := toAPIName(v)
		results[i] = map[string]any{
			"name": slug,
			"url":  baseURL + slug + "/",
		}
	}
	return map[string]any{
		"count":   len(results),
		"results": results,
	}
}

// pokemonListResponse formats a list of Pokemon names as PokeAPI species refs.
func pokemonListResponse(names []string) []map[string]any {
	out := make([]map[string]any, len(names))
	for i, n := range names {
		apiName := strings.ToLower(n)
		out[i] = map[string]any{
			"name": apiName,
			"url":  "/api/v2/pokemon/" + apiName + "/",
		}
	}
	return out
}

// GET /api/v2/pokemon-color
func ListPokemonColors(w http.ResponseWriter, r *http.Request) {
	colors, err := db.GetAllPokemonColors(r.Context())
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	writeJSON(w, 200, classificationListResponse(colors, "/api/v2/pokemon-color/"))
}

// GET /api/v2/pokemon-color/{color}
func GetPokemonColor(w http.ResponseWriter, r *http.Request) {
	color := chi.URLParam(r, "color")
	display := strings.ReplaceAll(color, "-", " ")
	names, err := db.GetPokemonByColor(r.Context(), display)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	writeJSON(w, 200, map[string]any{
		"name":            color,
		"pokemon_species": pokemonListResponse(names),
	})
}

// GET /api/v2/pokemon-shape
func ListPokemonShapes(w http.ResponseWriter, r *http.Request) {
	shapes, err := db.GetAllPokemonShapes(r.Context())
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	writeJSON(w, 200, classificationListResponse(shapes, "/api/v2/pokemon-shape/"))
}

// GET /api/v2/pokemon-shape/{shape}
func GetPokemonShape(w http.ResponseWriter, r *http.Request) {
	shape := chi.URLParam(r, "shape")
	display := strings.ReplaceAll(shape, "-", " ")
	names, err := db.GetPokemonByShape(r.Context(), display)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	writeJSON(w, 200, map[string]any{
		"name":            shape,
		"pokemon_species": pokemonListResponse(names),
	})
}

// GET /api/v2/pokemon-habitat
func ListPokemonHabitats(w http.ResponseWriter, r *http.Request) {
	habitats, err := db.GetAllPokemonHabitats(r.Context())
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	writeJSON(w, 200, classificationListResponse(habitats, "/api/v2/pokemon-habitat/"))
}

// GET /api/v2/pokemon-habitat/{habitat}
func GetPokemonHabitat(w http.ResponseWriter, r *http.Request) {
	habitat := chi.URLParam(r, "habitat")
	display := strings.ReplaceAll(habitat, "-", " ")
	names, err := db.GetPokemonByHabitat(r.Context(), display)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	writeJSON(w, 200, map[string]any{
		"name":            habitat,
		"pokemon_species": pokemonListResponse(names),
	})
}

// GET /api/v2/egg-group
func ListEggGroups(w http.ResponseWriter, r *http.Request) {
	groups, err := db.GetAllEggGroups(r.Context())
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	writeJSON(w, 200, classificationListResponse(groups, "/api/v2/egg-group/"))
}

// GET /api/v2/egg-group/{name}
func GetEggGroup(w http.ResponseWriter, r *http.Request) {
	name := chi.URLParam(r, "name")
	display := strings.ReplaceAll(name, "-", " ")
	names, err := db.GetPokemonByEggGroup(r.Context(), display)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	writeJSON(w, 200, map[string]any{
		"name":            name,
		"pokemon_species": pokemonListResponse(names),
	})
}

// --- Z-Moves ---

// GET /api/v2/z-move
func ListZMoves(w http.ResponseWriter, r *http.Request) {
	moves, err := db.GetAllZMoves(r.Context())
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if moves == nil {
		moves = []models.ZMove{}
	}
	writeJSON(w, 200, map[string]any{
		"count":   len(moves),
		"results": moves,
	})
}

// GET /api/v2/z-move/{name}
func GetZMove(w http.ResponseWriter, r *http.Request) {
	name := chi.URLParam(r, "name")
	displayName := strings.ReplaceAll(name, "-", " ")
	z, err := db.GetZMoveByName(r.Context(), displayName)
	if err != nil {
		z, err = db.GetZMoveByName(r.Context(), name)
		if err != nil {
			writeError(w, 404, "Z-Move not found")
			return
		}
	}
	writeJSON(w, 200, z)
}

// --- In-Game Trades ---

// GET /api/v2/in-game-trades?game=X
func ListInGameTrades(w http.ResponseWriter, r *http.Request) {
	game := r.URL.Query().Get("game")
	trades, err := db.GetAllInGameTrades(r.Context(), game)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if trades == nil {
		trades = []models.InGameTrade{}
	}
	writeJSON(w, 200, map[string]any{
		"count":   len(trades),
		"results": trades,
	})
}

// --- Contest Stats ---

// GET /api/v2/pokemon/{identifier}/contest-stats
func GetPokemonContestStats(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}
	stats, err := db.GetContestStats(r.Context(), p.Name)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if stats == nil {
		stats = []models.ContestStat{}
	}
	writeJSON(w, 200, map[string]any{
		"pokemon_name":  p.Name,
		"contest_stats": stats,
	})
}

// --- Event Pokemon ---

// GET /api/v2/event-pokemon?name=X&game=X
func ListEventPokemon(w http.ResponseWriter, r *http.Request) {
	name := r.URL.Query().Get("name")
	game := r.URL.Query().Get("game")
	events, err := db.GetAllEventPokemon(r.Context(), name, game)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if events == nil {
		events = []models.EventPokemon{}
	}
	writeJSON(w, 200, map[string]any{
		"count":   len(events),
		"results": events,
	})
}

// --- Mass Outbreaks ---

// GET /api/v2/mass-outbreaks?game=X&region=X
func ListMassOutbreaks(w http.ResponseWriter, r *http.Request) {
	game := r.URL.Query().Get("game")
	region := r.URL.Query().Get("region")
	outbreaks, err := db.GetAllMassOutbreaks(r.Context(), game, region)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if outbreaks == nil {
		outbreaks = []models.MassOutbreak{}
	}
	writeJSON(w, 200, map[string]any{
		"count":   len(outbreaks),
		"results": outbreaks,
	})
}

// --- Pokemon GO ---

// GET /api/v2/pokemon/{identifier}/go
func GetPokemonGoStats(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}
	g, err := db.GetPokemonGo(r.Context(), p.Name)
	if err != nil {
		writeError(w, 404, "Pokemon GO data not found")
		return
	}
	writeJSON(w, 200, g)
}

// --- Battle Facilities ---

// GET /api/v2/battle-facility?game=X
func ListBattleFacilities(w http.ResponseWriter, r *http.Request) {
	game := r.URL.Query().Get("game")
	facilities, err := db.GetAllBattleFacilities(r.Context(), game)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if facilities == nil {
		facilities = []models.BattleFacility{}
	}
	writeJSON(w, 200, map[string]any{
		"count":   len(facilities),
		"results": facilities,
	})
}

// --- Move Tutors ---

// GET /api/v2/move-tutor?game=X&move=X
func ListMoveTutors(w http.ResponseWriter, r *http.Request) {
	game := r.URL.Query().Get("game")
	move := r.URL.Query().Get("move")
	tutors, err := db.GetAllMoveTutorLocations(r.Context(), game, move)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if tutors == nil {
		tutors = []models.MoveTutorLocation{}
	}
	writeJSON(w, 200, map[string]any{
		"count":   len(tutors),
		"results": tutors,
	})
}

// --- Version Exclusives ---

// GET /api/v2/version-exclusive?game=X&game_pair=X
func ListVersionExclusives(w http.ResponseWriter, r *http.Request) {
	game := r.URL.Query().Get("game")
	gamePair := r.URL.Query().Get("game_pair")
	exclusives, err := db.GetAllVersionExclusives(r.Context(), game, gamePair)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if exclusives == nil {
		exclusives = []models.VersionExclusive{}
	}
	writeJSON(w, 200, map[string]any{
		"count":   len(exclusives),
		"results": exclusives,
	})
}

// --- Trainers ---

// GET /api/v2/trainer?game=X&role=X
func ListTrainers(w http.ResponseWriter, r *http.Request) {
	game := r.URL.Query().Get("game")
	role := r.URL.Query().Get("role")
	trainers, err := db.GetAllTrainers(r.Context(), game, role)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if trainers == nil {
		trainers = []models.Trainer{}
	}
	writeJSON(w, 200, map[string]any{
		"count":   len(trainers),
		"results": trainers,
	})
}

// GET /api/v2/trainer/{name}/team?game=X&variant=X
func GetTrainerTeam(w http.ResponseWriter, r *http.Request) {
	name := chi.URLParam(r, "name")
	game := r.URL.Query().Get("game")
	variant := r.URL.Query().Get("variant")
	pokemon, err := db.GetTrainerPokemon(r.Context(), name, game, variant)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if pokemon == nil {
		pokemon = []models.TrainerPokemon{}
	}
	writeJSON(w, 200, map[string]any{
		"trainer_name": name,
		"count":        len(pokemon),
		"results":      pokemon,
	})
}

// --- EV Targets ---

// GET /api/v2/pokemon/ev-targets?stat=hp&game=Sword/Shield
func GetEVTargets(w http.ResponseWriter, r *http.Request) {
	stat := strings.ToLower(r.URL.Query().Get("stat"))
	game := r.URL.Query().Get("game")

	if stat == "" {
		writeError(w, 400, "stat query parameter required (hp, attack, defense, sp-atk, sp-def, speed)")
		return
	}

	targets, err := db.GetEVTargetsByStat(r.Context(), stat, game)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if targets == nil {
		targets = []db.EVTarget{}
	}
	writeJSON(w, 200, map[string]any{
		"stat":    stat,
		"game":    game,
		"count":   len(targets),
		"results": targets,
	})
}

// --- helpers ---

func romanNumeral(n int) string {
	numerals := map[int]string{
		1: "i", 2: "ii", 3: "iii", 4: "iv", 5: "v",
		6: "vi", 7: "vii", 8: "viii", 9: "ix",
	}
	if s, ok := numerals[n]; ok {
		return s
	}
	return strconv.Itoa(n)
}
