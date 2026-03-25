-- Initialization script for Nextcloud database and user
CREATE USER nextcloud WITH PASSWORD 'nextcloud';
CREATE DATABASE nextcloud OWNER nextcloud;
GRANT ALL PRIVILEGES ON DATABASE nextcloud TO nextcloud;
ALTER ROLE nextcloud SET client_encoding TO 'utf8';
