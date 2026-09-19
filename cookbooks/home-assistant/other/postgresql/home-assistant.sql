-- Initialization script for Home Assistant database and user (recorder backend)
CREATE USER home_assistant WITH PASSWORD 'home_assistant';
CREATE DATABASE home_assistant OWNER home_assistant;
GRANT ALL PRIVILEGES ON DATABASE home_assistant TO home_assistant;
ALTER ROLE home_assistant SET client_encoding TO 'utf8';
