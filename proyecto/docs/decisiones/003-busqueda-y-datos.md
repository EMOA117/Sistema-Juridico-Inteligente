# Decisión 003: búsqueda vectorial y datos del MVP

**Estado:** adoptada para demostración local de ESCOM el 26 de octubre de 2026.

## Datos disponibles

El proyecto **no cuenta con acceso autorizado a casos históricos del CJA o del Tribunal**. El MVP usará exclusivamente casos, personas, documentos y conversaciones **sintéticos**, identificados como tales. No se describirán como casos reales anonimizados ni se usarán para afirmar precisión jurídica o tasas de acuerdo reales.

El conjunto de demostración contendrá casos civiles y familiares inventados con resultados conocidos para cubrir: asunto mediable, asunto no mediable, invitación rechazada, mediación sin acuerdo, convenio total, convenio parcial, contestación en plazo, vencimiento sin contestación, resolución y cierre. Incluirá expedientes de dos jueces distintos para probar el aislamiento de RAG. Los escenarios se mantendrán reproducibles y se versionarán junto con sus resultados esperados.

La recomendación ODR podrá recuperar **ejemplos sintéticos similares**, siempre identificados en pantalla como ejemplos de demostración. Si no hay un ejemplo con similitud suficiente, responderá que no hay sugerencia fundamentada. La revisión del mediador y la voluntad de las partes siguen siendo necesarias.

## Motor elegido

Para la demostración local se adopta **MongoDB con búsqueda vectorial en contenedor Linux**, conservando el diseño de `ia_conocimiento` y los filtros por ámbito de acceso. MongoDB documenta que la imagen `mongodb/mongodb-atlas-local` incluye `mongod` y `mongot` para desarrollo y pruebas, y que no es un despliegue de producción. [Guía local oficial de MongoDB](https://www.mongodb.com/docs/search/self-managed/current/installation/quick-start/).

Para una eventual instalación autogestionada institucional se requerirá verificar versión y topología antes de migrar: la documentación actual de MongoDB exige MongoDB Community **8.3 o posterior** para instalar `mongot`, proceso que el operador debe administrar. [Requisitos de instalación](https://www.mongodb.com/docs/search/self-managed/current/installation/linux/), [arquitectura autogestionada](https://www.mongodb.com/docs/search/self-managed/current/).

La búsqueda usará embeddings locales BGE-M3 de 1024 dimensiones, como propone el documento de arquitectura. Los índices vectoriales incluirán campos de filtro para `acceso`, `materia` y `expediente_id`. MongoDB exige indexar los campos usados en el prefiltro de `$vectorSearch`; el filtro se aplica antes de recuperar vecinos. [Documentación de índices](https://www.mongodb.com/docs/vector-search/indexes/vector-search-type/), [documentación de consultas](https://www.mongodb.com/docs/vector-search/query/aggregation-stages/vector-search-stage/).

## Límite de acceso

`core-api` valida primero la sesión y la asignación del juez al expediente. `ia-service` recibe una consulta acotada y solo busca fragmentos de prueba marcados `PUBLICO` o del `expediente_id` autorizado. No busca en conversaciones ODR, convenios originales ni índices de otros expedientes. La respuesta incluye fuente, documento y página; si no hay evidencia recuperada, no genera una conclusión.

## Criterios para dar por lista la búsqueda

1. El entorno local inicia `mongod` y `mongot`, crea el índice y recupera un fragmento sintético esperado.
2. El mismo texto, consultado desde otro expediente, no devuelve fragmentos privados del primero.
3. Un índice vacío o el servicio de búsqueda indisponible produce un mensaje de indisponibilidad, sin inventar fuentes y sin bloquear el trámite principal.
4. Se mide latencia real antes de afirmar que se cumplen los tiempos propuestos en la documentación.

En esta computadora el cliente Docker está instalado, pero su motor Linux no estaba iniciado al hacer esta decisión. La capacidad quedó verificada en la documentación del proveedor; la prueba de ejecución local sigue siendo una condición de implementación.
