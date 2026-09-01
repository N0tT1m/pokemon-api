//go:build !sqlite

package db

import (
	"errors"
	"fmt"

	"github.com/jackc/pgx/v5"
)

// IsNotFound reports whether err is the driver's "no rows" sentinel, so callers
// can map a genuine miss to 404 while letting real failures surface as 500.
func IsNotFound(err error) bool {
	return errors.Is(err, pgx.ErrNoRows)
}

// The helpers in this file render the SQL constructs that differ between
// Postgres and SQLite. Query code calls them instead of inlining dialect
// syntax; dialect_sqlite.go provides the matching SQLite renderings.

// ArrayContains renders a predicate testing that array column col contains the
// value bound to placeholder ph (e.g. "$1"), case-sensitively.
func ArrayContains(col, ph string) string {
	return fmt.Sprintf("%s = ANY(%s)", ph, col)
}

// ArrayContainsFold is the case-insensitive form of ArrayContains.
func ArrayContainsFold(col, ph string) string {
	return fmt.Sprintf("EXISTS (SELECT 1 FROM UNNEST(%s) e WHERE LOWER(e) = LOWER(%s))", col, ph)
}

// ArrayDistinct renders a complete query yielding each distinct non-empty
// element of array column col across table, ordered ascending.
func ArrayDistinct(table, col string) string {
	return fmt.Sprintf(
		"SELECT DISTINCT e FROM %s, UNNEST(%s) e WHERE e IS NOT NULL AND e <> '' ORDER BY e",
		table, col,
	)
}

// LikeFold renders a case-insensitive LIKE of col against placeholder ph.
func LikeFold(col, ph string) string {
	return fmt.Sprintf("%s ILIKE %s", col, ph)
}

// UTCTimestamp renders timestamp column col as an ISO-8601 UTC string.
func UTCTimestamp(col string) string {
	return fmt.Sprintf(`to_char(%s AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')`, col)
}

// CastText renders expr cast to text.
func CastText(expr string) string {
	return expr + "::TEXT"
}
