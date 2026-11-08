// P4 · Sala de negociación (ruta ODR). Todo lo de esta pantalla es confidencial.
import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AvisoConfidencial, Cargando, Estado, Folio, MensajeError, t, tonoDe } from '@/compartido/componentes';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { odr } from '@/compartido/servicios';
import { intentar, useDatos } from '@/compartido/servicios/useDatos';
import type { EstadoPropuesta } from '@/compartido/tipos';
import { PanelSugerencia, PanelMediador } from './sala/Paneles';

const textos: Record<EstadoPropuesta, string> = { PENDIENTE: '◷ Pendiente', ACEPTADA: '✓ Aceptada', RECHAZADA: '✕ Rechazada' };
const ABIERTA = ['EN_NEGOCIACION', 'CON_MEDIADOR'];

export default function SalaNegociacion() {
  const { id = '' } = useParams();
  const navegar = useNavigate();
  const { datos: m, error: errorCarga, recargar } = useDatos(() => odr.detalle(id), [id]);
  const [tipo, setTipo] = useState<'mensaje' | 'propuesta'>('mensaje');
  const [texto, setTexto] = useState('');
  const [error, setError] = useState('');

  async function responder(pid: string, estado: 'ACEPTADA' | 'RECHAZADA') {
    if (!confirm(`¿Confirmas ${estado === 'ACEPTADA' ? 'aceptar' : 'rechazar'} esta propuesta?`)) return;
    if (await intentar(() => odr.responder(pid, estado), setError)) recargar();
  }

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!texto.trim()) return;
    const ok = await intentar(() => (tipo === 'mensaje' ? odr.mensaje(id, texto) : odr.propuesta(id, texto)), setError);
    if (ok) { setTexto(''); recargar(); }
  }

  async function terminar() {
    if (!confirm('¿Terminar la mediación sin acuerdo? Después podrás decidir si continúas por la vía judicial.')) return;
    if (await intentar(() => odr.terminar(id, 'SIN_ACUERDO'), setError)) navegar('/ciudadano');
  }

  if (!m) return <div className="pagina"><EncabezadoCiudadano titulo="Sala de negociación" volverA="/ciudadano" />
    <div className="contenedor">{errorCarga ? <MensajeError>{errorCarga}</MensajeError> : <Cargando />}</div></div>;

  const abierta = ABIERTA.includes(m.estado);
  const otra = m.partes.map((p) => p.nombre).join(' · ');

  return (
    <div className="pagina">
      <EncabezadoCiudadano titulo="Sala de negociación" etiqueta="RUTA ODR" volverA="/ciudadano" />
      <div className="contenedor">
        <div className="tarjeta" style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px' }}>
          <span style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <Folio ruta="odr">{m.folio}</Folio>
            <Estado tono={tonoDe(m.resultado ?? m.estado)}>{t(m.resultado ?? m.estado)}</Estado>
            <span className="texto-2">{t(m.materia)} · {otra}</span>
          </span>
          {m.invitacion && m.estado === 'INVITACION_ENVIADA' && (
            <span>Invitación vigente hasta <strong>{new Date(m.invitacion.fecha_limite + 'T12:00').toLocaleDateString('es-MX')}</strong></span>
          )}
        </div>

        <AvisoConfidencial>
          <strong>Espacio confidencial.</strong> Mensajes y propuestas no se transfieren al expediente judicial si deciden ir a juicio.
        </AvisoConfidencial>
        <MensajeError>{error}</MensajeError>
        {m.estado === 'INVITACION_ENVIADA' && <p className="aviso-confidencial">Esperamos a que la otra parte acepte la invitación para abrir la conversación.</p>}

        <div className="fila">
          <section className="tarjeta" aria-labelledby="h-conv" style={{ flex: '2 1 520px', minWidth: 0 }}>
            <h2 id="h-conv" className="titulo-serif" style={{ fontSize: 24 }}>Conversación</h2>
            <div className="columna" aria-live="polite">
              {m.mensajes.length === 0 && <p className="texto-2">Aún no hay mensajes.</p>}
              {m.mensajes.map((x) => (
                <div key={x.id} style={{ alignSelf: x.autor === 'yo' ? 'flex-end' : 'flex-start', maxWidth: '75%' }}>
                  <p style={{ padding: '10px 14px', borderRadius: 8, background: x.autor === 'yo' ? 'var(--jade-tinte)' : x.autor === 'mediador' ? 'var(--laton-tinte)' : 'var(--gris-suave)' }}>{x.texto}</p>
                  <span className="pequeno texto-2">{x.autor === 'yo' ? 'Tú' : x.nombre} · {new Date(x.fecha).toLocaleString('es-MX')}</span>
                </div>
              ))}
            </div>
            {abierta && (
              <form onSubmit={enviar} className="columna">
                <div className="pestanas" role="tablist" aria-label="Tipo de envío">
                  <button type="button" role="tab" aria-selected={tipo === 'mensaje'} onClick={() => setTipo('mensaje')}>Mensaje</button>
                  {!m.soy_mediador && <button type="button" role="tab" aria-selected={tipo === 'propuesta'} onClick={() => setTipo('propuesta')}>Propuesta formal</button>}
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <label htmlFor="msg" className="solo-lector">{tipo === 'mensaje' ? 'Escribe tu mensaje' : 'Describe tu propuesta'}</label>
                  <input id="msg" value={texto} maxLength={2000} onChange={(e) => setTexto(e.target.value)}
                    placeholder={tipo === 'mensaje' ? 'Escribe tu mensaje…' : 'Ej. $10,000 al firmar y $5,000 a 60 días'}
                    style={{ flex: 1, minHeight: 48, padding: '0 14px', border: '1.5px solid var(--borde-campo)', borderRadius: 4, minWidth: 0 }} />
                  <button type="submit" className="boton jade">Enviar</button>
                </div>
              </form>
            )}
          </section>

          <aside className="columna" style={{ flex: '1 1 340px', gap: 16 }}>
            <section className="tarjeta" aria-labelledby="h-mesa">
              <h2 id="h-mesa" className="titulo-seccion">Mesa de propuestas</h2>
              {m.propuestas.length === 0 && <p className="texto-2">Sin propuestas todavía.</p>}
              {[...m.propuestas].reverse().map((p) => (
                <div key={p.id} className="columna" style={{ gap: 6, paddingBottom: 12, borderBottom: '1px solid var(--linea)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                    <span><strong>{p.resumen}</strong><br /><span className="pequeno texto-2">#{p.numero} · {p.autor === 'yo' ? 'tuya' : 'de la otra parte'}</span></span>
                    <Estado tono={tonoDe(p.estado)}>{textos[p.estado]}</Estado>
                  </div>
                  {abierta && p.estado === 'PENDIENTE' && p.autor === 'otra_parte' && !m.soy_mediador && (
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <button type="button" className="boton jade" onClick={() => responder(p.id, 'ACEPTADA')}>Aceptar</button>
                      <button type="button" className="boton secundario" onClick={() => { setTipo('propuesta'); setTexto(p.resumen); }}>Contraproponer</button>
                      <button type="button" className="boton peligro" onClick={() => responder(p.id, 'RECHAZADA')}>Rechazar</button>
                    </div>
                  )}
                </div>
              ))}
            </section>

            {abierta && !m.soy_mediador && <PanelSugerencia mediacionId={m.id} usar={(s) => { setTipo('propuesta'); setTexto(s); }} />}

            <section className="tarjeta">
              {m.estado === 'PENDIENTE_FORMALIZACION' && <Link className="boton jade" to={`/ciudadano/convenio/${m.id}`}>Revisar convenio</Link>}
              {abierta && !m.soy_mediador && <PanelMediador mediacion={m} alCambiar={recargar} alError={setError} />}
              {abierta && !m.soy_mediador && <button type="button" className="boton peligro" onClick={terminar}>Terminar sin acuerdo</button>}
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}
