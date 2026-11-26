-- P3 y P13: invitación a la contraparte y cola de notificaciones. No modifica migraciones previas.
BEGIN;

-- Cola de avisos (RF10). Solo metadatos: tipo, folio y enlace; nunca contenido ODR (decisión 002).
CREATE TABLE nucleo_comun.notificacion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    destinatario_id uuid REFERENCES nucleo_comun.usuario(id),
    correo text,
    tipo text NOT NULL,
    folio text,
    entidad text NOT NULL,
    entidad_id uuid NOT NULL,
    enlace text,
    enlace_cifrado bytea,               -- enlaces con secreto (invitación): cifrados, el token nunca en claro
    estado_envio text NOT NULL DEFAULT 'PENDIENTE' CHECK (estado_envio IN ('PENDIENTE','ENVIADA','FALLIDA','SIN_CORREO')),
    intentos int NOT NULL DEFAULT 0,
    proximo_intento timestamptz NOT NULL DEFAULT now(),
    ultimo_error text,
    creado_en timestamptz NOT NULL DEFAULT now(),
    enviado_en timestamptz,
    leida_en timestamptz,
    CHECK (destinatario_id IS NOT NULL OR correo IS NOT NULL)
);
CREATE INDEX ix_notificacion_pendientes ON nucleo_comun.notificacion (proximo_intento) WHERE estado_envio = 'PENDIENTE';
CREATE INDEX ix_notificacion_bandeja ON nucleo_comun.notificacion (destinatario_id, creado_en DESC);

-- Invitación: el token de 43 caracteres solo existe como hash SHA-256.
ALTER TABLE schema_odr.invitacion
  ADD COLUMN token_hash char(64) UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
  ADD COLUMN correo_destino text,
  ADD COLUMN respondida_en timestamptz,
  ADD CHECK (fecha_limite > creado_en::date);
CREATE INDEX ix_invitacion_por_vencer ON schema_odr.invitacion (fecha_limite) WHERE estado = 'ENVIADA';

-- Inserta un aviso por cada parte del conflicto (y el mediador si lo hay). Resuelve destinatarios sin que
-- el rol que llama tenga que leer usuarios ajenos.
CREATE FUNCTION nucleo_comun.notificar(p_conflicto_id uuid, p_tipo text, p_entidad text, p_entidad_id uuid,
                                       p_excluir uuid DEFAULT NULL, p_incluir_mediador boolean DEFAULT true)
RETURNS int LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, nucleo_comun, schema_odr, pg_temp AS $$
DECLARE n int := 0; f text; r record;
BEGIN
    SELECT folio INTO f FROM nucleo_comun.conflicto WHERE id = p_conflicto_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'Conflicto inexistente'; END IF;
    FOR r IN
        SELECT p.usuario_id, CASE WHEN p.usuario_id IS NULL THEN p.correo END AS correo
        FROM nucleo_comun.parte p WHERE p.conflicto_id = p_conflicto_id
          AND (p.usuario_id IS NOT NULL OR p.correo IS NOT NULL)
        UNION
        SELECT m.mediador_id, NULL FROM schema_odr.mediacion m
        WHERE p_incluir_mediador AND m.conflicto_id = p_conflicto_id AND m.mediador_id IS NOT NULL
    LOOP
        CONTINUE WHEN r.usuario_id IS NOT NULL AND r.usuario_id = p_excluir;
        -- Las partes aún no registradas solo reciben avisos de su invitación (correo propio).
        CONTINUE WHEN r.usuario_id IS NULL;
        INSERT INTO nucleo_comun.notificacion (destinatario_id, correo, tipo, folio, entidad, entidad_id, enlace)
        VALUES (r.usuario_id, r.correo, p_tipo, f, p_entidad, p_entidad_id, '/');
        n := n + 1;
    END LOOP;
    RETURN n;
END $$;

CREATE FUNCTION nucleo_comun.notificar_usuario(p_usuario_id uuid, p_tipo text, p_folio text, p_entidad text,
                                               p_entidad_id uuid, p_enlace text DEFAULT '/')
RETURNS void LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog, nucleo_comun, pg_temp AS $$
    INSERT INTO nucleo_comun.notificacion (destinatario_id, tipo, folio, entidad, entidad_id, enlace)
    VALUES (p_usuario_id, p_tipo, p_folio, p_entidad, p_entidad_id, p_enlace)
$$;

-- Información mínima de una invitación para la página pública (sin narrativa ni contenido ODR).
CREATE FUNCTION schema_odr.ver_invitacion(p_token_hash text)
RETURNS TABLE (folio text, materia text, solicitante text, invitado text, estado text, fecha_limite date)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, nucleo_comun, schema_odr, pg_temp AS $$
    SELECT c.folio, c.materia, ps.nombre, pd.nombre,
           CASE WHEN i.estado = 'ENVIADA' AND i.fecha_limite < CURRENT_DATE THEN 'VENCIDA' ELSE i.estado END,
           i.fecha_limite
    FROM schema_odr.invitacion i
    JOIN schema_odr.mediacion m ON m.id = i.mediacion_id
    JOIN nucleo_comun.conflicto c ON c.id = m.conflicto_id
    JOIN nucleo_comun.parte ps ON ps.conflicto_id = c.id AND ps.rol = 'DEMANDANTE'
    JOIN nucleo_comun.parte pd ON pd.id = i.contraparte_id
    WHERE i.token_hash = p_token_hash
$$;

-- RF3.7: la contraparte autenticada acepta o rechaza; aceptar la vincula como parte del conflicto.
CREATE FUNCTION schema_odr.responder_invitacion(p_token_hash text, p_acepta boolean)
RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, nucleo_comun, schema_odr, pg_temp AS $$
DECLARE i schema_odr.invitacion%ROWTYPE; m schema_odr.mediacion%ROWTYPE; c nucleo_comun.conflicto%ROWTYPE;
DECLARE actor uuid := nucleo_comun.actor_id(); parte_usuario uuid;
BEGIN
    IF actor IS NULL THEN RAISE EXCEPTION 'Inicia sesión para responder la invitación'; END IF;
    SELECT * INTO i FROM schema_odr.invitacion WHERE token_hash = p_token_hash FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Invitación no encontrada'; END IF;
    IF i.estado <> 'ENVIADA' THEN RAISE EXCEPTION 'La invitación ya fue respondida o venció'; END IF;
    IF i.fecha_limite < CURRENT_DATE THEN RAISE EXCEPTION 'La invitación venció'; END IF;
    SELECT * INTO m FROM schema_odr.mediacion WHERE id = i.mediacion_id FOR UPDATE;
    SELECT * INTO c FROM nucleo_comun.conflicto WHERE id = m.conflicto_id FOR UPDATE;
    IF c.solicitante_id = actor THEN RAISE EXCEPTION 'Quien invita no puede responder su propia invitación'; END IF;
    SELECT usuario_id INTO parte_usuario FROM nucleo_comun.parte WHERE id = i.contraparte_id;
    IF parte_usuario IS NOT NULL AND parte_usuario <> actor THEN RAISE EXCEPTION 'La invitación pertenece a otra persona'; END IF;
    IF NOT EXISTS (SELECT 1 FROM nucleo_comun.usuario_rol WHERE usuario_id = actor AND rol = 'CIUDADANO') THEN
        RAISE EXCEPTION 'Solo una cuenta ciudadana puede responder';
    END IF;

    UPDATE schema_odr.invitacion SET estado = CASE WHEN p_acepta THEN 'ACEPTADA' ELSE 'RECHAZADA' END,
           respondida_en = now() WHERE id = i.id;
    IF p_acepta THEN
        UPDATE nucleo_comun.parte SET usuario_id = actor WHERE id = i.contraparte_id;
        UPDATE schema_odr.mediacion SET estado = 'EN_NEGOCIACION' WHERE id = m.id;
    ELSE
        UPDATE schema_odr.mediacion SET estado = 'CONCLUIDA', resultado = 'NO_ACEPTADA', concluida_en = now() WHERE id = m.id;
        UPDATE nucleo_comun.conflicto SET estado = 'EN_ESPERA_DECISION' WHERE id = c.id;
    END IF;
    INSERT INTO nucleo_comun.bitacora (usuario_id, entidad, entidad_id, accion, estado_anterior, estado_nuevo, operacion_id)
    VALUES (actor, 'invitacion', i.id, CASE WHEN p_acepta THEN 'INVITACION_ACEPTADA' ELSE 'INVITACION_RECHAZADA' END,
            'ENVIADA', CASE WHEN p_acepta THEN 'ACEPTADA' ELSE 'RECHAZADA' END, gen_random_uuid());
    PERFORM nucleo_comun.notificar_usuario(c.solicitante_id,
        CASE WHEN p_acepta THEN 'INVITACION_ACEPTADA' ELSE 'INVITACION_RECHAZADA' END, c.folio, 'mediacion', m.id);
    RETURN m.id;
END $$;

-- Tarea diaria (P3): vence invitaciones expiradas, concluye la mediación como NO_ACEPTADA y avisa.
CREATE FUNCTION schema_odr.vencer_invitaciones() RETURNS int
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, nucleo_comun, schema_odr, pg_temp AS $$
DECLARE r record; n int := 0;
BEGIN
    FOR r IN SELECT i.id, i.mediacion_id, m.conflicto_id, c.solicitante_id, c.folio
             FROM schema_odr.invitacion i JOIN schema_odr.mediacion m ON m.id = i.mediacion_id
             JOIN nucleo_comun.conflicto c ON c.id = m.conflicto_id
             WHERE i.estado = 'ENVIADA' AND i.fecha_limite < CURRENT_DATE
             FOR UPDATE OF i SKIP LOCKED
    LOOP
        UPDATE schema_odr.invitacion SET estado = 'VENCIDA' WHERE id = r.id;
        UPDATE schema_odr.mediacion SET estado = 'CONCLUIDA', resultado = 'NO_ACEPTADA', concluida_en = now()
        WHERE id = r.mediacion_id AND estado = 'INVITACION_ENVIADA';
        UPDATE nucleo_comun.conflicto SET estado = 'EN_ESPERA_DECISION' WHERE id = r.conflicto_id AND estado = 'EN_MEDIACION';
        INSERT INTO nucleo_comun.bitacora (entidad, entidad_id, accion, estado_anterior, estado_nuevo, operacion_id)
        VALUES ('invitacion', r.id, 'INVITACION_VENCIDA', 'ENVIADA', 'VENCIDA', gen_random_uuid());
        PERFORM nucleo_comun.notificar_usuario(r.solicitante_id, 'INVITACION_VENCIDA', r.folio, 'mediacion', r.mediacion_id);
        n := n + 1;
    END LOOP;
    RETURN n;
END $$;

-- Permisos ---------------------------------------------------------------------------------------
REVOKE ALL ON FUNCTION nucleo_comun.notificar(uuid, text, text, uuid, uuid, boolean),
                     nucleo_comun.notificar_usuario(uuid, text, text, text, uuid, text),
                     schema_odr.ver_invitacion(text), schema_odr.responder_invitacion(text, boolean),
                     schema_odr.vencer_invitaciones() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nucleo_comun.notificar(uuid, text, text, uuid, uuid, boolean)
  TO rol_app_nucleo, rol_app_odr, rol_app_judicial, rol_app_admin;
GRANT EXECUTE ON FUNCTION nucleo_comun.notificar_usuario(uuid, text, text, text, uuid, text)
  TO rol_app_nucleo, rol_app_odr, rol_app_judicial, rol_app_admin;
GRANT USAGE ON SCHEMA nucleo_comun TO rol_tareas;
GRANT USAGE ON SCHEMA schema_odr TO rol_auth, rol_tareas, rol_app_nucleo;
GRANT EXECUTE ON FUNCTION schema_odr.ver_invitacion(text) TO rol_auth;
GRANT EXECUTE ON FUNCTION schema_odr.responder_invitacion(text, boolean) TO rol_app_nucleo;
GRANT EXECUTE ON FUNCTION schema_odr.vencer_invitaciones() TO rol_tareas;
-- La invitación con su enlace cifrado la inserta ODR al crear la mediación.
GRANT INSERT ON nucleo_comun.notificacion TO rol_app_odr;

-- Bandeja propia (rol núcleo) y despacho (rol de tareas).
GRANT SELECT, UPDATE (leida_en) ON nucleo_comun.notificacion TO rol_app_nucleo;
GRANT SELECT, UPDATE (estado_envio, intentos, proximo_intento, ultimo_error, enviado_en) ON nucleo_comun.notificacion TO rol_tareas;
GRANT SELECT (id, correo, nombre) ON nucleo_comun.usuario TO rol_tareas;
ALTER TABLE nucleo_comun.notificacion ENABLE ROW LEVEL SECURITY;
CREATE POLICY notificacion_propia ON nucleo_comun.notificacion TO rol_app_nucleo
USING (destinatario_id = nucleo_comun.actor_id()) WITH CHECK (destinatario_id = nucleo_comun.actor_id());
CREATE POLICY notificacion_invitacion ON nucleo_comun.notificacion FOR INSERT TO rol_app_odr
WITH CHECK (tipo = 'INVITACION' AND destinatario_id IS NULL AND correo IS NOT NULL);
CREATE POLICY notificacion_despacho ON nucleo_comun.notificacion TO rol_tareas USING (true) WITH CHECK (true);
CREATE POLICY usuario_despacho ON nucleo_comun.usuario FOR SELECT TO rol_tareas USING (true);
COMMIT;
