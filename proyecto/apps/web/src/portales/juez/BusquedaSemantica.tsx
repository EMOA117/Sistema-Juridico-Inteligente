// P11 · Búsqueda semántica (RAG) restringida: solo fuentes públicas de la materia y documentos del expediente activo.
import { useEffect, useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CajaIA, Cargando, MensajeError } from '@/compartido/componentes';
import { ia, judicial, type FragmentoRag } from '@/compartido/servicios';
import { useDatos } from '@/compartido/servicios/useDatos';

export default function BusquedaSemantica() {
  const [params] = useSearchParams();
  const { datos: expedientes } = useDatos(() => judicial.expedientes());
  const [expediente, setExpediente] = useState(params.get('expediente') ?? '');
  const [pregunta, setPregunta] = useState('');
  const [fuentes, setFuentes] = useState({ expediente: true, publico: true });
  const [r, setR] = useState<Awaited<ReturnType<typeof ia.consultar>> | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { if (!expediente && expedientes?.length) setExpediente(expedientes[0].id); }, [expedientes, expediente]);

  async function consultar(e: FormEvent) {
    e.preventDefault();
    setBuscando(true);
    setError('');
    try { setR(await ia.consultar(expediente, pregunta, fuentes.expediente, fuentes.publico)); }
    catch (err) { setError(err instanceof Error ? err.message : 'No se pudo consultar'); }
    setBuscando(false);
  }

  return (
    <>
      <h1 className="titulo-serif" style={{ fontSize: 40 }}>Búsqueda jurídica</h1>
      <form className="tarjeta" onSubmit={consultar}>
        <div className="fila" style={{ alignItems: 'flex-end' }}>
          <div className="campo" style={{ minWidth: 220 }}>
            <label htmlFor="exp">Expediente activo</label>
            <select id="exp" value={expediente} onChange={(e) => setExpediente(e.target.value)}>
              {expedientes?.map((x) => <option key={x.id} value={x.id}>{x.numero} · {x.partes}</option>)}
            </select>
          </div>
          <div className="campo crece" style={{ minWidth: 260 }}>
            <label htmlFor="q">Pregunta en lenguaje natural</label>
            <input id="q" value={pregunta} maxLength={500} onChange={(e) => setPregunta(e.target.value)} placeholder="¿Qué pruebas ofreció el demandado sobre la reparación?" />
          </div>
          <button type="submit" className="boton toga" disabled={buscando || !expediente || pregunta.length < 5}>{buscando ? 'Consultando…' : 'Consultar'}</button>
        </div>
        <fieldset style={{ border: 0, padding: 0, margin: 0, display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <legend className="solo-lector">Buscar en</legend>
          <span className="texto-2">Buscar en:</span>
          <label style={{ display: 'flex', gap: 6, alignItems: 'center', minHeight: 44 }}><input type="checkbox" checked={fuentes.expediente} onChange={(e) => setFuentes({ ...fuentes, expediente: e.target.checked })} />Documentos del expediente</label>
          <label style={{ display: 'flex', gap: 6, alignItems: 'center', minHeight: 44 }}><input type="checkbox" checked={fuentes.publico} onChange={(e) => setFuentes({ ...fuentes, publico: e.target.checked })} />Fuentes públicas (sintéticas)</label>
          <span className="pequeno texto-2">Solo documentos autorizados para este expediente · la consulta queda en bitácora</span>
        </fieldset>
      </form>
      <MensajeError>{error}</MensajeError>
      {buscando && <Cargando />}
      {r && !buscando && (
        <div className="fila">
          <section aria-labelledby="h-sin" style={{ flex: '1 1 400px' }}>
            <CajaIA titulo={`Síntesis asistida por IA · verifique en los originales${r.latencia_ms ? ` · ${(r.latencia_ms / 1000).toFixed(1)} s` : ''}`}>
              <h2 id="h-sin" className="solo-lector">Síntesis</h2>
              {!r.disponible ? <p>El asistente no está disponible. Intente más tarde.</p>
                : r.sintesis ? <p><Citas texto={r.sintesis} /></p> : <p>{r.motivo ?? 'Sin evidencia suficiente: no se genera conclusión.'}</p>}
              <span className="pequeno texto-2">Apoyo al análisis (RF8.6): no es una resolución.</span>
            </CajaIA>
          </section>
          <section aria-labelledby="h-frag" className="columna" style={{ flex: '1 1 400px' }}>
            <h2 id="h-frag" className="titulo-seccion">Fragmentos originales</h2>
            {r.fragmentos.length === 0 && <p className="texto-2">Sin fragmentos.</p>}
            {r.fragmentos.map((f: FragmentoRag) => (
              <article key={f.id} id={`f${f.n}`} className="tarjeta" style={{ padding: 16, gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                  <span className="mono pequeno"><strong>{f.n}</strong> · {f.documento} · pág. {f.pagina ?? 's/n'} · {f.acceso === 'EXPEDIENTE' ? 'expediente' : 'fuente pública'}</span>
                  <span className="mono pequeno texto-2">similitud {f.puntaje.toFixed(2)}</span>
                </div>
                <p className="titulo-serif">“{f.texto}”</p>
              </article>
            ))}
          </section>
        </div>
      )}
    </>
  );
}

function Citas({ texto }: { texto: string }) {
  const partes = texto.split(/(\[\d+\])/g);
  return <>{partes.map((p, i) => /^\[\d+\]$/.test(p) ? <a key={i} href={`#f${p.slice(1, -1)}`}>{p}</a> : <span key={i}>{p}</span>)}</>;
}
