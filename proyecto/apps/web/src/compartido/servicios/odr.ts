import { http } from './api';

export interface AsuntoODR {
  id: string; titulo: string; materia: string | null; estado: string; solicitante_id: string;
  narrativa_inicial?: string; mediable?: boolean; creado_en: string;
  estado_mediacion?: string; resultado?: string;
}
export interface ParteODR { id: string; usuario_id: string | null; rol: string; nombre: string; correo: string; domicilio_notificaciones: string }
export interface MensajeODR { id: string; autor_id: string; texto: string; creado_en: string }
export interface PropuestaODR extends MensajeODR { estado: string; monto: string | null; responde_a_id: string | null }
export interface ConvenioODR {
  id: string; tipo: 'TOTAL' | 'PARCIAL'; terminos: string; puntos_pendientes: string[];
  hash_sha256: string; formalizado_en: string | null; modo_firma: string;
  firmas: { usuario_id: string; firmado_en: string; modo: string }[];
}
export interface DetalleODR {
  conflicto: AsuntoODR; partes: ParteODR[];
  mediacion: { id: string; estado: string; resultado: string | null; mediador_id: string | null; solicitud_mediador_en: string | null } | null;
  invitacion: { estado: string; fecha_limite: string } | null;
  mensajes: MensajeODR[]; propuestas: PropuestaODR[];
  sesiones: { id: string; fecha_hora: string; enlace: string }[];
  notas: { id: string; sesion_id: string; texto: string }[];
  convenio: ConvenioODR | null;
}
export interface AvisoODR { id: string; conflicto_id: string; evento: string; leida: boolean; creado_en: string }
export const etiqueta = (valor: string) => valor.toLowerCase().replace(/_/g, ' ');
export const fecha = (valor: string) => new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(valor));
export const enviar = <T = unknown>(ruta: string, datos: unknown = {}, metodo = 'POST', idempotente = false) =>
  http<T>(ruta, { method: metodo, body: JSON.stringify(datos), headers: idempotente ? { 'Idempotency-Key': crypto.randomUUID() } : {} });
export const cargarODR = (id: string) => http<DetalleODR>(`/odr/${id}`);
export async function descargarConvenio(id: string) {
  const r = await fetch(`${import.meta.env.VITE_API_URL ?? '/api'}/odr/${id}/convenio/documento`, {
    headers: { Authorization: `Bearer ${sessionStorage.getItem('token') ?? ''}` },
  });
  if (!r.ok) {
    if (r.status === 401) window.dispatchEvent(new Event('sesion-expirada'));
    throw new Error('No se pudo descargar el convenio.');
  }
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement('a'); a.href = url; a.download = `convenio-${id}.pdf`; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
