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
