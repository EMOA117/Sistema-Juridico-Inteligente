-- Iteración ODR: aplicar después de 004 como propietario de la base.
BEGIN;
ALTER TABLE nucleo_comun.usuario ADD COLUMN mfa_secreto text;
ALTER TABLE nucleo_comun.conflicto ADD COLUMN titulo text NOT NULL DEFAULT 'Conflicto';
ALTER TABLE nucleo_comun.bitacora ADD COLUMN motivo text NOT NULL DEFAULT 'OPERACION_USUARIO';
ALTER TABLE schema_odr.mediacion ADD COLUMN solicitud_mediador_en timestamptz;
ALTER TABLE schema_odr.invitacion ADD COLUMN respondida_en timestamptz;
CREATE UNIQUE INDEX invitacion_por_mediacion ON schema_odr.invitacion(mediacion_id);
ALTER TABLE schema_odr.propuesta ADD COLUMN autor_id uuid REFERENCES nucleo_comun.usuario;
ALTER TABLE schema_odr.propuesta ADD COLUMN responde_a_id uuid REFERENCES schema_odr.propuesta;
ALTER TABLE schema_odr.propuesta ADD COLUMN estado text NOT NULL DEFAULT 'PENDIENTE'
  CHECK (estado IN ('PENDIENTE','ACEPTADA','RECHAZADA'));
ALTER TABLE schema_odr.propuesta ADD COLUMN monto numeric(14,2) CHECK (monto >= 0);
ALTER TABLE schema_odr.propuesta ADD COLUMN respondida_por uuid REFERENCES nucleo_comun.usuario;
ALTER TABLE schema_odr.convenio ADD COLUMN documento_cifrado bytea;
ALTER TABLE schema_odr.convenio ADD COLUMN modo_firma text CHECK (modo_firma = 'DEMOSTRACION');
CREATE TABLE schema_odr.sesion (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mediacion_id uuid NOT NULL REFERENCES schema_odr.mediacion,
  fecha_hora timestamptz NOT NULL, enlace text NOT NULL,
  creado_en timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE schema_odr.nota_mediador ADD COLUMN sesion_id uuid REFERENCES schema_odr.sesion;
CREATE TABLE schema_odr.firma (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  convenio_id uuid NOT NULL REFERENCES schema_odr.convenio,
  usuario_id uuid NOT NULL REFERENCES nucleo_comun.usuario,
  hash_sha256 text NOT NULL CHECK (length(hash_sha256) = 64),
  modo text NOT NULL CHECK (modo = 'DEMOSTRACION'),
  operacion_id uuid NOT NULL UNIQUE,
  firmado_en timestamptz NOT NULL DEFAULT now(),
  UNIQUE(convenio_id, usuario_id)
);
CREATE TABLE nucleo_comun.notificacion (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  destinatario_id uuid REFERENCES nucleo_comun.usuario,
  correo_destino text NOT NULL,
  conflicto_id uuid NOT NULL REFERENCES nucleo_comun.conflicto,
  evento text NOT NULL, leida boolean NOT NULL DEFAULT false,
  creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON nucleo_comun.notificacion(correo_destino, creado_en DESC);
CREATE INDEX ON schema_odr.mensaje(mediacion_id, creado_en);
CREATE INDEX ON schema_odr.propuesta(mediacion_id, creado_en);

-- Las guardas cruzan esquemas; se ejecutan como propietario con search_path fijo.
ALTER FUNCTION nucleo_comun.validar_estado_conflicto() SECURITY DEFINER;
GRANT UPDATE (estado) ON nucleo_comun.conflicto TO rol_app_odr;
CREATE POLICY conflicto_odr_estado ON nucleo_comun.conflicto FOR UPDATE TO rol_app_odr
USING (nucleo_comun.es_parte(id) OR nucleo_comun.es_mediador_conflicto(id))
WITH CHECK (nucleo_comun.es_parte(id) OR nucleo_comun.es_mediador_conflicto(id));
GRANT UPDATE (estado, respondida_por) ON schema_odr.propuesta TO rol_app_odr;
GRANT SELECT, INSERT ON schema_odr.sesion, schema_odr.firma TO rol_app_odr;
ALTER TABLE schema_odr.sesion ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_odr.firma ENABLE ROW LEVEL SECURITY;
CREATE POLICY sesion_relacion ON schema_odr.sesion TO rol_app_odr
USING (EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id))
WITH CHECK (EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id AND m.mediador_id = nucleo_comun.actor_id()));
CREATE POLICY firma_relacion ON schema_odr.firma TO rol_app_odr
USING (EXISTS (SELECT 1 FROM schema_odr.convenio v WHERE v.id = convenio_id))
WITH CHECK (usuario_id = nucleo_comun.actor_id() AND EXISTS (SELECT 1 FROM schema_odr.convenio v WHERE v.id = convenio_id));
GRANT SELECT, INSERT, UPDATE ON nucleo_comun.notificacion TO rol_app_nucleo;
GRANT INSERT ON nucleo_comun.notificacion TO rol_app_odr;
ALTER TABLE nucleo_comun.notificacion ENABLE ROW LEVEL SECURITY;
CREATE POLICY notificacion_propia ON nucleo_comun.notificacion TO rol_app_nucleo
USING (destinatario_id = nucleo_comun.actor_id())
WITH CHECK (destinatario_id = nucleo_comun.actor_id());
CREATE POLICY notificacion_emision ON nucleo_comun.notificacion FOR INSERT TO rol_app_odr
WITH CHECK (nucleo_comun.es_parte(conflicto_id) OR nucleo_comun.es_mediador_conflicto(conflicto_id));

-- Registro/login vincula invitaciones únicamente al correo de la cuenta autenticada.
-- El MVP usa correos sintéticos; verificación institucional de correo pendiente.
CREATE FUNCTION nucleo_comun.vincular_invitaciones() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE correo_actor text;
BEGIN
 SELECT correo INTO correo_actor FROM nucleo_comun.usuario WHERE id = nucleo_comun.actor_id() AND activo;
 UPDATE nucleo_comun.parte SET usuario_id = nucleo_comun.actor_id()
 WHERE lower(correo) = correo_actor AND usuario_id IS NULL AND rol = 'DEMANDADO';
 UPDATE nucleo_comun.notificacion SET destinatario_id = nucleo_comun.actor_id()
 WHERE correo_destino = correo_actor AND destinatario_id IS NULL;
END $$;
REVOKE ALL ON FUNCTION nucleo_comun.vincular_invitaciones() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nucleo_comun.vincular_invitaciones() TO rol_app_nucleo;

-- Descubrimiento de identidad mínimo; no expone hashes ni datos institucionales.
CREATE FUNCTION nucleo_comun.ciudadano_por_correo(p_correo text) RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
 SELECT u.id FROM nucleo_comun.usuario u JOIN nucleo_comun.usuario_rol r ON r.usuario_id=u.id
 WHERE u.correo=p_correo AND u.activo AND r.rol='CIUDADANO'
$$;
REVOKE ALL ON FUNCTION nucleo_comun.ciudadano_por_correo(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nucleo_comun.ciudadano_por_correo(text) TO rol_app_nucleo;

CREATE FUNCTION schema_odr.asignar_mediador(p_mediacion uuid) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE m schema_odr.mediacion%ROWTYPE; elegido uuid;
BEGIN
 PERFORM pg_advisory_xact_lock(7459031);
 SELECT * INTO m FROM schema_odr.mediacion WHERE id=p_mediacion FOR UPDATE;
 IF NOT FOUND OR NOT nucleo_comun.es_parte(m.conflicto_id) OR m.estado <> 'EN_NEGOCIACION' THEN
   RAISE EXCEPTION 'No puede solicitar mediador';
 END IF;
 IF m.mediador_id IS NOT NULL THEN RETURN m.mediador_id; END IF;
 SELECT u.id INTO elegido FROM nucleo_comun.usuario u JOIN nucleo_comun.usuario_rol r ON r.usuario_id=u.id
 WHERE r.rol='MEDIADOR' AND u.activo AND u.mfa_habilitado
 ORDER BY (SELECT count(*) FROM schema_odr.mediacion a WHERE a.mediador_id=u.id AND a.estado<>'CONCLUIDA'), u.id LIMIT 1;
 UPDATE schema_odr.mediacion SET solicitud_mediador_en=now(), mediador_id=elegido WHERE id=m.id;
 RETURN elegido;
END $$;
REVOKE ALL ON FUNCTION schema_odr.asignar_mediador(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION schema_odr.asignar_mediador(uuid) TO rol_app_odr;

-- Tarea acotada, sin permisos de lectura ODR para el ejecutor.
CREATE FUNCTION schema_odr.vencer_invitaciones() RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE m record; cantidad integer := 0;
BEGIN
 FOR m IN SELECT a.id,a.conflicto_id FROM schema_odr.mediacion a
 JOIN schema_odr.invitacion i ON i.mediacion_id=a.id
 WHERE i.estado='ENVIADA' AND i.fecha_limite < (now() AT TIME ZONE 'America/Mexico_City')::date
 AND a.estado='INVITACION_ENVIADA' FOR UPDATE OF a SKIP LOCKED LOOP
   UPDATE schema_odr.invitacion SET estado='VENCIDA', respondida_en=now() WHERE mediacion_id=m.id;
   UPDATE schema_odr.mediacion SET estado='CONCLUIDA',resultado='NO_ACEPTADA',concluida_en=now() WHERE id=m.id;
   UPDATE nucleo_comun.conflicto SET estado='EN_ESPERA_DECISION' WHERE id=m.conflicto_id;
   INSERT INTO nucleo_comun.bitacora(entidad,entidad_id,accion,estado_anterior,estado_nuevo,operacion_id,motivo)
   VALUES ('conflicto',m.conflicto_id,'INVITACION_VENCIDA','EN_MEDIACION','EN_ESPERA_DECISION',gen_random_uuid(),'PLAZO_VENCIDO');
   INSERT INTO nucleo_comun.notificacion(destinatario_id,correo_destino,conflicto_id,evento)
   SELECT usuario_id,correo,m.conflicto_id,'INVITACION_VENCIDA' FROM nucleo_comun.parte WHERE conflicto_id=m.conflicto_id;
   cantidad := cantidad+1;
 END LOOP;
 RETURN cantidad;
END $$;
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='rol_tarea_odr') THEN CREATE ROLE rol_tarea_odr NOLOGIN; END IF;
END $$;
GRANT USAGE ON SCHEMA schema_odr TO rol_tarea_odr;
REVOKE ALL ON FUNCTION schema_odr.vencer_invitaciones() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION schema_odr.vencer_invitaciones() TO rol_tarea_odr;

-- Evidencias y bitácora son de solo adición incluso para el propietario accidental.
CREATE FUNCTION nucleo_comun.solo_adicion() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Registro de solo adición'; END $$;
CREATE TRIGGER bitacora_inmutable BEFORE UPDATE OR DELETE ON nucleo_comun.bitacora
FOR EACH ROW EXECUTE FUNCTION nucleo_comun.solo_adicion();
CREATE TRIGGER firma_inmutable BEFORE UPDATE OR DELETE ON schema_odr.firma
FOR EACH ROW EXECUTE FUNCTION nucleo_comun.solo_adicion();
COMMIT;
