# Contratos de canalización

Habrá dos variantes versionadas del intercambio ODR → judicial:

- **Ordinaria:** datos de las partes, narrativa inicial de los hechos y materia del conflicto.
- **Convenio parcial formalizado:** esos mismos datos más los puntos pendientes que siguen controvertidos.

El contrato nunca incluye mensajes, propuestas, contrapropuestas, notas privadas del mediador ni los términos ya acordados. La implementación deberá validar el tipo de salida, el estado del convenio, la identidad de quien ejecuta la canalización y la ausencia de campos confidenciales antes de crear el expediente judicial.

Los esquemas de solicitud y respuesta se definirán aquí antes de escribir los controladores.
