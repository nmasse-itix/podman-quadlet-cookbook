-- Initialization script for Gitea database and user
CREATE USER gitea WITH PASSWORD 'gitea';
CREATE DATABASE gitea OWNER gitea;
GRANT ALL PRIVILEGES ON DATABASE gitea TO gitea;
ALTER ROLE gitea SET client_encoding TO 'utf8';