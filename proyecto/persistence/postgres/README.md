# Migraciones PostgreSQL del MVP

Orden de aplicación con `psql -v ON_ERROR_STOP=1`: `001_base.sql` a `006_integridad_odr.sql`. Ejecutarlas en una **base vacía** como propietario con permiso de crear roles. La base original se probó en PostgreSQL 16; la implementación ODR y sus seis migraciones se validan con PostgreSQL 17. El comando `python -m api.gestion preparar` aplica todas en una nueva base local y genera un login NOINHERIT para la demostración.

La prueba original es [`../../tests/integracion/postgres_smoke.sql`](../../tests/integracion/postgres_smoke.sql); abre una transacción y termina con `ROLLBACK`. La suite `services/core-api/tests/test_odr_api.py` crea una base temporal, aplica las seis migraciones y prueba la API y sus barreras con PostgreSQL real. Consulta la [guía ODR](../../docs/odr-primera-iteracion.md).

## Límite de acceso

Las migraciones crean roles **NOLOGIN**. La configuración local debe crear un login distinto para autenticación, núcleo, ODR, judicial, administración y canalización, y otorgar a cada uno únicamente su rol correspondiente. No se guarda ninguna contraseña en el repositorio. La API establece `app.usuario_id` mediante `SET LOCAL` después de validar el token; nunca lo toma directamente de un encabezado enviado por el cliente.

`rol_canalizador` ejecuta `nucleo_comun.canalizar_conflicto` y su envoltura `canalizar_odr` (clave de idempotencia y evento). No recibe `USAGE` ni `SELECT` sobre `schema_odr`. Las funciones obtienen el resultado de mediación y, si procede, los puntos pendientes de un convenio parcial formalizado; crean la demanda y actualizan el conflicto en una misma transacción. `rol_app_judicial` tampoco recibe acceso al esquema ODR.

Las tablas sensibles tienen RLS. Las funciones `SECURITY DEFINER` se crean con un `search_path` fijo y revocan `EXECUTE` a `PUBLIC`, siguiendo la [guía de PostgreSQL para funciones privilegiadas](https://www.postgresql.org/docs/current/sql-createfunction.html). El propietario de tablas y funciones es de mantenimiento, no un usuario de la aplicación. [Documentación de RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html).

Las reglas SQL protegen además el plazo judicial del prototipo, el cierre condicionado, las versiones de convenio ya aceptadas y registros de solo adición. La API verifica credenciales y TOTP antes de abrir la transacción. El alta del operador y su secreto TOTP se realiza por CLI; no existe un alta institucional pública.
