# Entorno local de demostración

Servicios de apoyo para la demostración de ESCOM con **datos sintéticos**. No es un despliegue de producción.

| Servicio | Imagen | Puerto | Uso |
| --- | --- | --- | --- |
| PostgreSQL 16 | `postgres:16.4` | 5433 | Datos transaccionales (`nucleo_comun`, `schema_odr`, `schema_judicial`, `analitica`). |
| MongoDB + búsqueda vectorial | `mongodb/mongodb-atlas-local:8.0.4` | 27018 | Conocimiento e interacciones de IA (`ia_conocimiento`, `ia_uso`, `ia_uso_odr`). |
| Mailpit | `axllent/mailpit` | 1025 (SMTP), 8025 (web) | Bandeja de correos de prueba: <http://localhost:8025>. |
| RustFS | `rustfs/rustfs:1.0.4` | 9000 (S3), 9001 (consola) | Almacén de documentos compatible con S3 y con Object Lock (WORM). Sustituye a MinIO, cuya imagen ya no se publica en Docker Hub. |

Ollama corre **fuera de Docker**, directamente en la Mac, para usar la GPU. Los servicios lo buscan en `http://localhost:11434`.

## Puesta en marcha

```bash
cp .env.example .env        # y cambia las contraseñas
docker compose up -d
./init-db.sh                # migraciones, logins por rol y prueba de humo
```

`./init-db.sh --reiniciar` borra la base de demostración y la crea desde cero.

Después, en `services/core-api`, se siembran los datos sintéticos:

```bash
uv run python -m herramientas.sembrar
```

Después, en `services/core-api`, se crea la PKI de demostración (CA raíz y TSA locales, sin validez legal):

```bash
uv run python -m herramientas.pki_init
```

El script de siembra genera contraseñas y secretos TOTP aleatorios para las cuentas demo y los guarda en `credenciales-demo.txt`. Ese archivo está ignorado por git y no debe compartirse.

## Roles de base de datos

`init-db.sh` crea un login por rol de aplicación (`app_nucleo`, `app_auth`, `app_odr`, `app_judicial`, `app_admin`, `app_canalizador`, `app_tareas`). Todos usan la contraseña `PG_APP_PASSWORD`. Cada módulo de `core-api` se conecta solo con el suyo, y el rol judicial no tiene acceso a `schema_odr`.

## Asistente de IA

```bash
OLLAMA_MODELS="/ruta/a/modelos" ollama serve       # opcional: carpeta de modelos en otro disco
ollama pull qwen2.5:7b && ollama pull bge-m3
cd ../../services/ia-service && uv run python ../../persistence/mongo/inicializar.py
```

## Arranque diario (4 terminales)

```bash
cd services/core-api && uv run uvicorn api.main:app --app-dir src --port 8000 --reload
cd services/core-api/src && uv run --project .. python -m tareas      # correos, vencimientos e indexación
cd services/ia-service && uv run uvicorn api.main:app --app-dir src --port 8001
cd apps/web && npm run dev
```

Tras sembrar datos o reiniciar Mongo: `uv run python -m herramientas.reindexar` (en `services/core-api/src`).

## Windows (PowerShell)

Requisitos: Docker Desktop (con WSL 2), Python 3.12+ con [`uv`](https://docs.astral.sh/uv/), Node 22.12+ y Ollama para Windows. `init-db.sh` es un script de Bash: ejecútalo desde **Git Bash** o WSL; el resto de los comandos funciona en PowerShell desde la raíz del repositorio.

```powershell
cd proyecto/infrastructure/local
Copy-Item .env.example .env          # y cambia las contraseñas
docker compose up -d
bash ./init-db.sh                    # desde Git Bash o WSL

cd ../../services/core-api
uv run python -m herramientas.sembrar
uv run python -m herramientas.pki_init

ollama pull qwen2.5:7b; ollama pull bge-m3
cd ../ia-service; uv run python ../../persistence/mongo/inicializar.py
```

Arranque diario, una terminal de PowerShell por proceso:

```powershell
cd proyecto/services/core-api;     uv run uvicorn api.main:app --app-dir src --port 8000 --reload
cd proyecto/services/core-api/src; uv run --project .. python -m tareas
cd proyecto/services/ia-service;   uv run uvicorn api.main:app --app-dir src --port 8001
cd proyecto/apps/web;              npm ci; npm run dev
```

Si el puerto 5433 o 27018 está ocupado, cámbialo en `docker-compose.yml` y en los `.env` de los servicios.

## Pruebas

```bash
cd services/core-api && uv run --extra test pytest -q -m "not ia_real"   # integración contra la BD del compose
cd services/core-api && uv run --extra test pytest -q -m ia_real         # con ia-service y Ollama reales (lentas)
cd apps/web && npm run test:e2e                                          # recorrido en navegador; requiere todo levantado
```

La prueba de navegador usa el Chrome instalado. Para usar el Chromium de Playwright: `npx playwright install chromium` y `PLAYWRIGHT_CHANNEL= npm run test:e2e`.
