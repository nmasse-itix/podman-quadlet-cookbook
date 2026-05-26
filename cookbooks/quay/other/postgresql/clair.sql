-- Initialization script for Clair database and user
CREATE USER clair WITH PASSWORD 'clair';
CREATE DATABASE clair OWNER clair;
GRANT ALL PRIVILEGES ON DATABASE clair TO clair;
