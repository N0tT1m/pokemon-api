//go:build sqlite

package db

import (
	"database/sql"
	"errors"
	"fmt"
)

// IsNotFound reports whether err is the driver's "no rows" sentinel, so callers
// can map a genuine miss to 404 while letting real failures surface as 500.
func IsNotFound(err error) bool {
	return errors.Is(err, sql.ErrNoRows)
}

// SQLite renderings of the dialect-specific constructs. See
// dialect_postgres.go for the contract each helper must satisfy.
//
// Array columns are TEXT holding a JSON array, so membership and expansion go
// through json_each() rather than Postgres' array operators.

// ArrayContains renders a predicate testing that array column col contains the
// value bound to placeholder ph (e.g. "$1"), case-sensitively.
func ArrayContains(col, ph string) string {
	return fmt.Sprintf("EXISTS (SELECT 1 FROM json_each(%s) WHERE value = %s)", col, ph)
}

// ArrayContainsFold is the case-insensitive form of ArrayContains.
func ArrayContainsFold(col, ph string) string {
	return fmt.Sprintf("EXISTS (SELECT 1 FROM json_each(%s) WHERE LOWER(value) = LOWER(%s))", col, ph)
}

// ArrayDistinct renders a complete query yielding each distinct non-empty
// element of array column col across table, ordered ascending.
func ArrayDistinct(table, col string) string {
	return fmt.Sprintf(
		"SELECT DISTINCT je.value FROM %s, json_each(%s.%s) je WHERE je.value IS NOT NULL AND je.value <> '' ORDER BY je.value",
		table, table, col,
	)
}

// LikeFold renders a case-insensitive LIKE of col against placeholder ph.
// SQLite's LIKE is already case-insensitive for ASCII, but folding both sides
// keeps behaviour identical for non-ASCII input.
func LikeFold(col, ph string) string {
	return fmt.Sprintf("LOWER(%s) LIKE LOWER(%s)", col, ph)
}

// UTCTimestamp renders timestamp column col as an ISO-8601 UTC string. The
// ingest pipeline already stores these as ISO-8601 text; strftime normalises
// the format and drops any fractional seconds.
func UTCTimestamp(col string) string {
	return fmt.Sprintf(`strftime('%%Y-%%m-%%dT%%H:%%M:%%SZ', %s)`, col)
}

// CastText renders expr cast to text.
func CastText(expr string) string {
	return fmt.Sprintf("CAST(%s AS TEXT)", expr)
}
