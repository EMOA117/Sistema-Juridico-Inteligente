#!/usr/bin/env bash
# Aplica las migraciones en una base vacía y crea un login por rol de aplicación.
set -euo pipefail
cd "$(dirname "$0")"
set -a; source .env; set +a
MIG=../../persistence/postgres
export PGHOST=localhost PGPORT=5433 PGDATABASE=sji PGUSER=sji_propietario PGPASSWORD="$PG_PROPIETARIO_PASSWORD"

# --reiniciar borra la base de demostración y la crea vacía (solo datos sintéticos).
if [[ "${1:-}" == "--reiniciar" ]]; then
  psql -q -d postgres -c "DROP DATABASE IF EXISTS sji WITH (FORCE)" -c "CREATE DATABASE sji"
fi

for f in "$MIG"/0*.sql; do
  echo "→ $(basename "$f")"
  psql -q -v ON_ERROR_STOP=1 -f "$f"
done

# Un login por rol NOLOGIN definido en las migraciones (README de persistence/postgres).
for par in app_nucleo:rol_app_nucleo app_auth:rol_auth app_odr:rol_app_odr app_judicial:rol_app_judicial \
           app_admin:rol_app_admin app_canalizador:rol_canalizador app_tareas:rol_tareas; do
  login=${par%%:*}; rol=${par##*:}
  psql -q -v ON_ERROR_STOP=1 -v login="$login" -v rol="$rol" -v pass="$PG_APP_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'login', :'pass')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'login') \gexec
SELECT format('GRANT %I TO %I', :'rol', :'login') \gexec
SQL
done

echo "→ prueba de humo"
psql -q -v ON_ERROR_STOP=1 -o /dev/null -f ../../tests/integracion/postgres_smoke.sql
echo "Base lista."
