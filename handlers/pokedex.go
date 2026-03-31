package handlers

import (
	"net/http"
	"strconv"
	"strings"

	"github.com/N0tT1m/pokemon-api/db"
	"github.com/go-chi/chi/v5"
)

// Mapping from PokeAPI-style version-group slugs to our DB game names.
var versionGroupToGame = map[string][]string{
	"red-blue":                        {"Red/Blue/Yellow"},
	"yellow":                          {"Red/Blue/Yellow"},
	"gold-silver":                     {"Gold/Silver/Crystal"},
	"crystal":                         {"Gold/Silver/Crystal"},
	"ruby-sapphire":                   {"Ruby/Sapphire/Emerald"},
	"emerald":                         {"Ruby/Sapphire/Emerald"},
	"firered-leafgreen":               {"FireRed/LeafGreen"},
	"diamond-pearl":                   {"Diamond/Pearl"},
	"platinum":                        {"Platinum"},
	"heartgold-soulsilver":            {"HeartGold/SoulSilver"},
	"black-white":                     {"Black/White"},
	"black-2-white-2":                 {"Black 2/White 2"},
	"x-y":                             {"X/Y"},
	"omega-ruby-alpha-sapphire":       {"Omega Ruby/Alpha Sapphire"},
	"sun-moon":                        {"Sun/Moon"},
	"ultra-sun-ultra-moon":            {"Ultra Sun/Ultra Moon"},
	"lets-go-pikachu-lets-go-eevee":   {"Let's Go Pikachu/Eevee"},
	"sword-shield":                    {"Sword/Shield"},
	"brilliant-diamond-shining-pearl": {"Brilliant Diamond/Shining Pearl"},
	"legends-arceus":                  {"Legends: Arceus"},
	"scarlet-violet":                  {"Scarlet/Violet"},
	"the-teal-mask":                   {"The Teal Mask"},
	"the-indigo-disk":                 {"The Indigo Disk"},
	"legends-z-a":                     {"Legends: Z-A"},
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
			writeError(w, 500, err.Error())
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

// Mapping from PokeAPI regional-dex names to our DB game names.
var regionToGame = map[string]string{
	"kanto":            "Red/Blue/Yellow",
	"original-johto":   "Gold/Silver/Crystal",
	"hoenn":            "Ruby/Sapphire/Emerald",
	"original-sinnoh":  "Diamond/Pearl",
	"extended-sinnoh":  "Platinum",
	"original-unova":   "Black/White",
	"updated-unova":    "Black 2/White 2",
	"kalos-central":    "X/Y",
	"kalos-coastal":    "X/Y",
	"kalos-mountain":   "X/Y",
	"original-alola":   "Sun/Moon",
	"updated-alola":    "Ultra Sun/Ultra Moon",
	"galar":            "Sword/Shield",
	"isle-of-armor":    "Sword/Shield",
	"crown-tundra":     "Sword/Shield",
	"hisui":            "Legends: Arceus",
	"paldea":           "Scarlet/Violet",
	"kitakami":         "The Teal Mask",
	"blueberry":        "The Indigo Disk",
}

func slugToGameName(slug string) string {
	// Check region names first (e.g. "kanto", "galar", "paldea")
	if game, ok := regionToGame[slug]; ok {
		return game
	}

	for vgSlug, games := range versionGroupToGame {
		dexSlug := strings.ToLower(strings.ReplaceAll(strings.ReplaceAll(games[0], " ", "-"), "/", "-"))
		if slug == dexSlug || slug == vgSlug {
			return games[0]
		}
	}
	return ""
}
