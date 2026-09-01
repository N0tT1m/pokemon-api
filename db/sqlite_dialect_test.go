//go:build sqlite

package db

import (
	"context"
	"database/sql"
	"path/filepath"
	"reflect"
	"testing"

	"github.com/N0tT1m/pokemon-api/models"
	_ "modernc.org/sqlite"
)

// newTestDB writes a small SQLite fixture exercising the JSON-array columns and
// points Connect at it.
func newTestDB(t *testing.T) {
	t.Helper()

	path := filepath.Join(t.TempDir(), "pokedex.db")
	seed, err := sql.Open("sqlite", "file:"+path)
	if err != nil {
		t.Fatalf("open seed db: %v", err)
	}

	const ddl = `
		CREATE TABLE pokemon (
			name        TEXT PRIMARY KEY,
			types       TEXT NOT NULL DEFAULT '[]',
			egg_groups  TEXT NOT NULL DEFAULT '[]',
			abilities   TEXT NOT NULL DEFAULT '[]',
			url TEXT, national_no TEXT, species TEXT, height TEXT, weight TEXT,
			ev_yield TEXT, catch_rate TEXT, base_friendship TEXT, base_exp TEXT,
			growth_rate TEXT, gender_ratio TEXT, egg_cycles TEXT,
			hp INTEGER, attack INTEGER, defense INTEGER,
			sp_atk INTEGER, sp_def INTEGER, speed INTEGER, total INTEGER
		);
		CREATE TABLE raid_events (scraped_at TEXT);
		INSERT INTO pokemon (name, types, egg_groups) VALUES
			('Totodile',  '["Water"]',        '["Monster","Water 1"]'),
			('Feraligatr','["Water"]',        '["Monster","Water 1"]'),
			('Lapras',    '["Water","Ice"]',  '["Monster","Water 1"]'),
			('Pikachu',   '["Electric"]',     '["Field","Fairy"]'),
			('Missingno', '[]',               '[]');
		-- Species whose scraped names do not slugify to their PokeAPI
		-- identifier. Empty type/egg-group arrays keep them out of the
		-- membership and DISTINCT assertions above.
		INSERT INTO pokemon (name) VALUES
			('Farfetch''d'), ('Sirfetch''d'), ('Mr. Mime'), ('Mr. Rime'),
			('Mime Jr.'), ('Type: Null'), ('Flabébé'),
			('Nidoran♀ (female)'), ('Nidoran♂ (male)');
		INSERT INTO raid_events (scraped_at) VALUES ('2026-07-18T12:34:56Z');
	`
	if _, err := seed.Exec(ddl); err != nil {
		t.Fatalf("seed schema: %v", err)
	}
	if err := seed.Close(); err != nil {
		t.Fatalf("close seed db: %v", err)
	}

	t.Setenv("SQLITE_PATH", path)
	if err := Connect(context.Background()); err != nil {
		t.Fatalf("Connect: %v", err)
	}
	t.Cleanup(func() { Pool.Close() })
}

// TestArrayContainsFold covers the json_each membership rewrite of what was
// EXISTS (SELECT 1 FROM UNNEST(types) ...) on Postgres.
func TestArrayContainsFold(t *testing.T) {
	newTestDB(t)
	ctx := context.Background()

	got, err := GetPokemonByType(ctx, "water")
	if err != nil {
		t.Fatalf("GetPokemonByType: %v", err)
	}
	want := []string{"Feraligatr", "Lapras", "Totodile"}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("GetPokemonByType(water) = %v, want %v", got, want)
	}

	got, err = GetPokemonByEggGroup(ctx, "FIELD")
	if err != nil {
		t.Fatalf("GetPokemonByEggGroup: %v", err)
	}
	if want := []string{"Pikachu"}; !reflect.DeepEqual(got, want) {
		t.Errorf("GetPokemonByEggGroup(FIELD) = %v, want %v", got, want)
	}
}

// TestArrayDistinct covers the json_each expansion of SELECT DISTINCT unnest().
// Missingno's empty array must contribute nothing.
func TestArrayDistinct(t *testing.T) {
	newTestDB(t)

	got, err := GetAllEggGroups(context.Background())
	if err != nil {
		t.Fatalf("GetAllEggGroups: %v", err)
	}
	want := []string{"Fairy", "Field", "Monster", "Water 1"}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("GetAllEggGroups() = %v, want %v", got, want)
	}
}

// TestStrArrayScan confirms a JSON array column decodes into models.StrArray.
func TestStrArrayScan(t *testing.T) {
	newTestDB(t)

	var types models.StrArray
	err := Pool.QueryRow(context.Background(),
		`SELECT types FROM pokemon WHERE name = $1`, "Lapras").Scan(&types)
	if err != nil {
		t.Fatalf("scan StrArray: %v", err)
	}
	want := models.StrArray{"Water", "Ice"}
	if !reflect.DeepEqual(types, want) {
		t.Errorf("types = %v, want %v", types, want)
	}

	// An empty JSON array must scan to an empty (non-error) slice.
	var empty models.StrArray
	err = Pool.QueryRow(context.Background(),
		`SELECT types FROM pokemon WHERE name = $1`, "Missingno").Scan(&empty)
	if err != nil {
		t.Fatalf("scan empty StrArray: %v", err)
	}
	if len(empty) != 0 {
		t.Errorf("empty types = %v, want length 0", empty)
	}
}

// TestUTCTimestamp confirms the strftime rendering matches the ISO-8601 UTC
// shape the API contract promises.
func TestUTCTimestamp(t *testing.T) {
	newTestDB(t)

	var got string
	q := `SELECT ` + UTCTimestamp("scraped_at") + ` FROM raid_events`
	if err := Pool.QueryRow(context.Background(), q).Scan(&got); err != nil {
		t.Fatalf("scan timestamp: %v", err)
	}
	if want := "2026-07-18T12:34:56Z"; got != want {
		t.Errorf("UTCTimestamp = %q, want %q", got, want)
	}
}

// TestRewritePlaceholders guards the $N -> ?N conversion. Binding by name
// would misorder the reused and out-of-order cases.
func TestRewritePlaceholders(t *testing.T) {
	cases := []struct{ in, want string }{
		{"SELECT 1", "SELECT 1"},
		{"WHERE a = $1", "WHERE a = ?1"},
		{"WHERE a = $1 AND b = $2", "WHERE a = ?1 AND b = ?2"},
		{"WHERE a = $2 AND b = $1", "WHERE a = ?2 AND b = ?1"},
		{"WHERE a = $1 OR b = $1", "WHERE a = ?1 OR b = ?1"},
		{"WHERE a = '$1' AND b = $1", "WHERE a = '$1' AND b = ?1"},
		{"WHERE cost = '5$' AND b = $1", "WHERE cost = '5$' AND b = ?1"},
	}
	for _, c := range cases {
		if got := rewritePlaceholders(c.in); got != c.want {
			t.Errorf("rewritePlaceholders(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

// TestPlaceholderBinding proves reused and out-of-order placeholders actually
// bind correctly end-to-end, not just textually.
func TestPlaceholderBinding(t *testing.T) {
	newTestDB(t)

	var name string
	err := Pool.QueryRow(context.Background(),
		`SELECT name FROM pokemon WHERE name = $2 AND $1 = 'ignored'`,
		"ignored", "Totodile").Scan(&name)
	if err != nil {
		t.Fatalf("out-of-order bind: %v", err)
	}
	if name != "Totodile" {
		t.Errorf("name = %q, want %q", name, "Totodile")
	}
}

// TestGetPokemonByNameSlug covers the slug branch of GetPokemonByName. The
// scraper stores pokemondb's punctuation verbatim, so a caller asking for
// PokeAPI's "mr-mime" must still reach the row stored as "Mr. Mime". Before
// the slug branch existed every one of these returned no rows, and the API
// answered 404.
func TestGetPokemonByNameSlug(t *testing.T) {
	newTestDB(t)
	ctx := context.Background()

	cases := map[string]string{
		"farfetchd": "Farfetch'd",
		"sirfetchd": "Sirfetch'd",
		"mr-mime":   "Mr. Mime",
		"mr-rime":   "Mr. Rime",
		"mime-jr":   "Mime Jr.",
		"type-null": "Type: Null",
		"flabebe":   "Flabébé",

		// Exact stored names must keep working, in any case.
		"Totodile": "Totodile",
		"pikachu":  "Pikachu",
	}
	for slug, want := range cases {
		p, err := GetPokemonByName(ctx, slug)
		if err != nil {
			t.Errorf("GetPokemonByName(%q): %v", slug, err)
			continue
		}
		if p.Name != want {
			t.Errorf("GetPokemonByName(%q) = %q, want %q", slug, p.Name, want)
		}
	}

	// A genuinely absent species must still miss rather than resolve to
	// something adjacent.
	if _, err := GetPokemonByName(ctx, "not-a-pokemon"); err == nil {
		t.Error("GetPokemonByName(not-a-pokemon) succeeded, want an error")
	}
}
