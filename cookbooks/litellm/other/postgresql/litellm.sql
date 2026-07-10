-- Initialization script for LiteLLM database and user
CREATE USER litellm WITH PASSWORD 'litellm';
CREATE DATABASE litellm OWNER litellm;
GRANT ALL PRIVILEGES ON DATABASE litellm TO litellm;
ALTER ROLE litellm SET client_encoding TO 'utf8';
