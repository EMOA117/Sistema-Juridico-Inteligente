-- RF3.4–RF3.8 y RF4.1–RF4.2: padrón de mediadores, asignación, agenda, notas y revisión del convenio.
BEGIN;

CREATE TABLE schema_odr.mediador (
    usuario_id uuid PRIMARY KEY REFERENCES nucleo_comun.usuario(id),
    num_certificacion text NOT NULL UNIQUE,
    especialidades text[] NOT NULL CHECK (especialidades <@ ARRAY['CIVIL','FAMILIAR'] AND cardinality(especialidades) > 0),
    max_casos int NOT NULL DEFAULT 10 CHECK (max_casos BETWEEN 1 AND 50),
    activo boolean NOT NULL DEFAULT true
);

ALTER TABLE schema_odr.mediacion DROP CONSTRAINT mediacion_estado_check;
ALTER TABLE schema_odr.mediacion
  ADD CONSTRAINT mediacion_estado_check CHECK (estado IN ('INVITACION_ENVIADA','EN_NEGOCIACION','CON_MEDIADOR','PENDIENTE_FORMALIZACION','CONCLUIDA')),
  ADD CHECK (estado <> 'CON_MEDIADOR' OR mediador_id IS NOT NULL);

CREATE TABLE schema_odr.solicitud_mediador (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mediacion_id uuid NOT NULL REFERENCES schema_odr.mediacion(id),
    solicitante_id uuid NOT NULL REFERENCES nucleo_comun.usuario(id),
    mediador_id uuid REFERENCES nucleo_comun.usuario(id),
    creada_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE schema_odr.sesion_mediacion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mediacion_id uuid NOT NULL REFERENCES schema_odr.mediacion(id),
    mediador_id uuid NOT NULL REFERENCES nucleo_comun.usuario(id),
    inicio timestamptz NOT NULL,
    duracion_min int NOT NULL DEFAULT 60 CHECK (duracion_min BETWEEN 15 AND 240),
    modalidad text NOT NULL CHECK (modalidad IN ('VIDEOLLAMADA_CONJUNTA','SESION_PRIVADA','TELEFONICA')),
    enlace text,
    estado text NOT NULL DEFAULT 'PROGRAMADA' CHECK (estado IN ('PROGRAMADA','CANCELADA','REALIZADA')),
    creada_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_sesion_mediador ON schema_odr.sesion_mediacion (mediador_id, inicio);

-- RF4.2: cada parte revisa y aprueba el borrador; editar el convenio invalida las aprobaciones.
ALTER TABLE schema_odr.convenio ADD COLUMN redactado_por uuid REFERENCES nucleo_comun.usuario(id),
                                ADD COLUMN actualizado_en timestamptz NOT NULL DEFAULT now();
CREATE TABLE schema_odr.aprobacion_convenio (
    convenio_id uuid NOT NULL REFERENCES schema_odr.convenio(id),
    usuario_id uuid NOT NULL REFERENCES nucleo_comun.usuario(id),
    aprobado_en timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (convenio_id, usuario_id)
);

-- Carga y asignaciones: solo metadatos (sin mensajes, propuestas ni notas) para administración.
CREATE VIEW schema_odr.v_carga_mediadores AS
  SELECT md.usuario_id, u.nombre, md.num_certificacion, md.especialidades, md.max_casos, md.activo,
         count(m.id) FILTER (WHERE m.estado <> 'CONCLUIDA') AS mediaciones_activas
  FROM schema_odr.mediador md JOIN nucleo_comun.usuario u ON u.id = md.usuario_id
  LEFT JOIN schema_odr.mediacion m ON m.mediador_id = md.usuario_id
  GROUP BY md.usuario_id, u.nombre, md.num_certificacion, md.especialidades, md.max_casos, md.activo;
CREATE VIEW schema_odr.v_asignaciones AS
  SELECT m.id AS mediacion_id, c.folio, c.materia, m.estado, m.mediador_id, u.nombre AS mediador,
         (SELECT max(s.creada_en) FROM schema_odr.solicitud_mediador s WHERE s.mediacion_id = m.id) AS solicitado_en
  FROM schema_odr.mediacion m JOIN nucleo_comun.conflicto c ON c.id = m.conflicto_id
  LEFT JOIN nucleo_comun.usuario u ON u.id = m.mediador_id
  WHERE m.estado <> 'CONCLUIDA';

-- Datos públicos del mediador asignado (nombre y certificación) para las partes.
CREATE FUNCTION schema_odr.mediador_publico(p_mediacion_id uuid)
RETURNS TABLE (nombre text, num_certificacion text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, nucleo_comun, schema_odr, pg_temp AS $$
    SELECT u.nombre, md.num_certificacion FROM schema_odr.mediacion m
    JOIN nucleo_comun.usuario u ON u.id = m.mediador_id JOIN schema_odr.mediador md ON md.usuario_id = m.mediador_id
    WHERE m.id = p_mediacion_id AND (nucleo_comun.es_parte(m.conflicto_id) OR m.mediador_id = nucleo_comun.actor_id())
$$;

-- RF3.4: una parte solicita mediador (asignación automática) o administración reasigna a uno concreto.
CREATE FUNCTION schema_odr.asignar_mediador(p_mediacion_id uuid, p_mediador_id uuid DEFAULT NULL)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, nucleo_comun, schema_odr, pg_temp AS $$
DECLARE actor uuid := nucleo_comun.actor_id(); m schema_odr.mediacion%ROWTYPE; c nucleo_comun.conflicto%ROWTYPE;
DECLARE es_admin boolean; elegido uuid; anterior uuid;
BEGIN
    SELECT * INTO m FROM schema_odr.mediacion WHERE id = p_mediacion_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Mediación no encontrada'; END IF;
    SELECT * INTO c FROM nucleo_comun.conflicto WHERE id = m.conflicto_id;
    es_admin := EXISTS (SELECT 1 FROM nucleo_comun.usuario_rol WHERE usuario_id = actor AND rol = 'ADMINISTRADOR');
    IF NOT es_admin AND NOT nucleo_comun.es_parte(c.id) THEN RAISE EXCEPTION 'Mediación no autorizada'; END IF;
    IF NOT es_admin AND p_mediador_id IS NOT NULL THEN RAISE EXCEPTION 'Las partes no eligen mediador'; END IF;
    IF m.estado NOT IN ('EN_NEGOCIACION','CON_MEDIADOR','PENDIENTE_FORMALIZACION') THEN
        RAISE EXCEPTION 'La mediación no admite asignar mediador en su estado actual';
    END IF;
    IF NOT es_admin AND m.mediador_id IS NOT NULL THEN RETURN m.mediador_id; END IF;   -- idempotente

    IF p_mediador_id IS NOT NULL THEN
        SELECT usuario_id INTO elegido FROM schema_odr.v_carga_mediadores
        WHERE usuario_id = p_mediador_id AND activo AND c.materia = ANY (especialidades);
        IF elegido IS NULL THEN RAISE EXCEPTION 'El mediador no está activo o no atiende la materia'; END IF;
    ELSE
        SELECT usuario_id INTO elegido FROM schema_odr.v_carga_mediadores
        WHERE activo AND c.materia = ANY (especialidades) AND mediaciones_activas < max_casos
        ORDER BY mediaciones_activas, usuario_id LIMIT 1;
        IF elegido IS NULL THEN RAISE EXCEPTION 'No hay mediadores disponibles para la materia; intenta más tarde'; END IF;
    END IF;

    anterior := m.mediador_id;
    UPDATE schema_odr.mediacion SET mediador_id = elegido,
           estado = CASE WHEN estado = 'EN_NEGOCIACION' THEN 'CON_MEDIADOR' ELSE estado END
    WHERE id = m.id;
    INSERT INTO schema_odr.solicitud_mediador (mediacion_id, solicitante_id, mediador_id) VALUES (m.id, actor, elegido);
    INSERT INTO nucleo_comun.bitacora (usuario_id, entidad, entidad_id, accion, estado_anterior, estado_nuevo, operacion_id)
    VALUES (actor, 'mediacion', m.id, CASE WHEN anterior IS NULL THEN 'MEDIADOR_ASIGNADO' ELSE 'MEDIADOR_REASIGNADO' END,
            m.estado, CASE WHEN m.estado = 'EN_NEGOCIACION' THEN 'CON_MEDIADOR' ELSE m.estado END, gen_random_uuid());
    PERFORM nucleo_comun.notificar_usuario(elegido, 'MEDIACION_ASIGNADA', c.folio, 'mediacion', m.id);
    PERFORM nucleo_comun.notificar(c.id, 'MEDIADOR_ASIGNADO', 'mediacion', m.id, NULL, false);
    RETURN elegido;
END $$;

-- Permisos ---------------------------------------------------------------------------------------
REVOKE ALL ON FUNCTION schema_odr.mediador_publico(uuid), schema_odr.asignar_mediador(uuid, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION schema_odr.mediador_publico(uuid) TO rol_app_odr;
GRANT EXECUTE ON FUNCTION schema_odr.asignar_mediador(uuid, uuid) TO rol_app_odr, rol_app_admin;

GRANT SELECT, INSERT, UPDATE ON schema_odr.solicitud_mediador, schema_odr.sesion_mediacion,
                               schema_odr.aprobacion_convenio TO rol_app_odr;
GRANT DELETE ON schema_odr.aprobacion_convenio TO rol_app_odr;   -- al editar el borrador se reinician aprobaciones
GRANT SELECT ON schema_odr.mediador TO rol_app_odr;
-- Las propuestas siguen siendo inmutables (003); solo se registra la respuesta de la otra parte.
GRANT UPDATE (estado, respondida_por) ON schema_odr.propuesta TO rol_app_odr;

-- Administración: padrón y asignaciones; ningún acceso a mensajes, propuestas, notas ni convenios.
GRANT USAGE ON SCHEMA schema_odr TO rol_app_admin;
GRANT SELECT, INSERT, UPDATE ON schema_odr.mediador TO rol_app_admin;
GRANT SELECT ON schema_odr.v_carga_mediadores, schema_odr.v_asignaciones TO rol_app_admin;

ALTER TABLE schema_odr.mediador ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_odr.solicitud_mediador ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_odr.sesion_mediacion ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_odr.aprobacion_convenio ENABLE ROW LEVEL SECURITY;
CREATE POLICY mediador_admin ON schema_odr.mediador TO rol_app_admin USING (true) WITH CHECK (true);
CREATE POLICY mediador_lectura ON schema_odr.mediador FOR SELECT TO rol_app_odr USING (true);
CREATE POLICY solicitud_relacion ON schema_odr.solicitud_mediador TO rol_app_odr
USING (EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id))
WITH CHECK (EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id));
CREATE POLICY sesion_lectura ON schema_odr.sesion_mediacion FOR SELECT TO rol_app_odr
USING (EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id));
CREATE POLICY sesion_mediador ON schema_odr.sesion_mediacion FOR INSERT TO rol_app_odr
WITH CHECK (mediador_id = nucleo_comun.actor_id()
            AND EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id AND m.mediador_id = nucleo_comun.actor_id()));
CREATE POLICY sesion_mediador_edicion ON schema_odr.sesion_mediacion FOR UPDATE TO rol_app_odr
USING (mediador_id = nucleo_comun.actor_id()) WITH CHECK (mediador_id = nucleo_comun.actor_id());
CREATE POLICY aprobacion_relacion ON schema_odr.aprobacion_convenio TO rol_app_odr
USING (EXISTS (SELECT 1 FROM schema_odr.convenio v WHERE v.id = convenio_id))
WITH CHECK (EXISTS (SELECT 1 FROM schema_odr.convenio v WHERE v.id = convenio_id));
COMMIT;
