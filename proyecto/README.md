# Proyecto: Sistema Jurídico Inteligente

Estructura inicial basada en `Sistema_Juridico_Inteligente_revisado.docx`. Esta carpeta contiene los límites de los componentes; todavía no define bibliotecas, esquemas de API ni despliegues ejecutables.

## Componentes

| Carpeta | Responsabilidad |
| --- | --- |
| `apps/web` | Aplicación web React con portales para ciudadanía, mediación, judicatura y administración. |
| `services/core-api` | Monolito modular FastAPI: reglas de negocio, permisos, expedientes, ODR, canalización y acceso transaccional a PostgreSQL. |
| `services/ia-service` | Servicio interno de clasificación, recomendaciones, borradores, sugerencia de turno, RAG e ingesta. No consulta PostgreSQL directamente. |
| `contracts` | Definiciones de intercambio entre cliente, núcleo, IA y tareas; incluye los dos contratos de canalización. |
| `persistence` | Migraciones, políticas e índices para PostgreSQL y MongoDB; configuración del repositorio de documentos. No almacena expedientes reales. |
| `infrastructure` | Configuración futura de desarrollo local, contenedores y despliegue institucional. |
| `tests` | Pruebas entre componentes y del recorrido completo. Cada servicio también tiene sus pruebas propias. |
| `docs` | Evaluación de la arquitectura y decisiones técnicas. |

## Recorrido principal del MVP

`web/ciudadano → core-api/orientacion → ia-service/clasificacion → core-api/odr → core-api/canalizacion (si procede) → core-api/judicial → solución documentada y cierre`.

La canalización es el único puente de datos de ODR a la vía judicial. El dominio judicial no lee mensajes ni notas de mediación. `core-api` controla autenticación, autorización y cambios de estado; `ia-service` entrega sugerencias sujetas a revisión humana.

La revisión de viabilidad y las decisiones previas a la implementación están en [docs/arquitectura.md](docs/arquitectura.md). La primera entrega es una demostración local de ESCOM con datos sintéticos.
