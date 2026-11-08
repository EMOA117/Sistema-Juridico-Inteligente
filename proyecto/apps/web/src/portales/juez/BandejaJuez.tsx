// P9 / P12 · Bandeja del juez, expediente con línea de tiempo y dictamen preliminar.
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Cargando, Estado, MensajeError, t, tonoDe } from '@/compartido/componentes';
import { judicial } from '@/compartido/servicios';
import { intentar, useDatos } from '@/compartido/servicios/useDatos';
import type { EstadoExpediente } from '@/compartido/tipos';
import { ListaExpediente } from './ListaExpediente';
import { PanelResolucion } from './PanelResolucion';

const filtros: { id: string; texto: string; estados?: EstadoExpediente[] }[] = [
  { id: 'todos', texto: 'Todos' },
  { id: 'revisar', texto: 'Por revisar', estados: ['EN_REVISION', 'PREVENIDO'] },
  { id: 'tramite', texto: 'En trámite', estados: ['ADMITIDO', 'EN_TRAMITE'] },
  { id: 'resueltos', texto: 'Resueltos', estados: ['RESUELTO', 'CERRADO', 'DESECHADO'] },
];

export default function BandejaJuez() {
  const { datos: expedientes, error: errorCarga, recargar: recargarLista } = useDatos(() => judicial.expedientes());
  const [filtro, setFiltro] = useState('revisar');
  const [busqueda, setBusqueda] = useState('');
  const [seleccion, setSeleccion] = useState<string | null>(null);

  const visibles = useMemo(() => {
    const f = filtros.find((x) => x.id === filtro);
    const q = busqueda.toLowerCase();
    return (expedientes ?? []).filter((e) => (!f?.estados || f.estados.includes(e.estado)) &&
      (!q || e.numero.includes(q) || e.partes.toLowerCase().includes(q)));
  }, [expedientes, filtro, busqueda]);

  const contar = (estados?: EstadoExpediente[]) => (expedientes ?? []).filter((e) => !estados || estados.includes(e.estado)).length;

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
      <MensajeError>{errorCarga}</MensajeError>

      {!expedientes ? <Cargando /> : (
        <div className="tabla-scroll">
          <table className="tabla">
            <thead>
              <tr><th scope="col">Expediente</th><th scope="col">Partes</th><th scope="col">Materia</th><th scope="col">Estado</th><th scope="col">Origen</th><th scope="col">Ingreso</th></tr>
            </thead>
            <tbody>
              {visibles.map((e) => (
                <tr key={e.id} className={seleccion === e.id ? 'seleccionada' : ''} onClick={() => setSeleccion(e.id)}>
                  <td><button type="button" className="mono" onClick={() => setSeleccion(e.id)} style={{ border: 0, background: 'none', color: 'var(--toga)', fontWeight: 600, cursor: 'pointer', padding: 0 }}>{e.numero}</button></td>
                  <td>{e.partes}</td>
                  <td>{t(e.materia)}</td>
                  <td><Estado tono={tonoDe(e.estado)}>{t(e.estado)}</Estado></td>
                  <td>{t(e.origen)}</td>
                  <td>{new Date(e.creado_en).toLocaleDateString('es-MX')}</td>
                </tr>
              ))}
              {visibles.length === 0 && <tr><td colSpan={6} className="texto-2">Sin expedientes en este filtro.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {seleccion && <DetalleExpediente key={seleccion} id={seleccion} alCambiar={recargarLista} />}
    </>
  );
}

function DetalleExpediente({ id, alCambiar }: { id: string; alCambiar: () => void }) {
  const { datos: e, recargar } = useDatos(() => judicial.expediente(id), [id]);
  const [dictamen, setDictamen] = useState<'ADMITIR' | 'PREVENIR'>('ADMITIR');
  const [motivo, setMotivo] = useState('');
  const [error, setError] = useState('');

  if (!e) return <Cargando />;

  async function registrar() {
    if (dictamen === 'PREVENIR' && !motivo.trim()) return setError('La prevención requiere indicar qué debe corregirse.');
    if (!confirm(`¿Registrar el dictamen "${dictamen.toLowerCase()}" para el expediente ${e!.numero}? Se notificará a las partes.`)) return;
    if (await intentar(() => judicial.dictamen(id, dictamen, motivo || undefined), setError)) {
      setMotivo('');
      recargar();
      alCambiar();
    }
  }

  return (
    <>
      <div className="fila">
        <section className="tarjeta" aria-labelledby="h-exp" style={{ flex: '2 1 480px', minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
            <h2 id="h-exp" className="titulo-serif" style={{ fontSize: 28 }}>Expediente {e.numero}</h2>
            <Link to={`/juez/busqueda?expediente=${e.id}`}>Consultar con búsqueda jurídica →</Link>
          </div>
          <span className="texto-2">{e.partes} · {t(e.materia)} · origen {t(e.origen)}</span>
          {e.puntos_pendientes && e.puntos_pendientes.length > 0 && (
            <div className="aviso-confidencial"><span><strong>Puntos pendientes de convenio parcial:</strong> {e.puntos_pendientes.join('; ')}</span></div>
          )}
          <details>
            <summary style={{ cursor: 'pointer', fontWeight: 700 }}>Texto de la demanda</summary>
            <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--fuente-titulo)', fontSize: 16 }}>{e.texto_final}</pre>
          </details>
        </section>

        {e.soy_juez && e.estado === 'EN_REVISION' && (
          <section className="tarjeta" aria-labelledby="h-dic" style={{ flex: '1 1 320px' }}>
            <h2 id="h-dic" className="titulo-serif" style={{ fontSize: 24 }}>Dictamen preliminar</h2>
            <MensajeError>{error}</MensajeError>
            {([['ADMITIR', 'Admitir', 'Se emplaza al demandado'], ['PREVENIR', 'Prevenir', 'El ciudadano corrige y reenvía']] as const).map(([valor, titulo, ayuda]) => (
              <label key={valor} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', minHeight: 44 }}>
                <input type="radio" name="dic" checked={dictamen === valor} onChange={() => setDictamen(valor)} style={{ marginTop: 5 }} />
                <span><strong>{titulo}</strong><br /><span className="pequeno texto-2">{ayuda}</span></span>
              </label>
            ))}
            <div className="campo">
              <label htmlFor="motivo">Nota o fundamento</label>
              <textarea id="motivo" rows={3} value={motivo} onChange={(ev) => setMotivo(ev.target.value)} placeholder="Opcional al admitir" />
            </div>
            <button type="button" className="boton toga" onClick={registrar}>Registrar dictamen</button>
          </section>
        )}
        {e.soy_juez && <PanelResolucion expediente={e} alCambiar={() => { recargar(); alCambiar(); }} />}
      </div>
      <ListaExpediente expediente={e} />
    </>
  );
}
