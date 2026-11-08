// P9 / P12 · Bandeja del juez, expediente con línea de tiempo y dictamen preliminar.
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { CajaIA, Cargando, Estado } from '@/compartido/componentes';
import { judicial } from '@/compartido/servicios';
import type { EstadoExpediente, ExpedienteResumen } from '@/compartido/tipos';

const filtros: { id: string; texto: string; estados?: EstadoExpediente[] }[] = [
  { id: 'todos', texto: 'Todos' },
  { id: 'turno', texto: 'En turno', estados: ['EN_TURNO'] },
  { id: 'revisar', texto: 'Por revisar', estados: ['EN_REVISION', 'PREVENIDO'] },
  { id: 'tramite', texto: 'En trámite', estados: ['ADMITIDO', 'EN_TRAMITE'] },
  { id: 'resueltos', texto: 'Resueltos', estados: ['RESUELTO', 'CERRADO', 'DESECHADO'] },
];

const etiquetaEstado: Record<EstadoExpediente, string> = {
  EN_TURNO: '◷ En turno', EN_REVISION: '◷ Por revisar', PREVENIDO: '↺ Prevenido', ADMITIDO: '✓ Admitido',
  EN_TRAMITE: '→ En trámite', RESUELTO: '✓ Resuelto', DESECHADO: '✕ Desechado', CERRADO: '✓ Cerrado',
};

type Dictamen = 'ADMITIR' | 'PREVENIR' | 'DESECHAR';

export default function BandejaJuez() {
  const [expedientes, setExpedientes] = useState<ExpedienteResumen[] | null>(null);
  const [filtro, setFiltro] = useState('revisar');
  const [busqueda, setBusqueda] = useState('');
  const [seleccion, setSeleccion] = useState<ExpedienteResumen | null>(null);
  const [dictamen, setDictamen] = useState<Dictamen>('ADMITIR');
  const [motivo, setMotivo] = useState('');

  useEffect(() => { judicial.bandeja().then(setExpedientes); }, []);

  const visibles = useMemo(() => {
    const f = filtros.find((x) => x.id === filtro);
    const q = busqueda.toLowerCase();
    return (expedientes ?? []).filter((e) =>
      (!f?.estados || f.estados.includes(e.estado)) &&
      (!q || e.numero.includes(q) || e.partes.toLowerCase().includes(q)));
  }, [expedientes, filtro, busqueda]);

  function contar(estados?: EstadoExpediente[]) {
    return (expedientes ?? []).filter((e) => !estados || estados.includes(e.estado)).length;
  }

  function firmar() {
    if (!seleccion) return;
    if (dictamen !== 'ADMITIR' && !motivo.trim()) return alert('Prevenir o desechar requiere fundamentación.');
    if (!confirm(`¿Firmar dictamen "${dictamen.toLowerCase()}" para el expediente ${seleccion.numero}?`)) return;
    // TODO: POST /expedientes/{id}/dictamen  + firma electrónica + notificación a las partes
    const nuevo: EstadoExpediente = dictamen === 'ADMITIR' ? 'ADMITIDO' : dictamen === 'PREVENIR' ? 'PREVENIDO' : 'DESECHADO';
    setExpedientes((es) => es?.map((e) => (e.id === seleccion.id ? { ...e, estado: nuevo } : e)) ?? null);
    setSeleccion(null);
    setMotivo('');
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 16 }}>
        <h1 className="titulo-serif" style={{ fontSize: 40 }}>Bandeja de asuntos</h1>
        <div className="campo" style={{ minWidth: 280 }}>
          <label htmlFor="buscar">Buscar expediente</label>
          <input id="buscar" placeholder="Buscar por número o parte" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
        </div>
      </div>

      <div className="pestanas" role="tablist" aria-label="Filtrar por estado">
        {filtros.map((f) => (
          <button key={f.id} type="button" role="tab" aria-selected={filtro === f.id} onClick={() => setFiltro(f.id)}>
            {f.texto} <span className="mono">{contar(f.estados)}</span>
          </button>
        ))}
      </div>

      {!expedientes ? <Cargando /> : (
        <div className="tabla-scroll">
          <table className="tabla">
            <thead>
              <tr><th scope="col">Expediente</th><th scope="col">Partes</th><th scope="col">Materia</th><th scope="col">Estado</th><th scope="col">Origen</th><th scope="col">Plazo</th></tr>
            </thead>
            <tbody>
              {visibles.map((e) => (
                <tr key={e.id} className={seleccion?.id === e.id ? 'seleccionada' : ''} onClick={() => setSeleccion(e)}>
                  <td><button type="button" className="mono" onClick={() => setSeleccion(e)} style={{ border: 0, background: 'none', color: 'var(--toga)', fontWeight: 600, cursor: 'pointer', padding: 0 }}>{e.numero}</button></td>
                  <td>{e.partes}</td>
                  <td>{e.materia}</td>
                  <td><Estado tono="tramite">{etiquetaEstado[e.estado]}</Estado></td>
                  <td>{e.origen}</td>
                  <td>{e.plazoDias > 0 ? `${e.plazoDias} días` : '—'}</td>
                </tr>
              ))}
              {visibles.length === 0 && <tr><td colSpan={6} className="texto-2">Sin expedientes en este filtro.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {seleccion && (
        <div className="fila">
          <section className="tarjeta" aria-labelledby="h-exp" style={{ flex: '2 1 480px', minWidth: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
              <h2 id="h-exp" className="titulo-serif" style={{ fontSize: 28 }}>Expediente {seleccion.numero}</h2>
              <Link to="/juez/busqueda">Consultar con búsqueda jurídica →</Link>
            </div>
            <CajaIA titulo="Resumen de revisión preliminar">
              {/* TODO: resumen real desde ia-service */}
              <p>Requisitos formales completos. Falta domicilio del demandado en el escrito inicial. Pruebas: 2 anexos documentales.</p>
            </CajaIA>
            {/* TODO: GET /expedientes/{id}/actuaciones */}
            <ol className="lista-tiempo">
              <li><span><strong>{seleccion.origen}</strong><br /><span className="pequeno texto-2">Contenido confidencial de mediación excluido</span></span></li>
              <li><span><strong>Demanda confirmada y presentada</strong><br /><span className="pequeno texto-2">Demanda.pdf · Anexo 1 · Anexo 2</span></span></li>
              <li><span><strong>Asignado a este juzgado</strong><br /><span className="pequeno texto-2">Confirmado por Oficialía</span></span></li>
            </ol>
          </section>

          <section className="tarjeta" aria-labelledby="h-dic" style={{ flex: '1 1 320px' }}>
            <h2 id="h-dic" className="titulo-serif" style={{ fontSize: 24 }}>Dictamen preliminar</h2>
            {([['ADMITIR', 'Admitir', 'Se emplaza al demandado'], ['PREVENIR', 'Prevenir', 'El ciudadano corrige y reenvía'], ['DESECHAR', 'Desechar', 'Requiere fundamentación']] as const).map(([valor, titulo, ayuda]) => (
              <label key={valor} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', minHeight: 44 }}>
                <input type="radio" name="dic" checked={dictamen === valor} onChange={() => setDictamen(valor)} style={{ marginTop: 5 }} />
                <span><strong>{titulo}</strong><br /><span className="pequeno texto-2">{ayuda}</span></span>
              </label>
            ))}
            <div className="campo">
              <label htmlFor="motivo">Nota o fundamento</label>
              <textarea id="motivo" rows={3} value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Opcional al admitir" />
            </div>
            <button type="button" className="boton toga" onClick={firmar}>Firmar y registrar dictamen</button>
            <span className="pequeno texto-2">Se solicitará firma electrónica y se notificará a las partes.</span>
          </section>
        </div>
      )}
    </>
  );
}
