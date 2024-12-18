#!/bin/bash

# Environment variables
DB_NAME=${APP_ID:-visionatrix}
DB_USER=${APP_ID:-visionatrix}
DB_PASS=${APP_ID:-visionatrix}

# Check if EXTERNAL_DATABASE is set
if [ -n "${EXTERNAL_DATABASE}" ]; then
    DATABASE_URI="${EXTERNAL_DATABASE}"
    echo "Using external database. DATABASE_URI is set to: $DATABASE_URI"

    # Check if DATABASE_URI is already in /etc/environment, if not, add it
    if ! grep -q "^export DATABASE_URI=" /etc/environment; then
        echo "export DATABASE_URI=\"${EXTERNAL_DATABASE}\"" >> /etc/environment
    fi

    # Reload environment variables
    . /etc/environment
    exit 0
fi

source /ex_app_scripts/common_pgsql.sh

ensure_postgres_installed
init_and_start_postgres

# Check if the user exists and create if not
sudo -u postgres $PG_SQL -c "SELECT 1 FROM pg_user WHERE usename = '$DB_USER'" | grep -q 1 || \
sudo -u postgres $PG_SQL -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" && \
sudo -u postgres $PG_SQL -c "ALTER USER $DB_USER WITH SUPERUSER;"

# Check if the database exists and create if not
sudo -u postgres $PG_SQL -c "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
sudo -u postgres $PG_SQL -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

if [ -z "${DATABASE_URI}" ]; then
    # Set DATABASE_URI environment variable
    DATABASE_URI="postgresql+psycopg://$DB_USER:$DB_PASS@/$DB_NAME?host=/var/run/postgresql"
    echo "export DATABASE_URI=\"postgresql+psycopg://$DB_USER:$DB_PASS@/$DB_NAME?host=/var/run/postgresql\"" >> /etc/environment
    echo "DATABASE_URI was not set. It is now set to: $DATABASE_URI"
else
    echo "DATABASE_URI is already set to: $DATABASE_URI"
fi
