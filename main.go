package main

import (
	"context"
	"embed"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/N0tT1m/pokemon-api/db"
	"github.com/N0tT1m/pokemon-api/handlers"
	"github.com/N0tT1m/pokemon-api/internal/denden"
	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

//go:embed docs/openapi.yaml docs/index.html docs/playground.html
var docsFS embed.FS

func main() {
	ctx := context.Background()

	// Structured logging to stdout (den-den-mushi schema). When $DENDEN_HUB_HTTP
	// is set, lines are also shipped to the hub over HTTP; otherwise stdout only.
	denden.SetDefault("pokemon-api")

	if err := db.Connect(ctx); err != nil {
		slog.Error("failed to connect to database", "err", err)
		os.Exit(1)
	}
	defer db.Pool.Close()

	r := chi.NewRouter()
	r.Use(requestLogger)
	r.Use(middleware.Recoverer)
	r.Use(corsMiddleware)
	// Bound per-request work: cancels r.Context() (and therefore any in-flight DB
	// query using it) after 30s, well under the server's 60s WriteTimeout.
	r.Use(middleware.Timeout(30 * time.Second))

	// Liveness probe target for Container Apps / any orchestrator.
	r.Get("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		// Write can only fail on a dropped client connection; nothing to recover.
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	})

	// API documentation (Redoc reference + Swagger UI playground)
	r.Get("/docs", serveEmbedded("docs/index.html", "text/html; charset=utf-8"))
	r.Get("/playground", serveEmbedded("docs/playground.html", "text/html; charset=utf-8"))
	r.Get("/openapi.yaml", serveEmbedded("docs/openapi.yaml", "application/yaml; charset=utf-8"))

	// PokeAPI-compatible endpoints
	r.Get("/api/v2/pokemon", handlers.ListPokemon)
	r.Get("/api/v2/pokemon/competitive", handlers.ListPokemonCompetitive)
	r.Get("/api/v2/pokemon/ev-targets", handlers.GetEVTargets)
	r.Get("/api/v2/pokemon/{identifier}", handlers.GetPokemon)
	r.Get("/api/v2/pokemon/{identifier}/encounters", handlers.GetPokemonEncounters)
	r.Get("/api/v2/pokemon/{identifier}/moves", handlers.GetPokemonMoves)
	r.Get("/api/v2/pokemon/{identifier}/type-defenses", handlers.GetPokemonTypeDefenses)
	r.Get("/api/v2/pokemon-species/{identifier}", handlers.GetPokemonSpecies)
	r.Get("/api/v2/evolution-chain/{id}", handlers.GetEvolutionChain)
	r.Get("/api/v2/type", handlers.ListTypes)
	r.Get("/api/v2/type/{identifier}", handlers.GetType)
	r.Get("/api/v2/type/{identifier}/names", handlers.GetTypeNames)
	r.Get("/api/v2/item/{identifier}/names", handlers.GetItemNames)
	r.Get("/api/v2/move/{identifier}/names", handlers.GetMoveNames)
	r.Get("/api/v2/ability/{identifier}/names", handlers.GetAbilityNames)
	r.Get("/api/v2/generation/{id}", handlers.GetGeneration)

	// Classification & egg-group filters
	r.Get("/api/v2/pokemon-color", handlers.ListPokemonColors)
	r.Get("/api/v2/pokemon-color/{color}", handlers.GetPokemonColor)
	r.Get("/api/v2/pokemon-shape", handlers.ListPokemonShapes)
	r.Get("/api/v2/pokemon-shape/{shape}", handlers.GetPokemonShape)
	r.Get("/api/v2/pokemon-habitat", handlers.ListPokemonHabitats)
	r.Get("/api/v2/pokemon-habitat/{habitat}", handlers.GetPokemonHabitat)
	r.Get("/api/v2/egg-group", handlers.ListEggGroups)
	r.Get("/api/v2/egg-group/{name}", handlers.GetEggGroup)

	// PokeAPI-compatible pokedex endpoints
	r.Get("/api/v2/version-group/{name}", handlers.GetVersionGroup)
	r.Get("/api/v2/pokedex/{identifier}", handlers.GetPokedex)

	// Custom game-specific endpoints
	r.Get("/api/v2/pokedex/game/{game}", handlers.GetGamePokedex)
	r.Get("/api/v2/games", handlers.ListGames)

	// Reference database endpoints
	r.Get("/api/v2/item", handlers.ListItems)
	r.Get("/api/v2/item/{identifier}", handlers.GetItem)
	r.Get("/api/v2/item/{identifier}/locations", handlers.GetItemLocations)
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
	r.Get("/api/v2/pokemon/{identifier}/held-items", handlers.GetPokemonHeldItems)
	r.Get("/api/v2/pokemon/{identifier}/biology", handlers.GetPokemonBiologyHandler)
	r.Get("/api/v2/pokemon/{identifier}/game-locations", handlers.GetPokemonGameLocationsHandler)
	r.Get("/api/v2/pokemon/{identifier}/forms", handlers.GetPokemonForms)
	r.Get("/api/v2/pokemon/{identifier}/egg-move-parents", handlers.GetEggMoveParents)

	// TM location endpoints
	r.Get("/api/v2/tm", handlers.ListTmLocations)
	r.Get("/api/v2/tm/games", handlers.ListTmGames)

	// Item location browse endpoints
	r.Get("/api/v2/item-locations", handlers.ListItemLocationsByGame)
	r.Get("/api/v2/item-locations/games", handlers.ListItemLocationGames)

	// Location encounter endpoints
	r.Get("/api/v2/location/games", handlers.ListEncounterGames)
	r.Get("/api/v2/location/regions", handlers.ListRegions)
	r.Get("/api/v2/location/pokemon/{name}", handlers.GetPokemonLocationEncounters)
	r.Get("/api/v2/location/region/{region}/routes", handlers.ListRoutes)
	r.Get("/api/v2/location/region/{region}/route/{route}", handlers.GetRouteEncounters)

	// News / live event endpoints
	r.Get("/api/v2/news/raids", handlers.ListRaids)
	r.Get("/api/v2/news/raids/active", handlers.ListActiveRaids)
	r.Get("/api/v2/news/raids/{pokemon}", handlers.GetRaidByPokemon)

	// Classification, GO stats, contest stats
	r.Get("/api/v2/pokemon/{identifier}/classification", handlers.GetPokemonClassification)
	r.Get("/api/v2/pokemon/{identifier}/go", handlers.GetPokemonGoStats)
	r.Get("/api/v2/pokemon/{identifier}/contest-stats", handlers.GetPokemonContestStats)

	// Z-Moves
	r.Get("/api/v2/z-move", handlers.ListZMoves)
	r.Get("/api/v2/z-move/{name}", handlers.GetZMove)

	// In-game trades (?game=X)
	r.Get("/api/v2/in-game-trades", handlers.ListInGameTrades)

	// Event Pokemon (?name=X&game=X)
	r.Get("/api/v2/event-pokemon", handlers.ListEventPokemon)

	// Mass outbreaks (?game=X&region=X)
	r.Get("/api/v2/mass-outbreaks", handlers.ListMassOutbreaks)

	// Battle facilities (?game=X)
	r.Get("/api/v2/battle-facility", handlers.ListBattleFacilities)

	// Move tutors (?game=X&move=X)
	r.Get("/api/v2/move-tutor", handlers.ListMoveTutors)

	// Version exclusives (?game=X&game_pair=X)
	r.Get("/api/v2/version-exclusive", handlers.ListVersionExclusives)

	// Trainers (?game=X&role=X) and trainer teams
	r.Get("/api/v2/trainer", handlers.ListTrainers)
	r.Get("/api/v2/trainer/{name}/team", handlers.GetTrainerTeam)

	port := os.Getenv("PORT")
	if port == "" {
		port = "158"
	}

	// TLS_CERT=off disables the HTTPS listener entirely, for environments that
	// terminate TLS upstream — Azure Container Apps ingress, or any reverse
	// proxy. The plain HTTP listener then carries all traffic.
	certFile := os.Getenv("TLS_CERT")
	keyFile := os.Getenv("TLS_KEY")
	tlsEnabled := certFile != "off"
	if certFile == "" {
		certFile = "/app/certs/fullchain.pem"
	}
	if keyFile == "" {
		keyFile = "/app/certs/privkey.pem"
	}

	httpPort := os.Getenv("PORT_HTTP")
	if httpPort == "" {
		httpPort = "157"
	}
	if !tlsEnabled && httpPort == "off" {
		slog.Error("TLS_CERT=off requires PORT_HTTP to name a port, otherwise nothing would listen")
		os.Exit(1)
	}

	newServer := func(addr string) *http.Server {
		return &http.Server{
			Addr:              addr,
			Handler:           r,
			ReadHeaderTimeout: 10 * time.Second,
			ReadTimeout:       30 * time.Second,
			WriteTimeout:      60 * time.Second,
			IdleTimeout:       120 * time.Second,
		}
	}

	var httpSrv *http.Server
	if httpPort != "off" {
		httpSrv = newServer(":" + httpPort)
		go func() {
			slog.Info("starting HTTP server", "port", httpPort)
			if err := httpSrv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
				slog.Error("HTTP server error", "err", err)
			}
		}()
	}

	var tlsSrv *http.Server
	if tlsEnabled {
		tlsSrv = newServer(":" + port)
		go func() {
			slog.Info("starting HTTPS server", "port", port)
			if err := tlsSrv.ListenAndServeTLS(certFile, keyFile); err != nil && !errors.Is(err, http.ErrServerClosed) {
				slog.Error("HTTPS server error", "err", err)
				os.Exit(1)
			}
		}()
	}

	// Graceful shutdown on SIGINT / SIGTERM
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh
	slog.Info("shutdown signal received, draining connections")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if tlsSrv != nil {
		if err := tlsSrv.Shutdown(shutdownCtx); err != nil {
			slog.Error("HTTPS shutdown error", "err", err)
		}
	}
	if httpSrv != nil {
		if err := httpSrv.Shutdown(shutdownCtx); err != nil {
			slog.Error("HTTP shutdown error", "err", err)
		}
	}
	slog.Info("shutdown complete")
}

// requestLogger emits one structured log line per request via the default
// (den-den) slog logger, replacing chi's text-format middleware.Logger.
func requestLogger(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ww := middleware.NewWrapResponseWriter(w, r.ProtoMajor)
		start := time.Now()
		defer func() {
			slog.Info("request",
				"method", r.Method,
				"path", r.URL.Path,
				"status", ww.Status(),
				"bytes", ww.BytesWritten(),
				"duration_ms", time.Since(start).Milliseconds(),
				"remote", r.RemoteAddr,
			)
		}()
		next.ServeHTTP(ww, r)
	})
}

func serveEmbedded(path, contentType string) http.HandlerFunc {
	data, err := docsFS.ReadFile(path)
	if err != nil {
		slog.Error("embed: failed to read file", "path", path, "err", err)
		os.Exit(1)
	}
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", contentType)
		// Write can only fail on a dropped client connection; nothing to recover.
		_, _ = w.Write(data)
	}
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Wildcard is intentional: this is a public, read-only (GET/OPTIONS) API
		// that sends no credentials or cookies, so any origin may read it.
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
