FROM golang:1.26-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o pokedex-api .

FROM python:3.13-alpine
RUN apk add --no-cache ca-certificates libpq dos2unix
RUN pip install --no-cache-dir scrapy psycopg2-binary itemadapter

WORKDIR /app

# Copy Go binary
COPY --from=builder /app/pokedex-api .

# Copy scraper code
COPY pokemondb_scraper/ /app/pokemondb_scraper/

RUN mkdir /app/certs/
COPY privkey.pem /app/certs/privkey.pem
COPY fullchain.pem /app/certs/fullchain.pem

# Copy entrypoint
COPY entrypoint.sh .
RUN dos2unix entrypoint.sh && chmod +x entrypoint.sh

EXPOSE 158

ENTRYPOINT ["./entrypoint.sh"]
