//go:build sqlite

package db

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"runtime"
	"strings"

	_ "modernc.org/sqlite"
)

// sqliteDB adapts *sql.DB to Querier.
type sqliteDB struct{ db *sql.DB }

// sqliteRows wraps *sql.Rows so Close() matches the Rows interface, which
// mirrors pgx and returns nothing.
type sqliteRows struct{ rows *sql.Rows }

func (r sqliteRows) Next() bool             { return r.rows.Next() }
func (r sqliteRows) Scan(dest ...any) error { return r.rows.Scan(dest...) }
func (r sqliteRows) Close()                 { _ = r.rows.Close() }
func (r sqliteRows) Err() error             { return r.rows.Err() }

func (d sqliteDB) Query(ctx context.Context, query string, args ...any) (Rows, error) {
	rows, err := d.db.QueryContext(ctx, rewritePlaceholders(query), args...)
	if err != nil {
		return nil, err
	}
	return sqliteRows{rows: rows}, nil
}

func (d sqliteDB) QueryRow(ctx context.Context, query string, args ...any) Row {
	return d.db.QueryRowContext(ctx, rewritePlaceholders(query), args...)
}

func (d sqliteDB) Exec(ctx context.Context, query string, args ...any) error {
	_, err := d.db.ExecContext(ctx, rewritePlaceholders(query), args...)
	return err
}

func (d sqliteDB) Close() { _ = d.db.Close() }

// rewritePlaceholders converts Postgres $N placeholders to SQLite's ?N ordinal
// form. Left as-is, SQLite treats $1 as a *named* parameter and assigns
// indexes by order of first appearance, which silently misbinds any query that
// repeats or reorders its placeholders. Text inside single-quoted literals is
// left alone.
func rewritePlaceholders(q string) string {
	if !strings.Contains(q, "$") {
		return q
	}

	var b strings.Builder
	b.Grow(len(q))
	inLiteral := false
	for i := 0; i < len(q); i++ {
		c := q[i]
		switch {
		case c == '\'':
			inLiteral = !inLiteral
			b.WriteByte(c)
		case c == '$' && !inLiteral && i+1 < len(q) && q[i+1] >= '0' && q[i+1] <= '9':
			b.WriteByte('?')
		default:
			b.WriteByte(c)
		}
	}
	return b.String()
}

func Connect(ctx context.Context) error {
	path := os.Getenv("SQLITE_PATH")
	if path == "" {
		path = "/app/data/pokedex.db"
	}

	// The shipped database is baked into the container image and never written
	// at runtime, so open it read-only. immutable=1 additionally lets SQLite
	// skip all locking and change-detection, which is the bulk of the win for
	// a read-only workload. Set SQLITE_IMMUTABLE=0 when pointing at a file
	// that something else may be writing (e.g. during local ingest).
	immutable := "1"
	if os.Getenv("SQLITE_IMMUTABLE") == "0" {
		immutable = "0"
	}
	dsn := fmt.Sprintf("file:%s?mode=ro&immutable=%s&_pragma=busy_timeout(5000)", path, immutable)

	sdb, err := sql.Open("sqlite", dsn)
	if err != nil {
		return fmt.Errorf("unable to open sqlite database at %s: %w", path, err)
	}

	// Read-only connections don't contend, so allow one per core.
	conns := runtime.NumCPU()
	if conns < 4 {
		conns = 4
	}
	sdb.SetMaxOpenConns(conns)
	sdb.SetMaxIdleConns(conns)

	if err := sdb.PingContext(ctx); err != nil {
		return fmt.Errorf("unable to ping sqlite database at %s: %w", path, err)
	}
	Pool = sqliteDB{db: sdb}
	return nil
}
