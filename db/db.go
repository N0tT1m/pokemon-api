package db

import (
	"context"
	"fmt"
	"os"

	"github.com/jackc/pgx/v5/pgxpool"
)

var Pool *pgxpool.Pool

func Connect(ctx context.Context) error {
	uri := os.Getenv("DATABASE_URI")
	if uri == "" {
		uri = "postgresql://pokedex:pokedex@localhost:5432/pokedex"
	}

	pool, err := pgxpool.New(ctx, uri)
	if err != nil {
		return fmt.Errorf("unable to connect to database: %w", err)
	}
	if err := pool.Ping(ctx); err != nil {
		return fmt.Errorf("unable to ping database: %w", err)
	}
	Pool = pool
	return nil
}
