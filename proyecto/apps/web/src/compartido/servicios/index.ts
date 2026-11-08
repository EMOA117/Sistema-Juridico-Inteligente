// Un objeto por módulo de core-api. Las rutas coinciden con los routers de FastAPI.
import type {
  Aviso, CargaJuez, Convenio, MediadorPadron, SesionMediacion, Conflicto, Demanda, Expediente, ExpedienteResumen, Indicadores, Mediacion, MediacionResumen,
  Materia, Orientacion, Parte, RespuestaLogin, Usuario,
} from '@/compartido/tipos';
import { get, patch, post, put } from './api';

export const identidad = {
  iniciarSesion: (correo: string, contrasena: string, codigo_mfa?: string) =>
    post<RespuestaLogin>('/auth/login', { correo, contrasena, codigo_mfa: codigo_mfa || null }),
  registrar: (datos: { nombre: string; correo: string; curp: string; contrasena: string }) =>
    post<RespuestaLogin>('/auth/registro', datos),
  yo: () => get<Usuario>('/auth/yo'),
  renovar: () => post<{ token: string }>('/auth/renovar'),
  altaMfa: () => post<{ qr_svg: string; secreto: string }>('/auth/mfa/alta'),
  confirmarMfa: (codigo: string) => post<{ token: string; usuario: Usuario }>('/auth/mfa/confirmar', { codigo }),
  cambiarContrasena: (actual: string, nueva: string) => post('/auth/cambiar-contrasena', { actual, nueva }),
  personal: () => get<(Usuario & { activo: boolean; mfa_habilitado: boolean })[]>('/admin/usuarios'),
  altaPersonal: (datos: { nombre: string; correo: string; rol: string; cargo?: string }) =>
    post<{ id: string; contrasena_temporal: string }>('/admin/usuarios', datos),
  estadoPersonal: (id: string, activo: boolean) => patch(`/admin/usuarios/${id}`, { activo }),
};

export const conflictos = {
  mios: () => get<Conflicto[]>('/conflictos'),
  detalle: (id: string) => get<Conflicto & { partes: Parte[] }>(`/conflictos/${id}`),
  crear: (solicitante: Partial<Parte> & { nombre: string; domicilio?: string }, contraparte: { nombre: string; correo?: string; domicilio?: string }) =>
    post<{ id: string; folio: string }>('/conflictos', { solicitante, contraparte }),
  narrativa: (id: string, narrativa: string) => put<Orientacion>(`/conflictos/${id}/narrativa`, { narrativa }),
  confirmar: (id: string, materia: Materia) => post(`/conflictos/${id}/confirmar`, { materia }),
  actualizarParte: (parteId: string, datos: { domicilio?: string; correo?: string }) => patch(`/conflictos/partes/${parteId}`, datos),
  canalizar: (id: string) => post<{ demanda_id: string }>(`/conflictos/${id}/canalizar`),
  invitar: (id: string, correo: string, plazo_dias: number) =>
    post<{ mediacion_id: string; fecha_limite: string }>(`/conflictos/${id}/mediacion`, { correo, plazo_dias }),
};

export const invitaciones = {
  ver: (token: string) => get<{ folio: string; materia: Materia; solicitante: string; invitado: string; estado: string; fecha_limite: string }>(`/invitaciones/${token}`),
  responder: (token: string, acepta: boolean) => post<{ mediacion_id: string }>(`/invitaciones/${token}/responder`, { acepta }),
};

export const notificaciones = {
  bandeja: () => get<{ sin_leer: number; avisos: Aviso[] }>('/notificaciones'),
  leidas: (ids?: string[]) => post('/notificaciones/leidas', { ids: ids ?? null }),
};

export const odr = {
  mediaciones: () => get<MediacionResumen[]>('/mediaciones'),
  detalle: (id: string) => get<Mediacion>(`/mediaciones/${id}`),
  mensaje: (id: string, texto: string) => post(`/mediaciones/${id}/mensajes`, { texto }),
  propuesta: (id: string, texto: string) => post(`/mediaciones/${id}/propuestas`, { texto }),
  responder: (propuestaId: string, estado: 'ACEPTADA' | 'RECHAZADA') =>
    post(`/mediaciones/propuestas/${propuestaId}/responder`, { estado }),
  terminar: (id: string, resultado: 'SIN_ACUERDO' | 'DESISTIMIENTO') => post(`/mediaciones/${id}/terminar`, { resultado }),
  solicitarMediador: (id: string) => post<{ nombre: string; num_certificacion: string }>(`/mediaciones/${id}/solicitar-mediador`),
  sesiones: (id: string) => get<SesionMediacion[]>(`/mediaciones/${id}/sesiones`),
  programarSesion: (id: string, datos: { inicio: string; duracion_min: number; modalidad: string; enlace?: string }) =>
    post(`/mediaciones/${id}/sesiones`, datos),
  cambiarSesion: (sesionId: string, estado: 'CANCELADA' | 'REALIZADA') => post(`/mediaciones/sesiones/${sesionId}/estado`, { estado }),
  agenda: () => get<SesionMediacion[]>('/mediador/agenda'),
  notas: (id: string) => get<{ id: string; texto: string; creado_en: string }[]>(`/mediaciones/${id}/notas`),
  agregarNota: (id: string, texto: string) => post(`/mediaciones/${id}/notas`, { texto }),
  concluir: (id: string, resultado: 'SIN_ACUERDO' | 'DESISTIMIENTO' | 'NO_ACEPTADA') => post(`/mediaciones/${id}/concluir`, { resultado }),
  convenio: (id: string) => get<Convenio | null>(`/mediaciones/${id}/convenio`),
  redactarConvenio: (id: string, datos: { tipo: 'TOTAL' | 'PARCIAL'; terminos: string; puntos_pendientes: string[] }) =>
    put(`/mediaciones/${id}/convenio`, datos),
  aprobarConvenio: (id: string) => post(`/mediaciones/${id}/convenio/aprobar`),
};

export const judicial = {
  demandaDeConflicto: (conflictoId: string) => get<Demanda>(`/conflictos/${conflictoId}/demanda`),
  borrador: (demandaId: string, pretension: string, tipo_juicio: string) =>
    post<{ texto: string; origen: string; modelo?: string; latencia_ms?: number }>(`/demandas/${demandaId}/borrador`, { pretension, tipo_juicio }),
  guardar: (demandaId: string, texto: string) => put(`/demandas/${demandaId}`, { texto }),
  confirmar: (demandaId: string, texto: string) =>
    post<{ expediente_id: string; numero: string }>(`/demandas/${demandaId}/confirmar`, { texto }),
  expedientes: () => get<ExpedienteResumen[]>('/expedientes'),
  expediente: (id: string) => get<Expediente>(`/expedientes/${id}`),
  dictamen: (id: string, decision: 'ADMITIR' | 'PREVENIR', texto?: string) =>
    post<{ estado: string }>(`/expedientes/${id}/dictamen`, { decision, texto }),
  corregir: (id: string, texto: string) => post(`/expedientes/${id}/correccion`, { texto }),
};

export const administracion = {
  turno: () => get<{ id: string; numero: string; materia: Materia; origen: string; creado_en: string }[]>('/admin/turno'),
  carga: () => get<CargaJuez[]>('/admin/carga-jueces'),
  asignar: (expedienteId: string, juez_id: string) => post(`/admin/expedientes/${expedienteId}/asignar`, { juez_id }),
  indicadores: () => get<Indicadores>('/admin/indicadores'),
  padronMediadores: () => get<{
    mediadores: MediadorPadron[];
    sin_registro: { id: string; nombre: string; correo: string }[];
    asignaciones: { mediacion_id: string; folio: string; materia: Materia; estado: string; mediador_id: string | null; mediador: string | null; solicitado_en: string | null }[];
  }>('/admin/mediadores'),
  registrarMediador: (usuarioId: string, datos: { num_certificacion: string; especialidades: Materia[]; max_casos: number; activo: boolean }) =>
    put(`/admin/mediadores/${usuarioId}`, datos),
  reasignar: (mediacionId: string, mediador_id: string) => post(`/admin/asignaciones/${mediacionId}`, { mediador_id }),
};
