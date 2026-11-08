// Tipos de dominio del cliente. Reflejan las respuestas de core-api y sus enums
// (services/core-api/src/modulos/estado/modelo.py e identidad/autorizacion.py).

export type Rol = 'CIUDADANO' | 'MEDIADOR' | 'JUEZ' | 'ADMINISTRADOR';
export type Materia = 'CIVIL' | 'FAMILIAR';

export type EstadoConflicto =
  | 'CAPTURA' | 'ORIENTADO' | 'EN_MEDIACION' | 'EN_ESPERA_DECISION' | 'CANALIZADO' | 'CONCLUIDO';

export type EstadoExpediente =
  | 'EN_TURNO' | 'EN_REVISION' | 'PREVENIDO' | 'ADMITIDO' | 'EN_TRAMITE' | 'RESUELTO' | 'DESECHADO' | 'CERRADO';

export type EstadoMediacion = 'INVITACION_ENVIADA' | 'EN_NEGOCIACION' | 'CON_MEDIADOR' | 'PENDIENTE_FORMALIZACION' | 'CONCLUIDA';
export type ResultadoMediacion = 'ACUERDO_TOTAL' | 'ACUERDO_PARCIAL' | 'NO_ACEPTADA' | 'SIN_ACUERDO' | 'DESISTIMIENTO';

export interface Usuario {
  id: string;
  nombre: string;
  correo: string;
  rol: Rol;
  cargo?: string | null;
  mfa?: boolean;
}

export interface RespuestaLogin {
  token: string;
  usuario: Usuario;
  requiere_alta_mfa: boolean;
  debe_cambiar_password: boolean;
}

export interface Conflicto {
  id: string;
  folio: string;
  estado: EstadoConflicto;
  materia: Materia | null;
  mediable: boolean | null;
  complejidad: 'BAJA' | 'MEDIA' | 'ALTA' | null;
  confianza_clasificacion: number | null;
  narrativa_inicial: string | null;
  creado_en: string;
  solicitante: string;
  contraparte: string;
  soy_solicitante: boolean;
}

export interface Parte {
  id: string;
  rol: 'DEMANDANTE' | 'DEMANDADO';
  nombre: string;
  correo: string | null;
  domicilio_notificaciones: string | null;
  registrada?: boolean;
}

export interface Orientacion {
  materia: Materia;
  confianza: number;
  complejidad: 'BAJA' | 'MEDIA' | 'ALTA';
  mediable: boolean;
  motivo: string;
  origen: 'IA' | 'REGLAS';
  modelo?: string;
  latencia_ms?: number;
}

export interface MediacionResumen {
  id: string;
  conflicto_id: string;
  folio: string;
  materia: Materia;
  estado: EstadoMediacion;
  resultado: ResultadoMediacion | null;
  partes: string;
  propuestas: number;
}

export interface Mensaje {
  id: string;
  autor: 'yo' | 'otra_parte' | 'mediador';
  nombre: string;
  texto: string;
  fecha: string;
}

export type EstadoPropuesta = 'PENDIENTE' | 'ACEPTADA' | 'RECHAZADA';

export interface Propuesta {
  id: string;
  numero: number;
  autor: 'yo' | 'otra_parte' | 'mediador';
  resumen: string;
  estado: EstadoPropuesta;
  fecha: string;
}

export interface Mediacion {
  id: string;
  conflicto_id: string;
  folio: string;
  materia: Materia;
  estado: EstadoMediacion;
  resultado: ResultadoMediacion | null;
  soy_mediador: boolean;
  tiene_mediador: boolean;
  invitacion: { estado: string; fecha_limite: string } | null;
  partes: { rol: string; nombre: string }[];
  mediador: { nombre: string; num_certificacion: string } | null;
  sesiones: SesionMediacion[];
  mensajes: Mensaje[];
  propuestas: Propuesta[];
}

export interface Demanda {
  id: string;
  folio: string;
  estado: 'BORRADOR' | 'CONFIRMADA';
  origen: string;
  materia: Materia;
  narrativa_inicial: string;
  puntos_pendientes: string[];
  texto_final: string | null;
  partes: { demandante: Parte; demandado: Parte };
  soy_solicitante: boolean;
  expediente: { id: string; numero: string; estado: EstadoExpediente } | null;
}

export interface ExpedienteResumen {
  id: string;
  numero: string;
  estado: EstadoExpediente;
  materia: Materia;
  origen: string;
  folio: string;
  partes: string;
  creado_en: string;
  juez_id: string | null;
}

export interface Expediente extends ExpedienteResumen {
  demanda_id: string;
  texto_final: string | null;
  narrativa_inicial: string;
  puntos_pendientes: string[] | null;
  historial: { estado_anterior: string; estado_nuevo: string; motivo: string; ocurrido_en: string }[];
  actuaciones: { tipo: string; texto: string | null; ocurrido_en: string }[];
  documentos: { id: string; tipo: string; nombre: string; hash_sha256: string; creado_en: string }[];
  soy_juez: boolean;
}

export interface CargaJuez {
  juez_id: string;
  nombre: string;
  juzgado_id: string;
  juzgado: string;
  especialidad: Materia;
  expedientes_activos: number;
}

export interface Indicadores {
  conflictos_recibidos: number;
  mediaciones_iniciadas: number;
  acuerdos: number;
  mediaciones_concluidas: number;
  canalizados: number;
  expedientes: number;
  tasa_acuerdo: number | null;
  por_materia: { materia: Materia; total: number }[];
  expedientes_por_estado: { estado: EstadoExpediente; total: number }[];
}

export interface Fragmento {
  id: string;
  documento: string;
  pagina: string;
  puntaje: number;
  texto: string;
}

export interface Aviso {
  id: string;
  tipo: string;
  texto: string;
  folio: string | null;
  entidad: string;
  entidad_id: string;
  creado_en: string;
  leida_en: string | null;
}

export interface SesionMediacion {
  id: string;
  mediacion_id?: string;
  folio?: string;
  inicio: string;
  duracion_min: number;
  modalidad: 'VIDEOLLAMADA_CONJUNTA' | 'SESION_PRIVADA' | 'TELEFONICA';
  enlace: string | null;
  estado: 'PROGRAMADA' | 'CANCELADA' | 'REALIZADA';
}

export interface Convenio {
  id: string;
  tipo: 'TOTAL' | 'PARCIAL';
  terminos: string;
  puntos_pendientes: string[];
  formalizado_en: string | null;
  hash_sha256: string | null;
  documento_id: string | null;
  folio: string;
  materia: Materia;
  estado_mediacion: EstadoMediacion;
  mediador: { nombre: string; num_certificacion: string } | null;
  partes: { nombre: string; rol: string; aprobo: boolean; soy_yo: boolean }[];
  aprobado_por_todas: boolean;
}

export interface MediadorPadron {
  usuario_id: string;
  nombre: string;
  num_certificacion: string;
  especialidades: Materia[];
  max_casos: number;
  activo: boolean;
  mediaciones_activas: number;
}
