// P7 · Demanda asistida (ruta judicial). Solo recibe partes, hechos, materia y, si aplica, puntos pendientes.
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CajaIA, Cargando, Folio, MensajeError, t } from '@/compartido/componentes';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { conflictos, judicial } from '@/compartido/servicios';
import { intentar, useDatos } from '@/compartido/servicios/useDatos';

const tiposJuicio = { CIVIL: ['Juicio oral civil', 'Juicio ordinario civil'], FAMILIAR: ['Controversia del orden familiar', 'Juicio oral familiar'] };

export default function DemandaAsistida() {
  const { conflictoId = '' } = useParams();
  const navegar = useNavigate();
  const { datos: d, error: errorCarga, recargar } = useDatos(async () => {
    const c = await conflictos.detalle(conflictoId);
    if (c.estado === 'EN_ESPERA_DECISION' || c.estado === 'ORIENTADO') await conflictos.canalizar(conflictoId);  // idempotente
    return judicial.demandaDeConflicto(conflictoId);
  }, [conflictoId]);
  const [pretension, setPretension] = useState('');
  const [tipo, setTipo] = useState('');
  const [domicilio, setDomicilio] = useState('');
  const [texto, setTexto] = useState('');
  const [sello, setSello] = useState('');
  const [revisado, setRevisado] = useState(false);
  const [generando, setGenerando] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!d) return;
    setTexto(d.texto_final ?? '');
    setDomicilio(d.partes.demandado.domicilio_notificaciones ?? '');
    setTipo(tiposJuicio[d.materia][0]);
  }, [d]);

  if (!d) return <div className="pagina"><EncabezadoCiudadano titulo="Demanda asistida" volverA="/ciudadano" />
    <div className="contenedor">{errorCarga ? <MensajeError>{errorCarga}</MensajeError> : <Cargando />}</div></div>;

  const presentada = d.estado === 'CONFIRMADA';

  async function guardarDomicilio() {
    if (!d || domicilio === (d.partes.demandado.domicilio_notificaciones ?? '')) return;
    await intentar(() => conflictos.actualizarParte(d.partes.demandado.id, { domicilio }), setError);
  }

  async function generar() {
    if (!d) return;
    setGenerando(true);
    await guardarDomicilio();
    await intentar(async () => {
      const r = await judicial.borrador(d.id, pretension, tipo);
      setTexto(r.texto);
      setSello(r.origen === 'IA' ? `Borrador generado por IA · ${r.modelo} · ${Math.round((r.latencia_ms ?? 0) / 100) / 10} s` : 'Borrador desde plantilla procesal · editable');
      setRevisado(false);
    }, setError);
    setGenerando(false);
  }

  async function presentar() {
    if (!d || !confirm('¿Confirmas presentar la demanda? Esta acción no se puede deshacer.')) return;
    await guardarDomicilio();
    await intentar(async () => {
      const r = await judicial.confirmar(d.id, texto);
      alert(`Demanda presentada. Expediente ${r.numero}.`);
      navegar('/ciudadano');
    }, setError);
  }

  return (
    <div className="pagina">
      <EncabezadoCiudadano titulo="Demanda asistida" etiqueta="RUTA JUDICIAL" volverA="/ciudadano" />
      <div className="contenedor">
        <div className="tarjeta" style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px' }}>
          <span style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <Folio ruta="odr">{d.folio}</Folio> →
            <Folio ruta="judicial">{d.expediente ? `EXP ${d.expediente.numero}` : 'Demanda en borrador'}</Folio>
            <span className="texto-2">Origen: <strong>{t(d.origen)}</strong></span>
          </span>
          <span className="pequeno texto-2" style={{ maxWidth: 460 }}>
            Solo se transfirieron partes, hechos y materia{d.puntos_pendientes.length ? ' y los puntos pendientes del convenio parcial' : ''}. Los mensajes y propuestas de la mediación no pasan al juzgado.
          </span>
        </div>
        <MensajeError>{error}</MensajeError>

        <div className="fila">
          <section className="tarjeta" aria-labelledby="h-datos" style={{ flex: '1 1 400px', minWidth: 0 }}>
            <h2 id="h-datos" className="titulo-serif" style={{ fontSize: 24 }}>Datos del caso</h2>
            <div className="fila">
              <div className="tarjeta suave crece" style={{ padding: 14, gap: 2, minWidth: 160 }}>
                <span className="pequeno texto-2">Demandante</span><strong>{d.partes.demandante.nombre}</strong>
              </div>
              <div className="tarjeta suave crece" style={{ padding: 14, gap: 2, minWidth: 160 }}>
                <span className="pequeno texto-2">Demandado</span><strong>{d.partes.demandado.nombre}</strong>
              </div>
            </div>
            <div className="campo">
              <label htmlFor="dom">Domicilio del demandado <span style={{ color: 'var(--bermellon)' }}>*</span></label>
              <input id="dom" value={domicilio} disabled={presentada} onChange={(e) => setDomicilio(e.target.value)} onBlur={guardarDomicilio} />
              {!domicilio && !d.partes.demandado.correo && <span className="error">Falta un dato de contacto del demandado</span>}
            </div>
            <div className="campo">
              <span className="rotulo">Hechos <span className="pequeno texto-2">· desde tu orientación</span></span>
              <p className="aviso-confidencial">{d.narrativa_inicial}</p>
            </div>
            {d.puntos_pendientes.length > 0 && (
              <div className="campo">
                <span className="rotulo">Puntos pendientes del convenio parcial</span>
                <ul>{d.puntos_pendientes.map((x) => <li key={x}>{x}</li>)}</ul>
              </div>
            )}
            {!presentada && (
              <>
                <div className="campo">
                  <label htmlFor="pre">Lo que pides al juez <span style={{ color: 'var(--bermellon)' }}>*</span></label>
                  <input id="pre" value={pretension} maxLength={500} onChange={(e) => setPretension(e.target.value)} placeholder="Ej. Pago de $15,000 más intereses legales" />
                </div>
                <div className="campo">
                  <label htmlFor="tipo">Tipo de juicio</label>
                  <select id="tipo" value={tipo} onChange={(e) => setTipo(e.target.value)}>
                    {tiposJuicio[d.materia].map((x) => <option key={x}>{x}</option>)}
                  </select>
                </div>
                <button type="button" className="boton secundario" disabled={pretension.length < 5 || generando} onClick={generar}>
                  {generando ? 'Generando borrador…' : texto ? 'Regenerar borrador' : 'Generar borrador'}
                </button>
              </>
            )}
          </section>

          <section aria-labelledby="h-doc" className="columna" style={{ flex: '2 1 560px', minWidth: 0 }}>
            <CajaIA titulo={sello || (presentada ? 'Demanda presentada' : 'Borrador · editable')}>
              <label htmlFor="borrador" id="h-doc" className="solo-lector">Texto de la demanda</label>
              <textarea id="borrador" value={texto} readOnly={presentada} onChange={(e) => { setTexto(e.target.value); setRevisado(false); }} rows={22}
                placeholder="Indica lo que pides al juez y genera el borrador."
                style={{ width: '100%', padding: '32px 40px', border: '1px solid var(--linea)', borderRadius: 4, background: '#fff', fontFamily: 'var(--fuente-titulo)', fontSize: 17, lineHeight: 1.7 }} />
            </CajaIA>
          </section>
        </div>
      </div>

      {!presentada && (
        <footer style={{ position: 'sticky', bottom: 0, background: '#fff', borderTop: '1px solid var(--linea)', padding: '16px 32px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 12, minHeight: 44 }}>
            <input type="checkbox" checked={revisado} onChange={(e) => setRevisado(e.target.checked)} style={{ width: 22, height: 22 }} />
            <span>Revisé y edité el contenido. Entiendo que <strong>la demanda no se presenta sin mi confirmación</strong>.</span>
          </label>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button type="button" className="boton secundario" disabled={!texto} onClick={() => intentar(() => judicial.guardar(d.id, texto).then(recargar), setError)}>Guardar borrador</button>
            <button type="button" className="boton toga" disabled={!revisado || texto.length < 100 || (!domicilio && !d.partes.demandado.correo)} onClick={presentar}>
              Confirmar y presentar demanda
            </button>
          </div>
        </footer>
      )}
    </div>
  );
}
