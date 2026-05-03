FROM python:3.13-alpine

RUN apk add --no-cache libpq dos2unix \
    && pip install --no-cache-dir psycopg2-binary requests

WORKDIR /app

COPY . .

ENV PYTHONPATH=/app
ENV CSV_DATA_DIR=/app/csv_data

# Snapshot the PokeAPI CSVs we need at image-build time so the runtime
# loader doesn't depend on GitHub being reachable.
RUN python prefetch.py

RUN dos2unix entrypoint.sh && chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
