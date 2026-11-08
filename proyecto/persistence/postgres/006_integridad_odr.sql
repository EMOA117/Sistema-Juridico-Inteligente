BEGIN;
-- Restringir las notas también por la mediación asignada en la propia base.
DROP POLICY nota_solo_mediador ON schema_odr.nota_mediador;
CREATE POLICY nota_solo_mediador ON schema_odr.nota_mediador TO rol_app_odr
USING (mediador_id=nucleo_comun.actor_id() AND nucleo_comun.tiene_rol('MEDIADOR')
  AND EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id=mediacion_id AND m.mediador_id=nucleo_comun.actor_id()))
WITH CHECK (mediador_id=nucleo_comun.actor_id() AND nucleo_comun.tiene_rol('MEDIADOR')
  AND EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id=mediacion_id AND m.mediador_id=nucleo_comun.actor_id()));
CREATE TRIGGER mensaje_inmutable BEFORE UPDATE OR DELETE ON schema_odr.mensaje
FOR EACH ROW EXECUTE FUNCTION nucleo_comun.solo_adicion();
CREATE TRIGGER nota_inmutable BEFORE UPDATE OR DELETE ON schema_odr.nota_mediador
FOR EACH ROW EXECUTE FUNCTION nucleo_comun.solo_adicion();

CREATE FUNCTION schema_odr.proteger_version_convenio() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE m schema_odr.mediacion%ROWTYPE;
BEGIN
 IF EXISTS (SELECT 1 FROM schema_odr.firma f WHERE f.convenio_id=OLD.id) AND
   (NEW.hash_sha256 IS DISTINCT FROM OLD.hash_sha256 OR NEW.documento_cifrado IS DISTINCT FROM OLD.documento_cifrado
    OR NEW.terminos_acordados_cifrados IS DISTINCT FROM OLD.terminos_acordados_cifrados
    OR NEW.tipo IS DISTINCT FROM OLD.tipo OR NEW.puntos_pendientes IS DISTINCT FROM OLD.puntos_pendientes
    OR NEW.mediacion_id IS DISTINCT FROM OLD.mediacion_id OR NEW.documento_id IS DISTINCT FROM OLD.documento_id) THEN
   RAISE EXCEPTION 'La versión aceptada no puede modificarse';
 END IF;
 IF NEW.formalizado_en IS NOT NULL AND OLD.formalizado_en IS NULL AND NEW.documento_cifrado IS NOT NULL THEN
   SELECT * INTO m FROM schema_odr.mediacion WHERE id=NEW.mediacion_id;
   IF EXISTS (SELECT 1 FROM nucleo_comun.parte p WHERE p.conflicto_id=m.conflicto_id AND
       (p.usuario_id IS NULL OR NOT EXISTS (SELECT 1 FROM schema_odr.firma f
          WHERE f.convenio_id=NEW.id AND f.usuario_id=p.usuario_id AND f.hash_sha256=NEW.hash_sha256)))
      OR (m.mediador_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM schema_odr.firma f
          WHERE f.convenio_id=NEW.id AND f.usuario_id=m.mediador_id AND f.hash_sha256=NEW.hash_sha256)) THEN
      RAISE EXCEPTION 'Faltan aceptaciones de la misma versión';
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER version_convenio BEFORE UPDATE ON schema_odr.convenio
FOR EACH ROW EXECUTE FUNCTION schema_odr.proteger_version_convenio();

CREATE TABLE nucleo_comun.operacion_canalizacion (
  clave uuid PRIMARY KEY, actor_id uuid NOT NULL REFERENCES nucleo_comun.usuario,
  conflicto_id uuid NOT NULL REFERENCES nucleo_comun.conflicto,
  demanda_id uuid NOT NULL REFERENCES schema_judicial.demanda,
  creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE nucleo_comun.evento_pendiente (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tipo text NOT NULL,
  conflicto_id uuid NOT NULL REFERENCES nucleo_comun.conflicto,
  referencia_id uuid NOT NULL, creado_en timestamptz NOT NULL DEFAULT now(),
  UNIQUE(tipo,referencia_id)
);
-- La cola contiene solo identificadores; ningún cuerpo ODR.
CREATE FUNCTION nucleo_comun.canalizar_odr(p_conflicto uuid,p_actor uuid,p_operacion uuid) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE previa nucleo_comun.operacion_canalizacion%ROWTYPE; demanda uuid;
BEGIN
 IF p_actor IS DISTINCT FROM nucleo_comun.actor_id() THEN RAISE EXCEPTION 'Actor no autorizado'; END IF;
 -- La función ordinaria bloquea el conflicto y valida actor/estado, aun en reintentos.
 demanda := nucleo_comun.canalizar_conflicto(p_conflicto,p_actor);
 SELECT * INTO previa FROM nucleo_comun.operacion_canalizacion WHERE clave=p_operacion;
 IF FOUND THEN
   IF previa.actor_id<>p_actor OR previa.conflicto_id<>p_conflicto THEN RAISE EXCEPTION 'Clave usada para otra operación'; END IF;
   RETURN previa.demanda_id;
 END IF;
 INSERT INTO nucleo_comun.operacion_canalizacion(clave,actor_id,conflicto_id,demanda_id)
 VALUES(p_operacion,p_actor,p_conflicto,demanda);
 INSERT INTO nucleo_comun.evento_pendiente(tipo,conflicto_id,referencia_id)
 VALUES('DemandaBorradorCreada',p_conflicto,demanda) ON CONFLICT DO NOTHING;
 RETURN demanda;
END $$;
REVOKE ALL ON FUNCTION nucleo_comun.canalizar_odr(uuid,uuid,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nucleo_comun.canalizar_odr(uuid,uuid,uuid) TO rol_canalizador;
COMMIT;
