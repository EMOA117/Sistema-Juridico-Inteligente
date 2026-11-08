# Primera iteración ODR

Implementación local de demostración con datos sintéticos. Las pantallas de `feature/pantallas-base-web` se validaron (TypeScript, compilación y pruebas existentes), se actualizaron sus dependencias vulnerables y se integraron mediante merge en `main`. `feature/modulo-ODR` parte de ese merge. Los cambios son locales; publicar ramas es una operación separada.

## Ejecutar en Windows

Requisitos: Python 3.12+, Node 22.12+ o 24, PostgreSQL 17 y `uv`. Los comandos se ejecutan desde la raíz del repositorio. El servidor PostgreSQL debe estar iniciado. Usa una cuenta local con permiso para crear una base y un login; la aplicación recibe un usuario nuevo `NOINHERIT`, sin privilegios de propietario.

```powershell
uv venv --python 3.12
uv pip install --python .venv/Scripts/python.exe -e './proyecto/services/core-api[test]'

# Cambia la conexión por la de tu PostgreSQL local. No uses bases de producción.
.\.venv\Scripts\python.exe -m api.gestion preparar `
  --admin-url 'postgresql://postgres@127.0.0.1:5432/postgres' `
  --nombre odr_demo --env-file .env --mediador-demo

# El paso anterior solicita una contraseña para mediador@example.test y muestra
# una URI TOTP para configurarla en un autenticador. No es un código fijo.
.\.venv\Scripts\python.exe -m uvicorn api.main:app --factory `
  --env-file .env --host 127.0.0.1 --port 8000 --no-access-log
```

En otra terminal:

```powershell
cd proyecto/apps/web
npm ci
npm run dev -- --host 127.0.0.1
```

Abre `http://127.0.0.1:5173`. La documentación OpenAPI está en `http://127.0.0.1:8000/docs`. La API escucha únicamente en loopback; no publicar este entorno como servicio institucional.

El preparador crea una base nueva, aplica `001`–`006`, genera claves JWT y AES-256 distintas y escribe `.env` (ignorado por Git). Rechaza bases, logins o archivos ya existentes para evitar sobrescrituras. Conserva ese archivo: cambiar la clave AES impide descifrar los datos guardados. Para un ambiente existente, respalda primero y aplica únicamente las migraciones aún no instaladas, en orden, con una cuenta propietaria.

## Recorrido de demostración

1. Registra un ciudadano con correo sintético y contraseña de 12 o más caracteres.
2. Crea un asunto: captura las dos partes antes del relato. Registra materia y mediabilidad manuales; el prototipo conserva el alcance civil/familiar de las decisiones del repositorio.
3. Elige mediación y un plazo de 1–30 días naturales (7 por defecto). Copia el enlace de la sala. La fecha límite es inclusiva, en `America/Mexico_City`.
4. En otra sesión de navegador, registra a la contraparte con el correo indicado. Su invitación aparece en la bandeja y puede aceptarla o rechazarla. También funciona si la cuenta existía al capturar.
5. Intercambia mensajes, propuestas, contrapropuestas y respuestas. El contenido persiste; la sala consulta cambios cada cinco segundos.
6. Solicita mediador. Se asigna un operador activo con MFA y menor carga; si no hay disponible, la solicitud queda registrada y puede reintentarse. En el portal de mediación se programan sesiones con enlaces HTTPS y notas privadas del mediador.
7. Consulta ejemplos sintéticos de acuerdo. Se recuperan por coincidencia de palabras y materia, con identificador de fuente y abstención cuando no hay coincidencia suficiente.
8. Redacta y revisa un convenio total o parcial. El parcial exige puntos pendientes separados de los términos acordados. Descarga el PDF y registra la aceptación de cada parte y del mediador, si está asignado. La primera aceptación bloquea la versión; cada aceptación referencia su SHA-256.
9. Un total formalizado concluye el conflicto. Un parcial, rechazo, vencimiento, desistimiento o conclusión sin acuerdo deja `EN_ESPERA_DECISION`. La persona solicitante puede pedir la canalización; nunca sucede automáticamente.
10. Consulta los datos transferidos al borrador judicial: partes (referencias), narrativa inicial, materia y, solo en la excepción parcial formalizada, puntos pendientes. No se transfieren mensajes, propuestas, notas, PDF ni términos acordados.

`SIN_ACUERDO` se registra por el mediador asignado; cualquier parte puede desistir. La aceptación de una propuesta no sustituye la aceptación del convenio.

## Cobertura y límites explícitos

| Requisitos del PDF | Implementación de esta iteración |
| --- | --- |
| RF1.1–1.4 | Registro ciudadano, Argon2, JWT de 15 minutos, TOTP institucional, roles leídos de BD, relación con el caso y bitácora sin cuerpos ODR. El registro no verifica identidad ni propiedad del correo: solo datos sintéticos. |
| RF2.1, RF2.4–2.5 | Captura secuencial, orientación manual y decisión expresa de ruta. |
| RF2.2–2.3 | Clasificador PLN y estimación de complejidad pendientes; no se simulan predicciones como reales. |
| RF3.1–3.2, RF3.4–3.8 | Negociación persistente, propuestas, mediador, resultados, invitación con plazo, sesiones y notas. |
| RF3.3 | Recuperación léxica de corpus sintético versionado. MongoDB/BGE-M3 y casos históricos no están integrados; requiere revisión humana. |
| RF4.1–4.2 | PDF de revisión, edición antes de la primera aceptación, huella estable y acceso autenticado. |
| RF4.3–4.4 | Aceptación de demostración explícita, deshabilitable con `ODR_FIRMA_DEMO=false`; fecha de servidor y evidencia de usuarios. No es firma electrónica institucional ni sello de tiempo certificado. |
| RF4.5–4.6 | Canalización transaccional con lista positiva, convenio parcial formalizado, clave de idempotencia y evento `DemandaBorradorCreada`. |
| RF10 | Avisos persistentes en plataforma y lectura por destinatario. Correo/SMTP y distribución externa pendientes; el usuario comparte el enlace de la invitación. |
| RNF confidencialidad | AES-256-GCM en mensajes, propuestas, notas, términos, PDF y secreto TOTP; roles PostgreSQL, RLS, notas privadas, bitácora de solo adición y separación del rol judicial. |

Los documentos se almacenan cifrados en PostgreSQL para esta primera versión, no en un repositorio de objetos con retención institucional. Faltan TLS de despliegue, verificación de correo/identidad, protección distribuida contra abuso, revocación central de sesiones, firma/certificados institucionales, almacenamiento WORM, consumo externo de eventos, correo y la integración IA objetivo. Cerrar sesión elimina el token del navegador; un token copiado sigue vigente hasta su expiración. Las pantallas judiciales y administrativas conservan la vista previa de la rama base y muestran una advertencia de datos simulados.

La clave AES se requiere al iniciar; no se generan claves efímeras al reiniciar. Las transacciones fijan `SET LOCAL ROLE` y `app.usuario_id`. Se permiten DSN independientes mediante `DATABASE_URL_ROL_APP_ODR`, `DATABASE_URL_ROL_APP_JUDICIAL`, etc. Para un despliegue institucional deben aprovisionarse credenciales separadas por dominio; el login local reúne membresías para simplificar la demostración.

El alcance de firma, IA y formalización descrito arriba es académico. No debe presentarse como cumplimiento jurídico institucional ni como rendimiento validado de modelos.

## Vencimiento de invitaciones

Las consultas de bandeja/sala y las respuestas de invitación procesan vencimientos antes de responder. Además puede ejecutarse el comando siguiente desde un planificador local (con las variables de `.env` cargadas):

```powershell
uv run --no-project --env-file .env .venv/Scripts/python.exe -m api.gestion vencer-invitaciones
```

La tarea usa `rol_tarea_odr`, que solo puede ejecutar la función acotada. Dos ejecuciones no concluyen dos veces la misma invitación. El vencimiento no cierra ni canaliza el conflicto.

## Pruebas

```powershell
# Una conexión de prueba con permiso CREATE DATABASE; nunca una base institucional.
$env:TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:5432/postgres'
.\.venv\Scripts\python.exe -m pytest proyecto/services/core-api/tests -q

cd proyecto/apps/web
npm run build
npm audit --audit-level=moderate
# API y web deben estar iniciadas contra una base sintética.
$env:PLAYWRIGHT_CHANNEL='msedge' # O instala Chromium: npx playwright install chromium
npm run test:e2e
```

Las pruebas API crean una base `odr_test_<uuid>`, aplican todas las migraciones y eliminan exclusivamente esa base al finalizar. Sin `TEST_DATABASE_URL` se omiten las pruebas de integración; no contar esa ejecución como validación completa. La prueba de navegador utiliza dos contextos independientes, descarga el PDF, comprueba persistencia tras recargar, errores JavaScript y desbordamiento en móvil. Sus datos sintéticos quedan en la base de demostración.

Casos automatizados: autenticación/MFA, campos adicionales rechazados, tercero y juez sin acceso a ODR, datos cifrados, propuestas propias rechazadas, total/parcial, versión y hash del PDF, firmas pendientes, firma demo desactivada, notas privadas, registro tardío de contraparte, rechazo/vencimiento, desistimiento, sin acuerdo, ruta directa, canalización concurrente/idempotente, evento único, avisos sin cuerpos y negativa a exportar negociación.

## Estructura de implementación

- `services/core-api/src/api/main.py`: contratos HTTP y dependencia de identidad.
- `services/core-api/src/modulos/odr/`: reglas transaccionales, validación, documentos y ejemplos.
- `persistence/postgres/005_odr.sql` y `006_integridad_odr.sql`: persistencia, RLS, tareas, inmutabilidad e idempotencia.
- `apps/web/src/portales/odr/`: bandeja, captura y sala compartida por ciudadanía/mediador.
- `apps/web/src/compartido/servicios/odr.ts`: cliente y tipos del módulo.
- `services/core-api/tests/test_odr_api.py` y `apps/web/tests/odr.spec.ts`: aceptación API y navegador.

Las pantallas antiguas de ciudadanía/mediación se conservan como referencia visual; las rutas activas usan `portales/odr`. La documentación fuente es `Sistema_Juridico_Inteligente.pdf` (RF3/RF4, páginas 16–17) junto con las decisiones `001`–`003` ya adoptadas en el repositorio.
