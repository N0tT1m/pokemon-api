package models

// StrArray is a list of strings that lives in a Postgres TEXT[] column by
// default and, under the `sqlite` build tag, in a TEXT column holding a JSON
// array. Its underlying type is []string, so it marshals to JSON identically
// either way and the API response shape is unchanged.
//
// Under the default (Postgres) build it has no Scan method, which lets pgx use
// its native array codec. The sqlite build adds one — see strarray_sqlite.go.
type StrArray []string
