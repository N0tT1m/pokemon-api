# Azure deployment (SQLite build)

This directory holds everything needed to run the Pokedex API on Azure
Container Apps with no database server. It is not a fork of the API — the Go
code is shared with the Postgres deployment and selected at compile time by the
`sqlite` build tag.

## How the two builds differ

| | default build | `-tags sqlite` |
|---|---|---|
| Backend | Postgres via pgx | SQLite via `modernc.org/sqlite` (pure Go, no cgo) |
| Array columns | `TEXT[]` | `TEXT` holding a JSON array |
| Data location | Postgres server | `pokedex.db` baked into the image, read-only |
| TLS | in-process, from `certs/` | terminated by Container Apps ingress |

Everything that differs lives behind a build tag:

```
models/strarray.go          StrArray type, shared
models/strarray_sqlite.go   its JSON Scanner (sqlite build only)
db/pool.go                  Querier/Rows/Row interfaces, shared
db/connect_postgres.go      pgx pool adapter
db/connect_sqlite.go        database/sql adapter + $N -> ?N placeholder rewrite
db/dialect_postgres.go      ANY/UNNEST/ILIKE/to_char/::TEXT
db/dialect_sqlite.go        json_each/LOWER LIKE/strftime/CAST
```

`db/queries.go` and all of `handlers/` are shared verbatim. A new endpoint
added to the Postgres API works on Azure with no extra effort.

## Deploy

### 1. Build the database

```sh
pip install -r azure/pipeline/requirements.txt
python3 azure/pipeline/build_db.py \
    --db-path azure/pokedex.db --csv-dir azure/pipeline/csv_data --fresh
```

This runs all 25 spiders and the PokeAPI CSV load, so it takes a while. See
`azure/pipeline/README.md` for the ingest details and the faster iteration
flags (`--skip-scrape`, `--only <spider>`).

### 2. Build and push the image

The build context is the **repository root**, not this directory:

```sh
docker build -f azure/Dockerfile -t pokedex-api:azure .
```

Push it anywhere Container Apps can pull from. Azure Container Registry Basic
is about $5/month; GitHub Container Registry and Docker Hub are free for public
images and cost nothing extra:

```sh
docker tag pokedex-api:azure ghcr.io/<you>/pokedex-api:$(date +%Y-%m-%d)
docker push ghcr.io/<you>/pokedex-api:$(date +%Y-%m-%d)
```

### 3. Deploy

```sh
az group create --name pokedex-rg --location eastus

az deployment group create \
  --resource-group pokedex-rg \
  --template-file azure/main.bicep \
  --parameters containerImage=ghcr.io/<you>/pokedex-api:2026-07-18 \
               customDomain=poke-api.duocore.dev
```

For a private registry, add `registryServer`, `registryUsername`, and
`registryPassword`.

At this point the API is live on its `*.azurecontainerapps.io` hostname. The
custom domain is not bound yet — `bindCustomDomain` defaults to false.

### 4. Point DNS at the app

The deployment prints the two records to create. Read them back with:

```sh
az deployment group show -g pokedex-rg -n main \
  --query 'properties.outputs.{cname:dnsCnameRecord.value,txt:dnsTxtRecord.value}' -o yaml
```

You will get something like:

```
cname: poke-api.duocore.dev        CNAME  pokedex-api.<hash>.eastus.azurecontainerapps.io
txt:   asuid.poke-api.duocore.dev  TXT    A1B2C3...
```

Create both at whatever hosts DNS for `duocore.dev`. The `asuid` TXT record
proves you control the name; the CNAME both routes traffic and is what
certificate issuance validates against. If your provider wants names relative
to the zone, use `poke-api` and `asuid.poke-api`.

Wait for propagation before continuing — issuance fails if the CNAME is not
yet visible:

```sh
dig +short poke-api.duocore.dev
dig +short TXT asuid.poke-api.duocore.dev
```

### 5. Bind the domain and issue the certificate

Re-run the same deployment with binding switched on:

```sh
az deployment group create \
  --resource-group pokedex-rg \
  --template-file azure/main.bicep \
  --parameters containerImage=ghcr.io/<you>/pokedex-api:2026-07-18 \
               customDomain=poke-api.duocore.dev \
               bindCustomDomain=true
```

This creates an Azure-managed certificate and binds it with SNI. Issuance
usually takes a few minutes.

```sh
curl -I https://poke-api.duocore.dev/healthz
```

**On HTTPS:** the certificate is free, auto-renewing, and managed entirely by
Azure — nothing to rotate and no cron job. Ingress runs with
`allowInsecure: false`, so plain HTTP is redirected to HTTPS automatically.
The container itself still speaks plain HTTP (`TLS_CERT=off`); TLS terminates
at ingress, which is why no certificate is mounted into the image.

The two-phase split exists because certificate issuance validates via CNAME:
the DNS record has to point at the app, which means the app must already
exist. Setting `bindCustomDomain=true` on a first deploy fails for that reason.

## Cost

Container Apps' monthly free grant is 180,000 vCPU-seconds and 360,000
GiB-seconds. The template requests 0.5 vCPU / 1 GiB and scales to zero, so an
API that is idle most of the day generally lands inside the grant — call it
**$0–3/month**, plus registry if you use ACR. There is no database line item,
which is where the Postgres deployment's ~$15–25/month went.

Scale-to-zero means the first request after an idle period pays a cold start.
Set `minReplicas: 1` in `main.bicep` if that matters; it costs roughly $10–12
a month.

## Refreshing the data

The database is a read-only image layer, so refreshing data is a rebuild:

```sh
python3 azure/pipeline/build_db.py \
    --db-path azure/pokedex.db --csv-dir azure/pipeline/csv_data --fresh
docker build -f azure/Dockerfile -t pokedex-api:azure .
# push, then:
az containerapp update -g pokedex-rg -n pokedex-api --image <new tag>
```

Use a dated or digest tag rather than `:latest` — Container Apps creates a new
revision per image reference, and an unchanged tag will not reliably roll.

## Running locally

```sh
go build -tags sqlite -o pokedex-api-sqlite .
SQLITE_PATH=azure/pokedex.db TLS_CERT=off PORT_HTTP=8080 ./pokedex-api-sqlite
curl localhost:8080/api/v2/pokemon/totodile
```

`SQLITE_IMMUTABLE=0` disables the immutable-file optimisation; set it if you
are pointing at a database that the ingest pipeline is concurrently writing.

Run the SQLite-specific tests with:

```sh
go test -tags sqlite ./db/
```
