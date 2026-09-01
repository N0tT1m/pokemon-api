package handlers

import "testing"

func TestParseGenderRate(t *testing.T) {
	cases := []struct {
		in   string
		want int
	}{
		// Symbol form, as used by earlier scrapes.
		{"87.5% ♂, 12.5% ♀", 1},
		{"75% ♂, 25% ♀", 2},
		{"50% ♂, 50% ♀", 4},
		{"12.5% ♂, 87.5% ♀", 7},
		{"0% ♂, 100% ♀", 8},

		// Worded form, exactly as pokemondb renders it and as it is stored in
		// the database — including the doubled space the scraper's text-node
		// join produces. These are every distinct ratio present across the
		// 1025 rows.
		{"87.5% male ,  12.5% female", 1},
		{"75% male ,  25% female", 2},
		{"50% male ,  50% female", 4},
		{"25% male ,  75% female", 6},
		{"12.5% male ,  87.5% female", 7},
		{"0% male ,  100% female", 8},
		{"100% male ,  0% female", 0},
		{"87.5% male, 12.5% female", 1}, // normalized spacing

		// Genderless species and missing data.
		{"Genderless", -1},
		{"—", -1},
		{"", -1},
		{"no female marker", -1},
	}
	for _, c := range cases {
		if got := parseGenderRate(c.in); got != c.want {
			t.Errorf("parseGenderRate(%q) = %d, want %d", c.in, got, c.want)
		}
	}
}

func TestParseEVYield(t *testing.T) {
	m := parseEVYield("2 Sp. Atk, 1 Speed")
	if m["special-attack"] != 2 {
		t.Errorf("special-attack = %d, want 2", m["special-attack"])
	}
	if m["speed"] != 1 {
		t.Errorf("speed = %d, want 1", m["speed"])
	}
	if m["hp"] != 0 {
		t.Errorf("hp = %d, want 0", m["hp"])
	}

	none := parseEVYield("None")
	for k, v := range none {
		if v != 0 {
			t.Errorf("parseEVYield(None)[%q] = %d, want 0", k, v)
		}
	}
}

func TestParseHeightToDecimeters(t *testing.T) {
	cases := []struct {
		in   string
		want int
	}{
		{"0.7 m (2'04\")", 7},
		{"1.7 m", 17},
		{"0.2 m", 2},
		{"garbage", 0},
	}
	for _, c := range cases {
		if got := parseHeightToDecimeters(c.in); got != c.want {
			t.Errorf("parseHeightToDecimeters(%q) = %d, want %d", c.in, got, c.want)
		}
	}
}

func TestParseWeightToHectograms(t *testing.T) {
	cases := []struct {
		in   string
		want int
	}{
		{"6.9 kg (15.2 lbs)", 69},
		{"90.5 kg", 905},
		{"garbage", 0},
	}
	for _, c := range cases {
		if got := parseWeightToHectograms(c.in); got != c.want {
			t.Errorf("parseWeightToHectograms(%q) = %d, want %d", c.in, got, c.want)
		}
	}
}

func TestParseIntOrNil(t *testing.T) {
	if v := parseIntOrNil("45 (5.9% ...)"); v != 45 {
		t.Errorf("parseIntOrNil = %v, want 45", v)
	}
	if v := parseIntOrNil(""); v != nil {
		t.Errorf("parseIntOrNil(\"\") = %v, want nil", v)
	}
	if v := parseIntOrNil("N/A"); v != nil {
		t.Errorf("parseIntOrNil(N/A) = %v, want nil", v)
	}
}

func TestToAPIName(t *testing.T) {
	cases := map[string]string{
		"Mr. Mime":    "mr.-mime",
		"Ho Oh":       "ho-oh",
		"  Pikachu  ": "pikachu",
	}
	for in, want := range cases {
		if got := toAPIName(in); got != want {
			t.Errorf("toAPIName(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestSpeciesSlug(t *testing.T) {
	cases := map[string]string{
		// Punctuation PokeAPI drops.
		"Farfetch'd": "farfetchd",
		"Sirfetch'd": "sirfetchd",
		"Mr. Mime":   "mr-mime",
		"Mr. Rime":   "mr-rime",
		"Mime Jr.":   "mime-jr",
		"Type: Null": "type-null",
		"Flabébé":    "flabebe",

		// Not derivable from the stored name; covered by the override map.
		"Nidoran♀ (female)": "nidoran-f",
		"Nidoran♂ (male)":   "nidoran-m",

		// Ordinary names must be untouched beyond lowercasing and hyphenation.
		"Pikachu":    "pikachu",
		"Totodile":   "totodile",
		"Ho Oh":      "ho-oh",
		"Porygon-Z":  "porygon-z",
		"  Squirtle": "squirtle",
	}
	for in, want := range cases {
		if got := speciesSlug(in); got != want {
			t.Errorf("speciesSlug(%q) = %q, want %q", in, got, want)
		}
	}
}

// TestSpeciesSlugRoundTrip guards the two directions against drifting apart:
// every slug the override map produces must map back to the same stored name.
func TestSpeciesSlugRoundTrip(t *testing.T) {
	for dbName, slug := range speciesSlugOverrides {
		back, ok := dbNameForSlug[slug]
		if !ok {
			t.Errorf("slug %q has no dbNameForSlug entry", slug)
			continue
		}
		if back != dbName {
			t.Errorf("dbNameForSlug[%q] = %q, want %q", slug, back, dbName)
		}
	}
	if len(dbNameForSlug) != len(speciesSlugOverrides) {
		t.Errorf("maps differ in size: %d vs %d", len(dbNameForSlug), len(speciesSlugOverrides))
	}
}
