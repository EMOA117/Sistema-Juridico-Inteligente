# Contratos de canalización

Habrá dos variantes versionadas del intercambio ODR → judicial:

- **Ordinaria:** datos de las partes, narrativa inicial de los hechos y materia del conflicto. Cubre la vía directa, invitación no aceptada, mediación sin acuerdo y desistimiento de la mediación cuando el solicitante decide continuar judicialmente.
- **Convenio parcial formalizado:** esos mismos datos más los puntos pendientes que siguen controvertidos.

El contrato nunca incluye mensajes, propuestas, contrapropuestas, notas privadas del mediador ni los términos ya acordados. La implementación deberá validar el tipo de salida, el estado del convenio, la identidad de quien ejecuta la canalización y la ausencia de campos confidenciales antes de crear el expediente judicial.

El [esquema v1](canalizacion.v1.schema.json) define ambos objetos con `additionalProperties: false`. El sobre contiene `version`, `tipo`, `conflicto_id` y `origen` para control técnico; los datos sustantivos permitidos son `partes`, `narrativa_inicial`, `materia` y, solo en la variante parcial, `puntos_pendientes`. El identificador del convenio se consulta dentro de ODR para comprobar su formalización, pero no se copia al expediente judicial.

La validación del esquema no sustituye la revisión de contenido: los puntos pendientes no deben incorporar términos ya acordados ni transcripciones de la negociación. La función de canalización realiza esta comprobación y crea el borrador en una transacción; una solicitud repetida devuelve la demanda ya creada.
