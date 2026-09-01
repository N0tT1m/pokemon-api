//go:build !sqlite

package db

import (
	"context"
	"fmt"
	"os"

	"github.com/jackc/pgx/v5/pgxpool"
)

// pgPool adapts *pgxpool.Pool to Querier. pgx.Rows already satisfies Rows, so
// Query can hand it back untouched.
type pgPool struct{ pool *pgxpool.Pool }

func (p pgPool) Query(ctx context.Context, sql string, args ...any) (Rows, error) {
	return p.pool.Query(ctx, sql, args...)
}

func (p pgPool) QueryRow(ctx context.Context, sql string, args ...any) Row {
	return p.pool.QueryRow(ctx, sql, args...)
}

func (p pgPool) Exec(ctx context.Context, sql string, args ...any) error {
	_, err := p.pool.Exec(ctx, sql, args...)
	return err
}

func (p pgPool) Close() { p.pool.Close() }

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
	Pool = pgPool{pool: pool}
	return nil
}
