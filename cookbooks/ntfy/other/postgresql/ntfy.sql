-- Initialization script for ntfy database and user
CREATE USER ntfy WITH PASSWORD 'ntfy';
CREATE DATABASE ntfy OWNER ntfy;
GRANT ALL PRIVILEGES ON DATABASE ntfy TO ntfy;
ALTER ROLE ntfy SET client_encoding TO 'utf8';
