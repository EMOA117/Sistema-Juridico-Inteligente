// P4 · Portal del mediador: mediaciones asignadas, sesión, notas confidenciales y conclusión.
import { useEffect, useState } from 'react';
import { AvisoConfidencial, Cargando, Estado } from '@/compartido/componentes';
import { odr } from '@/compartido/servicios';
import type { Mediacion, ResultadoMediacion } from '@/compartido/tipos';

const resultados: [ResultadoMediacion, string][] = [
  ['ACUERDO_TOTAL', 'Acuerdo total'],
  ['ACUERDO_PARCIAL', 'Acuerdo parcial'],
  ['SIN_ACUERDO', 'Sin acuerdo'],
  ['DESISTIMIENTO', 'Desistimiento'],
];

export default function PortalMediador() {
  const [mediaciones, setMediaciones] = useState<Mediacion[] | null>(null);
  const [seleccion, setSeleccion] = useState<Mediacion | null>(null);
  const [notas, setNotas] = useState('');
  const [resultado, setResultado] = useState<ResultadoMediacion | null>(null);

  useEffect(() => {
    odr.mediaciones().then((m) => { setMediaciones(m); setSeleccion(m[0]); });
  }, []);

  function registrar() {
    if (!resultado || !seleccion) return;
    const texto = resultados.find(([r]) => r === resultado)?.[1];
    if (!confirm(`¿Registrar "${texto}" para ${seleccion.folio}? Esta acción cambia el estado del conflicto.`)) return;
    // TODO: POST /odr/{folio}/conclusion  { resultado }
    alert('Conclusión registrada (simulado).');
  }

  return (
    <>
      <div>
        <h1 className="titulo-serif" style={{ fontSize: 40 }}>Mis mediaciones</h1>
        <span className="texto-2">{mediaciones?.length ?? 0} activas</span>
      </div>

      <div className="fila">
        <section aria-labelledby="h-lista" className="columna" style={{ flex: '1 1 300px' }}>
          <h2 id="h-lista" className="titulo-seccion">Asignadas a mí</h2>
          {!mediaciones && <Cargando />}
          {mediaciones?.map((m) => (
            <button key={m.id} type="button" onClick={() => setSeleccion(m)} className="tarjeta"
              style={{ textAlign: 'left', cursor: 'pointer', padding: 16, gap: 4, borderColor: seleccion?.id === m.id ? 'var(--jade)' : undefined, borderWidth: seleccion?.id === m.id ? 2 : 1 }}>
              <span style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                <span className="mono" style={{ color: 'var(--jade)', fontWeight: 600 }}>{m.folio}</span>
                <Estado tono="pendiente">{m.estadoTexto}</Estado>
              </span>
              <strong>{m.partes} · {m.materia}</strong>
              <span className="pequeno texto-2">{m.detalle}</span>
            </button>
          ))}
        </section>

        {seleccion && (
          <section aria-labelledby="h-det" className="columna" style={{ flex: '2 1 520px', minWidth: 0, gap: 16 }}>
            <div className="tarjeta">
              <h2 id="h-det" className="titulo-serif" style={{ fontSize: 28 }}>{seleccion.partes}</h2>
              <div className="fila" style={{ alignItems: 'flex-end' }}>
                <div className="campo crece" style={{ minWidth: 200 }}>
                  <label htmlFor="fecha">Programar sesión virtual</label>
                  <input id="fecha" type="datetime-local" />
                </div>
                <div className="campo crece" style={{ minWidth: 200 }}>
                  <label htmlFor="modo">Modalidad</label>
                  <select id="modo"><option>Videollamada conjunta</option><option>Sesión privada (caucus)</option></select>
                </div>
                {/* TODO: POST /odr/{folio}/sesiones */}
                <button type="button" className="boton jade" onClick={() => alert('Invitación enviada (simulado).')}>Enviar invitación</button>
              </div>
            </div>

            <div className="tarjeta">
              <div className="campo">
                <label htmlFor="notas">Notas de sesión</label>
                <textarea id="notas" rows={5} value={notas} onChange={(e) => setNotas(e.target.value)} />
              </div>
              <AvisoConfidencial>Las notas nunca se transfieren al expediente judicial.</AvisoConfidencial>

              <fieldset style={{ border: 0, padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                <legend className="titulo-seccion" style={{ marginBottom: 8 }}>Registrar conclusión</legend>
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                  {resultados.map(([valor, texto]) => (
                    <label key={valor} style={{ display: 'flex', alignItems: 'center', gap: 6, minHeight: 44 }}>
                      <input type="radio" name="fin" checked={resultado === valor} onChange={() => setResultado(valor)} />{texto}
                    </label>
                  ))}
                </div>
                <button type="button" className="boton" disabled={!resultado} onClick={registrar}>Registrar (pide confirmación)</button>
              </fieldset>
            </div>
          </section>
        )}
      </div>
    </>
  );
}
