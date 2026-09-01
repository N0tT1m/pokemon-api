//go:build !sqlite

package db

import (
	"reflect"
	"testing"

	"github.com/N0tT1m/pokemon-api/models"
	"github.com/jackc/pgx/v5/pgtype"
)

// TestPgxScansTextArrayIntoStrArray pins the assumption that makes the shared
// core work: models.StrArray carries no Scan method in the Postgres build, so
// pgx must reach it through its underlying []string type. If a future change
// gives StrArray a Scanner in this build, or pgx drops the reflection-based
// wrap, every array column would silently fail to decode — this catches that
// without needing a live server.
func TestPgxScansTextArrayIntoStrArray(t *testing.T) {
	m := pgtype.NewMap()

	for _, format := range []int16{pgtype.TextFormatCode, pgtype.BinaryFormatCode} {
		cases := []struct {
			name string
			src  []string
		}{
			{"multiple elements", []string{"Water", "Ice"}},
			{"single element", []string{"Water"}},
			{"empty array", []string{}},
			{"element with comma", []string{"Water 1", "Field, Fairy"}},
		}

		for _, c := range cases {
			encoded, err := m.Encode(pgtype.TextArrayOID, format, c.src, nil)
			if err != nil {
				t.Fatalf("%s/format=%d: encode: %v", c.name, format, err)
			}

			var got models.StrArray
			if err := m.Scan(pgtype.TextArrayOID, format, encoded, &got); err != nil {
				t.Fatalf("%s/format=%d: scan into StrArray: %v", c.name, format, err)
			}

			want := models.StrArray(c.src)
			if !reflect.DeepEqual(got, want) {
				t.Errorf("%s/format=%d: got %#v, want %#v", c.name, format, got, want)
			}
		}
	}
}

// TestPgxScansNullTextArray confirms a NULL array column yields a nil slice
// rather than an error, matching the SQLite build's behaviour.
func TestPgxScansNullTextArray(t *testing.T) {
	m := pgtype.NewMap()

	var got models.StrArray
	if err := m.Scan(pgtype.TextArrayOID, pgtype.TextFormatCode, nil, &got); err != nil {
		t.Fatalf("scan NULL into StrArray: %v", err)
	}
	if got != nil {
		t.Errorf("got %#v, want nil", got)
	}
}
