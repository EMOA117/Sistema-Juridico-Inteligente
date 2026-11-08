-- Catálogos, folios, documentos y permisos que necesita la API HTTP. No modifica migraciones previas.
BEGIN;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_tareas') THEN CREATE ROLE rol_tareas NOLOGIN; END IF;
END $$;

-- La validación de transiciones consulta ODR y judicial: se ejecuta como propietario para que
-- ningún rol de aplicación necesite leer el dominio ajeno.
ALTER FUNCTION nucleo_comun.validar_estado_conflicto() SECURITY DEFINER;

-- Identidad (P1): CURP ciudadana, secreto TOTP cifrado y bloqueo por intentos fallidos.
ALTER TABLE nucleo_comun.usuario
  ADD COLUMN curp char(18) UNIQUE CHECK (curp ~ '^[A-Z][AEIOUX][A-Z]{2}[0-9]{6}[HM][A-Z]{5}[A-Z0-9][0-9]$'),
  ADD COLUMN mfa_secreto_cifrado bytea,
  ADD COLUMN intentos_fallidos int NOT NULL DEFAULT 0,
  ADD COLUMN bloqueado_hasta timestamptz,
  ADD COLUMN debe_cambiar_password boolean NOT NULL DEFAULT false,
  ADD COLUMN cargo text,
  ADD CHECK (NOT mfa_habilitado OR mfa_secreto_cifrado IS NOT NULL);
GRANT UPDATE (intentos_fallidos, bloqueado_hasta) ON nucleo_comun.usuario TO rol_auth;
CREATE POLICY usuario_auth_intentos ON nucleo_comun.usuario FOR UPDATE TO rol_auth USING (true) WITH CHECK (true);

-- Folios legibles (CF-2027-000123 y 458/2027).
CREATE SEQUENCE nucleo_comun.folio_conflicto_seq;
CREATE SEQUENCE schema_judicial.numero_expediente_seq;
ALTER TABLE nucleo_comun.conflicto
  ADD COLUMN folio text UNIQUE NOT NULL
    DEFAULT 'CF-' || to_char(now(), 'YYYY') || '-' || lpad(nextval('nucleo_comun.folio_conflicto_seq')::text, 6, '0'),
  ADD COLUMN complejidad text CHECK (complejidad IN ('BAJA','MEDIA','ALTA')),
  ADD COLUMN confianza_clasificacion numeric(4,3) CHECK (confianza_clasificacion BETWEEN 0 AND 1),
  ADD COLUMN interaccion_ia_id char(24) CHECK (interaccion_ia_id ~ '^[0-9a-f]{24}$');
ALTER TABLE schema_judicial.expediente
  ADD COLUMN numero text UNIQUE NOT NULL
    DEFAULT nextval('schema_judicial.numero_expediente_seq')::text || '/' || to_char(now(), 'YYYY');

-- Propuestas estructuradas (RF3.2): autor, número y respuesta.
ALTER TABLE schema_odr.propuesta
  ADD COLUMN autor_id uuid REFERENCES nucleo_comun.usuario(id),
  ADD COLUMN estado text NOT NULL DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE','ACEPTADA','RECHAZADA')),
  ADD COLUMN respondida_por uuid REFERENCES nucleo_comun.usuario(id);
CREATE INDEX ix_mensaje_hilo ON schema_odr.mensaje (mediacion_id, creado_en);
CREATE INDEX ix_propuesta_hilo ON schema_odr.propuesta (mediacion_id, creado_en);

-- Juzgados y adscripción de jueces (RF7.7); la carga se calcula, no se guarda.
CREATE TABLE schema_judicial.juzgado (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre text NOT NULL UNIQUE,
    materia text NOT NULL CHECK (materia IN ('CIVIL','FAMILIAR')),
    activo boolean NOT NULL DEFAULT true
);
CREATE TABLE schema_judicial.juez_adscripcion (
    juez_id uuid PRIMARY KEY REFERENCES nucleo_comun.usuario(id),
    juzgado_id uuid NOT NULL REFERENCES schema_judicial.juzgado(id),
    especialidad text NOT NULL CHECK (especialidad IN ('CIVIL','FAMILIAR'))
);
ALTER TABLE schema_judicial.expediente ADD COLUMN juzgado_id uuid REFERENCES schema_judicial.juzgado(id);
CREATE INDEX ix_expediente_juez ON schema_judicial.expediente (juez_id, estado);
CREATE VIEW schema_judicial.v_carga_jueces AS
  SELECT a.juez_id, a.juzgado_id, j.nombre AS juzgado, a.especialidad,
         count(e.id) FILTER (WHERE e.estado NOT IN ('CERRADO','DESECHADO')) AS expedientes_activos
  FROM schema_judicial.juez_adscripcion a
  JOIN schema_judicial.juzgado j ON j.id = a.juzgado_id AND j.activo
  LEFT JOIN schema_judicial.expediente e ON e.juez_id = a.juez_id
  GROUP BY a.juez_id, a.juzgado_id, j.nombre, a.especialidad;

-- Actuaciones del expediente (dictamen, prevención, notas) como registros nuevos, nunca sobrescritos.
CREATE TABLE schema_judicial.actuacion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    expediente_id uuid NOT NULL REFERENCES schema_judicial.expediente(id),
    usuario_id uuid NOT NULL REFERENCES nucleo_comun.usuario(id),
    tipo text NOT NULL CHECK (tipo IN ('DICTAMEN_ADMITIR','DICTAMEN_PREVENIR','DICTAMEN_DESECHAR','CORRECCION','NOTA')),
    texto text,
    documento_id uuid,
    ocurrido_en timestamptz NOT NULL DEFAULT now()
);

-- Documentos oficiales: el archivo vive en el almacén de objetos; aquí, su referencia y huella.
CREATE TABLE nucleo_comun.documento (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dominio text NOT NULL CHECK (dominio IN ('ODR','JUDICIAL')),
    conflicto_id uuid REFERENCES nucleo_comun.conflicto(id),
    expediente_id uuid REFERENCES schema_judicial.expediente(id),
    tipo text NOT NULL CHECK (tipo IN ('ANEXO','DEMANDA','CONVENIO','RESOLUCION','DICTAMEN','CONTESTACION')),
    nombre text NOT NULL,
    clave_objeto text NOT NULL UNIQUE,
    version_objeto text,
    hash_sha256 char(64) NOT NULL CHECK (hash_sha256 ~ '^[0-9a-f]{64}$'),
    paginas int,
    subido_por uuid NOT NULL REFERENCES nucleo_comun.usuario(id),
    creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_documento_expediente ON nucleo_comun.documento (expediente_id, creado_en);
CREATE INDEX ix_bitacora_entidad ON nucleo_comun.bitacora (entidad, entidad_id);

-- Permisos ---------------------------------------------------------------------------------------
GRANT INSERT ON nucleo_comun.bitacora TO rol_app_admin, rol_auth, rol_tareas;
GRANT USAGE ON SEQUENCE nucleo_comun.bitacora_id_seq TO rol_app_admin, rol_auth, rol_tareas;
GRANT USAGE ON SEQUENCE nucleo_comun.folio_conflicto_seq TO rol_app_nucleo;
GRANT USAGE ON SEQUENCE schema_judicial.numero_expediente_seq TO rol_app_judicial;

-- ODR cambia el estado del conflicto (documento §11.3.5) sin poder tocar otras columnas.
GRANT UPDATE (estado) ON nucleo_comun.conflicto TO rol_app_odr;
CREATE POLICY conflicto_odr_estado ON nucleo_comun.conflicto FOR UPDATE TO rol_app_odr
USING (nucleo_comun.es_parte(id) OR nucleo_comun.es_mediador_conflicto(id))
WITH CHECK (nucleo_comun.es_parte(id) OR nucleo_comun.es_mediador_conflicto(id));

-- Juzgados: administración gestiona; judicial consulta.
GRANT SELECT, INSERT, UPDATE ON schema_judicial.juzgado, schema_judicial.juez_adscripcion TO rol_app_admin;
GRANT SELECT ON schema_judicial.juzgado, schema_judicial.juez_adscripcion, schema_judicial.v_carga_jueces TO rol_app_judicial, rol_app_admin;
GRANT UPDATE (juzgado_id) ON schema_judicial.expediente TO rol_app_admin;
-- Administración ve solo metadatos de la demanda para el turno, nunca el texto.
GRANT SELECT (id, conflicto_id, estado, origen, materia, creada_en) ON schema_judicial.demanda TO rol_app_admin;
CREATE POLICY demanda_admin_metadatos ON schema_judicial.demanda FOR SELECT TO rol_app_admin USING (true);
GRANT SELECT (id, nombre, correo) ON nucleo_comun.usuario TO rol_app_admin;
CREATE POLICY usuario_admin_directorio ON nucleo_comun.usuario FOR SELECT TO rol_app_admin USING (true);
GRANT SELECT ON nucleo_comun.usuario_rol TO rol_app_admin;
CREATE POLICY roles_admin ON nucleo_comun.usuario_rol FOR SELECT TO rol_app_admin USING (true);
-- Los jueces ven nombres de usuarios con quien comparten expediente (partes) vía parte; nada más.

GRANT SELECT, INSERT ON schema_judicial.actuacion TO rol_app_judicial;
ALTER TABLE schema_judicial.actuacion ENABLE ROW LEVEL SECURITY;
CREATE POLICY actuacion_relacion ON schema_judicial.actuacion TO rol_app_judicial
USING (EXISTS (SELECT 1 FROM schema_judicial.expediente e WHERE e.id = expediente_id))
WITH CHECK (usuario_id = nucleo_comun.actor_id()
            AND EXISTS (SELECT 1 FROM schema_judicial.expediente e WHERE e.id = expediente_id));

GRANT SELECT, INSERT ON nucleo_comun.documento TO rol_app_odr, rol_app_judicial;
ALTER TABLE nucleo_comun.documento ENABLE ROW LEVEL SECURITY;
CREATE POLICY documento_odr ON nucleo_comun.documento TO rol_app_odr
USING (dominio = 'ODR' AND (nucleo_comun.es_parte(conflicto_id) OR nucleo_comun.es_mediador_conflicto(conflicto_id)))
WITH CHECK (dominio = 'ODR' AND subido_por = nucleo_comun.actor_id());
CREATE POLICY documento_judicial ON nucleo_comun.documento TO rol_app_judicial
USING (dominio = 'JUDICIAL' AND (
        (expediente_id IS NOT NULL AND EXISTS (SELECT 1 FROM schema_judicial.expediente e WHERE e.id = expediente_id))
        OR (expediente_id IS NULL AND nucleo_comun.es_parte(conflicto_id))))
WITH CHECK (dominio = 'JUDICIAL' AND subido_por = nucleo_comun.actor_id());

-- El solicitante reenvía una demanda prevenida (RF7.4) sin obtener permiso general de edición.
CREATE FUNCTION schema_judicial.reenviar_correccion(p_expediente_id uuid, p_texto text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, nucleo_comun, schema_judicial, pg_temp AS $$
DECLARE e schema_judicial.expediente%ROWTYPE; d schema_judicial.demanda%ROWTYPE;
BEGIN
    SELECT * INTO e FROM schema_judicial.expediente WHERE id = p_expediente_id FOR UPDATE;
    SELECT * INTO d FROM schema_judicial.demanda WHERE id = e.demanda_id;
    IF NOT FOUND OR NOT nucleo_comun.es_solicitante(d.conflicto_id) THEN RAISE EXCEPTION 'Expediente no autorizado'; END IF;
    IF e.estado <> 'PREVENIDO' THEN RAISE EXCEPTION 'Solo una demanda prevenida puede corregirse'; END IF;
    IF nullif(btrim(p_texto), '') IS NULL THEN RAISE EXCEPTION 'La corrección no puede estar vacía'; END IF;
    UPDATE schema_judicial.demanda SET texto_final = p_texto WHERE id = d.id;
    INSERT INTO schema_judicial.actuacion (expediente_id, usuario_id, tipo, texto)
    VALUES (e.id, nucleo_comun.actor_id(), 'CORRECCION', 'Demanda corregida y reenviada');
    UPDATE schema_judicial.expediente SET estado = 'EN_REVISION' WHERE id = e.id;
END $$;
REVOKE ALL ON FUNCTION schema_judicial.reenviar_correccion(uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION schema_judicial.reenviar_correccion(uuid, text) TO rol_app_judicial;

-- Analítica: solo conteos agregados, sin contenido (P14).
CREATE VIEW analitica.v_indicadores AS
  SELECT
    (SELECT count(*) FROM nucleo_comun.conflicto) AS conflictos_recibidos,
    (SELECT count(*) FROM schema_odr.mediacion) AS mediaciones_iniciadas,
    (SELECT count(*) FROM schema_odr.mediacion WHERE resultado IN ('ACUERDO_TOTAL','ACUERDO_PARCIAL')) AS acuerdos,
    (SELECT count(*) FROM schema_odr.mediacion WHERE estado = 'CONCLUIDA') AS mediaciones_concluidas,
    (SELECT count(*) FROM schema_judicial.demanda WHERE origen <> 'DIRECTA') AS canalizados,
    (SELECT count(*) FROM schema_judicial.expediente) AS expedientes;
CREATE VIEW analitica.v_conflictos_por_materia AS
  SELECT materia, count(*) AS total FROM nucleo_comun.conflicto WHERE materia IS NOT NULL GROUP BY materia;
CREATE VIEW analitica.v_expedientes_por_estado AS
  SELECT estado, count(*) AS total FROM schema_judicial.expediente GROUP BY estado;
GRANT USAGE ON SCHEMA analitica TO rol_app_admin;
GRANT SELECT ON ALL TABLES IN SCHEMA analitica TO rol_app_admin;
COMMIT;
