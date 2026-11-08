import type { ReactNode } from 'react';
import { IconoCandado, IconoIA } from './Iconos';
export * from './Iconos';

/** Folio de un asunto: círculo = ruta ODR (jade), cuadro = ruta judicial (toga). */
export function Folio({ ruta, children }: { ruta: 'odr' | 'judicial'; children: ReactNode }) {
  return <span className={`folio ${ruta}`}>{children}</span>;
}

export type TonoEstado = 'aceptada' | 'pendiente' | 'rechazada' | 'tramite';
export function Estado({ tono, children }: { tono: TonoEstado; children: ReactNode }) {
  return <span className={`estado ${tono}`}>{children}</span>;
}

/** Todo contenido generado por IA va dentro de esta caja: identificado y editable. */
export function CajaIA({ titulo = 'Asistido por IA · editable', children }: { titulo?: string; children: ReactNode }) {
  return (
    <div className="caja-ia">
      <span className="sello"><IconoIA />{titulo}</span>
      {children}
    </div>
  );
}

export function AvisoConfidencial({ children }: { children: ReactNode }) {
  return (
    <div className="aviso-confidencial" role="note">
      <IconoCandado />
      <span>{children}</span>
    </div>
  );
}

/** Riel de etapas. `actual` es el índice de la etapa en curso. */
export function Riel({ etapas, actual, ruta = 'odr' }: { etapas: string[]; actual: number; ruta?: 'odr' | 'judicial' }) {
  return (
    <div className={`riel ${ruta === 'judicial' ? 'judicial' : ''}`} aria-label={`Avance: etapa ${actual + 1} de ${etapas.length}, ${etapas[actual]}`}>
      {etapas.map((e, i) => (
        <span key={e} style={{ display: 'contents' }}>
          {i > 0 && <span className="tramo" style={i > actual ? { opacity: 0.35 } : undefined} />}
          <span className={`paso ${i < actual ? 'hecho' : ''} ${i === actual ? 'actual' : ''}`}>
            <span className="marca-paso" />
            {e}
          </span>
        </span>
      ))}
    </div>
  );
}

export function Cargando() {
  return <p className="texto-2" role="status">Cargando…</p>;
}

export function MensajeError({ children }: { children: ReactNode }) {
  if (!children) return null;
  return <p role="alert" className="estado rechazada" style={{ alignSelf: 'flex-start', whiteSpace: 'normal' }}>{children}</p>;
}

/** Etiquetas legibles de estados y materias del dominio. */
export const textoEstado: Record<string, string> = {
  CAPTURA: 'En captura', ORIENTADO: 'Orientado', EN_MEDIACION: 'En mediación', EN_ESPERA_DECISION: 'Esperando tu decisión',
  CANALIZADO: 'En vía judicial', CONCLUIDO: 'Concluido',
  INVITACION_ENVIADA: 'Invitación enviada', EN_NEGOCIACION: 'En negociación', CON_MEDIADOR: 'Con mediador',
  PENDIENTE_FORMALIZACION: 'Convenio por formalizar', CONCLUIDA: 'Concluida',
  EN_TURNO: 'En turno', EN_REVISION: 'Por revisar', PREVENIDO: 'Prevenido', ADMITIDO: 'Admitido', EN_TRAMITE: 'En trámite',
  RESUELTO: 'Resuelto', DESECHADO: 'Desechado', CERRADO: 'Cerrado',
  ACUERDO_TOTAL: 'Acuerdo total', ACUERDO_PARCIAL: 'Acuerdo parcial', NO_ACEPTADA: 'Invitación no aceptada',
  SIN_ACUERDO: 'Sin acuerdo', DESISTIMIENTO: 'Desistimiento', DIRECTA: 'Directa',
  CIVIL: 'Civil', FAMILIAR: 'Familiar',
};
export const t = (v: string | null | undefined) => (v ? textoEstado[v] ?? v : '—');

export function tonoDe(estado: string): TonoEstado {
  if (['CONCLUIDO', 'ACEPTADA', 'ADMITIDO', 'RESUELTO', 'CERRADO', 'ACUERDO_TOTAL'].includes(estado)) return 'aceptada';
  if (['PREVENIDO', 'DESECHADO', 'RECHAZADA', 'SIN_ACUERDO', 'NO_ACEPTADA'].includes(estado)) return 'rechazada';
  if (['CANALIZADO', 'EN_TURNO', 'EN_TRAMITE'].includes(estado)) return 'tramite';
  return 'pendiente';
}
