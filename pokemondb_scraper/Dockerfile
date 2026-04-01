FROM python:3.13-alpine

RUN apk add --no-cache libpq dos2unix \
    && pip install --no-cache-dir scrapy psycopg2-binary itemadapter

WORKDIR /app

COPY pokemondb_scraper/ /app/pokemondb_scraper/
COPY entrypoint.sh .
RUN dos2unix entrypoint.sh && chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
