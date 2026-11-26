-- 011 · Integridad ODR y canalización con clave de operación.
-- Integra lo que aportó feature/modulo-ODR (Edgar) sobre el esquema de 001–010:
--   * mensajes y notas solo de adición (no se editan ni borran);
--   * las notas solo las ve el mediador mientras siga asignado a la mediación (también tras una reasignación);
--   * canalización con clave de idempotencia y evento pendiente (patrón outbox) que procesa la tarea en segundo plano.
BEGIN;

CREATE FUNCTION nucleo_comun.solo_adicion() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    RAISE EXCEPTION 'Registro de solo adición: % no admite %', TG_TABLE_NAME, TG_OP;
END $$;

CREATE TRIGGER mensaje_inmutable BEFORE UPDATE OR DELETE ON schema_odr.mensaje
FOR EACH ROW EXECUTE FUNCTION nucleo_comun.solo_adicion();
CREATE TRIGGER nota_inmutable BEFORE UPDATE OR DELETE ON schema_odr.nota_mediador
FOR EACH ROW EXECUTE FUNCTION nucleo_comun.solo_adicion();

DROP POLICY nota_solo_mediador ON schema_odr.nota_mediador;
CREATE POLICY nota_solo_mediador ON schema_odr.nota_mediador TO rol_app_odr
USING (mediador_id = nucleo_comun.actor_id() AND nucleo_comun.tiene_rol('MEDIADOR')
       AND EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id AND m.mediador_id = nucleo_comun.actor_id()))
WITH CHECK (mediador_id = nucleo_comun.actor_id() AND nucleo_comun.tiene_rol('MEDIADOR')
       AND EXISTS (SELECT 1 FROM schema_odr.mediacion m WHERE m.id = mediacion_id AND m.mediador_id = nucleo_comun.actor_id()));

-- Una misma clave siempre devuelve la misma demanda; reutilizarla para otro conflicto o actor se rechaza.
CREATE TABLE nucleo_comun.operacion_canalizacion (
    clave        uuid PRIMARY KEY,
    actor_id     uuid NOT NULL REFERENCES nucleo_comun.usuario,
    conflicto_id uuid NOT NULL REFERENCES nucleo_comun.conflicto,
    demanda_id   uuid NOT NULL REFERENCES schema_judicial.demanda,
    creado_en    timestamptz NOT NULL DEFAULT now()
);

-- La cola contiene solo identificadores; ningún contenido ODR (decisión 002).
CREATE TABLE nucleo_comun.evento_pendiente (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo          text NOT NULL CHECK (tipo IN ('DemandaBorradorCreada')),
    conflicto_id  uuid NOT NULL REFERENCES nucleo_comun.conflicto,
    referencia_id uuid NOT NULL,
    creado_en     timestamptz NOT NULL DEFAULT now(),
    procesado_en  timestamptz,
    UNIQUE (tipo, referencia_id)
);
CREATE INDEX ix_evento_pendiente ON nucleo_comun.evento_pendiente (creado_en) WHERE procesado_en IS NULL;
ALTER TABLE nucleo_comun.operacion_canalizacion ENABLE ROW LEVEL SECURITY;
ALTER TABLE nucleo_comun.evento_pendiente ENABLE ROW LEVEL SECURITY;

CREATE FUNCTION nucleo_comun.canalizar_odr(p_conflicto uuid, p_actor uuid, p_clave uuid) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE previa nucleo_comun.operacion_canalizacion%ROWTYPE; demanda uuid;
BEGIN
    IF p_actor IS DISTINCT FROM nucleo_comun.actor_id() THEN RAISE EXCEPTION 'Actor no autorizado'; END IF;
    -- La función ordinaria bloquea el conflicto y valida actor y estado, también en los reintentos.
    demanda := nucleo_comun.canalizar_conflicto(p_conflicto, p_actor);
    IF p_clave IS NOT NULL THEN
        SELECT * INTO previa FROM nucleo_comun.operacion_canalizacion WHERE clave = p_clave;
        IF FOUND THEN
            IF previa.actor_id <> p_actor OR previa.conflicto_id <> p_conflicto THEN
                RAISE EXCEPTION 'Clave usada para otra operación';
            END IF;
            RETURN previa.demanda_id;
        END IF;
        INSERT INTO nucleo_comun.operacion_canalizacion (clave, actor_id, conflicto_id, demanda_id)
        VALUES (p_clave, p_actor, p_conflicto, demanda);
    END IF;
    INSERT INTO nucleo_comun.evento_pendiente (tipo, conflicto_id, referencia_id)
    VALUES ('DemandaBorradorCreada', p_conflicto, demanda) ON CONFLICT DO NOTHING;
    RETURN demanda;
END $$;
REVOKE ALL ON FUNCTION nucleo_comun.canalizar_odr(uuid, uuid, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nucleo_comun.canalizar_odr(uuid, uuid, uuid) TO rol_canalizador;

-- Consumidor del evento: avisa a la persona solicitante que su borrador de demanda está listo.
-- SKIP LOCKED permite varios procesos de tareas sin duplicar avisos.
CREATE FUNCTION nucleo_comun.procesar_eventos_pendientes(p_limite int DEFAULT 50) RETURNS int
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $$
DECLARE e record; n int := 0;
BEGIN
    FOR e IN SELECT ev.id, ev.conflicto_id, c.solicitante_id, c.folio
             FROM nucleo_comun.evento_pendiente ev JOIN nucleo_comun.conflicto c ON c.id = ev.conflicto_id
             WHERE ev.procesado_en IS NULL ORDER BY ev.creado_en LIMIT p_limite
             FOR UPDATE OF ev SKIP LOCKED LOOP
        PERFORM nucleo_comun.notificar_usuario(e.solicitante_id, 'DEMANDA_BORRADOR_LISTA', e.folio, 'conflicto',
                                               e.conflicto_id, '/ciudadano/demanda/' || e.conflicto_id);
        UPDATE nucleo_comun.evento_pendiente SET procesado_en = now() WHERE id = e.id;
        n := n + 1;
    END LOOP;
    RETURN n;
END $$;
REVOKE ALL ON FUNCTION nucleo_comun.procesar_eventos_pendientes(int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nucleo_comun.procesar_eventos_pendientes(int) TO rol_tareas;

COMMIT;
