# Núcleo transaccional y API ODR

Se implementaron las reglas puras de estados en `src/modulos/estado/modelo.py`, la autorización por rol y relación con el recurso en `src/modulos/identidad/autorizacion.py`, y las primitivas de contraseña Argon2 y JWT en `src/modulos/identidad/credenciales.py`. La transacción establece `app.usuario_id` de forma local mediante `src/compartido/seguridad/contexto_bd.py`, después de autenticar a la persona.

Para ejecutar las pruebas tras instalar las dependencias del `pyproject.toml`:

```powershell
python -m pytest tests -q
```

La API ejecutable está en `api.main:app` (factoría). Incluye registro ciudadano, contraseña y JWT, TOTP institucional verificado en servidor, operaciones ODR persistentes y autorización por rol/relación. El cliente no elige su rol ni el valor MFA del token. Consulta la [guía de primera iteración](../../docs/odr-primera-iteracion.md) para aprovisionamiento, variables, alcance y pruebas PostgreSQL/navegador. Las primitivas existentes y las migraciones `001`–`004` se conservan; `005`–`006` añaden la implementación ODR.
