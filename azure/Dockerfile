# Azure Container Apps image: the API built against SQLite, with the database
# baked in as a read-only layer.
#
# The build context is the REPOSITORY ROOT, not this directory:
#   python3 azure/pipeline/build_db.py --out azure/pokedex.db
#   docker build -f azure/Dockerfile -t pokedex-api:azure .

FROM golang:1.26-alpine AS builder
WORKDIR /src

COPY go.mod go.sum ./
RUN go mod download

COPY . .
# modernc.org/sqlite is pure Go, so this stays a static, CGO-free binary and
# the runtime stage needs no libsqlite3.
RUN CGO_ENABLED=0 go build -tags sqlite -ldflags="-s -w" -o /out/pokedex-api .

FROM alpine:3.21
RUN apk add --no-cache ca-certificates \
    && adduser -D -u 10001 pokedex

WORKDIR /app
COPY --from=builder /out/pokedex-api .

# Produced by azure/pipeline/build_db.py. Baked into the image rather than
# mounted: the API only reads it, so there is no volume to pay for and no
# SQLite-over-network-filesystem locking to get wrong. Refreshing the data
# means rebuilding this image.
COPY azure/pokedex.db /app/data/pokedex.db

USER pokedex

ENV SQLITE_PATH=/app/data/pokedex.db \
    SQLITE_IMMUTABLE=1 \
    TLS_CERT=off \
    PORT_HTTP=158

EXPOSE 158
CMD ["./pokedex-api"]
