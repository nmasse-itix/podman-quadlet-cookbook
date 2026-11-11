-- Initialization script for the NetBird management database and user.
-- The password here MUST match the one in the PostgreSQL DSN of management.env
-- (NETBIRD_STORE_ENGINE_POSTGRES_DSN). This example ships an insecure password; the
-- operator overrides both in production.
CREATE USER netbird WITH PASSWORD 'netbird';
CREATE DATABASE netbird OWNER netbird;
GRANT ALL PRIVILEGES ON DATABASE netbird TO netbird;
ALTER ROLE netbird SET client_encoding TO 'utf8';
