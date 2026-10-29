# Intercambio entre el núcleo y el servicio de IA

`ia-service` escucha solo en la red interna. `core-api` autentica al operador y autoriza el recurso antes de llamar al servicio. Las llamadas usan identidad de servicio y cifrado en tránsito.

## Clasificación inicial

`POST /interno/orientacion/clasificar`

Solicitud: `{ "conflicto_id": "uuid", "narrativa_inicial": "texto capturado antes de mediar", "materias_permitidas": ["CIVIL", "FAMILIAR"] }`.

Respuesta: `{ "materia_sugerida": "CIVIL", "confianza": 0.82, "complejidad": "MEDIA", "mediable_sugerido": true, "motivos": ["explicación breve"], "modelo_version": "demo-1" }`.

El núcleo comprueba que ya se capturaron ambas partes antes de enviar el relato. No envía nombres, contactos ni mensajes de mediación. La sugerencia requiere confirmación humana y un resultado de baja confianza permite orientación manual.

## Sugerencia de turno judicial

`POST /interno/turnos/sugerir`

Solicitud:

```json
{
  "expediente_id": "uuid",
  "materia": "CIVIL",
  "candidatos": [
    { "juzgado_id": "uuid", "juez_id": "uuid", "especialidad": "CIVIL", "expedientes_activos": 12 }
  ]
}
```

Respuesta:

```json
{
  "expediente_id": "uuid",
  "sugerencias": [
    { "juzgado_id": "uuid", "juez_id": "uuid", "puntaje": 0.78, "justificacion": "Especialidad y carga" }
  ],
  "modelo_version": "demo-1"
}
```

No se envían nombres de las partes, hechos, demanda ni datos ODR. `core-api` valida que los identificadores devueltos pertenezcan a la lista enviada y exige confirmación de un operador. Si IA falla, el turno puede realizarse manualmente.

## Búsqueda RAG para juez

`POST /interno/rag/consultar`

Solicitud: `{ "expediente_id": "uuid", "materia": "CIVIL", "consulta": "pregunta del juez", "documentos_permitidos": ["uuid"], "incluir_fuentes_publicas": true }`.

Respuesta: `{ "estado": "CON_FUENTES", "sintesis": "texto basado en fragmentos", "fuentes": [{ "documento_id": "uuid", "pagina": 2, "fragmento": "texto recuperado" }], "modelo_version": "demo-1" }`. Si no hay fragmentos permitidos, devuelve `estado: "SIN_FUENTES"`, síntesis vacía y lista de fuentes vacía.

`core-api` valida antes que el juez esté asignado al expediente y construye la lista de documentos autorizados. `ia-service` aplica el filtro por `expediente_id` y esos identificadores en el índice; no recibe credenciales de PostgreSQL ni consulta ODR. La salida se registra en `ia_uso` con los controles de acceso correspondientes.
