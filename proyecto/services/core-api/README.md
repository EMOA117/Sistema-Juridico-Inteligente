# Núcleo transaccional: primera base

Se implementaron las reglas puras de estados en `src/modulos/estado/modelo.py`, la autorización por rol y relación con el recurso en `src/modulos/identidad/autorizacion.py`, y las primitivas de contraseña Argon2 y JWT en `src/modulos/identidad/credenciales.py`. La transacción establece `app.usuario_id` de forma local mediante `src/compartido/seguridad/contexto_bd.py`, después de autenticar a la persona.

Para ejecutar las pruebas tras instalar las dependencias del `pyproject.toml`:

```powershell
python -m unittest discover -s tests -v
```

Esta entrega establece el modelo y las barreras de acceso. Aún no hay servidor HTTP, repositorios de datos ni flujo de inicio de sesión completo. El segundo factor para personal debe verificarse antes de emitir un token con `mfa=true`; el cliente nunca puede elegir ese valor. Las pruebas de la base de datos están en [migraciones PostgreSQL](../../persistence/postgres/README.md).
