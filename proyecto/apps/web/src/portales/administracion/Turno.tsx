// P9 / RF7.1 · Turno: el personal administrativo confirma a qué juez se asigna cada expediente.
import { useState } from 'react';
import { Cargando, MensajeError, t } from '@/compartido/componentes';
import { administracion } from '@/compartido/servicios';
import { intentar, useDatos } from '@/compartido/servicios/useDatos';
import { SugerenciaTurno } from './SugerenciaTurno';

export default function Turno() {
  const { datos, error: errorCarga, recargar } = useDatos(async () => {
    const [turno, carga] = await Promise.all([administracion.turno(), administracion.carga()]);
    return { turno, carga };
  });
  const [eleccion, setEleccion] = useState<Record<string, string>>({});
  const [error, setError] = useState('');

  async function asignar(expedienteId: string, numero: string) {
    const juez = eleccion[expedienteId];
    const nombre = datos?.carga.find((c) => c.juez_id === juez)?.nombre;
    if (!juez || !confirm(`¿Asignar el expediente ${numero} a ${nombre}?`)) return;
    if (await intentar(() => administracion.asignar(expedienteId, juez), setError)) recargar();
  }

  return (
    <>
      <div>
        <h1 className="titulo-serif" style={{ fontSize: 40 }}>Turno de expedientes</h1>
        <span className="texto-2">La asignación siempre la confirma una persona; la sugerencia es solo apoyo.</span>
      </div>
      <MensajeError>{errorCarga || error}</MensajeError>
      {!datos ? <Cargando /> : (
        <div className="fila">
          <section className="columna" style={{ flex: '2 1 520px', gap: 12 }} aria-labelledby="h-turno">
            <h2 id="h-turno" className="titulo-seccion">En turno ({datos.turno.length})</h2>
            {datos.turno.length === 0 && <p className="tarjeta texto-2">No hay expedientes por asignar.</p>}
            {datos.turno.map((e) => {
              const elegibles = datos.carga.filter((c) => c.especialidad === e.materia);
              return (
                <article key={e.id} className="tarjeta">
                  <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                    <strong className="mono">EXP {e.numero}</strong>
                    <span className="texto-2">{t(e.materia)} · origen {t(e.origen)} · {new Date(e.creado_en).toLocaleDateString('es-MX')}</span>
                  </div>
                  <SugerenciaTurno expedienteId={e.id} elegir={(juez) => setEleccion({ ...eleccion, [e.id]: juez })} />
                  <div className="fila" style={{ alignItems: 'flex-end' }}>
                    <div className="campo crece" style={{ minWidth: 220 }}>
                      <label htmlFor={`juez-${e.id}`}>Juez</label>
                      <select id={`juez-${e.id}`} value={eleccion[e.id] ?? ''} onChange={(ev) => setEleccion({ ...eleccion, [e.id]: ev.target.value })}>
                        <option value="">Selecciona…</option>
                        {elegibles.map((c) => <option key={c.juez_id} value={c.juez_id}>{c.nombre} · {c.juzgado} · {c.expedientes_activos} activos</option>)}
                      </select>
                    </div>
                    <button type="button" className="boton toga" disabled={!eleccion[e.id]} onClick={() => asignar(e.id, e.numero)}>Confirmar asignación</button>
                  </div>
                </article>
              );
            })}
          </section>
          <aside className="tarjeta" style={{ flex: '1 1 300px' }} aria-labelledby="h-carga">
            <h2 id="h-carga" className="titulo-seccion">Carga de jueces</h2>
            {datos.carga.map((c) => (
              <div key={c.juez_id} className="columna" style={{ gap: 0 }}>
                <strong>{c.nombre}</strong>
                <span className="pequeno texto-2">{c.juzgado} · {t(c.especialidad)} · {c.expedientes_activos} activos</span>
              </div>
            ))}
          </aside>
        </div>
      )}
    </>
  );
}
