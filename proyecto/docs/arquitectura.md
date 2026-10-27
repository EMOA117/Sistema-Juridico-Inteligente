# Revisión inicial de la arquitectura

## Veredicto

La arquitectura propuesta **sí sirve como base del MVP civil y familiar**. La división entre aplicación web, núcleo transaccional modular y servicio interno de IA es coherente con el recorrido completo: captura, análisis, mediación, canalización, demanda, contestación y resolución. Mantener los módulos jurídicos dentro de un solo `core-api` facilita transacciones y evita distribuir prematuramente el flujo de un expediente.

La estructura de carpetas refleja límites lógicos, no implica desplegar cada módulo como un microservicio. Se prevén dos unidades de servicio: `core-api` e `ia-service`. Las tareas de segundo plano pertenecen al núcleo y pueden ejecutarse en procesos de trabajo separados cuando exista esa necesidad.

## Límites que deben conservarse

1. **ODR y vía judicial:** esquemas y permisos distintos. Solo `canalizacion` construye la transferencia. El contrato ordinario contiene partes, narrativa inicial y materia; el excepcional añade los puntos pendientes de un convenio parcial formalizado. Ninguno transporta mensajes, propuestas o notas del mediador.
2. **Decisión humana:** clasificación, recomendaciones, borradores, turno y RAG son asistencia. El núcleo registra la aceptación, corrección o rechazo por la persona autorizada.
3. **Cierre:** cada caso cerrado referencia una solución documentada. Un convenio parcial mantiene abiertos los puntos pendientes; la ruta judicial exige la resolución y las constancias de firma, sello de tiempo y firmeza previstas en el documento.
4. **Acceso a datos:** `core-api` es dueño de los datos transaccionales en PostgreSQL. `ia-service` recibe la información mínima por una API interna autenticada y utiliza MongoDB para conocimiento e interacciones de IA según el dominio y sus permisos.
5. **Documentos:** el repositorio de objetos conserva los archivos; PostgreSQL conserva sus referencias, estados y huellas. Los documentos formalizados requieren política de retención inmutable.

## Ajustes necesarios antes de programar

| Prioridad | Decisión o riesgo | Propuesta de trabajo |
| --- | --- | --- |
| Alta | Falta concretar contratos y estados del caso de punta a punta. | Definir OpenAPI y eventos; empezar por captura, canalización ordinaria y parcial, contestación, solución y cierre. |
| Alta | PostgreSQL, MongoDB y almacenamiento de objetos no comparten una transacción. | Registrar eventos pendientes en PostgreSQL y procesarlos con reintentos e idempotencia; tratar los índices y análisis como derivados reconstruibles. |
| Alta | La confidencialidad ODR exige más que carpetas separadas. | Probar permisos de base de datos y de API; impedir que el expediente judicial, RAG, logs o trazas reciban contenido de negociación. |
| Alta | La búsqueda vectorial y los datos históricos anonimizados dependen del entorno disponible. | Confirmar capacidades del MongoDB institucional y acceso a un conjunto permitido de casos antes de comprometer las funciones de recomendación y RAG. |
| Media | La infraestructura completa descrita en el documento requiere operación institucional. | Construir primero un entorno local reproducible; conservar las interfaces para desplegar después en el centro de datos del Tribunal. |
| Media | La interfaz deja abierta la elección entre React y Vue. | Elegir una al iniciar `apps/web`; el límite arquitectónico no cambia. |
| Media | El plazo de 15 días requiere una fecha inicial comprobable y tratamiento de vencimientos. | Registrar el emplazamiento validado, calcular la fecha límite con la regla del documento y probar la tarea de vencimiento; revisar la regla procesal aplicable antes de uso real. |

## Primera secuencia de implementación sugerida

1. Modelo de estados y contratos: caso, partes, invitación, mediación, canalización, demanda, emplazamiento, contestación, resolución y cierre.
2. Identidad, autorización y migraciones de PostgreSQL con separación ODR/judicial.
3. Captura secuencial y clasificación de materia; permitir revisión humana del resultado.
4. Mediación y ambos contratos de canalización, con pruebas de confidencialidad.
5. Expediente, demanda, contestación y resolución; impedir cualquier cierre sin solución.
6. Integrar después recomendaciones, RAG, analítica y despliegue institucional según datos y recursos disponibles.

Esta revisión evalúa la coherencia técnica del diseño. La configuración institucional y las reglas procesales concretas deben validarse con los responsables del Tribunal antes de operar con casos reales.
