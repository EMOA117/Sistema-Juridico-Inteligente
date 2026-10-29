BEGIN;

CREATE FUNCTION schema_judicial.fijar_plazo() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    IF NEW.fecha_emplazamiento_validado IS DISTINCT FROM OLD.fecha_emplazamiento_validado THEN
        IF OLD.fecha_emplazamiento_validado IS NOT NULL THEN
            RAISE EXCEPTION 'El emplazamiento validado no puede reemplazarse';
        END IF;
        IF OLD.estado <> 'ADMITIDO' THEN
            RAISE EXCEPTION 'Solo un expediente admitido puede registrar emplazamiento';
        END IF;
        NEW.fecha_limite_contestacion := NEW.fecha_emplazamiento_validado + 15;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tr_fijar_plazo BEFORE UPDATE ON schema_judicial.expediente
FOR EACH ROW EXECUTE FUNCTION schema_judicial.fijar_plazo();

CREATE FUNCTION schema_judicial.validar_estado() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
DECLARE r schema_judicial.resolucion%ROWTYPE;
BEGIN
    IF NEW.estado = OLD.estado THEN RETURN NEW; END IF;
    IF NEW.estado = 'EN_REVISION' AND OLD.estado = 'EN_TURNO' AND NEW.juez_id IS NOT NULL THEN RETURN NEW; END IF;
    IF NEW.estado = 'PREVENIDO' AND OLD.estado = 'EN_REVISION' THEN RETURN NEW; END IF;
    IF NEW.estado = 'EN_REVISION' AND OLD.estado = 'PREVENIDO' THEN RETURN NEW; END IF;
    IF NEW.estado = 'ADMITIDO' AND OLD.estado = 'EN_REVISION' THEN RETURN NEW; END IF;
    IF NEW.estado = 'EN_TRAMITE' AND OLD.estado = 'ADMITIDO'
       AND NEW.fecha_emplazamiento_validado IS NOT NULL
       AND (EXISTS (SELECT 1 FROM schema_judicial.contestacion c WHERE c.expediente_id = NEW.id)
            OR CURRENT_DATE > NEW.fecha_limite_contestacion) THEN RETURN NEW; END IF;

    IF NEW.estado IN ('RESUELTO','DESECHADO','CERRADO') THEN
        SELECT * INTO r FROM schema_judicial.resolucion WHERE expediente_id = NEW.id;
        IF NOT FOUND OR nullif(btrim(r.resultado), '') IS NULL OR r.sello_tiempo IS NULL OR r.firmada_en IS NULL THEN
            RAISE EXCEPTION 'Se requiere resolución firmada, resultado y sello de tiempo';
        END IF;
        IF NEW.estado = 'DESECHADO' AND OLD.estado IN ('EN_REVISION','PREVENIDO') THEN RETURN NEW; END IF;
        IF NEW.estado = 'RESUELTO' AND OLD.estado = 'EN_TRAMITE' THEN RETURN NEW; END IF;
        IF NEW.estado = 'CERRADO' AND OLD.estado IN ('RESUELTO','DESECHADO')
           AND NEW.fecha_firmeza IS NOT NULL AND r.fecha_firmeza = NEW.fecha_firmeza THEN RETURN NEW; END IF;
    END IF;
    RAISE EXCEPTION 'Transición judicial no permitida: % -> %', OLD.estado, NEW.estado;
END $$;
CREATE TRIGGER tr_validar_estado_expediente BEFORE UPDATE OF estado ON schema_judicial.expediente
FOR EACH ROW EXECUTE FUNCTION schema_judicial.validar_estado();

CREATE FUNCTION nucleo_comun.validar_estado_conflicto() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    IF NEW.estado = OLD.estado THEN RETURN NEW; END IF;
    IF OLD.estado = 'CAPTURA' AND NEW.estado = 'ORIENTADO' AND NEW.narrativa_inicial IS NOT NULL
       AND NEW.materia IS NOT NULL AND NEW.mediable IS NOT NULL
       AND (SELECT count(*) FROM nucleo_comun.parte p WHERE p.conflicto_id = NEW.id) = 2 THEN RETURN NEW; END IF;
    IF OLD.estado = 'ORIENTADO' AND NEW.estado = 'EN_MEDIACION' AND NEW.mediable = true THEN RETURN NEW; END IF;
    IF OLD.estado = 'EN_MEDIACION' AND NEW.estado = 'CONCLUIDO'
       AND EXISTS (SELECT 1 FROM schema_odr.mediacion m JOIN schema_odr.convenio v ON v.mediacion_id = m.id
                   WHERE m.conflicto_id = NEW.id AND m.resultado = 'ACUERDO_TOTAL'
                     AND v.tipo = 'TOTAL' AND v.formalizado_en IS NOT NULL) THEN RETURN NEW; END IF;
    IF OLD.estado = 'EN_MEDIACION' AND NEW.estado = 'EN_ESPERA_DECISION'
       AND EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.conflicto_id = NEW.id
                   AND (m.resultado IN ('NO_ACEPTADA','SIN_ACUERDO','DESISTIMIENTO') OR
                        (m.resultado = 'ACUERDO_PARCIAL' AND EXISTS
                         (SELECT 1 FROM schema_odr.convenio v WHERE v.mediacion_id = m.id
                          AND v.tipo = 'PARCIAL' AND v.formalizado_en IS NOT NULL)))) THEN RETURN NEW; END IF;
    IF OLD.estado IN ('ORIENTADO','EN_ESPERA_DECISION') AND NEW.estado = 'CANALIZADO'
       AND EXISTS (SELECT 1 FROM schema_judicial.demanda d WHERE d.conflicto_id = NEW.id) THEN RETURN NEW; END IF;
    IF OLD.estado = 'CANALIZADO' AND NEW.estado = 'CONCLUIDO'
       AND EXISTS (SELECT 1 FROM schema_judicial.demanda d JOIN schema_judicial.expediente e ON e.demanda_id = d.id
                   WHERE d.conflicto_id = NEW.id AND e.estado = 'CERRADO') THEN RETURN NEW; END IF;
    RAISE EXCEPTION 'Transición de conflicto no permitida: % -> %', OLD.estado, NEW.estado;
END $$;
CREATE TRIGGER tr_validar_estado_conflicto BEFORE UPDATE OF estado ON nucleo_comun.conflicto
FOR EACH ROW EXECUTE FUNCTION nucleo_comun.validar_estado_conflicto();

CREATE FUNCTION schema_odr.bloquear_convenio_formalizado() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    IF OLD.formalizado_en IS NOT NULL THEN
        RAISE EXCEPTION 'Un convenio formalizado no puede modificarse ni borrarse';
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tr_convenio_inmutable BEFORE UPDATE OR DELETE ON schema_odr.convenio
FOR EACH ROW EXECUTE FUNCTION schema_odr.bloquear_convenio_formalizado();

CREATE FUNCTION schema_judicial.registrar_historial() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, schema_judicial, pg_temp AS $$
DECLARE actor uuid;
BEGIN
    actor := nullif(current_setting('app.usuario_id', true), '')::uuid;
    IF actor IS NULL THEN RAISE EXCEPTION 'Falta app.usuario_id'; END IF;
    INSERT INTO schema_judicial.historial_estado (expediente_id, usuario_id, estado_anterior, estado_nuevo, motivo)
    VALUES (NEW.id, actor, OLD.estado, NEW.estado, 'CAMBIO_ESTADO');
    RETURN NEW;
END $$;
CREATE TRIGGER tr_historial_expediente AFTER UPDATE OF estado ON schema_judicial.expediente
FOR EACH ROW WHEN (NEW.estado IS DISTINCT FROM OLD.estado)
EXECUTE FUNCTION schema_judicial.registrar_historial();

CREATE FUNCTION nucleo_comun.canalizar_conflicto(p_conflicto_id uuid, p_usuario_id uuid)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, nucleo_comun, schema_odr, schema_judicial, pg_temp AS $$
DECLARE c nucleo_comun.conflicto%ROWTYPE;
DECLARE m schema_odr.mediacion%ROWTYPE;
DECLARE v schema_odr.convenio%ROWTYPE;
DECLARE actor uuid;
DECLARE origen text;
DECLARE pendientes text[];
DECLARE demandante uuid;
DECLARE demandado uuid;
DECLARE demanda_id uuid;
BEGIN
    actor := nullif(current_setting('app.usuario_id', true), '')::uuid;
    IF actor IS NULL OR actor <> p_usuario_id THEN RAISE EXCEPTION 'Actor no autorizado'; END IF;
    SELECT * INTO c FROM nucleo_comun.conflicto WHERE id = p_conflicto_id FOR UPDATE;
    IF NOT FOUND OR c.solicitante_id <> actor THEN RAISE EXCEPTION 'Conflicto no autorizado'; END IF;
    SELECT id INTO demanda_id FROM schema_judicial.demanda WHERE conflicto_id = c.id;
    IF FOUND AND c.estado = 'CANALIZADO' THEN RETURN demanda_id; END IF;
    IF c.estado NOT IN ('ORIENTADO','EN_ESPERA_DECISION') OR c.narrativa_inicial IS NULL OR c.materia IS NULL THEN
        RAISE EXCEPTION 'Estado o captura incompleta para canalización';
    END IF;
    IF c.estado = 'ORIENTADO' THEN
        origen := 'DIRECTA';
    ELSE
        SELECT * INTO m FROM schema_odr.mediacion WHERE conflicto_id = c.id;
        IF NOT FOUND THEN RAISE EXCEPTION 'Falta resultado de mediación'; END IF;
        IF m.resultado = 'NO_ACEPTADA' THEN origen := 'NO_ACEPTADA';
        ELSIF m.resultado = 'SIN_ACUERDO' THEN origen := 'SIN_ACUERDO';
        ELSIF m.resultado = 'DESISTIMIENTO' THEN origen := 'DESISTIMIENTO';
        ELSIF m.resultado = 'ACUERDO_PARCIAL' THEN
            SELECT * INTO v FROM schema_odr.convenio WHERE mediacion_id = m.id AND tipo = 'PARCIAL' AND formalizado_en IS NOT NULL;
            IF NOT FOUND OR coalesce(cardinality(v.puntos_pendientes),0) = 0 THEN RAISE EXCEPTION 'Convenio parcial no formalizado'; END IF;
            origen := 'ACUERDO_PARCIAL';
            pendientes := v.puntos_pendientes;
        ELSE RAISE EXCEPTION 'Resultado no canalizable'; END IF;
    END IF;
    SELECT id INTO demandante FROM nucleo_comun.parte WHERE conflicto_id = c.id AND rol = 'DEMANDANTE';
    SELECT id INTO demandado FROM nucleo_comun.parte WHERE conflicto_id = c.id AND rol = 'DEMANDADO';
    IF demandante IS NULL OR demandado IS NULL THEN RAISE EXCEPTION 'Faltan partes'; END IF;
    INSERT INTO schema_judicial.demanda (conflicto_id, origen, demandante_id, demandado_id, narrativa_inicial, materia, puntos_pendientes)
    VALUES (c.id, origen, demandante, demandado, c.narrativa_inicial, c.materia, pendientes)
    RETURNING id INTO demanda_id;
    UPDATE nucleo_comun.conflicto SET estado = 'CANALIZADO' WHERE id = c.id;
    INSERT INTO nucleo_comun.bitacora (usuario_id, entidad, entidad_id, accion, estado_anterior, estado_nuevo, operacion_id)
    VALUES (actor, 'conflicto', c.id, 'CANALIZAR', c.estado, 'CANALIZADO', gen_random_uuid());
    RETURN demanda_id;
END $$;
REVOKE ALL ON FUNCTION nucleo_comun.canalizar_conflicto(uuid, uuid) FROM PUBLIC;
COMMIT;
