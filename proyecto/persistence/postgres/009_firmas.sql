-- RF4.3, RF4.4, RF9.1–RF9.5, RNF5.1: certificados, firmas de convenio, resolución firmada, firmeza y verificación.
BEGIN;

-- Certificado X.509 por firmante (PKI local de demostración). La llave privada se guarda cifrada (simula un HSM).
CREATE TABLE nucleo_comun.certificado (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id uuid NOT NULL REFERENCES nucleo_comun.usuario(id),
    num_serie text NOT NULL UNIQUE,
    cert_pem text NOT NULL,
    llave_cifrada bytea NOT NULL,
    emitido_en timestamptz NOT NULL DEFAULT now(),
    vence_en timestamptz NOT NULL,
    revocado boolean NOT NULL DEFAULT false
);
CREATE UNIQUE INDEX ux_certificado_vigente ON nucleo_comun.certificado (usuario_id) WHERE NOT revocado;

-- Firmas del convenio: una por parte registrada y, si lo hay, por el mediador.
CREATE TABLE schema_odr.firma_convenio (
    convenio_id uuid NOT NULL REFERENCES schema_odr.convenio(id),
    usuario_id uuid NOT NULL REFERENCES nucleo_comun.usuario(id),
    num_serie text NOT NULL,
    sello_tiempo timestamptz NOT NULL,
    PRIMARY KEY (convenio_id, usuario_id)
);
-- Documento en proceso de firma (bucket de trabajo); el final va al almacén WORM.
ALTER TABLE schema_odr.convenio ADD COLUMN clave_borrador text;

-- Las firmas existentes se invalidan si cambia el texto: se revoca la aprobación al editar (008) y aquí se
-- impide editar un convenio que ya tiene firmas.
CREATE FUNCTION schema_odr.bloquear_convenio_firmado() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, schema_odr, pg_temp AS $$
BEGIN
    IF (NEW.terminos_acordados_cifrados IS DISTINCT FROM OLD.terminos_acordados_cifrados
        OR NEW.tipo IS DISTINCT FROM OLD.tipo OR NEW.puntos_pendientes IS DISTINCT FROM OLD.puntos_pendientes)
       AND EXISTS (SELECT 1 FROM schema_odr.firma_convenio f WHERE f.convenio_id = OLD.id) THEN
        RAISE EXCEPTION 'El convenio ya tiene firmas: no puede modificarse';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER tr_convenio_firmado BEFORE UPDATE ON schema_odr.convenio
FOR EACH ROW EXECUTE FUNCTION schema_odr.bloquear_convenio_firmado();

-- RF6.5 / RF9.3: al cerrar el expediente judicial se concluye el conflicto (el rol judicial no edita el núcleo).
CREATE FUNCTION nucleo_comun.concluir_por_expediente(p_expediente_id uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, nucleo_comun, schema_judicial, pg_temp AS $$
DECLARE e schema_judicial.expediente%ROWTYPE; cid uuid;
BEGIN
    SELECT * INTO e FROM schema_judicial.expediente WHERE id = p_expediente_id;
    IF NOT FOUND OR e.juez_id IS DISTINCT FROM nucleo_comun.actor_id() THEN RAISE EXCEPTION 'Expediente no autorizado'; END IF;
    IF e.estado <> 'CERRADO' THEN RAISE EXCEPTION 'El expediente no está cerrado'; END IF;
    SELECT conflicto_id INTO cid FROM schema_judicial.demanda WHERE id = e.demanda_id;
    UPDATE nucleo_comun.conflicto SET estado = 'CONCLUIDO' WHERE id = cid AND estado = 'CANALIZADO';
    INSERT INTO nucleo_comun.bitacora (usuario_id, entidad, entidad_id, accion, estado_anterior, estado_nuevo, operacion_id)
    VALUES (nucleo_comun.actor_id(), 'conflicto', cid, 'CONCLUIDO_POR_RESOLUCION', 'CANALIZADO', 'CONCLUIDO', gen_random_uuid());
    PERFORM nucleo_comun.notificar(cid, 'EXPEDIENTE_CERRADO', 'expediente', p_expediente_id, NULL, false);
END $$;

-- Verificación pública por huella SHA-256: confirma existencia, tipo y fecha; nunca devuelve contenido.
CREATE FUNCTION nucleo_comun.verificar_documento(p_hash text)
RETURNS TABLE (tipo text, dominio text, referencia text, creado_en timestamptz, firmas int)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, nucleo_comun, schema_odr, schema_judicial, pg_temp AS $$
    SELECT d.tipo, d.dominio,
           coalesce(c.folio, 'EXP ' || e.numero),
           d.creado_en,
           CASE d.tipo WHEN 'CONVENIO' THEN (SELECT count(*)::int FROM schema_odr.convenio v
                                             JOIN schema_odr.firma_convenio f ON f.convenio_id = v.id WHERE v.documento_id = d.id)
                       ELSE 1 END
    FROM nucleo_comun.documento d
    LEFT JOIN nucleo_comun.conflicto c ON c.id = d.conflicto_id AND d.dominio = 'ODR'
    LEFT JOIN schema_judicial.expediente e ON e.id = d.expediente_id
    WHERE d.hash_sha256 = lower(p_hash) AND d.tipo IN ('CONVENIO','RESOLUCION','DICTAMEN')
$$;

-- Permisos ---------------------------------------------------------------------------------------
GRANT SELECT, INSERT ON nucleo_comun.certificado TO rol_app_odr, rol_app_judicial;
ALTER TABLE nucleo_comun.certificado ENABLE ROW LEVEL SECURITY;
CREATE POLICY certificado_propio ON nucleo_comun.certificado TO rol_app_odr, rol_app_judicial
USING (usuario_id = nucleo_comun.actor_id()) WITH CHECK (usuario_id = nucleo_comun.actor_id());

GRANT SELECT, INSERT ON schema_odr.firma_convenio TO rol_app_odr;
ALTER TABLE schema_odr.firma_convenio ENABLE ROW LEVEL SECURITY;
CREATE POLICY firma_convenio_relacion ON schema_odr.firma_convenio TO rol_app_odr
USING (EXISTS (SELECT 1 FROM schema_odr.convenio v WHERE v.id = convenio_id))
WITH CHECK (usuario_id = nucleo_comun.actor_id() AND EXISTS (SELECT 1 FROM schema_odr.convenio v WHERE v.id = convenio_id));

GRANT UPDATE (fecha_firmeza) ON schema_judicial.resolucion TO rol_app_judicial;
-- Las partes consultan la resolución de su expediente (solo lectura).
CREATE POLICY resolucion_partes ON schema_judicial.resolucion FOR SELECT TO rol_app_judicial
USING (EXISTS (SELECT 1 FROM schema_judicial.expediente e WHERE e.id = expediente_id));

REVOKE ALL ON FUNCTION nucleo_comun.concluir_por_expediente(uuid), nucleo_comun.verificar_documento(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nucleo_comun.concluir_por_expediente(uuid) TO rol_app_judicial;
GRANT EXECUTE ON FUNCTION nucleo_comun.verificar_documento(text) TO rol_auth;
COMMIT;
