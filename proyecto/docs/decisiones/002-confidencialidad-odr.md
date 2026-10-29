# Decisión 002: aislamiento verificable de la mediación

**Estado:** adoptada para la demostración local de ESCOM; se aplicará aun con datos sintéticos.

## Clasificación de datos

| Dominio | Datos | Lectura permitida |
| --- | --- | --- |
| `nucleo_comun` | Identidad de partes, narrativa inicial, materia, estado y bitácora de metadatos. | Roles autorizados según relación con el asunto. |
| `schema_odr` | Invitaciones, mensajes, propuestas, contrapropuestas, notas del mediador y términos de convenio. | Participantes y mediador asignado, según el dato; nunca el rol judicial. |
| `schema_judicial` | Demanda, expediente, actuaciones, contestación y resolución. | Partes y operadores autorizados del expediente. |
| `ia_uso_odr` | Interacciones de recomendación de mediación. | Solo el servicio ODR autorizado. |
| `ia_uso` y corpus judicial | Consultas judiciales y fragmentos de expedientes autorizados. | Servicio de IA y usuario judicial autorizado por `core-api`. |

## Cruce ODR → judicial

1. `core-api` recibe la solicitud del solicitante autenticado y verifica que puede actuar sobre el conflicto.
2. Un adaptador de canalización invoca **una función transaccional de base de datos** con `conflicto_id` y actor. El rol de ejecución solo obtiene permiso para ejecutar esa función; no puede hacer consultas libres a `schema_odr`.
3. La función verifica estado, resultado y, para la excepción parcial, la formalización del convenio. Construye el objeto con una lista positiva de campos, valida el esquema versionado y crea una sola demanda borrador. La operación completa confirma o revierte en una transacción de PostgreSQL.
4. `rol_app_judicial` no tiene `USAGE` ni `SELECT` sobre `schema_odr`. La API judicial no expone endpoints de mensajes, propuestas, notas ni convenios ODR.
5. Ningún documento ODR original se indexa en el corpus del expediente judicial. Los puntos pendientes del convenio parcial se revisan para excluir términos acordados y contexto de negociación antes de canalizar.

El resumen de la demanda debe derivarse de la **narrativa inicial** y, en la ruta parcial, de los **puntos pendientes**. No se usa un resumen automático de toda la conversación de mediación.

## Salidas secundarias

- Logs, trazas, eventos y notificaciones incluyen identificadores, tipo de evento y estado; excluyen cuerpos ODR, narrativa sensible, prompts y documentos.
- Las recomendaciones de mediación se registran solo en `ia_uso_odr`; las consultas judiciales, solo en `ia_uso`.
- El acceso RAG requiere autorización previa por expediente y aplica un filtro por `expediente_id` antes de la búsqueda. Las fuentes públicas sintéticas se separan de los documentos de cada expediente.
- Analítica usa conteos agregados y estados, nunca mensajes o notas.
- Un documento o interacción sintéticos creados para probar la mediación no se convierten automáticamente en material de entrenamiento o conocimiento judicial.

## Pruebas obligatorias del límite

| Prueba | Resultado esperado |
| --- | --- |
| Usuario judicial consulta tablas ODR, incluso con un `conflicto_id` conocido. | Permiso denegado. |
| Solicitud de canalización incluye campos extra como `mensajes` o `notas_mediador`. | Rechazo de esquema; no se crea demanda. |
| Acuerdo parcial sin formalizar intenta canalizar puntos pendientes. | Rechazo; ningún cambio de estado. |
| Mediación activa intenta canalizarse. | Rechazo; ningún cambio de estado. |
| Reintento de la misma canalización. | Devuelve el mismo `demanda_id`; no duplica demanda. |
| Juez A busca fragmentos del expediente de Juez B. | `403` antes de invocar RAG; no se revela contenido. |
| Se inspeccionan logs, avisos, eventos e índice judicial tras canalizar. | No aparece texto de negociación ni términos ya acordados. |

Estas pruebas serán parte de la aceptación del MVP, no solo comprobaciones manuales de interfaz.
