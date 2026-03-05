#!/bin/bash
# ACORN All-in-One Entrypoint
# Initializes DB, seeds kernels, starts supervisord
set -e

echo "[acorn-aio] Initializing PostgreSQL..."
if [ ! -f /var/lib/postgresql/16/main/PG_VERSION ]; then
    su postgres -c "/usr/lib/postgresql/16/bin/initdb -D /var/lib/postgresql/16/main"
fi

su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/16/main -l /tmp/pg_init.log start"
sleep 3

su postgres -c "psql -c \"CREATE USER acorn WITH PASSWORD 'acorn' SUPERUSER;\"" 2>/dev/null || true
su postgres -c "psql -c \"CREATE DATABASE acorn OWNER acorn;\"" 2>/dev/null || true

su postgres -c "psql -U acorn -d acorn -f /opt/acorn/api/db/schema.sql" 2>/dev/null || true
su postgres -c "psql -U acorn -d acorn -f /opt/acorn/scripts/seed_kernels.sql" 2>/dev/null || true

su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/16/main stop"
sleep 2

echo "[acorn-aio] Starting ACORN services via supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/acorn.conf
