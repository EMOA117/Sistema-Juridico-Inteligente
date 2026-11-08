# Núcleo transaccional (core-api)

API REST en FastAPI. Cada módulo tiene tres capas (`router` → `servicio` → SQL), siguiendo el §11.1.1 del documento, y se conecta a PostgreSQL **solo con su rol** (`compartido/bd.py`). La autorización se aplica dos veces:
- en la aplicación, con `exigir_acceso` / `exigir_rol`;
- en la base de datos, con RLS y `app.usuario_id` fijado mediante `SET LOCAL` en cada transacción.

## Ejecutar

```bash
cp .env.example .env          # SJI_PG_PASSWORD = PG_APP_PASSWORD de infrastructure/local/.env
uv sync --extra test
uv run uvicorn api.main:app --app-dir src --port 8000 --reload
```

La documentación interactiva queda en <http://localhost:8000/docs>.

## Módulos

| Módulo | Rol BD | Endpoints principales |
| --- | --- | --- |
| `identidad` | `app_auth`, `app_nucleo`, `app_admin` | `POST /auth/login` (TOTP obligatorio para personal, bloqueo de 15 min tras 5 intentos), `POST /auth/registro` (CURP con dígito verificador), `POST /auth/mfa/alta`, `POST /auth/mfa/confirmar`, `POST /auth/renovar`, `POST /auth/cambiar-contrasena`, `GET/POST/PATCH /admin/usuarios` |
| `orientacion` | `app_nucleo` | `POST /conflictos`, `PUT /conflictos/{id}/narrativa`, `POST /conflictos/{id}/confirmar` |
| `odr` | `app_odr` | `GET /mediaciones/{id}`, mensajes y propuestas cifrados (AES-256-GCM) |
| `canalizacion` | `app_canalizador` | `POST /conflictos/{id}/canalizar` (solo invoca `canalizar_conflicto`) |
| `judicial` | `app_judicial` | demanda, confirmación, expediente, dictamen, corrección |
| `administracion` | `app_admin` | turno, carga de jueces, juzgados, indicadores agregados |
| `odr.invitaciones` | `app_odr`, `app_auth` | `POST /conflictos/{id}/mediacion` (token de 43 caracteres, solo se guarda su SHA-256), `GET /invitaciones/{token}`, `POST /invitaciones/{token}/responder` |
| `notificaciones` | `app_nucleo` | `GET /notificaciones`, `POST /notificaciones/leidas` |

Algunas funciones (`clasificador`, `generador_borrador`, `despues_de_*`) son **puntos de extensión**. Ahí se conectan las notificaciones y el servicio de IA sin cambiar las reglas del flujo.

## Tareas en segundo plano

```bash
uv run python -m tareas      # desde src/: envío de avisos por correo (Mailpit) y vencimiento de invitaciones
```

Cada cambio de estado inserta un aviso `PENDIENTE` en `nucleo_comun.notificacion` dentro de la misma transacción. La tarea los envía por SMTP con reintentos (retroceso exponencial, máximo 5) y `Message-ID` estable. Los correos solo contienen folio, tipo de evento y enlace.

## Pruebas

```bash
uv run pytest
```
