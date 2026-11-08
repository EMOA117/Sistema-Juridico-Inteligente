// Paneles laterales de la sala: mediador certificado (RF3.4) y sugerencia de acuerdo por IA (RF3.3).
import { useState } from 'react';
import { CajaIA } from '@/compartido/componentes';
import { ia, odr } from '@/compartido/servicios';
import { intentar } from '@/compartido/servicios/useDatos';
import type { Mediacion } from '@/compartido/tipos';

export const textoModalidad: Record<string, string> = {
  VIDEOLLAMADA_CONJUNTA: 'Videollamada conjunta', SESION_PRIVADA: 'Sesión privada', TELEFONICA: 'Llamada telefónica',
};

/** RF3.3 · Fórmula de arreglo sugerida por IA a partir de casos sintéticos similares. Nunca es una resolución. */
export function PanelSugerencia({ mediacionId, usar }: { mediacionId: string; usar: (texto: string) => void }) {
  const [estado, setEstado] = useState<'inicial' | 'cargando' | 'listo'>('inicial');
  const [r, setR] = useState<Awaited<ReturnType<typeof ia.sugerenciaAcuerdo>> | null>(null);

  async function pedir() {
    setEstado('cargando');
    try { setR(await ia.sugerenciaAcuerdo(mediacionId)); } catch { setR({ disponible: false }); }
    setEstado('listo');
  }

  return (
    <CajaIA titulo={r?.latencia_ms ? `Sugerencia de acuerdo · IA · ${(r.latencia_ms / 1000).toFixed(1)} s` : 'Sugerencia de acuerdo · IA'}>
      {estado === 'inicial' && (
        <>
          <p className="pequeno">El asistente compara su caso con ejemplos sintéticos similares y propone una fórmula de arreglo.</p>
          <button type="button" className="boton secundario" onClick={pedir}>Pedir sugerencia</button>
        </>
      )}
      {estado === 'cargando' && <p className="pequeno" role="status">Analizando casos similares… puede tardar unos segundos.</p>}
      {estado === 'listo' && r && (!r.disponible ? (
        <p className="pequeno">El asistente no está disponible ahora. Pueden seguir negociando normalmente.</p>
      ) : !r.sugerencia ? (
        <p className="pequeno">{r.fundamento}</p>
      ) : (
        <>
          <p><strong>{r.sugerencia}</strong></p>
          <p className="pequeno">{r.fundamento} <span className="texto-2">({r.casos} ejemplos sintéticos de demostración)</span></p>
          <span className="pequeno texto-2">No es una resolución. Pueden ignorarla o modificarla.</span>
          <button type="button" className="boton secundario" onClick={() => usar(r.sugerencia!)}>Usar como mi contrapropuesta</button>
        </>
      ))}
    </CajaIA>
  );
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
