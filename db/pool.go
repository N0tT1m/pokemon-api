package db

import "context"

// Row is the single-row result of QueryRow.
type Row interface {
	Scan(dest ...any) error
}

// Rows iterates a multi-row result. The signatures deliberately match pgx's
// pgx.Rows so query code reads identically on both backends — in particular
// Close() returns nothing, and the SQLite adapter absorbs sql.Rows' error.
type Rows interface {
	Next() bool
	Scan(dest ...any) error
	Close()
	Err() error
}

// Querier is the backend-agnostic database handle every query in this package
// runs against. It is implemented by a pgx pool in the default build and by
// database/sql over SQLite under the `sqlite` build tag.
type Querier interface {
	Query(ctx context.Context, sql string, args ...any) (Rows, error)
	QueryRow(ctx context.Context, sql string, args ...any) Row
	Exec(ctx context.Context, sql string, args ...any) error
	Close()
}

// Pool is populated by Connect, whose implementation is selected by build tag.
var Pool Querier
