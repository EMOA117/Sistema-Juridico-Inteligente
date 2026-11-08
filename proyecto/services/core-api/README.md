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
| `identidad` | `app_auth` | `POST /auth/login`, `GET /auth/yo` |
| `orientacion` | `app_nucleo` | `POST /conflictos`, `PUT /conflictos/{id}/narrativa`, `POST /conflictos/{id}/confirmar` |
| `odr` | `app_odr` | `GET /mediaciones/{id}`, mensajes y propuestas cifrados (AES-256-GCM) |
| `canalizacion` | `app_canalizador` | `POST /conflictos/{id}/canalizar` (solo invoca `canalizar_conflicto`) |
| `judicial` | `app_judicial` | demanda, confirmación, expediente, dictamen, corrección |
| `administracion` | `app_admin` | turno, carga de jueces, juzgados, indicadores agregados |

Algunas funciones (`clasificador`, `generador_borrador`, `despues_de_*`) son **puntos de extensión**. Ahí se conectan las notificaciones y el servicio de IA sin cambiar las reglas del flujo.

## Pruebas

```bash
uv run pytest
```
