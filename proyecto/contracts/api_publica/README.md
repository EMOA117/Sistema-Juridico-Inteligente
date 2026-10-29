# Operaciones públicas del flujo del MVP

Rutas propuestas para `core-api`; cada operación de escritura exige autenticación, autorización por relación con el caso y registro de auditoría.

| Método y ruta | Efecto principal |
| --- | --- |
| `POST /v1/conflictos` | Crea conflicto en `CAPTURA`. |
| `PUT /v1/conflictos/{id}/partes` | Captura demandante y demandado. |
| `PUT /v1/conflictos/{id}/narrativa` | Guarda relato inicial tras capturar las partes. |
| `POST /v1/conflictos/{id}/orientacion` | Obtiene sugerencia de PLN y registra materia y vía confirmadas. |
| `POST /v1/conflictos/{id}/invitaciones` | Inicia mediación si la vía procede y fue elegida. |
| `POST /v1/invitaciones/{id}/respuesta` | Acepta o rechaza la invitación. |
| `POST /v1/mediaciones/{id}/conclusion` | Registra resultado de mediación. |
| `POST /v1/convenios/{id}/formalizacion` | Formaliza convenio firmado y distingue total o parcial. |
| `POST /v1/conflictos/{id}/canalizacion` | Crea el borrador judicial con el contrato permitido; requiere `Idempotency-Key`. |
| `POST /v1/demandas/{id}/confirmacion` | Confirma borrador revisado y crea expediente. |
| `POST /v1/expedientes/{id}/turno` | Confirma juzgado y juez sugeridos o asignación manual. |
| `POST /v1/expedientes/{id}/prevenciones` | Registra correcciones requeridas por el juez. |
| `POST /v1/expedientes/{id}/correcciones` | Presenta corrección y devuelve el expediente a revisión. |
| `POST /v1/expedientes/{id}/admisiones` | Registra admisión de la demanda. |
| `POST /v1/expedientes/{id}/desechamientos` | Registra resolución firmada de desechamiento. |
| `POST /v1/expedientes/{id}/emplazamientos` | Registra emplazamiento válido y calcula el plazo de 15 días del prototipo. |
| `POST /v1/expedientes/{id}/contestaciones` | Registra escrito, fecha y condición de plazo. |
| `POST /v1/expedientes/{id}/resoluciones` | Registra resolución firmada, resultado y sello de tiempo. |
| `POST /v1/expedientes/{id}/firmeza` | Registra constancia de firmeza. |
| `POST /v1/expedientes/{id}/cierre` | Cierra solo si existe solución documentada y firme. |

Las respuestas distinguen `403` por falta de permiso, `409` por estado incompatible y `422` por datos incompletos. Cada escritura recibe un identificador de operación; las rutas que puedan repetirse por reintento requieren `Idempotency-Key`. Los cuerpos JSON detallados se derivan de [la decisión de estados](../../docs/decisiones/001-estados-y-contratos.md) al implementar cada ruta.
