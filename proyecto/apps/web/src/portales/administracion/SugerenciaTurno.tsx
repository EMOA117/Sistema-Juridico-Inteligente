// RF7.2 · Sugerencia de turno por carga y especialidad. Solo apoyo: la asignación la confirma una persona.
import { useState } from 'react';
import { CajaIA } from '@/compartido/componentes';
import { ia } from '@/compartido/servicios';

export function SugerenciaTurno({ expedienteId, elegir }: { expedienteId: string; elegir: (juezId: string) => void }) {
  const [r, setR] = useState<Awaited<ReturnType<typeof ia.sugerenciaTurno>> | null>(null);
  const [cargando, setCargando] = useState(false);

  async function pedir() {
    setCargando(true);
    try { setR(await ia.sugerenciaTurno(expedienteId)); } catch { setR({ disponible: false, sugerencias: [] }); }
    setCargando(false);
  }

  if (!r) return <button type="button" className="boton secundario" style={{ alignSelf: 'flex-start' }} disabled={cargando} onClick={pedir}>
    {cargando ? 'Calculando sugerencia…' : 'Sugerir juez con IA'}</button>;
  if (!r.disponible || r.sugerencias.length === 0) return <p className="pequeno texto-2">Sin sugerencia disponible: asigna manualmente.</p>;
  const [primera] = r.sugerencias;
  return (
    <CajaIA titulo="Sugerencia de turno · IA">
      <p className="pequeno">{primera.justificacion} <span className="mono">Puntaje {primera.puntaje.toFixed(2)}</span></p>
      <button type="button" className="boton secundario" style={{ alignSelf: 'flex-start' }} onClick={() => elegir(primera.juez_id)}>Usar sugerencia</button>
    </CajaIA>
  );
}
