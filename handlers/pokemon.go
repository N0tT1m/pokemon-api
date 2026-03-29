package handlers

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"github.com/N0tT1m/pokedex-api/db"
	"github.com/N0tT1m/pokedex-api/models"
	"github.com/go-chi/chi/v5"
)

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

// lookupPokemon resolves an identifier (name or national dex number) to a Pokemon.
func lookupPokemon(r *http.Request) (*models.Pokemon, error) {
	identifier := strings.ToLower(chi.URLParam(r, "identifier"))

	// Try as number first
	if no, err := strconv.Atoi(identifier); err == nil {
		return db.GetPokemonByNationalNo(r.Context(), no)
	}
	return db.GetPokemonByName(r.Context(), identifier)
}

// GET /api/v2/pokemon?limit=N&offset=N
func ListPokemon(w http.ResponseWriter, r *http.Request) {
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	offset, _ := strconv.Atoi(r.URL.Query().Get("offset"))
	if limit <= 0 {
		limit = 1025
	}

	entries, total, err := db.GetAllPokemon(r.Context(), limit, offset)
	if err != nil {
		writeError(w, 500, err.Error())
		return
	}

	// Match PokeAPI format — use numeric IDs in URLs so extractIdFromUrl works
	results := make([]map[string]any, len(entries))
	for i, e := range entries {
		numID := "0"
		if e.NationalNo != nil {
			numID = strings.TrimLeft(*e.NationalNo, "0")
			if numID == "" {
				numID = "0"
			}
		}
		results[i] = map[string]any{
			"name": strings.ToLower(e.Name),
			"url":  "/api/v2/pokemon/" + numID + "/",
		}
	}

	writeJSON(w, 200, map[string]any{
		"count":   total,
		"results": results,
	})
}

// GET /api/v2/pokemon/{identifier}
// Returns PokeAPI-compatible JSON structure.
func GetPokemon(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}

	id := 0
	if p.NationalNo != nil {
		id, _ = strconv.Atoi(strings.TrimLeft(*p.NationalNo, "0"))
	}

	// Build types array matching PokeAPI
	types := make([]map[string]any, len(p.Types))
	for i, t := range p.Types {
		types[i] = map[string]any{
			"slot": i + 1,
			"type": map[string]any{
				"name": strings.ToLower(t),
				"url":  "/api/v2/type/" + strings.ToLower(t),
			},
		}
	}

	// Build abilities
	abilities := make([]map[string]any, len(p.Abilities))
	for i, a := range p.Abilities {
		a = strings.TrimSpace(a)
		isHidden := strings.Contains(a, "(Hidden)")
		cleanName := strings.TrimSpace(strings.Replace(a, "(Hidden)", "", 1))
		apiName := strings.ToLower(strings.ReplaceAll(cleanName, " ", "-"))
		abilities[i] = map[string]any{
			"is_hidden": isHidden,
			"slot":      i + 1,
			"ability": map[string]any{
				"name": apiName,
				"url":  "/api/v2/ability/" + apiName,
			},
		}
	}

	// Build stats matching PokeAPI
	statNames := []struct {
		key  string
		name string
		val  *int
	}{
		{"hp", "hp", p.HP},
		{"attack", "attack", p.Attack},
		{"defense", "defense", p.Defense},
		{"sp_atk", "special-attack", p.SpAtk},
		{"sp_def", "special-defense", p.SpDef},
		{"speed", "speed", p.Speed},
	}

	// Calculate EV effort values from ev_yield text
	evMap := parseEVYield(deref(p.EVYield))

	stats := make([]map[string]any, len(statNames))
	for i, s := range statNames {
		baseStat := 0
		if s.val != nil {
			baseStat = *s.val
		}
		stats[i] = map[string]any{
			"base_stat": baseStat,
			"effort":    evMap[s.name],
			"stat": map[string]any{
				"name": s.name,
				"url":  "/api/v2/stat/" + s.name,
			},
		}
	}

	spriteID := strconv.Itoa(id)
	resp := map[string]any{
		"id":              id,
		"name":            strings.ToLower(p.Name),
		"base_experience": parseIntOrNil(deref(p.BaseExp)),
		"height":          0, // raw decimeters not stored; Flutter formats from this
		"weight":          0,
		"types":           types,
		"abilities":       abilities,
		"stats":           stats,
		"sprites": map[string]any{
			"front_default": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/" + spriteID + ".png",
			"other": map[string]any{
				"official-artwork": map[string]any{
					"front_default": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/" + spriteID + ".png",
				},
			},
		},
	}

	writeJSON(w, 200, resp)
}

// GET /api/v2/pokemon-species/{identifier}
func GetPokemonSpecies(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon species not found")
		return
	}

	id := 0
	if p.NationalNo != nil {
		id, _ = strconv.Atoi(strings.TrimLeft(*p.NationalNo, "0"))
	}

	evos, _ := db.GetEvolutions(r.Context(), p.Name)

	genderRate := -1 // default genderless
	if p.GenderRatio != nil && *p.GenderRatio != "" && *p.GenderRatio != "Genderless" {
		genderRate = parseGenderRate(*p.GenderRatio)
	}

	resp := map[string]any{
		"id":   id,
		"name": strings.ToLower(p.Name),
		"genera": []map[string]any{
			{
				"genus":    deref(p.Species),
				"language": map[string]string{"name": "en"},
			},
		},
		"capture_rate":   parseIntOrNil(deref(p.CatchRate)),
		"base_happiness": parseIntOrNil(deref(p.BaseFriendship)),
		"growth_rate": map[string]any{
			"name": strings.ToLower(strings.ReplaceAll(deref(p.GrowthRate), " ", "-")),
		},
		"gender_rate":   genderRate,
		"hatch_counter": parseIntOrNil(deref(p.EggCycles)),
		"egg_groups":    formatEggGroups(p.EggGroups),
		"flavor_text_entries": []map[string]any{
			{
				"flavor_text": "", // we don't have flavor text in our DB
				"language":    map[string]string{"name": "en"},
			},
		},
		"evolution_chain": buildEvolutionChainRef(evos, id),
	}

	writeJSON(w, 200, resp)
}

// GET /api/v2/evolution-chain/{id}
func GetEvolutionChain(w http.ResponseWriter, r *http.Request) {
	// The ID here is the Pokemon's national dex number (we use it as chain ID)
	idStr := chi.URLParam(r, "id")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		writeError(w, 400, "Invalid evolution chain ID")
		return
	}

	// Find the pokemon by national number to get its name
	p, err := db.GetPokemonByNationalNo(r.Context(), id)
	if err != nil {
		writeError(w, 404, "Evolution chain not found")
		return
	}

	evos, _ := db.GetEvolutions(r.Context(), p.Name)
	chain := buildEvolutionTree(evos)

	writeJSON(w, 200, map[string]any{
		"id":    id,
		"chain": chain,
	})
}

// GET /api/v2/pokemon/{identifier}/encounters
func GetPokemonEncounters(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}

	locs, _ := db.GetLocations(r.Context(), p.Name)
	if locs == nil {
		locs = []models.Location{}
	}

	writeJSON(w, 200, locs)
}

// GET /api/v2/pokedex/game/{game}
func GetGamePokedex(w http.ResponseWriter, r *http.Request) {
	game := chi.URLParam(r, "game")

	regional, _ := db.GetRegionalDex(r.Context(), game)
	national, _ := db.GetGameNationalDex(r.Context(), game)

	resp := map[string]any{
		"game":     game,
		"regional": regional,
		"national": national,
	}
	writeJSON(w, 200, resp)
}

// GET /api/v2/games
func ListGames(w http.ResponseWriter, r *http.Request) {
	games, err := db.GetAllGames(r.Context())
	if err != nil {
		writeError(w, 500, err.Error())
		return
	}
	writeJSON(w, 200, map[string]any{"games": games})
}

// GET /api/v2/pokemon/{identifier}/moves
func GetPokemonMoves(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}

	moves, _ := db.GetMoves(r.Context(), p.Name)
	if moves == nil {
		moves = []models.Move{}
	}

	writeJSON(w, 200, moves)
}

// GET /api/v2/pokemon/{identifier}/type-defenses
func GetPokemonTypeDefenses(w http.ResponseWriter, r *http.Request) {
	p, err := lookupPokemon(r)
	if err != nil {
		writeError(w, 404, "Pokemon not found")
		return
	}

	defenses, _ := db.GetTypeDefenses(r.Context(), p.Name)
	if defenses == nil {
		defenses = []models.TypeDefense{}
	}

	writeJSON(w, 200, defenses)
}

// --- helpers ---

func deref(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

func parseIntOrNil(s string) any {
	s = strings.TrimSpace(s)
	if s == "" {
		return nil
	}
	// Take only digits from start (e.g. "45 (5.9% ...)" -> 45)
	digits := ""
	for _, c := range s {
		if c >= '0' && c <= '9' {
			digits += string(c)
		} else {
			break
		}
	}
	if v, err := strconv.Atoi(digits); err == nil {
		return v
	}
	return nil
}

func parseEVYield(s string) map[string]int {
	m := map[string]int{
		"hp": 0, "attack": 0, "defense": 0,
		"special-attack": 0, "special-defense": 0, "speed": 0,
	}
	statAliases := map[string]string{
		"hp": "hp", "attack": "attack", "defense": "defense",
		"sp. atk": "special-attack", "sp. def": "special-defense",
		"speed": "speed", "sp.atk": "special-attack", "sp.def": "special-defense",
	}
	for _, part := range strings.Split(s, ",") {
		part = strings.TrimSpace(part)
		if part == "" || part == "None" {
			continue
		}
		// Format: "1 Sp. Atk" or "2 Attack"
		fields := strings.SplitN(part, " ", 2)
		if len(fields) != 2 {
			continue
		}
		val, err := strconv.Atoi(fields[0])
		if err != nil {
			continue
		}
		statKey := strings.ToLower(strings.TrimSpace(fields[1]))
		if apiName, ok := statAliases[statKey]; ok {
			m[apiName] = val
		}
	}
	return m
}

func parseGenderRate(s string) int {
	// Format: "87.5% ♂, 12.5% ♀" -> PokeAPI gender_rate (female eighths)
	// gender_rate = female% / 12.5
	parts := strings.Split(s, ",")
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if strings.Contains(p, "♀") {
			numStr := strings.TrimRight(strings.TrimSpace(strings.Replace(p, "♀", "", 1)), "%")
			if val, err := strconv.ParseFloat(numStr, 64); err == nil {
				return int(val / 12.5)
			}
		}
	}
	return -1
}

func formatEggGroups(groups []string) []map[string]any {
	result := make([]map[string]any, len(groups))
	for i, g := range groups {
		result[i] = map[string]any{
			"name": strings.ToLower(strings.ReplaceAll(strings.TrimSpace(g), " ", "-")),
		}
	}
	return result
}

func buildEvolutionChainRef(evos []models.Evolution, pokemonID int) map[string]any {
	return map[string]any{
		"url": "/api/v2/evolution-chain/" + strconv.Itoa(pokemonID) + "/",
	}
}

func evoNumID(e models.Evolution) string {
	numID := "0"
	if e.Number != nil {
		numID = strings.TrimLeft(strings.TrimPrefix(*e.Number, "#"), "0")
		if numID == "" {
			numID = "0"
		}
	}
	return numID
}

func buildEvolutionTree(evos []models.Evolution) map[string]any {
	if len(evos) == 0 {
		return map[string]any{
			"species":    map[string]any{"name": "", "url": ""},
			"evolves_to": []any{},
		}
	}

	// Build nodes and index by name
	type evoNode struct {
		data     map[string]any
		name     string
		children []int
	}
	nodes := make([]evoNode, len(evos))
	nameToIdx := map[string]int{}

	for i, e := range evos {
		details := []map[string]any{}
		if e.EvolvesVia != nil && *e.EvolvesVia != "" {
			details = append(details, map[string]any{
				"trigger": map[string]string{"name": "level-up"},
			})
		}
		numID := evoNumID(e)
		nodes[i] = evoNode{
			name: e.Name,
			data: map[string]any{
				"species": map[string]any{
					"name": strings.ToLower(e.Name),
					"url":  "/api/v2/pokemon-species/" + numID + "/",
				},
				"evolution_details": details,
				"evolves_to":        []any{},
			},
		}
		nameToIdx[e.Name] = i
	}

	// Wire parent→child using evolves_from
	var roots []int
	for i, e := range evos {
		if e.EvolvesFrom == nil || *e.EvolvesFrom == "" {
			roots = append(roots, i)
		} else if parentIdx, ok := nameToIdx[*e.EvolvesFrom]; ok {
			nodes[parentIdx].children = append(nodes[parentIdx].children, i)
		} else {
			roots = append(roots, i)
		}
	}

	// Recursively assemble the tree
	var build func(idx int) map[string]any
	build = func(idx int) map[string]any {
		n := nodes[idx]
		childMaps := make([]any, len(n.children))
		for i, ci := range n.children {
			childMaps[i] = build(ci)
		}
		n.data["evolves_to"] = childMaps
		return n.data
	}

	if len(roots) > 0 {
		return build(roots[0])
	}
	return build(0)
}
