FROM golang:1.26-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o pokedex-api .

FROM alpine:3.21
RUN apk add --no-cache ca-certificates
WORKDIR /app
COPY --from=builder /app/pokedex-api .
RUN mkdir /app/certs/
EXPOSE 158
CMD ["./pokedex-api"]
