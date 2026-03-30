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
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	offset, _ := strconv.Atoi(r.URL.Query().Get("offset"))
	if limit <= 0 {
		limit = 2000
	}

	items, total, err := db.GetAllItems(r.Context(), limit, offset)
	if err != nil {
		writeError(w, 500, err.Error())
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

	resp := map[string]any{
		"id":   0,
		"name": apiName,
		"cost": 0,
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
		"held_by_pokemon": []any{},
	}

	writeJSON(w, 200, resp)
}

// --- Moves ---

// GET /api/v2/move?limit=N&offset=N
func ListMoves(w http.ResponseWriter, r *http.Request) {
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	offset, _ := strconv.Atoi(r.URL.Query().Get("offset"))
	if limit <= 0 {
		limit = 1000
	}

	moves, total, err := db.GetAllMoveDetails(r.Context(), limit, offset)
	if err != nil {
		writeError(w, 500, err.Error())
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

	resp := map[string]any{
		"id":       0,
		"name":     apiName,
		"accuracy": m.Accuracy,
		"power":    m.Power,
		"pp":       m.PP,
		"priority": 0,
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
	}

	writeJSON(w, 200, resp)
}

// --- Abilities ---

// GET /api/v2/ability?limit=N&offset=N
func ListAbilities(w http.ResponseWriter, r *http.Request) {
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	offset, _ := strconv.Atoi(r.URL.Query().Get("offset"))
	if limit <= 0 {
		limit = 400
	}

	abilities, total, err := db.GetAllAbilities(r.Context(), limit, offset)
	if err != nil {
		writeError(w, 500, err.Error())
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
		writeError(w, 500, err.Error())
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
		writeError(w, 500, err.Error())
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

// GET /api/v2/location/regions
func ListRegions(w http.ResponseWriter, r *http.Request) {
	regions, err := db.GetAllRegions(r.Context())
	if err != nil {
		writeError(w, 500, err.Error())
		return
	}
	writeJSON(w, 200, map[string]any{"regions": regions})
}

// GET /api/v2/location/pokemon/{name}
func GetPokemonLocationEncounters(w http.ResponseWriter, r *http.Request) {
	name := chi.URLParam(r, "name")
	encounters, err := db.GetEncountersByPokemon(r.Context(), name)
	if err != nil {
		writeError(w, 500, err.Error())
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

// GET /api/v2/location/region/{region}/routes
func ListRoutes(w http.ResponseWriter, r *http.Request) {
	region := chi.URLParam(r, "region")
	routes, err := db.GetRoutesByRegion(r.Context(), region)
	if err != nil {
		writeError(w, 500, err.Error())
		return
	}
	writeJSON(w, 200, map[string]any{"region": region, "routes": routes})
}

// GET /api/v2/location/region/{region}/route/{route}
func GetRouteEncounters(w http.ResponseWriter, r *http.Request) {
	region := chi.URLParam(r, "region")
	route := chi.URLParam(r, "route")

	encounters, err := db.GetLocationEncounters(r.Context(), region, route)
	if err != nil {
		writeError(w, 500, err.Error())
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
