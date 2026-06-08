#!/usr/bin/env bash
set -euo pipefail

runuser -u postgres -- psql -tc "SELECT 1 FROM pg_roles WHERE rolname = 'foliun'" | grep -q 1 || runuser -u postgres -- psql -c "CREATE ROLE foliun WITH LOGIN PASSWORD 'foliun';"
runuser -u postgres -- psql -tc "SELECT 1 FROM pg_database WHERE datname = 'foliun'" | grep -q 1 || runuser -u postgres -- createdb -O foliun foliun
runuser -u postgres -- psql -d foliun -c "CREATE EXTENSION IF NOT EXISTS vector;"
