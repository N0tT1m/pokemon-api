package handlers

import (
	"net/http"
	"strings"

	"github.com/N0tT1m/pokemon-api/db"
	"github.com/N0tT1m/pokemon-api/models"
	"github.com/go-chi/chi/v5"
)

// GET /api/v2/news/raids
// Returns all scraped raid events, active ones first.
func ListRaids(w http.ResponseWriter, r *http.Request) {
	events, err := db.GetAllRaidEvents(r.Context())
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if events == nil {
		events = []models.RaidEvent{}
	}
	writeJSON(w, 200, map[string]any{
		"count":   len(events),
		"results": events,
	})
}

// GET /api/v2/news/raids/active
// Returns only raids currently marked as active.
func ListActiveRaids(w http.ResponseWriter, r *http.Request) {
	events, err := db.GetActiveRaidEvents(r.Context())
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if events == nil {
		events = []models.RaidEvent{}
	}
	writeJSON(w, 200, map[string]any{
		"count":   len(events),
		"results": events,
	})
}

// GET /api/v2/news/raids/{pokemon}
// Returns all raid events for a specific Pokemon plus the recommended counters.
// Optional query param: ?tera_type=Dragon
func GetRaidByPokemon(w http.ResponseWriter, r *http.Request) {
	pokemon := chi.URLParam(r, "pokemon")
	teraType := strings.TrimSpace(r.URL.Query().Get("tera_type"))

	events, err := db.GetRaidEventsByPokemon(r.Context(), pokemon)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if len(events) == 0 {
		writeError(w, 404, "No raid events found for "+pokemon)
		return
	}

	counters, err := db.GetRaidCounters(r.Context(), pokemon, teraType)
	if err != nil {
		writeServerError(w, r, err)
		return
	}
	if counters == nil {
		counters = []models.RaidCounter{}
	}

	writeJSON(w, 200, map[string]any{
		"pokemon":  events[0].PokemonName,
		"events":   events,
		"counters": counters,
	})
}
