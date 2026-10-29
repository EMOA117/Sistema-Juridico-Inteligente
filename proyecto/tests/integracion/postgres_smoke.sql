-- Aplicar después de 001, 002, 003 y 004 en una base de prueba. Todo se revierte.
BEGIN;
INSERT INTO nucleo_comun.usuario (id, correo, nombre, password_hash) VALUES
 ('11111111-1111-4111-8111-111111111111', 'actor@example.test', 'Actor sintético', 'hash-qa'),
 ('22222222-2222-4222-8222-222222222222', 'contraparte@example.test', 'Contraparte sintética', 'hash-qa'),
 ('44444444-4444-4444-8444-444444444444', 'juez@example.test', 'Juez sintético', 'hash-qa');
INSERT INTO nucleo_comun.usuario_rol VALUES
 ('11111111-1111-4111-8111-111111111111', 'CIUDADANO'),
 ('22222222-2222-4222-8222-222222222222', 'CIUDADANO'),
 ('44444444-4444-4444-8444-444444444444', 'JUEZ');

-- Ruta directa: partes antes de orientar, canalización idempotente.
INSERT INTO nucleo_comun.conflicto (id, solicitante_id, narrativa_inicial, materia, mediable)
VALUES ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', '11111111-1111-4111-8111-111111111111', 'Relato inicial sintético', 'CIVIL', true);
INSERT INTO nucleo_comun.parte (id, conflicto_id, usuario_id, rol, nombre) VALUES
 ('a1111111-1111-4111-8111-111111111111','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','11111111-1111-4111-8111-111111111111','DEMANDANTE','Actor sintético'),
 ('a2222222-2222-4222-8222-222222222222','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','22222222-2222-4222-8222-222222222222','DEMANDADO','Contraparte sintética');
UPDATE nucleo_comun.conflicto SET estado = 'ORIENTADO' WHERE id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
SELECT set_config('app.usuario_id', '11111111-1111-4111-8111-111111111111', true);
SET ROLE rol_canalizador;
SELECT nucleo_comun.canalizar_conflicto('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','11111111-1111-4111-8111-111111111111');
SELECT nucleo_comun.canalizar_conflicto('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','11111111-1111-4111-8111-111111111111');
DO $$ BEGIN
  PERFORM 1 FROM schema_odr.mediacion;
  RAISE EXCEPTION 'rol_canalizador obtuvo acceso ODR';
EXCEPTION WHEN insufficient_privilege THEN NULL;
END $$;
RESET ROLE;
DO $$ BEGIN
  IF (SELECT count(*) FROM schema_judicial.demanda WHERE conflicto_id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa') <> 1 THEN
    RAISE EXCEPTION 'La canalización directa duplicó o no creó demanda';
  END IF;
END $$;

-- Ruta parcial: solo los puntos pendientes pasan a la demanda.
INSERT INTO nucleo_comun.conflicto (id, solicitante_id, narrativa_inicial, materia, mediable)
VALUES ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', '11111111-1111-4111-8111-111111111111', 'Otro relato inicial sintético', 'FAMILIAR', true);
INSERT INTO nucleo_comun.parte (id, conflicto_id, usuario_id, rol, nombre) VALUES
 ('b1111111-1111-4111-8111-111111111111','bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','11111111-1111-4111-8111-111111111111','DEMANDANTE','Actor sintético'),
 ('b2222222-2222-4222-8222-222222222222','bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','22222222-2222-4222-8222-222222222222','DEMANDADO','Contraparte sintética');
UPDATE nucleo_comun.conflicto SET estado = 'ORIENTADO' WHERE id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
UPDATE nucleo_comun.conflicto SET estado = 'EN_MEDIACION' WHERE id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
INSERT INTO schema_odr.mediacion (id, conflicto_id, estado, resultado, concluida_en)
VALUES ('cccccccc-cccc-4ccc-8ccc-cccccccccccc','bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','CONCLUIDA','ACUERDO_PARCIAL',now());
INSERT INTO schema_odr.convenio (mediacion_id, tipo, puntos_pendientes, terminos_acordados_cifrados,
                                formalizado_en, documento_id, hash_sha256, num_serie_firma, sello_tiempo)
VALUES ('cccccccc-cccc-4ccc-8ccc-cccccccccccc','PARCIAL',ARRAY['Punto aún controvertido'],decode('DEADBEEF','hex'),
        now(),gen_random_uuid(),'hash-qa','cert-qa',now());
UPDATE nucleo_comun.conflicto SET estado = 'EN_ESPERA_DECISION' WHERE id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
SET ROLE rol_canalizador;
SELECT nucleo_comun.canalizar_conflicto('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','11111111-1111-4111-8111-111111111111');
RESET ROLE;
DO $$ BEGIN
  IF (SELECT origen FROM schema_judicial.demanda WHERE conflicto_id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb') <> 'ACUERDO_PARCIAL'
     OR (SELECT puntos_pendientes[1] FROM schema_judicial.demanda WHERE conflicto_id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb') <> 'Punto aún controvertido' THEN
    RAISE EXCEPTION 'Contrato parcial incorrecto';
  END IF;
END $$;

-- Un expediente no se cierra sin resolución.
UPDATE schema_judicial.demanda SET estado = 'CONFIRMADA' WHERE conflicto_id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
INSERT INTO schema_judicial.expediente (id, demanda_id)
SELECT 'dddddddd-dddd-4ddd-8ddd-dddddddddddd', id FROM schema_judicial.demanda
WHERE conflicto_id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
UPDATE schema_judicial.expediente SET juez_id = '44444444-4444-4444-8444-444444444444', estado = 'EN_REVISION'
WHERE id = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';
UPDATE schema_judicial.expediente SET estado = 'ADMITIDO' WHERE id = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';
UPDATE schema_judicial.expediente SET fecha_emplazamiento_validado = DATE '2026-10-28'
WHERE id = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';
DO $$ BEGIN
  IF (SELECT fecha_limite_contestacion FROM schema_judicial.expediente
      WHERE id = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd') <> DATE '2026-11-12' THEN
    RAISE EXCEPTION 'El plazo no es de 15 días naturales';
  END IF;
END $$;
DO $$ BEGIN
  UPDATE schema_judicial.expediente SET estado = 'CERRADO' WHERE id = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';
  RAISE EXCEPTION 'Se permitió cerrar sin solución';
EXCEPTION WHEN raise_exception THEN
  IF SQLERRM = 'Se permitió cerrar sin solución' THEN RAISE; END IF;
END $$;
INSERT INTO schema_judicial.contestacion (expediente_id, fecha_presentacion, documento_id)
VALUES ('dddddddd-dddd-4ddd-8ddd-dddddddddddd', TIMESTAMPTZ '2026-11-10 12:00:00+00', gen_random_uuid());
DO $$ BEGIN
  IF NOT (SELECT en_plazo FROM schema_judicial.contestacion WHERE expediente_id = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd') THEN
    RAISE EXCEPTION 'La contestación en plazo fue marcada tardía';
  END IF;
END $$;
UPDATE schema_judicial.expediente SET estado = 'EN_TRAMITE' WHERE id = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';

SET ROLE rol_app_judicial;
SELECT set_config('app.usuario_id', '44444444-4444-4444-8444-444444444444', true);
DO $$ BEGIN
  IF (SELECT count(*) FROM schema_judicial.expediente WHERE id = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd') <> 1 THEN
    RAISE EXCEPTION 'El juez asignado no ve su expediente';
  END IF;
END $$;
SELECT set_config('app.usuario_id', '55555555-5555-4555-8555-555555555555', true);
DO $$ BEGIN
  IF (SELECT count(*) FROM schema_judicial.expediente WHERE id = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd') <> 0 THEN
    RAISE EXCEPTION 'Un tercero ve el expediente';
  END IF;
END $$;
DO $$ BEGIN
  PERFORM 1 FROM schema_odr.mensaje;
  RAISE EXCEPTION 'rol_app_judicial obtuvo acceso ODR';
EXCEPTION WHEN insufficient_privilege THEN NULL;
END $$;
RESET ROLE;
ROLLBACK;
