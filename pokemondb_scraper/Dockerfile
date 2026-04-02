FROM python:3.13-alpine

RUN apk add --no-cache libpq dos2unix \
    && pip install --no-cache-dir scrapy psycopg2-binary itemadapter

WORKDIR /app

COPY . .

ENV SCRAPY_SETTINGS_MODULE=pokemondb_scraper.settings
RUN dos2unix entrypoint.sh && chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
