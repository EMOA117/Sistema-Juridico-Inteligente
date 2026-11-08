// Tipos de dominio del cliente. Reflejan los enums de core-api
// (services/core-api/src/modulos/estado/modelo.py e identidad/autorizacion.py).

export type Rol = 'CIUDADANO' | 'MEDIADOR' | 'JUEZ' | 'ADMINISTRADOR';

export type EstadoConflicto =
  | 'CAPTURA' | 'ORIENTADO' | 'EN_MEDIACION' | 'EN_ESPERA_DECISION' | 'CANALIZADO' | 'CONCLUIDO';

export type EstadoExpediente =
  | 'EN_TURNO' | 'EN_REVISION' | 'PREVENIDO' | 'ADMITIDO' | 'EN_TRAMITE' | 'RESUELTO' | 'DESECHADO' | 'CERRADO';

export type ResultadoMediacion = 'ACUERDO_TOTAL' | 'ACUERDO_PARCIAL' | 'SIN_ACUERDO' | 'DESISTIMIENTO';

export type Materia = 'Civil' | 'Familiar' | 'Mercantil';

export interface Usuario {
  id: string;
  nombre: string;
  correo: string;
  rol: Rol;
  cargo?: string;
}

export interface Asunto {
  id: string;
  folio: string;               // CF-… (ODR) o EXP …/… (judicial)
  ruta: 'odr' | 'judicial';
  titulo: string;
  materia: Materia;
  estadoTexto: string;
  aviso?: string;
}

export interface Actividad {
  titulo: string;
  detalle?: string;
  referencia: string;
}

export interface Orientacion {
  folio: string;
  materia: Materia;
  certeza: number;             // 0..1
  complejidad: 'Baja' | 'Media' | 'Alta';
  mediable: boolean;
  motivo: string;
}

export interface Mensaje {
  id: string;
  autor: 'yo' | 'otra_parte';
  texto: string;
  fecha: string;
}

export type EstadoPropuesta = 'PENDIENTE' | 'ACEPTADA' | 'RECHAZADA';

export interface Propuesta {
  id: string;
  numero: number;
  autor: 'yo' | 'otra_parte';
  resumen: string;
  estado: EstadoPropuesta;
}

export interface ExpedienteResumen {
  id: string;
  numero: string;
  partes: string;
  materia: Materia;
  estado: EstadoExpediente;
  origen: string;
  plazoDias: number;
}

export interface Fragmento {
  id: string;
  documento: string;
  pagina: string;
  puntaje: number;
  texto: string;
}

export interface Mediacion {
  id: string;
  folio: string;
  partes: string;
  materia: Materia;
  estadoTexto: string;
  detalle: string;
}
