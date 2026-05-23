-- Sample analytics dataset for QueryMind demos.
--
-- Load into a database you'll connect as a workspace (NOT the metadata DB):
--   createdb -h localhost -p 5432 -U querymind sales_demo
--   psql -h localhost -p 5432 -U querymind -d sales_demo -f infra/seed/seed_sales.sql
--
-- Then connect it in the UI as a Postgres workspace pointed at sales_demo.

DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id serial PRIMARY KEY,
    name        text NOT NULL,
    segment     text NOT NULL DEFAULT 'standard'
);

CREATE TABLE sales (
    order_id    serial PRIMARY KEY,
    customer_id integer REFERENCES customers(customer_id),
    ts          timestamptz NOT NULL,
    amount      numeric(10,2) NOT NULL,
    region      text NOT NULL,
    channel     text NOT NULL DEFAULT 'web'
);

INSERT INTO customers (name, segment) VALUES
    ('Alice', 'enterprise'),
    ('Bob',   'standard'),
    ('Carol', 'enterprise'),
    ('Dan',   'standard');

INSERT INTO sales (customer_id, ts, amount, region, channel) VALUES
    (1, now() - interval '28 days', 50.00,  'NA',   'web'),
    (2, now() - interval '25 days', 100.00, 'NA',   'web'),
    (3, now() - interval '20 days', 25.00,  'EU',   'partner'),
    (4, now() - interval '14 days', 200.00, 'EU',   'web'),
    (1, now() - interval '10 days', 75.00,  'APAC', 'web'),
    (2, now() - interval '7 days',  120.00, 'APAC', 'partner'),
    (3, now() - interval '3 days',  60.00,  'EU',   'web'),
    (4, now() - interval '1 day',   300.00, 'NA',   'web');

-- Recommended: create a read-only role for QueryMind to connect as.
-- (Run as a superuser; replace the password.)
--
--   CREATE ROLE querymind_ro LOGIN PASSWORD 'replace-me';
--   GRANT CONNECT ON DATABASE sales_demo TO querymind_ro;
--   GRANT USAGE ON SCHEMA public TO querymind_ro;
--   GRANT SELECT ON ALL TABLES IN SCHEMA public TO querymind_ro;
--   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO querymind_ro;
