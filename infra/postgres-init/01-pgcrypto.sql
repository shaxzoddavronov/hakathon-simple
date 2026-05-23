-- pgcrypto provides gen_random_uuid(), which the QueryMind AI metadata
-- schema uses as the default for every primary key column. The Alembic
-- migrations assume this extension already exists, so it must be created
-- before they run. Postgres executes every *.sql file in
-- /docker-entrypoint-initdb.d the first time the data directory is
-- initialized (i.e. on the very first `docker compose up`).
CREATE EXTENSION IF NOT EXISTS pgcrypto;
