package main

import (
	"context"
	"log"
	"net/http"
	"os"

	"github.com/N0tT1m/pokemon-api/db"
	"github.com/N0tT1m/pokemon-api/handlers"
	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

func main() {
	ctx := context.Background()

	if err := db.Connect(ctx); err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Pool.Close()

	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(corsMiddleware)

	// PokeAPI-compatible endpoints
	r.Get("/api/v2/pokemon", handlers.ListPokemon)
	r.Get("/api/v2/pokemon/{identifier}", handlers.GetPokemon)
	r.Get("/api/v2/pokemon/{identifier}/encounters", handlers.GetPokemonEncounters)
	r.Get("/api/v2/pokemon/{identifier}/moves", handlers.GetPokemonMoves)
	r.Get("/api/v2/pokemon/{identifier}/type-defenses", handlers.GetPokemonTypeDefenses)
	r.Get("/api/v2/pokemon-species/{identifier}", handlers.GetPokemonSpecies)
	r.Get("/api/v2/evolution-chain/{id}", handlers.GetEvolutionChain)

	// PokeAPI-compatible pokedex endpoints
	r.Get("/api/v2/version-group/{name}", handlers.GetVersionGroup)
	r.Get("/api/v2/pokedex/{identifier}", handlers.GetPokedex)

	// Custom game-specific endpoints
	r.Get("/api/v2/pokedex/game/{game}", handlers.GetGamePokedex)
	r.Get("/api/v2/games", handlers.ListGames)

	// Reference database endpoints
	r.Get("/api/v2/item", handlers.ListItems)
	r.Get("/api/v2/item/{identifier}", handlers.GetItem)
	r.Get("/api/v2/move", handlers.ListMoves)
	r.Get("/api/v2/move/{identifier}", handlers.GetMove)
	r.Get("/api/v2/ability", handlers.ListAbilities)
	r.Get("/api/v2/ability/{identifier}", handlers.GetAbility)
	r.Get("/api/v2/nature", handlers.ListNatures)
	r.Get("/api/v2/berry", handlers.ListBerries)
	r.Get("/api/v2/berry/{identifier}", handlers.GetBerry)
	r.Get("/api/v2/pokemon/{identifier}/flavor-text", handlers.GetPokemonFlavorText)
	r.Get("/api/v2/pokemon/{identifier}/names", handlers.GetPokemonNames)
	r.Get("/api/v2/pokemon/{identifier}/sprites-all", handlers.GetPokemonSprites)

	// Location encounter endpoints
	r.Get("/api/v2/location/regions", handlers.ListRegions)
	r.Get("/api/v2/location/pokemon/{name}", handlers.GetPokemonLocationEncounters)
	r.Get("/api/v2/location/region/{region}/routes", handlers.ListRoutes)
	r.Get("/api/v2/location/region/{region}/route/{route}", handlers.GetRouteEncounters)

	port := os.Getenv("PORT")
	if port == "" {
		port = "158"
	}

	certFile := os.Getenv("TLS_CERT")
	keyFile := os.Getenv("TLS_KEY")
	if certFile == "" {
		certFile = "/app/certs/fullchain.pem"
	}
	if keyFile == "" {
		keyFile = "/app/certs/privkey.pem"
	}

	log.Printf("Starting HTTPS server on :%s", port)
	log.Fatal(http.ListenAndServeTLS(":"+port, certFile, keyFile, r))
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		if r.Method == "OPTIONS" {
			w.WriteHeader(204)
			return
		}
		next.ServeHTTP(w, r)
	})
}
