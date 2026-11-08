-- P8/P10/P15: cola de indexación documental hacia ia-service. Solo documentos JUDICIALES; nada del dominio ODR.
BEGIN;
CREATE TABLE schema_judicial.indexacion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    expediente_id uuid NOT NULL REFERENCES schema_judicial.expediente(id),
    documento_id uuid REFERENCES nucleo_comun.documento(id),
    tipo text NOT NULL CHECK (tipo IN ('DEMANDA','ANEXO')),
    estado text NOT NULL DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE','HECHA','FALLIDA')),
    intentos int NOT NULL DEFAULT 0,
    fragmentos int,
    creado_en timestamptz NOT NULL DEFAULT now(),
    procesado_en timestamptz,
    CHECK ((tipo = 'ANEXO') = (documento_id IS NOT NULL))
);
CREATE INDEX ix_indexacion_pendiente ON schema_judicial.indexacion (creado_en) WHERE estado = 'PENDIENTE';

-- Material mínimo para indexar: texto o clave del objeto, materia y nombres a anonimizar. Sin datos ODR.
CREATE FUNCTION schema_judicial.material_indexacion(p_id uuid)
RETURNS TABLE (expediente_id uuid, materia text, tipo text, texto text, documento text, clave_objeto text,
               version_objeto text, documento_id uuid, nombres text[])
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, nucleo_comun, schema_judicial, pg_temp AS $$
    SELECT i.expediente_id, d.materia, i.tipo,
           CASE WHEN i.tipo = 'DEMANDA' THEN d.texto_final END,
           CASE WHEN i.tipo = 'DEMANDA' THEN 'Demanda EXP ' || e.numero ELSE doc.nombre END,
           doc.clave_objeto, doc.version_objeto, i.documento_id,
           ARRAY(SELECT p.nombre FROM nucleo_comun.parte p WHERE p.conflicto_id = d.conflicto_id)
    FROM schema_judicial.indexacion i
    JOIN schema_judicial.expediente e ON e.id = i.expediente_id
    JOIN schema_judicial.demanda d ON d.id = e.demanda_id
    LEFT JOIN nucleo_comun.documento doc ON doc.id = i.documento_id AND doc.dominio = 'JUDICIAL'
    WHERE i.id = p_id
$$;

GRANT INSERT ON schema_judicial.indexacion TO rol_app_judicial;
ALTER TABLE schema_judicial.indexacion ENABLE ROW LEVEL SECURITY;
CREATE POLICY indexacion_alta ON schema_judicial.indexacion FOR INSERT TO rol_app_judicial
WITH CHECK (EXISTS (SELECT 1 FROM schema_judicial.expediente e WHERE e.id = expediente_id));
GRANT USAGE ON SCHEMA schema_judicial TO rol_tareas;
GRANT SELECT, UPDATE (estado, intentos, fragmentos, procesado_en) ON schema_judicial.indexacion TO rol_tareas;
CREATE POLICY indexacion_tareas ON schema_judicial.indexacion TO rol_tareas USING (true) WITH CHECK (true);
REVOKE ALL ON FUNCTION schema_judicial.material_indexacion(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION schema_judicial.material_indexacion(uuid) TO rol_tareas;
COMMIT;
