package main

import (
	"context"
	"log"
	"net/http"
	"os"

	"github.com/N0tT1m/pokedex-api/db"
	"github.com/N0tT1m/pokedex-api/handlers"
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
