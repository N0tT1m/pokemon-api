FROM python:3.13-alpine

RUN apk add --no-cache libpq dos2unix \
    && pip install --no-cache-dir scrapy psycopg2-binary itemadapter

WORKDIR /app

COPY . .

ENV PYTHONPATH=/app

RUN ls -la /app/ && ls -la /app/pokemondb_scraper/ || echo "pokemondb_scraper dir MISSING"

RUN dos2unix entrypoint.sh && chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
