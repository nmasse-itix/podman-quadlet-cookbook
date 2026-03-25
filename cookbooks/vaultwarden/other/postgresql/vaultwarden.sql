-- Initialization script for Vaultwarden database and user
CREATE USER vaultwarden WITH PASSWORD 'vaultwarden';
CREATE DATABASE vaultwarden OWNER vaultwarden;
GRANT ALL PRIVILEGES ON DATABASE vaultwarden TO vaultwarden;
ALTER ROLE vaultwarden SET client_encoding TO 'utf8';