-- Roles sin login: provisionar credenciales distintas por servicio fuera de estas migraciones.
BEGIN;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_app_nucleo') THEN CREATE ROLE rol_app_nucleo NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_auth') THEN CREATE ROLE rol_auth NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_app_odr') THEN CREATE ROLE rol_app_odr NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_app_judicial') THEN CREATE ROLE rol_app_judicial NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_app_admin') THEN CREATE ROLE rol_app_admin NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rol_canalizador') THEN CREATE ROLE rol_canalizador NOLOGIN; END IF;
END $$;
REVOKE ALL ON SCHEMA nucleo_comun, schema_odr, schema_judicial, analitica FROM PUBLIC;
GRANT USAGE ON SCHEMA nucleo_comun TO rol_app_nucleo, rol_auth, rol_app_odr, rol_app_judicial, rol_app_admin, rol_canalizador;
GRANT USAGE ON SCHEMA schema_odr TO rol_app_odr;
GRANT USAGE ON SCHEMA schema_judicial TO rol_app_judicial, rol_app_admin;
GRANT SELECT, INSERT, UPDATE ON nucleo_comun.usuario TO rol_app_nucleo;
GRANT SELECT, INSERT ON nucleo_comun.usuario_rol TO rol_app_nucleo;
GRANT SELECT ON nucleo_comun.usuario, nucleo_comun.usuario_rol TO rol_auth;
GRANT SELECT, INSERT, UPDATE ON nucleo_comun.conflicto, nucleo_comun.parte TO rol_app_nucleo;
GRANT SELECT ON nucleo_comun.conflicto, nucleo_comun.parte TO rol_app_odr, rol_app_judicial;
GRANT INSERT ON nucleo_comun.bitacora TO rol_app_nucleo, rol_app_odr, rol_app_judicial;
GRANT USAGE ON SEQUENCE nucleo_comun.bitacora_id_seq TO rol_app_nucleo, rol_app_odr, rol_app_judicial;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA schema_odr TO rol_app_odr;
REVOKE UPDATE ON schema_odr.mensaje, schema_odr.propuesta, schema_odr.nota_mediador FROM rol_app_odr;
GRANT SELECT, UPDATE ON schema_judicial.demanda TO rol_app_judicial;
GRANT SELECT, INSERT, UPDATE ON schema_judicial.expediente TO rol_app_judicial;
GRANT SELECT, INSERT ON schema_judicial.contestacion, schema_judicial.resolucion TO rol_app_judicial;
GRANT SELECT ON schema_judicial.historial_estado TO rol_app_judicial;
GRANT SELECT ON schema_judicial.expediente TO rol_app_admin;
GRANT UPDATE (juez_id, estado) ON schema_judicial.expediente TO rol_app_admin;
GRANT USAGE ON SEQUENCE schema_judicial.historial_estado_id_seq TO rol_app_judicial;
GRANT EXECUTE ON FUNCTION nucleo_comun.canalizar_conflicto(uuid,uuid) TO rol_canalizador;

CREATE FUNCTION nucleo_comun.actor_id() RETURNS uuid LANGUAGE sql STABLE
SET search_path = pg_catalog, pg_temp AS $$
  SELECT nullif(current_setting('app.usuario_id', true), '')::uuid
$$;
REVOKE ALL ON FUNCTION nucleo_comun.actor_id() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nucleo_comun.actor_id() TO rol_app_nucleo, rol_app_odr, rol_app_judicial, rol_app_admin;

CREATE FUNCTION nucleo_comun.es_parte(p_conflicto_id uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, nucleo_comun, pg_temp AS $$
  SELECT EXISTS (
    SELECT 1 FROM nucleo_comun.conflicto c WHERE c.id = p_conflicto_id
      AND (c.solicitante_id = nucleo_comun.actor_id() OR EXISTS
           (SELECT 1 FROM nucleo_comun.parte p WHERE p.conflicto_id = c.id AND p.usuario_id = nucleo_comun.actor_id()))
  )
$$;
REVOKE ALL ON FUNCTION nucleo_comun.es_parte(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nucleo_comun.es_parte(uuid) TO rol_app_nucleo, rol_app_odr, rol_app_judicial;

CREATE FUNCTION nucleo_comun.es_solicitante(p_conflicto_id uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, nucleo_comun, pg_temp AS $$
  SELECT EXISTS (SELECT 1 FROM nucleo_comun.conflicto c
    WHERE c.id = p_conflicto_id AND c.solicitante_id = nucleo_comun.actor_id())
$$;
REVOKE ALL ON FUNCTION nucleo_comun.es_solicitante(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nucleo_comun.es_solicitante(uuid) TO rol_app_judicial;

CREATE FUNCTION nucleo_comun.tiene_rol(p_rol text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, nucleo_comun, pg_temp AS $$
  SELECT EXISTS (SELECT 1 FROM nucleo_comun.usuario_rol ur
    WHERE ur.usuario_id = nucleo_comun.actor_id() AND ur.rol = p_rol)
$$;
REVOKE ALL ON FUNCTION nucleo_comun.tiene_rol(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nucleo_comun.tiene_rol(text) TO rol_app_odr, rol_app_judicial;

CREATE FUNCTION nucleo_comun.es_juez_conflicto(p_conflicto_id uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, schema_judicial, pg_temp AS $$
  SELECT EXISTS (SELECT 1 FROM schema_judicial.demanda d
    JOIN schema_judicial.expediente e ON e.demanda_id = d.id
    WHERE d.conflicto_id = p_conflicto_id AND e.juez_id = nucleo_comun.actor_id())
$$;
REVOKE ALL ON FUNCTION nucleo_comun.es_juez_conflicto(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nucleo_comun.es_juez_conflicto(uuid) TO rol_app_judicial;

CREATE FUNCTION nucleo_comun.es_mediador_conflicto(p_conflicto_id uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, schema_odr, pg_temp AS $$
  SELECT EXISTS (SELECT 1 FROM schema_odr.mediacion m
    WHERE m.conflicto_id = p_conflicto_id AND m.mediador_id = nucleo_comun.actor_id())
$$;
REVOKE ALL ON FUNCTION nucleo_comun.es_mediador_conflicto(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nucleo_comun.es_mediador_conflicto(uuid) TO rol_app_odr;

ALTER TABLE nucleo_comun.usuario ENABLE ROW LEVEL SECURITY;
ALTER TABLE nucleo_comun.usuario_rol ENABLE ROW LEVEL SECURITY;
ALTER TABLE nucleo_comun.conflicto ENABLE ROW LEVEL SECURITY;
ALTER TABLE nucleo_comun.parte ENABLE ROW LEVEL SECURITY;
CREATE POLICY usuario_propio ON nucleo_comun.usuario TO rol_app_nucleo USING (id = nucleo_comun.actor_id());
CREATE POLICY usuario_autenticacion ON nucleo_comun.usuario FOR SELECT TO rol_auth USING (true);
CREATE POLICY usuario_alta ON nucleo_comun.usuario FOR INSERT TO rol_app_nucleo WITH CHECK (true);
CREATE POLICY roles_propios ON nucleo_comun.usuario_rol FOR SELECT TO rol_app_nucleo USING (usuario_id = nucleo_comun.actor_id());
CREATE POLICY roles_autenticacion ON nucleo_comun.usuario_rol FOR SELECT TO rol_auth USING (true);
CREATE POLICY rol_ciudadano_alta ON nucleo_comun.usuario_rol FOR INSERT TO rol_app_nucleo WITH CHECK (rol = 'CIUDADANO' AND usuario_id = nucleo_comun.actor_id());
CREATE POLICY conflicto_relacion ON nucleo_comun.conflicto TO rol_app_nucleo USING (nucleo_comun.es_parte(id)) WITH CHECK (solicitante_id = nucleo_comun.actor_id());
CREATE POLICY conflicto_odr_lectura ON nucleo_comun.conflicto FOR SELECT TO rol_app_odr USING (nucleo_comun.es_parte(id) OR nucleo_comun.es_mediador_conflicto(id));
CREATE POLICY conflicto_judicial_lectura ON nucleo_comun.conflicto FOR SELECT TO rol_app_judicial USING (nucleo_comun.es_parte(id) OR nucleo_comun.es_juez_conflicto(id));
CREATE POLICY parte_relacion ON nucleo_comun.parte TO rol_app_nucleo USING (nucleo_comun.es_parte(conflicto_id)) WITH CHECK (nucleo_comun.es_parte(conflicto_id));
CREATE POLICY parte_odr_lectura ON nucleo_comun.parte FOR SELECT TO rol_app_odr USING (nucleo_comun.es_parte(conflicto_id) OR nucleo_comun.es_mediador_conflicto(conflicto_id));
CREATE POLICY parte_judicial_lectura ON nucleo_comun.parte FOR SELECT TO rol_app_judicial USING (nucleo_comun.es_parte(conflicto_id) OR nucleo_comun.es_juez_conflicto(conflicto_id));

ALTER TABLE schema_odr.mediacion ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_odr.invitacion ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_odr.mensaje ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_odr.propuesta ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_odr.nota_mediador ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_odr.convenio ENABLE ROW LEVEL SECURITY;
CREATE POLICY mediacion_relacion ON schema_odr.mediacion TO rol_app_odr
USING (nucleo_comun.es_parte(conflicto_id) OR mediador_id = nucleo_comun.actor_id())
WITH CHECK (nucleo_comun.es_parte(conflicto_id) OR mediador_id = nucleo_comun.actor_id());
CREATE POLICY invitacion_relacion ON schema_odr.invitacion TO rol_app_odr
USING (EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id))
WITH CHECK (EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id));
CREATE POLICY mensaje_relacion ON schema_odr.mensaje TO rol_app_odr
USING (EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id))
WITH CHECK (EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id));
CREATE POLICY propuesta_relacion ON schema_odr.propuesta TO rol_app_odr
USING (EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id))
WITH CHECK (EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id));
CREATE POLICY nota_solo_mediador ON schema_odr.nota_mediador TO rol_app_odr
USING (mediador_id = nucleo_comun.actor_id() AND nucleo_comun.tiene_rol('MEDIADOR'))
WITH CHECK (mediador_id = nucleo_comun.actor_id() AND nucleo_comun.tiene_rol('MEDIADOR'));
CREATE POLICY convenio_relacion ON schema_odr.convenio TO rol_app_odr
USING (EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id))
WITH CHECK (EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id));

CREATE FUNCTION schema_judicial.puede_ver_demanda(p_demanda_id uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, nucleo_comun, schema_judicial, pg_temp AS $$
  SELECT EXISTS (
    SELECT 1 FROM schema_judicial.demanda d WHERE d.id = p_demanda_id
      AND (nucleo_comun.es_parte(d.conflicto_id) OR EXISTS
           (SELECT 1 FROM schema_judicial.expediente e WHERE e.demanda_id = d.id AND e.juez_id = nucleo_comun.actor_id()))
  )
$$;
REVOKE ALL ON FUNCTION schema_judicial.puede_ver_demanda(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION schema_judicial.puede_ver_demanda(uuid) TO rol_app_judicial;
ALTER TABLE schema_judicial.demanda ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_judicial.expediente ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_judicial.contestacion ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_judicial.resolucion ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_judicial.historial_estado ENABLE ROW LEVEL SECURITY;
CREATE POLICY demanda_lectura ON schema_judicial.demanda FOR SELECT TO rol_app_judicial
USING (schema_judicial.puede_ver_demanda(id));
CREATE POLICY demanda_edicion ON schema_judicial.demanda FOR UPDATE TO rol_app_judicial
USING (nucleo_comun.es_solicitante(conflicto_id)) WITH CHECK (nucleo_comun.es_solicitante(conflicto_id));
CREATE POLICY expediente_lectura ON schema_judicial.expediente FOR SELECT TO rol_app_judicial
USING (schema_judicial.puede_ver_demanda(demanda_id));
CREATE POLICY expediente_alta ON schema_judicial.expediente FOR INSERT TO rol_app_judicial
WITH CHECK (schema_judicial.puede_ver_demanda(demanda_id));
CREATE POLICY expediente_edicion_juez ON schema_judicial.expediente FOR UPDATE TO rol_app_judicial
USING (juez_id = nucleo_comun.actor_id() AND nucleo_comun.tiene_rol('JUEZ'))
WITH CHECK (juez_id = nucleo_comun.actor_id() AND nucleo_comun.tiene_rol('JUEZ'));
CREATE POLICY expediente_admin ON schema_judicial.expediente TO rol_app_admin USING (true) WITH CHECK (true);
CREATE POLICY contestacion_relacion ON schema_judicial.contestacion TO rol_app_judicial
USING (EXISTS (SELECT 1 FROM schema_judicial.expediente e WHERE e.id = expediente_id))
WITH CHECK (EXISTS (SELECT 1 FROM schema_judicial.expediente e WHERE e.id = expediente_id));
CREATE POLICY resolucion_relacion ON schema_judicial.resolucion TO rol_app_judicial
USING (nucleo_comun.tiene_rol('JUEZ') AND EXISTS (SELECT 1 FROM schema_judicial.expediente e WHERE e.id = expediente_id AND e.juez_id = nucleo_comun.actor_id()))
WITH CHECK (nucleo_comun.tiene_rol('JUEZ') AND EXISTS (SELECT 1 FROM schema_judicial.expediente e WHERE e.id = expediente_id AND e.juez_id = nucleo_comun.actor_id()));
CREATE POLICY historial_relacion ON schema_judicial.historial_estado FOR SELECT TO rol_app_judicial
USING (EXISTS (SELECT 1 FROM schema_judicial.expediente e WHERE e.id = expediente_id));
COMMIT;
