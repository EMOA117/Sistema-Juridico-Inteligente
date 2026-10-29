-- Ejecutar como propietario de la base. PostgreSQL 15+.
BEGIN;
CREATE SCHEMA IF NOT EXISTS nucleo_comun;
CREATE SCHEMA IF NOT EXISTS schema_odr;
CREATE SCHEMA IF NOT EXISTS schema_judicial;
CREATE SCHEMA IF NOT EXISTS analitica;

CREATE TABLE nucleo_comun.usuario (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    correo text NOT NULL UNIQUE,
    nombre text NOT NULL,
    password_hash text NOT NULL,
    activo boolean NOT NULL DEFAULT true,
    mfa_habilitado boolean NOT NULL DEFAULT false,
    creado_en timestamptz NOT NULL DEFAULT now(),
    CHECK (correo = lower(correo))
);
CREATE TABLE nucleo_comun.usuario_rol (
    usuario_id uuid NOT NULL REFERENCES nucleo_comun.usuario(id),
    rol text NOT NULL CHECK (rol IN ('CIUDADANO','MEDIADOR','JUEZ','ADMINISTRADOR')),
    PRIMARY KEY (usuario_id, rol)
);
CREATE TABLE nucleo_comun.conflicto (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    solicitante_id uuid NOT NULL REFERENCES nucleo_comun.usuario(id),
    estado text NOT NULL DEFAULT 'CAPTURA' CHECK (estado IN ('CAPTURA','ORIENTADO','EN_MEDIACION','EN_ESPERA_DECISION','CANALIZADO','CONCLUIDO')),
    narrativa_inicial text,
    materia text CHECK (materia IN ('CIVIL','FAMILIAR')),
    mediable boolean,
    creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE nucleo_comun.parte (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conflicto_id uuid NOT NULL REFERENCES nucleo_comun.conflicto(id),
    usuario_id uuid REFERENCES nucleo_comun.usuario(id),
    rol text NOT NULL CHECK (rol IN ('DEMANDANTE','DEMANDADO')),
    nombre text NOT NULL,
    correo text,
    domicilio_notificaciones text,
    UNIQUE (conflicto_id, rol)
);
CREATE TABLE nucleo_comun.bitacora (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id uuid,
    entidad text NOT NULL,
    entidad_id uuid NOT NULL,
    accion text NOT NULL,
    estado_anterior text,
    estado_nuevo text,
    operacion_id uuid NOT NULL,
    ocurrido_en timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE schema_odr.mediacion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conflicto_id uuid NOT NULL UNIQUE REFERENCES nucleo_comun.conflicto(id),
    mediador_id uuid REFERENCES nucleo_comun.usuario(id),
    estado text NOT NULL DEFAULT 'INVITACION_ENVIADA' CHECK (estado IN ('INVITACION_ENVIADA','EN_NEGOCIACION','PENDIENTE_FORMALIZACION','CONCLUIDA')),
    resultado text CHECK (resultado IN ('ACUERDO_TOTAL','ACUERDO_PARCIAL','NO_ACEPTADA','SIN_ACUERDO','DESISTIMIENTO')),
    concluida_en timestamptz,
    CHECK ((estado = 'CONCLUIDA') = (resultado IS NOT NULL AND concluida_en IS NOT NULL))
);
CREATE TABLE schema_odr.invitacion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mediacion_id uuid NOT NULL REFERENCES schema_odr.mediacion(id),
    contraparte_id uuid NOT NULL REFERENCES nucleo_comun.parte(id),
    estado text NOT NULL DEFAULT 'ENVIADA' CHECK (estado IN ('ENVIADA','ACEPTADA','RECHAZADA','VENCIDA')),
    fecha_limite date NOT NULL,
    creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE schema_odr.mensaje (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mediacion_id uuid NOT NULL REFERENCES schema_odr.mediacion(id),
    autor_id uuid NOT NULL REFERENCES nucleo_comun.usuario(id),
    contenido_cifrado bytea NOT NULL,
    creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE schema_odr.propuesta (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mediacion_id uuid NOT NULL REFERENCES schema_odr.mediacion(id),
    contenido_cifrado bytea NOT NULL,
    creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE schema_odr.nota_mediador (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mediacion_id uuid NOT NULL REFERENCES schema_odr.mediacion(id),
    mediador_id uuid NOT NULL REFERENCES nucleo_comun.usuario(id),
    contenido_cifrado bytea NOT NULL,
    creado_en timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE schema_odr.convenio (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mediacion_id uuid NOT NULL UNIQUE REFERENCES schema_odr.mediacion(id),
    tipo text NOT NULL CHECK (tipo IN ('TOTAL','PARCIAL')),
    puntos_pendientes text[] NOT NULL DEFAULT '{}',
    terminos_acordados_cifrados bytea NOT NULL,
    formalizado_en timestamptz,
    documento_id uuid,
    hash_sha256 text,
    num_serie_firma text,
    sello_tiempo timestamptz,
    CHECK (tipo <> 'PARCIAL' OR cardinality(puntos_pendientes) > 0),
    CHECK (formalizado_en IS NULL OR (documento_id IS NOT NULL AND hash_sha256 IS NOT NULL AND num_serie_firma IS NOT NULL AND sello_tiempo IS NOT NULL))
);

CREATE TABLE schema_judicial.demanda (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conflicto_id uuid NOT NULL UNIQUE REFERENCES nucleo_comun.conflicto(id),
    estado text NOT NULL DEFAULT 'BORRADOR' CHECK (estado IN ('BORRADOR','CONFIRMADA')),
    origen text NOT NULL CHECK (origen IN ('DIRECTA','NO_ACEPTADA','SIN_ACUERDO','DESISTIMIENTO','ACUERDO_PARCIAL')),
    demandante_id uuid NOT NULL REFERENCES nucleo_comun.parte(id),
    demandado_id uuid NOT NULL REFERENCES nucleo_comun.parte(id),
    narrativa_inicial text NOT NULL,
    materia text NOT NULL CHECK (materia IN ('CIVIL','FAMILIAR')),
    puntos_pendientes text[],
    texto_final text,
    creada_en timestamptz NOT NULL DEFAULT now(),
    CHECK ((origen = 'ACUERDO_PARCIAL') = (coalesce(cardinality(puntos_pendientes), 0) > 0))
);
CREATE TABLE schema_judicial.expediente (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    demanda_id uuid NOT NULL UNIQUE REFERENCES schema_judicial.demanda(id),
    juez_id uuid REFERENCES nucleo_comun.usuario(id),
    estado text NOT NULL DEFAULT 'EN_TURNO' CHECK (estado IN ('EN_TURNO','EN_REVISION','PREVENIDO','ADMITIDO','EN_TRAMITE','RESUELTO','DESECHADO','CERRADO')),
    fecha_emplazamiento_validado date,
    fecha_limite_contestacion date,
    fecha_firmeza date,
    creado_en timestamptz NOT NULL DEFAULT now(),
    CHECK ((fecha_emplazamiento_validado IS NULL) = (fecha_limite_contestacion IS NULL)),
    CHECK (fecha_limite_contestacion IS NULL OR fecha_limite_contestacion = fecha_emplazamiento_validado + 15)
);
CREATE TABLE schema_judicial.contestacion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    expediente_id uuid NOT NULL UNIQUE REFERENCES schema_judicial.expediente(id),
    fecha_presentacion timestamptz NOT NULL DEFAULT now(),
    en_plazo boolean NOT NULL,
    documento_id uuid NOT NULL
);
CREATE TABLE schema_judicial.resolucion (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    expediente_id uuid NOT NULL UNIQUE REFERENCES schema_judicial.expediente(id),
    resultado text NOT NULL,
    documento_id uuid NOT NULL,
    hash_sha256 text NOT NULL,
    num_serie_firma text NOT NULL,
    firmada_en timestamptz NOT NULL,
    sello_tiempo timestamptz NOT NULL,
    fecha_firmeza date
);
CREATE TABLE schema_judicial.historial_estado (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    expediente_id uuid NOT NULL REFERENCES schema_judicial.expediente(id),
    usuario_id uuid NOT NULL REFERENCES nucleo_comun.usuario(id),
    estado_anterior text NOT NULL,
    estado_nuevo text NOT NULL,
    motivo text NOT NULL,
    ocurrido_en timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON nucleo_comun.conflicto (solicitante_id, estado);
CREATE INDEX ON schema_odr.invitacion (fecha_limite) WHERE estado = 'ENVIADA';
CREATE INDEX ON schema_judicial.expediente (estado, fecha_limite_contestacion) WHERE estado = 'ADMITIDO';
COMMIT;
