// Paneles laterales de la sala: mediador certificado (RF3.4) y sugerencia de acuerdo por IA (RF3.3).
import { useState } from 'react';
import { odr } from '@/compartido/servicios';
import { intentar } from '@/compartido/servicios/useDatos';
import type { Mediacion } from '@/compartido/tipos';

export const textoModalidad: Record<string, string> = {
  VIDEOLLAMADA_CONJUNTA: 'Videollamada conjunta', SESION_PRIVADA: 'Sesión privada', TELEFONICA: 'Llamada telefónica',
};

export function PanelSugerencia(_: { mediacionId: string; usar: (texto: string) => void }) {
  return null;  // se completa con el asistente de IA
}

export function PanelMediador({ mediacion: m, alCambiar, alError }: { mediacion: Mediacion; alCambiar: () => void; alError: (m: string) => void }) {
  const [pidiendo, setPidiendo] = useState(false);

  async function solicitar() {
    if (!confirm('¿Solicitar la intervención de un mediador certificado? Se asignará según su especialidad y disponibilidad.')) return;
    setPidiendo(true);
    if (await intentar(() => odr.solicitarMediador(m.id), alError)) alCambiar();
    setPidiendo(false);
  }

  if (!m.mediador) {
    return <button type="button" className="boton secundario" disabled={pidiendo} onClick={solicitar}>Solicitar mediador certificado</button>;
  }
  return (
    <div className="columna" style={{ gap: 6 }}>
      <span className="titulo-seccion">Mediador asignado</span>
      <strong>{m.mediador.nombre}</strong>
      <span className="mono pequeno texto-2">Certificación {m.mediador.num_certificacion}</span>
      {m.sesiones.length > 0 && <span className="titulo-seccion" style={{ marginTop: 8 }}>Próximas sesiones</span>}
      {m.sesiones.map((s) => (
        <div key={s.id} className="pequeno">
          <strong>{new Date(s.inicio).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })}</strong> · {textoModalidad[s.modalidad]}
          {s.enlace && <> · <a href={s.enlace} target="_blank" rel="noreferrer">Enlace</a></>}
        </div>
      ))}
    </div>
  );
}
