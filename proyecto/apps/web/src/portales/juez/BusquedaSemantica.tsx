// P11 · Búsqueda semántica (RAG) restringida al expediente activo.
import { useState, type FormEvent } from 'react';
import { CajaIA, Cargando } from '@/compartido/componentes';
import { judicial } from '@/compartido/servicios';
import type { Fragmento } from '@/compartido/tipos';

export default function BusquedaSemantica() {
  const [expediente, setExpediente] = useState('458/2027');
  const [pregunta, setPregunta] = useState('');
  const [fuentes, setFuentes] = useState({ expediente: true, legislacion: true, jurisprudencia: false });
  const [fragmentos, setFragmentos] = useState<Fragmento[] | null>(null);
  const [buscando, setBuscando] = useState(false);

  async function consultar(e: FormEvent) {
    e.preventDefault();
    if (!pregunta.trim()) return;
    setBuscando(true);
    setFragmentos(await judicial.buscar(expediente, pregunta));
    setBuscando(false);
  }

  return (
    <>
      <h1 className="titulo-serif" style={{ fontSize: 40 }}>Búsqueda jurídica</h1>

      <form className="tarjeta" onSubmit={consultar}>
        <div className="fila" style={{ alignItems: 'flex-end' }}>
          <div className="campo" style={{ minWidth: 200 }}>
            <label htmlFor="exp">Expediente activo</label>
            <select id="exp" value={expediente} onChange={(e) => setExpediente(e.target.value)}>
              <option value="458/2027">458/2027 · Mercantil</option>
              <option value="452/2027">452/2027 · Civil</option>
            </select>
          </div>
          <div className="campo crece" style={{ minWidth: 260 }}>
            <label htmlFor="q">Pregunta en lenguaje natural</label>
            <input id="q" value={pregunta} onChange={(e) => setPregunta(e.target.value)} placeholder="¿Qué pruebas ofreció el demandado sobre el pago?" />
          </div>
          <button type="submit" className="boton toga" disabled={buscando}>{buscando ? 'Consultando…' : 'Consultar'}</button>
        </div>
        <fieldset style={{ border: 0, padding: 0, margin: 0, display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <legend className="solo-lector">Buscar en</legend>
          <span className="texto-2">Buscar en:</span>
          {([['expediente', 'Documentos del expediente'], ['legislacion', 'Legislación vigente'], ['jurisprudencia', 'Jurisprudencia y tesis']] as const).map(([k, t]) => (
            <label key={k} style={{ display: 'flex', gap: 6, alignItems: 'center', minHeight: 44 }}>
              <input type="checkbox" checked={fuentes[k]} onChange={(e) => setFuentes({ ...fuentes, [k]: e.target.checked })} />{t}
            </label>
          ))}
          <span className="pequeno texto-2">Solo documentos autorizados para este expediente</span>
        </fieldset>
      </form>

      {buscando && <Cargando />}
      {fragmentos && !buscando && (
        <div className="fila">
          <section aria-labelledby="h-sin" style={{ flex: '1 1 400px' }}>
            <CajaIA titulo="Síntesis asistida por IA · verifique en los originales">
              <h2 id="h-sin" className="solo-lector">Síntesis</h2>
              {/* TODO: síntesis real generada solo a partir de los fragmentos autorizados */}
              <p>En su contestación, el demandado afirma haber realizado un pago parcial de $5,000 <a href="#f1">[1]</a>. El recibo anexado no contiene firma de la actora <a href="#f2">[2]</a>. Los documentos privados no reconocidos requieren perfeccionamiento <a href="#f3">[3]</a>.</p>
              <span className="pequeno texto-2">Fuentes: {fragmentos.length} fragmentos · Consulta registrada en bitácora</span>
            </CajaIA>
          </section>
          <section aria-labelledby="h-frag" className="columna" style={{ flex: '1 1 400px' }}>
            <h2 id="h-frag" className="titulo-seccion">Fragmentos originales</h2>
            {fragmentos.map((f, i) => (
              <article key={f.id} id={f.id} className="tarjeta" style={{ padding: 16, gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                  <span className="mono pequeno"><strong>{i + 1}</strong> · {f.documento} · {f.pagina}</span>
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
