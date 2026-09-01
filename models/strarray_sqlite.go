//go:build sqlite

package models

import (
	"database/sql/driver"
	"encoding/json"
	"fmt"
)

// Scan decodes the JSON array text that the SQLite build stores for array
// columns. A NULL or empty column yields a nil slice, matching how pgx
// reports an absent Postgres array.
func (a *StrArray) Scan(src any) error {
	if src == nil {
		*a = nil
		return nil
	}

	var raw []byte
	switch v := src.(type) {
	case []byte:
		raw = v
	case string:
		raw = []byte(v)
	default:
		return fmt.Errorf("models: cannot scan %T into StrArray", src)
	}

	if len(raw) == 0 {
		*a = nil
		return nil
	}

	var out []string
	if err := json.Unmarshal(raw, &out); err != nil {
		return fmt.Errorf("models: decoding StrArray from %q: %w", raw, err)
	}
	*a = out
	return nil
}

// Value encodes the slice as a JSON array. A nil slice becomes "[]" rather
// than NULL so that json_each() in the dialect helpers always has an array to
// walk.
func (a StrArray) Value() (driver.Value, error) {
	if a == nil {
		return "[]", nil
	}
	b, err := json.Marshal([]string(a))
	if err != nil {
		return nil, fmt.Errorf("models: encoding StrArray: %w", err)
	}
	return string(b), nil
}
