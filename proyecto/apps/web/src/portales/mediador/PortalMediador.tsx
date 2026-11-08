// P4 · Portal del mediador (RF3.4–RF3.8): mediaciones asignadas, conversación, agenda, notas confidenciales,
// convenio y registro de la conclusión.
import { useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AvisoConfidencial, Cargando, Estado, MensajeError, t, tonoDe } from '@/compartido/componentes';
import { EditorConvenio } from '@/compartido/componentes/EditorConvenio';
import { odr } from '@/compartido/servicios';
import { intentar, useDatos } from '@/compartido/servicios/useDatos';
import { textoModalidad } from '@/portales/ciudadano/sala/Paneles';

export default function PortalMediador() {
  const [params, setParams] = useSearchParams();
  const { datos, error } = useDatos(async () => {
    const [lista, agenda] = await Promise.all([odr.mediaciones(), odr.agenda()]);
    return { lista, agenda };
  });
  const seleccion = params.get('m') ?? datos?.lista.find((m) => m.estado !== 'CONCLUIDA')?.id ?? null;
  const activas = datos?.lista.filter((m) => m.estado !== 'CONCLUIDA').length ?? 0;

  return (
    <>
      <div>
        <h1 className="titulo-serif" style={{ fontSize: 40 }}>Mis mediaciones</h1>
        <span className="texto-2">{activas} activas · {datos?.agenda.length ?? 0} sesiones programadas</span>
      </div>
      <MensajeError>{error}</MensajeError>
      {!datos ? <Cargando /> : (
        <div className="fila">
          <section aria-labelledby="h-lista" className="columna" style={{ flex: '1 1 280px', gap: 10 }}>
            <h2 id="h-lista" className="titulo-seccion">Asignadas a mí</h2>
            {datos.lista.length === 0 && <p className="tarjeta texto-2">No tienes mediaciones asignadas.</p>}
            {datos.lista.map((m) => (
              <button key={m.id} type="button" onClick={() => setParams({ m: m.id })} className="tarjeta"
                style={{ textAlign: 'left', cursor: 'pointer', padding: 14, gap: 4, borderColor: seleccion === m.id ? 'var(--jade)' : undefined, borderWidth: seleccion === m.id ? 2 : 1 }}>
                <span style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                  <span className="mono" style={{ color: 'var(--jade)', fontWeight: 600 }}>{m.folio}</span>
                  <Estado tono={tonoDe(m.resultado ?? m.estado)}>{t(m.resultado ?? m.estado)}</Estado>
                </span>
                <strong>{m.partes} · {t(m.materia)}</strong>
                <span className="pequeno texto-2">{m.propuestas} propuestas</span>
              </button>
            ))}
            {datos.agenda.length > 0 && (
              <div className="tarjeta" style={{ padding: 14 }}>
                <h2 className="titulo-seccion">Agenda</h2>
                {datos.agenda.map((s) => (
                  <span key={s.id} className="pequeno"><strong>{new Date(s.inicio).toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' })}</strong> · {s.folio} · {textoModalidad[s.modalidad]}</span>
                ))}
              </div>
            )}
          </section>
          {seleccion && <Detalle key={seleccion} id={seleccion} />}
        </div>
      )}
    </>
  );
}

function Detalle({ id }: { id: string }) {
  const { datos, recargar } = useDatos(async () => {
    const [m, notas, convenio, sesiones] = await Promise.all([odr.detalle(id), odr.notas(id), odr.convenio(id), odr.sesiones(id)]);
    return { m, notas, convenio, sesiones };
  }, [id]);
  const [mensaje, setMensaje] = useState('');
  const [nota, setNota] = useState('');
  const [sesion, setSesion] = useState({ inicio: '', duracion_min: 60, modalidad: 'VIDEOLLAMADA_CONJUNTA', enlace: '' });
  const [resultado, setResultado] = useState<'SIN_ACUERDO' | 'DESISTIMIENTO' | 'NO_ACEPTADA' | ''>('');
  const [error, setError] = useState('');

  if (!datos) return <Cargando />;
  const { m, notas, convenio, sesiones } = datos;
  const abierta = m.estado !== 'CONCLUIDA';

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (await intentar(() => odr.mensaje(id, mensaje), setError)) { setMensaje(''); recargar(); }
  }
  async function programar(e: FormEvent) {
    e.preventDefault();
    const inicio = new Date(sesion.inicio).toISOString();
    if (await intentar(() => odr.programarSesion(id, { ...sesion, inicio, enlace: sesion.enlace || undefined }), setError)) {
      setSesion({ ...sesion, inicio: '', enlace: '' });
      recargar();
    }
  }
  async function guardarNota(e: FormEvent) {
    e.preventDefault();
    if (await intentar(() => odr.agregarNota(id, nota), setError)) { setNota(''); recargar(); }
  }
  async function concluir() {
    if (!resultado || !confirm(`¿Registrar "${t(resultado)}"? La mediación se cerrará y se notificará a las partes.`)) return;
    if (await intentar(() => odr.concluir(id, resultado), setError)) recargar();
  }

  return (
    <section aria-labelledby="h-det" className="columna" style={{ flex: '3 1 560px', minWidth: 0, gap: 16 }}>
      <div className="tarjeta">
        <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
          <h2 id="h-det" className="titulo-serif" style={{ fontSize: 28 }}>{m.partes.map((p) => p.nombre).join(' vs. ')}</h2>
          <Estado tono={tonoDe(m.resultado ?? m.estado)}>{t(m.resultado ?? m.estado)}</Estado>
        </div>
        <span className="texto-2">{m.folio} · {t(m.materia)} · {m.propuestas.length} propuestas ({m.propuestas.filter((p) => p.estado === 'ACEPTADA').length} aceptadas)</span>
        <MensajeError>{error}</MensajeError>
      </div>

      <div className="fila">
        <div className="tarjeta" style={{ flex: '1 1 340px' }}>
          <h3 className="titulo-seccion">Conversación</h3>
          <div className="columna" style={{ maxHeight: 320, overflowY: 'auto' }}>
            {m.mensajes.map((x) => (
              <p key={x.id} className="pequeno" style={{ padding: '8px 10px', borderRadius: 6, background: x.autor === 'yo' ? 'var(--laton-tinte)' : 'var(--gris-suave)' }}>
                <strong>{x.autor === 'yo' ? 'Tú' : x.nombre}:</strong> {x.texto}
              </p>
            ))}
            {m.propuestas.map((p) => <p key={p.id} className="pequeno">Propuesta #{p.numero}: <strong>{p.resumen}</strong> · {t(p.estado)}</p>)}
          </div>
          {['CON_MEDIADOR'].includes(m.estado) && (
            <form onSubmit={enviar} style={{ display: 'flex', gap: 8 }}>
              <label htmlFor="med-msg" className="solo-lector">Mensaje a las partes</label>
              <input id="med-msg" value={mensaje} onChange={(e) => setMensaje(e.target.value)} placeholder="Mensaje a ambas partes…"
                style={{ flex: 1, minWidth: 0, minHeight: 44, padding: '0 12px', border: '1.5px solid var(--borde-campo)', borderRadius: 4 }} />
              <button type="submit" className="boton jade" disabled={!mensaje.trim()}>Enviar</button>
            </form>
          )}
        </div>

        <div className="tarjeta" style={{ flex: '1 1 300px' }}>
          <h3 className="titulo-seccion">Sesiones</h3>
          {sesiones.length === 0 && <p className="pequeno texto-2">Sin sesiones.</p>}
          {sesiones.map((s) => (
            <div key={s.id} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <span className="pequeno"><strong>{new Date(s.inicio).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })}</strong> · {textoModalidad[s.modalidad]} · {t(s.estado)}</span>
              {s.estado === 'PROGRAMADA' && (
                <span style={{ display: 'flex', gap: 6 }}>
                  <button type="button" className="boton secundario" style={{ minHeight: 36, padding: '0 10px', fontSize: 13 }} onClick={() => intentar(() => odr.cambiarSesion(s.id, 'REALIZADA').then(recargar), setError)}>Realizada</button>
                  <button type="button" className="boton peligro" style={{ minHeight: 36, padding: '0 10px', fontSize: 13 }} onClick={() => confirm('¿Cancelar la sesión? Se avisará a las partes.') && intentar(() => odr.cambiarSesion(s.id, 'CANCELADA').then(recargar), setError)}>Cancelar</button>
                </span>
              )}
            </div>
          ))}
          {abierta && (
            <form onSubmit={programar} className="columna" style={{ gap: 8 }}>
              <div className="campo"><label htmlFor="ses-inicio">Programar sesión virtual</label>
                <input id="ses-inicio" type="datetime-local" value={sesion.inicio} onChange={(e) => setSesion({ ...sesion, inicio: e.target.value })} /></div>
              <div className="campo"><label htmlFor="ses-modo">Modalidad</label>
                <select id="ses-modo" value={sesion.modalidad} onChange={(e) => setSesion({ ...sesion, modalidad: e.target.value })}>
                  {Object.entries(textoModalidad).map(([v, n]) => <option key={v} value={v}>{n}</option>)}
                </select></div>
              <div className="campo"><label htmlFor="ses-enlace">Enlace (opcional)</label>
                <input id="ses-enlace" type="url" value={sesion.enlace} onChange={(e) => setSesion({ ...sesion, enlace: e.target.value })} /></div>
              <button type="submit" className="boton jade" disabled={!sesion.inicio}>Enviar invitación a la sesión</button>
            </form>
          )}
        </div>
      </div>

      <div className="tarjeta">
        <h3 className="titulo-seccion">Notas de sesión</h3>
        <AvisoConfidencial>Las notas son confidenciales: solo tú las ves y nunca se transfieren al expediente judicial.</AvisoConfidencial>
        <form onSubmit={guardarNota} className="columna" style={{ gap: 8 }}>
          <label htmlFor="nota" className="solo-lector">Nueva nota</label>
          <textarea id="nota" rows={3} value={nota} onChange={(e) => setNota(e.target.value)} style={{ padding: 10, border: '1.5px solid var(--borde-campo)', borderRadius: 4 }} />
          <button type="submit" className="boton secundario" disabled={!nota.trim()}>Guardar nota</button>
        </form>
        {notas.map((n) => <p key={n.id} className="pequeno"><span className="texto-2">{new Date(n.creado_en).toLocaleString('es-MX')}</span> · {n.texto}</p>)}
      </div>

      {abierta && (
        <div className="tarjeta">
          <h3 className="titulo-seccion">Convenio</h3>
          {convenio && <p className="pequeno">Aprobaciones: {convenio.partes.map((p) => `${p.nombre} ${p.aprobo ? '✓' : '◷'}`).join(' · ')}</p>}
          {!convenio?.formalizado_en && <EditorConvenio mediacionId={id} actual={convenio} alGuardar={recargar}
            sugerencia={m.propuestas.filter((p) => p.estado === 'ACEPTADA').map((p, i) => `Cláusula ${i + 1}. ${p.resumen}.`).join('\n')} />}
        </div>
      )}

      {abierta && (
        <fieldset className="tarjeta" style={{ margin: 0 }}>
          <legend className="titulo-seccion" style={{ padding: '0 4px' }}>Registrar conclusión sin convenio</legend>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {(['SIN_ACUERDO', 'DESISTIMIENTO', 'NO_ACEPTADA'] as const).map((v) => (
              <label key={v} style={{ display: 'flex', alignItems: 'center', gap: 6, minHeight: 44 }}>
                <input type="radio" name="fin" checked={resultado === v} onChange={() => setResultado(v)} />{t(v)}
              </label>
            ))}
          </div>
          <span className="pequeno texto-2">Los acuerdos total o parcial se concluyen al firmar el convenio.</span>
          <button type="button" className="boton" disabled={!resultado} onClick={concluir}>Registrar (pide confirmación)</button>
        </fieldset>
      )}
    </section>
  );
}
