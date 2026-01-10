-- Initialization script for Keycloak database and user
CREATE USER keycloak WITH PASSWORD 'keycloak';
CREATE DATABASE keycloak OWNER keycloak;
GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;
ALTER ROLE keycloak SET client_encoding TO 'utf8';