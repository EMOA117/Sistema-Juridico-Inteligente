# Revisión inicial de la arquitectura

## Veredicto

La arquitectura propuesta **sí sirve como base del MVP civil y familiar**. La división entre aplicación web, núcleo transaccional modular y servicio interno de IA es coherente con el recorrido completo: captura, análisis, mediación, canalización, demanda, contestación y resolución. Mantener los módulos jurídicos dentro de un solo `core-api` facilita transacciones y evita distribuir prematuramente el flujo de un expediente. El primer despliegue será una demostración local para ESCOM con datos sintéticos.

La estructura de carpetas refleja límites lógicos, no implica desplegar cada módulo como un microservicio. Se prevén dos unidades de servicio: `core-api` e `ia-service`. Las tareas de segundo plano pertenecen al núcleo y pueden ejecutarse en procesos de trabajo separados cuando exista esa necesidad.

## Límites que deben conservarse

1. **ODR y vía judicial:** esquemas y permisos distintos. Solo `canalizacion` construye la transferencia. El contrato ordinario contiene partes, narrativa inicial y materia; el excepcional añade los puntos pendientes de un convenio parcial formalizado. Ninguno transporta mensajes, propuestas o notas del mediador.
2. **Decisión humana:** clasificación, recomendaciones, borradores, turno y RAG son asistencia. El núcleo registra la aceptación, corrección o rechazo por la persona autorizada.
3. **Cierre:** cada caso cerrado referencia una solución documentada. Un convenio parcial mantiene abiertos los puntos pendientes; la ruta judicial exige la resolución y las constancias de firma, sello de tiempo y firmeza previstas en el documento.
4. **Acceso a datos:** `core-api` es dueño de los datos transaccionales en PostgreSQL. `ia-service` recibe la información mínima por una API interna autenticada y utiliza MongoDB para conocimiento e interacciones de IA según el dominio y sus permisos.
5. **Documentos:** el repositorio de objetos conserva los archivos; PostgreSQL conserva sus referencias, estados y huellas. Los documentos formalizados requieren política de retención inmutable.

## Tres decisiones previas a la implementación

1. [Estados y contratos](decisiones/001-estados-y-contratos.md): flujo explícito, guardas de transición, cierre con solución y [dos variantes versionadas de canalización](../contracts/canalizacion/README.md).
2. [Confidencialidad ODR](decisiones/002-confidencialidad-odr.md): función transaccional como único puente, permisos de base de datos, lista positiva de datos y pruebas de no filtración.
3. [Búsqueda y datos](decisiones/003-busqueda-y-datos.md): corpus sintético para ESCOM y MongoDB Vector Search local en contenedor Linux. La prueba de ejecución se hará al configurar el entorno.

## Otros ajustes antes de programar

| Prioridad | Decisión o riesgo | Propuesta de trabajo |
| --- | --- | --- |
| Alta | PostgreSQL, MongoDB y almacenamiento de objetos no comparten una transacción. | Registrar eventos pendientes en PostgreSQL y procesarlos con reintentos e idempotencia; tratar los índices y análisis como derivados reconstruibles. |
| Media | La infraestructura completa descrita en el documento requiere operación institucional. | Construir primero un entorno local reproducible; conservar las interfaces para una eventual instalación institucional. |
| Resuelta | Interfaz web | Se usará **React** para los cuatro portales de `apps/web`; las vistas se diseñarán después. |
| Media | El plazo de 15 días requiere una fecha inicial comprobable y tratamiento de vencimientos. | Registrar el emplazamiento validado, calcular la fecha límite con la regla del documento y probar la tarea de vencimiento; revisar la regla procesal aplicable antes de uso real. |

## Primera secuencia de implementación sugerida

Los pasos 1 y 2 ya tienen una primera base en el repositorio: reglas de estado, contratos de canalización, autorización y migraciones PostgreSQL verificadas localmente. La elección de interfaz quedó fijada en React. La API HTTP, el inicio de sesión completo con segundo factor y las vistas aún no están implementados.

1. Modelo de estados y contratos: caso, partes, invitación, mediación, canalización, demanda, emplazamiento, contestación, resolución y cierre.
2. Identidad, autorización y migraciones de PostgreSQL con separación ODR/judicial.
3. Captura secuencial y clasificación de materia; permitir revisión humana del resultado.
4. Mediación y ambos contratos de canalización, con pruebas de confidencialidad.
5. Expediente, demanda, contestación y resolución; impedir cualquier cierre sin solución.
6. Integrar después recomendaciones, RAG, analítica y despliegue institucional según datos y recursos disponibles.

Esta revisión evalúa la coherencia técnica del diseño para una demostración académica. La configuración institucional y las reglas procesales concretas deben validarse con los responsables competentes antes de operar con casos reales.
