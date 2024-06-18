#!/bin/bash

# Environment variables
DB_NAME=${APP_ID:-vix}
DB_USER=${APP_ID:-vix_user}
DB_PASS=${APP_ID:-vix_pass}
BASE_DIR="${APP_PERSISTENT_STORAGE:-/nc_app_vix_data}"

# PostgreSQL version to use
PG_VERSION=15
PG_BIN="/usr/lib/postgresql/${PG_VERSION}/bin"
PG_SQL="/usr/lib/postgresql/${PG_VERSION}/bin/psql"

# Define the PostgreSQL data directory
DATA_DIR="${BASE_DIR}/pgsql"

# Check if PostgreSQL is installed by checking for the existence of binary files
if [ -d "$PG_BIN" ]; then
    echo "PostgreSQL binaries found."
else
    echo "PostgreSQL binaries not found."
    echo "Adding the PostgreSQL APT repository..."
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
    echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
    echo "Installing PostgreSQL..."
    apt-get update && apt-get install -y postgresql-$PG_VERSION
fi

# Ensure the directory exists and has the correct permissions
mkdir -p "$DATA_DIR"
chown -R postgres:postgres "$DATA_DIR"

if [ ! -d "$DATA_DIR/base" ]; then
    echo "Initializing the PostgreSQL database..."
    sudo -u postgres ${PG_BIN}/initdb -D "$DATA_DIR"
    PG_CONF="${DATA_DIR}/postgresql.conf"
    if ! grep -q "^listen_addresses\s*=\s*''" "$PG_CONF"; then
		echo "Updating PostgreSQL configuration to disable TCP/IP connections..."
		echo "listen_addresses = ''" >> "$PG_CONF"
	fi
fi

echo "Starting PostgreSQL..."
sudo -u postgres ${PG_BIN}/pg_ctl -D "$DATA_DIR" -l "${DATA_DIR}/logfile" start

echo "Waiting for PostgreSQL to start..."
until sudo -u postgres ${PG_SQL} -c "SELECT 1" > /dev/null 2>&1; do
    sleep 1
    echo -n "."
done
echo "PostgreSQL is up and running."

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
