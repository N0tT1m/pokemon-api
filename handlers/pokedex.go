package handlers

import (
	"net/http"
	"strconv"
	"strings"

	"github.com/N0tT1m/pokemon-api/db"
	"github.com/go-chi/chi/v5"
)

// gameMapping is the canonical record for a single DB game name. The
// VersionGroups and Regions fields list every PokeAPI-style slug that should
// resolve to this game. Adding a new game means appending one entry here —
// the lookup maps below are derived in init().
type gameMapping struct {
	Game          string
	VersionGroups []string
	Regions       []string
}

var gameMappings = []gameMapping{
	{"Red/Blue/Yellow", []string{"red-blue", "yellow"}, []string{"kanto"}},
	{"Gold/Silver/Crystal", []string{"gold-silver", "crystal"}, []string{"original-johto"}},
	{"Ruby/Sapphire/Emerald", []string{"ruby-sapphire", "emerald"}, []string{"hoenn"}},
	{"FireRed/LeafGreen", []string{"firered-leafgreen"}, nil},
	{"Diamond/Pearl", []string{"diamond-pearl"}, []string{"original-sinnoh"}},
	{"Platinum", []string{"platinum"}, []string{"extended-sinnoh"}},
	{"HeartGold/SoulSilver", []string{"heartgold-soulsilver"}, nil},
	{"Black/White", []string{"black-white"}, []string{"original-unova"}},
	{"Black 2/White 2", []string{"black-2-white-2"}, []string{"updated-unova"}},
	{"X/Y", []string{"x-y"}, []string{"kalos-central", "kalos-coastal", "kalos-mountain"}},
	{"Omega Ruby/Alpha Sapphire", []string{"omega-ruby-alpha-sapphire"}, nil},
	{"Sun/Moon", []string{"sun-moon"}, []string{"original-alola"}},
	{"Ultra Sun/Ultra Moon", []string{"ultra-sun-ultra-moon"}, []string{"updated-alola"}},
	{"Let's Go Pikachu/Eevee", []string{"lets-go-pikachu-lets-go-eevee"}, nil},
	{"Sword/Shield", []string{"sword-shield"}, []string{"galar", "isle-of-armor", "crown-tundra"}},
	{"Brilliant Diamond/Shining Pearl", []string{"brilliant-diamond-shining-pearl"}, nil},
	{"Legends: Arceus", []string{"legends-arceus"}, []string{"hisui"}},
	{"Scarlet/Violet", []string{"scarlet-violet"}, []string{"paldea"}},
	{"The Teal Mask", []string{"the-teal-mask"}, []string{"kitakami"}},
	{"The Indigo Disk", []string{"the-indigo-disk"}, []string{"blueberry"}},
	{"Legends: Z-A", []string{"legends-z-a"}, nil},
}

// Derived lookups, populated in init().
var (
	versionGroupToGame = map[string][]string{}
	regionToGame       = map[string]string{}
	dexSlugToGame      = map[string]string{}
)

func init() {
	for _, m := range gameMappings {
		dexSlug := strings.ToLower(strings.ReplaceAll(strings.ReplaceAll(m.Game, " ", "-"), "/", "-"))
		dexSlugToGame[dexSlug] = m.Game
		for _, vg := range m.VersionGroups {
			versionGroupToGame[vg] = []string{m.Game}
			dexSlugToGame[vg] = m.Game
		}
		for _, region := range m.Regions {
			regionToGame[region] = m.Game
		}
	}
}

// Pokedex name registry: maps pokedex ID/name to the game + dex type.
// We generate pokedex IDs as: regional dex = game-specific ID, national = 1
type pokedexRef struct {
	ID   int
	Name string
	Game string
	Type string // "regional" or "national"
}

// GET /api/v2/version-group/{name}
// Returns pokedex references that the game_version_filter expects.
func GetVersionGroup(w http.ResponseWriter, r *http.Request) {
	slug := chi.URLParam(r, "name")

	games, ok := versionGroupToGame[slug]
	if !ok {
		writeError(w, 404, "Version group not found: "+slug)
		return
	}

	pokedexes := []map[string]any{}

	for _, game := range games {
		// Check if regional dex data exists
		regional, _ := db.GetRegionalDex(r.Context(), game)
		if len(regional) > 0 {
			dexSlug := strings.ToLower(strings.ReplaceAll(strings.ReplaceAll(game, " ", "-"), "/", "-"))
			pokedexes = append(pokedexes, map[string]any{
				"name": dexSlug,
				"url":  "/api/v2/pokedex/" + dexSlug + "/",
			})
		}

		// Check if national dex data exists
		national, _ := db.GetGameNationalDex(r.Context(), game)
		if len(national) > 0 {
			pokedexes = append(pokedexes, map[string]any{
				"name": "national",
				"url":  "/api/v2/pokedex/1/",
			})
		}
	}

	// Fallback: if no game-specific dex data, offer the national dex from the pokemon table
	if len(pokedexes) == 0 {
		pokedexes = append(pokedexes, map[string]any{
			"name": "national",
			"url":  "/api/v2/pokedex/1/",
		})
	}

	writeJSON(w, 200, map[string]any{
		"name":      slug,
		"pokedexes": pokedexes,
	})
}

// GET /api/v2/pokedex/{identifier}
// Returns pokemon_entries in PokeAPI format.
// identifier can be "1" or "national" for national dex, or a game slug for regional.
func GetPokedex(w http.ResponseWriter, r *http.Request) {
	identifier := chi.URLParam(r, "identifier")

	// National dex
	if identifier == "1" || identifier == "national" {
		// Get the game from query param if specified, otherwise return full national
		game := r.URL.Query().Get("game")
		if game != "" {
			entries, _ := db.GetGameNationalDex(r.Context(), game)
			pokemonEntries := make([]map[string]any, len(entries))
			for i, e := range entries {
				pokemonEntries[i] = map[string]any{
					"entry_number": e.NationalNo,
					"pokemon_species": map[string]any{
						"name": strings.ToLower(e.PokemonName),
						"url":  "/api/v2/pokemon-species/" + strconv.Itoa(e.NationalNo) + "/",
					},
				}
			}
			writeJSON(w, 200, map[string]any{
				"name":            "national",
				"pokemon_entries": pokemonEntries,
			})
			return
		}

		// Full national dex from pokemon table
		entries, _, err := db.GetAllPokemon(r.Context(), 2000, 0)
		if err != nil {
			writeServerError(w, r, err)
			return
		}
		pokemonEntries := make([]map[string]any, len(entries))
		for i, e := range entries {
			numID := 0
			if e.NationalNo != nil {
				numID, _ = strconv.Atoi(strings.TrimLeft(*e.NationalNo, "0"))
			}
			pokemonEntries[i] = map[string]any{
				"entry_number": numID,
				"pokemon_species": map[string]any{
					"name": strings.ToLower(e.Name),
					"url":  "/api/v2/pokemon-species/" + strconv.Itoa(numID) + "/",
				},
			}
		}
		writeJSON(w, 200, map[string]any{
			"name":            "national",
			"pokemon_entries": pokemonEntries,
		})
		return
	}

	// Regional dex — identifier is a game slug like "brilliant-diamond-shining-pearl"
	// Convert slug back to game name
	game := slugToGameName(identifier)
	if game == "" {
		writeError(w, 404, "Pokedex not found: "+identifier)
		return
	}

	entries, _ := db.GetRegionalDex(r.Context(), game)
	pokemonEntries := make([]map[string]any, len(entries))
	for i, e := range entries {
		// Look up national dex number for the sprite URL
		numID := 0
		p, err := db.GetPokemonByName(r.Context(), e.PokemonName)
		if err == nil && p.NationalNo != nil {
			numID, _ = strconv.Atoi(strings.TrimLeft(*p.NationalNo, "0"))
		}

		pokemonEntries[i] = map[string]any{
			"entry_number": e.DexNumber,
			"pokemon_species": map[string]any{
				"name": strings.ToLower(e.PokemonName),
				"url":  "/api/v2/pokemon-species/" + strconv.Itoa(numID) + "/",
			},
		}
	}

	dexName := strings.ReplaceAll(identifier, "-", " ")
	writeJSON(w, 200, map[string]any{
		"name":            dexName,
		"pokemon_entries": pokemonEntries,
	})
}

// slugToGameName resolves any region, version-group, or dex slug to a DB game
// name. All three lookup maps are derived from gameMappings in init().
func slugToGameName(slug string) string {
	if game, ok := regionToGame[slug]; ok {
		return game
	}
	if game, ok := dexSlugToGame[slug]; ok {
		return game
	}
	return ""
}
