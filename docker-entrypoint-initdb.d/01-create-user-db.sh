#!/bin/bash
set -e

# Create the user database if it doesn't exist
# This prevents "database does not exist" errors when connections
# default to a database with the same name as the user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE $POSTGRES_USER;
EOSQL

