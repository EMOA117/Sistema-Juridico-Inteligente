// RF3.4 · Padrón de mediadores certificados y reasignación. Solo metadatos: sin acceso a la negociación.
import { useState } from 'react';
import { Cargando, Estado, MensajeError, t } from '@/compartido/componentes';
import { administracion } from '@/compartido/servicios';
import { intentar, useDatos } from '@/compartido/servicios/useDatos';
import type { Materia, MediadorPadron } from '@/compartido/tipos';

type Ficha = { num_certificacion: string; especialidades: Materia[]; max_casos: number; activo: boolean };

export default function Mediadores() {
  const { datos, error: errorCarga, recargar } = useDatos(() => administracion.padronMediadores());
  const [edicion, setEdicion] = useState<Record<string, Ficha>>({});
  const [reasig, setReasig] = useState<Record<string, string>>({});
  const [error, setError] = useState('');

  const ficha = (id: string, m?: MediadorPadron): Ficha => edicion[id] ?? (m
    ? { num_certificacion: m.num_certificacion, especialidades: m.especialidades, max_casos: m.max_casos, activo: m.activo }
    : { num_certificacion: '', especialidades: ['CIVIL'], max_casos: 10, activo: true });
  const cambiar = (id: string, base: Ficha, campo: Partial<Ficha>) => setEdicion({ ...edicion, [id]: { ...base, ...campo } });

  async function guardar(id: string, f: Ficha) {
    if (await intentar(() => administracion.registrarMediador(id, f), setError)) {
      const { [id]: _, ...resto } = edicion;
      setEdicion(resto);
      recargar();
    }
  }
  async function reasignar(mediacionId: string, folio: string) {
    if (!reasig[mediacionId] || !confirm(`¿Reasignar la mediación ${folio}? Se notificará al mediador y a las partes.`)) return;
    if (await intentar(() => administracion.reasignar(mediacionId, reasig[mediacionId]), setError)) recargar();
  }

  if (!datos) return errorCarga ? <MensajeError>{errorCarga}</MensajeError> : <Cargando />;
  const filas = [...datos.mediadores.map((m) => ({ id: m.usuario_id, nombre: m.nombre, m })),
    ...datos.sin_registro.map((u) => ({ id: u.id, nombre: u.nombre, m: undefined }))];

  return (
    <>
      <div>
        <h1 className="titulo-serif" style={{ fontSize: 40 }}>Mediadores certificados</h1>
        <span className="texto-2">Padrón, especialidad y carga. La asignación automática elige al mediador activo con menor carga en la materia.</span>
      </div>
      <MensajeError>{error}</MensajeError>
      <div className="tabla-scroll">
        <table className="tabla">
          <thead><tr><th scope="col">Mediador</th><th scope="col">Certificación</th><th scope="col">Especialidades</th><th scope="col">Carga</th><th scope="col">Activo</th><th scope="col"><span className="solo-lector">Guardar</span></th></tr></thead>
          <tbody>
            {filas.map(({ id, nombre, m }) => {
              const f = ficha(id, m);
              return (
                <tr key={id} style={{ cursor: 'default' }}>
                  <td>{nombre}{!m && <><br /><Estado tono="pendiente">Sin registrar</Estado></>}</td>
                  <td><label className="solo-lector" htmlFor={`cert-${id}`}>Certificación</label>
                    <input id={`cert-${id}`} className="mono" value={f.num_certificacion} onChange={(e) => cambiar(id, f, { num_certificacion: e.target.value })}
                      style={{ minHeight: 40, width: 130, padding: '0 8px', border: '1.5px solid var(--borde-campo)', borderRadius: 4 }} /></td>
                  <td>{(['CIVIL', 'FAMILIAR'] as const).map((e) => (
                    <label key={e} style={{ marginRight: 10, display: 'inline-flex', gap: 4, alignItems: 'center' }}>
                      <input type="checkbox" checked={f.especialidades.includes(e)}
                        onChange={(ev) => cambiar(id, f, { especialidades: ev.target.checked ? [...f.especialidades, e] : f.especialidades.filter((x) => x !== e) })} />{t(e)}
                    </label>))}</td>
                  <td className="mono">{m ? `${m.mediaciones_activas}/` : ''}
                    <label className="solo-lector" htmlFor={`max-${id}`}>Máximo de casos</label>
                    <input id={`max-${id}`} type="number" min={1} max={50} value={f.max_casos} onChange={(e) => cambiar(id, f, { max_casos: Number(e.target.value) })}
                      style={{ width: 60, minHeight: 40, border: '1.5px solid var(--borde-campo)', borderRadius: 4, padding: '0 6px' }} /></td>
                  <td><label className="solo-lector" htmlFor={`act-${id}`}>Activo</label>
                    <input id={`act-${id}`} type="checkbox" checked={f.activo} onChange={(e) => cambiar(id, f, { activo: e.target.checked })} /></td>
                  <td><button type="button" className="boton secundario" style={{ minHeight: 40 }} disabled={!edicion[id] || f.num_certificacion.length < 3 || f.especialidades.length === 0}
                    onClick={() => guardar(id, f)}>Guardar</button></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <section className="tarjeta" aria-labelledby="h-asig">
        <h2 id="h-asig" className="titulo-seccion">Mediaciones en curso</h2>
        {datos.asignaciones.length === 0 && <p className="texto-2">Sin mediaciones en curso.</p>}
        {datos.asignaciones.map((a) => {
          const elegibles = datos.mediadores.filter((m) => m.activo && m.especialidades.includes(a.materia));
          return (
            <div key={a.mediacion_id} className="fila" style={{ alignItems: 'center', borderBottom: '1px solid var(--linea)', paddingBottom: 10 }}>
              <span className="crece" style={{ minWidth: 220 }}><strong className="mono">{a.folio}</strong> · {t(a.materia)} · {t(a.estado)}<br />
                <span className="pequeno texto-2">{a.mediador ? `Mediador: ${a.mediador}` : 'Sin mediador'}</span></span>
              <label className="solo-lector" htmlFor={`re-${a.mediacion_id}`}>Nuevo mediador</label>
              <select id={`re-${a.mediacion_id}`} value={reasig[a.mediacion_id] ?? ''} onChange={(e) => setReasig({ ...reasig, [a.mediacion_id]: e.target.value })}
                style={{ minHeight: 44, border: '1.5px solid var(--borde-campo)', borderRadius: 4 }}>
                <option value="">Asignar a…</option>
                {elegibles.map((m) => <option key={m.usuario_id} value={m.usuario_id}>{m.nombre} ({m.mediaciones_activas}/{m.max_casos})</option>)}
              </select>
              <button type="button" className="boton secundario" disabled={!reasig[a.mediacion_id] || a.estado === 'INVITACION_ENVIADA'} onClick={() => reasignar(a.mediacion_id, a.folio)}>Asignar</button>
            </div>
          );
        })}
      </section>
    </>
  );
}
