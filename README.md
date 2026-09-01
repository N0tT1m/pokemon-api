# Pokemon API

[![CI](https://github.com/N0tT1m/pokemon-api/actions/workflows/ci.yml/badge.svg)](https://github.com/N0tT1m/pokemon-api/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A read-only, PokeAPI-compatible HTTP API for Pokemon data, written in Go. It
serves the usual species/moves/abilities/items data on [PokeAPI][pokeapi]-shaped
routes, and adds game-specific data that PokeAPI does not carry — raid
rotations, trainer teams, mass outbreaks, version exclusives, in-game trades,
TM locations, Z-moves and more.

This is the backend for the [pokedex][pokedex] Flutter app.

[pokeapi]: https://pokeapi.co/
[pokedex]: https://github.com/N0tT1m/pokedex

## Screenshots

The API serves its own documentation from the binary — no separate docs site to
deploy, and the spec can never drift from the build it ships in.

### Reference — `/docs`

A [Redoc][redoc] reference generated from the OpenAPI spec, with all 75
endpoints grouped by area and response samples alongside each one.

![The Pokemon API reference at /docs](docs/images/reference.png)

### Playground — `/playground`

A [Swagger UI][swagger] playground for firing real requests at the API and
reading the responses in place.

![The Pokemon API playground at /playground](docs/images/playground.png)

[redoc]: https://github.com/Redocly/redoc
[swagger]: https://swagger.io/tools/swagger-ui/

## Highlights

- **75 endpoints** under `/api/v2`, most of them drop-in compatible with PokeAPI's response schema
- **Two backends, one codebase** — Postgres by default, or SQLite via the `sqlite` build tag, selected at compile time
- **Identifiers are flexible** — endpoints taking `{identifier}` accept a lowercase name (`pikachu`) or a National Dex number (`25`)
- **Pagination** — list endpoints take `limit`/`offset` and return PokeAPI's `{ count, results }` envelope
- **Self-documenting** — OpenAPI 3.1 spec plus an interactive playground, served by the API itself

## Quick start

```sh
git clone https://github.com/N0tT1m/pokemon-api.git
cd pokemon-api
docker compose up -d --build
```

That brings up Postgres and the API. The database starts empty; populate it with
the scrapers and the PokeAPI CSV load:

```sh
docker compose --profile csv-load up csv-loader   # PokeAPI CSV data
docker compose --profile crawl up crawler         # scraped game data
```

Then:

```sh
curl -sk https://localhost:158/healthz
curl -sk https://localhost:158/api/v2/pokemon/totodile | jq .
```

`docker-compose.yml` mounts `./certs` for TLS. For local work without
certificates, set `TLS_CERT=off` and talk to the plain HTTP port instead.

### Running it directly

```sh
export DATABASE_URI=postgresql://pokedex:pokedex@localhost:5432/pokedex
export TLS_CERT=off PORT_HTTP=8080
go run .
```

## Documentation

With the API running, the spec and playground are served from the binary:

| Path | What |
| --- | --- |
| `/docs` | Rendered API reference |
| `/playground` | Interactive request playground |
| `/openapi.yaml` | OpenAPI 3.1 spec (71 documented paths) |
| `/healthz` | Health check |

The spec also lives at [`docs/openapi.yaml`](docs/openapi.yaml).

## Configuration

All configuration is by environment variable.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URI` | — | Postgres connection string (default build) |
| `SQLITE_PATH` | — | Path to `pokedex.db` (`sqlite` build) |
| `SQLITE_IMMUTABLE` | — | Open the SQLite file read-only/immutable |
| `PORT` | `158` | HTTPS listen port |
| `PORT_HTTP` | `157` | HTTP listen port; `off` to disable |
| `TLS_CERT` | `/app/certs/fullchain.pem` | Certificate; `off` disables HTTPS entirely |
| `TLS_KEY` | `/app/certs/privkey.pem` | Private key |
| `LOG_LEVEL` / `DENDEN_LEVEL` | `info` | Log verbosity |

Set `TLS_CERT=off` when something upstream terminates TLS — Azure Container
Apps ingress, or any reverse proxy. `PORT_HTTP` must then name a real port, or
the server refuses to start with nothing listening.

## Endpoints

A sample of what is available beyond the PokeAPI-compatible core:

```
GET /api/v2/pokemon/{identifier}/type-defenses
GET /api/v2/pokemon/{identifier}/egg-move-parents
GET /api/v2/pokemon/{identifier}/game-locations
GET /api/v2/pokemon/competitive
GET /api/v2/pokemon/ev-targets
GET /api/v2/news/raids/active
GET /api/v2/trainer/{name}/team
GET /api/v2/version-exclusive?game=X&game_pair=Y
GET /api/v2/mass-outbreaks
GET /api/v2/in-game-trades
GET /api/v2/z-move
GET /api/v2/tm
```

See the OpenAPI spec for the full list with parameters and response shapes.

## Architecture

```
main.go                 routing, middleware, TLS + graceful shutdown
handlers/               HTTP handlers, shared across both backends
db/                     query layer; connection + SQL dialect per backend
models/                 response models
internal/denden/        structured logging
docs/                   OpenAPI spec, reference page, playground
pokemondb_scraper/      Scrapy spiders (Postgres ingest)
pokeapi_csv_loader/     PokeAPI CSV ingest
azure/                  SQLite build + Azure Container Apps deployment
```

The Postgres/SQLite split lives entirely behind a build tag — `handlers/` and
`db/queries.go` are shared verbatim, so a new endpoint works on both backends
with no extra effort. See [`azure/README.md`](azure/README.md) for the details
and the serverless deployment path.

## Data

The database is built, not committed — it is a 60–120MB derived artifact
rebuilt from upstream sources. Two ingest paths produce it:

- **Postgres** — `pokemondb_scraper/` (25 Scrapy spiders) and `pokeapi_csv_loader/`
- **SQLite** — `azure/pipeline/build_db.py`, a single entrypoint that runs the same spiders and CSV load into one self-contained file

See [`azure/pipeline/README.md`](azure/pipeline/README.md) for build flags and
faster iteration options.

## Development

```sh
go build ./...
go vet ./...
go test ./...
go build -tags sqlite ./...    # verify the SQLite backend too
```

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- Pokemon data from [PokeAPI](https://pokeapi.co/) and [PokemonDB](https://pokemondb.net/)
- Additional data from [Bulbapedia](https://bulbapedia.bulbagarden.net/)

## Disclaimer

Unofficial and fan-made. Pokemon and Pokemon character names are trademarks of
Nintendo. This project is not affiliated with or endorsed by Nintendo, Game
Freak, or The Pokemon Company.
