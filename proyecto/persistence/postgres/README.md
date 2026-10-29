# Migraciones PostgreSQL del MVP

Orden de aplicación con `psql -v ON_ERROR_STOP=1`: `001_base.sql`, `002_reglas_y_canalizacion.sql`, `003_roles_y_rls.sql`, `004_contestacion.sql`. Ejecutarlas en una **base vacía** como propietario con permiso de crear roles. Las migraciones se aplicaron y probaron en un contenedor temporal PostgreSQL 16.

La prueba reproducible es [`../../tests/integracion/postgres_smoke.sql`](../../tests/integracion/postgres_smoke.sql). Ejecutarla después de las cuatro migraciones con `psql -v ON_ERROR_STOP=1 -f postgres_smoke.sql`; abre una transacción y termina con `ROLLBACK`. Comprueba ambos contratos de canalización, idempotencia, plazo, cierre condicionado y accesos de los roles.

## Límite de acceso

Las migraciones crean roles **NOLOGIN**. La configuración local debe crear un login distinto para autenticación, núcleo, ODR, judicial, administración y canalización, y otorgar a cada uno únicamente su rol correspondiente. No se guarda ninguna contraseña en el repositorio. La API establece `app.usuario_id` mediante `SET LOCAL` después de validar el token; nunca lo toma directamente de un encabezado enviado por el cliente.

`rol_canalizador` solo puede ejecutar `nucleo_comun.canalizar_conflicto`. No recibe `USAGE` ni `SELECT` sobre `schema_odr`. La función obtiene el resultado de mediación y, si procede, los puntos pendientes de un convenio parcial formalizado; crea la demanda y actualiza el conflicto en una misma transacción. `rol_app_judicial` tampoco recibe acceso al esquema ODR.

Las tablas sensibles tienen RLS. Las funciones `SECURITY DEFINER` se crean con un `search_path` fijo y revocan `EXECUTE` a `PUBLIC`, siguiendo la [guía de PostgreSQL para funciones privilegiadas](https://www.postgresql.org/docs/current/sql-createfunction.html). El propietario de tablas y funciones es de mantenimiento, no un usuario de la aplicación. [Documentación de RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html).

Las reglas SQL protegen además el plazo fijo de 15 días del prototipo y el cierre condicionado a una resolución firmada y firme. La verificación de credenciales y el MFA del personal se aplican en el servicio antes de abrir la transacción de negocio; la integración HTTP y el alta del segundo factor siguen pendientes.
