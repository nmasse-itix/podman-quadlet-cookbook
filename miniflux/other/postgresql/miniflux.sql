-- Initialization script for Miniflux database and user
CREATE USER miniflux WITH PASSWORD 'miniflux';
CREATE DATABASE miniflux OWNER miniflux;
GRANT ALL PRIVILEGES ON DATABASE miniflux TO miniflux;
ALTER ROLE miniflux SET client_encoding TO 'utf8';
