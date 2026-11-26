// P10–P12 · Emplazamiento, paso a trámite, resolución firmada (RF9.1–RF9.5) y firmeza con cierre (RF6.5).
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { MensajeError } from '@/compartido/componentes';
import { VentanaFirma } from '@/compartido/componentes/VentanaFirma';
import { abrirDocumento, firma } from '@/compartido/servicios';
import { intentar } from '@/compartido/servicios/useDatos';
import type { Expediente } from '@/compartido/tipos';

const hoy = () => new Date().toISOString().slice(0, 10);

export function PanelResolucion({ expediente: e, alCambiar }: { expediente: Expediente; alCambiar: () => void }) {
  return <Panel key={e.estado} expediente={e} alCambiar={alCambiar} />;  // reinicia fechas y campos en cada etapa
}

function Panel({ expediente: e, alCambiar }: { expediente: Expediente; alCambiar: () => void }) {
  const [fecha, setFecha] = useState(hoy());
  const [tipo, setTipo] = useState<'DESECHAMIENTO' | 'SENTENCIA'>(e.estado === 'EN_TRAMITE' ? 'SENTENCIA' : 'DESECHAMIENTO');
  const [resultado, setResultado] = useState('');
  const [texto, setTexto] = useState('');
  const [firmando, setFirmando] = useState(false);
  const [error, setError] = useState('');
  const plazoVencido = e.fecha_limite_contestacion && new Date(e.fecha_limite_contestacion) < new Date(hoy());

  const tarjeta = (titulo: string, contenido: React.ReactNode) => (
    <section className="tarjeta" style={{ flex: '1 1 320px' }} aria-label={titulo}>
      <h2 className="titulo-serif" style={{ fontSize: 24 }}>{titulo}</h2>
      <MensajeError>{error}</MensajeError>
      {contenido}
    </section>
  );

  if (e.resolucion) {
    return tarjeta('Resolución firmada', (
      <>
        <p><strong>{e.resolucion.resultado}</strong></p>
        <span className="mono pequeno texto-2">Serie {e.resolucion.num_serie_firma} · sello {new Date(e.resolucion.sello_tiempo).toLocaleString('es-MX')}</span>
        <span className="mono pequeno texto-2" style={{ wordBreak: 'break-all' }}>SHA-256 {e.resolucion.hash_sha256}</span>
        <button type="button" className="boton secundario" onClick={() => abrirDocumento(e.resolucion!.documento_id).catch((x) => setError(x.message))}>Abrir resolución PDF</button>
        <Link to={`/verificar/${e.resolucion.hash_sha256}`}>Verificar autenticidad</Link>
        {e.estado !== 'CERRADO' ? (
          <div className="fila" style={{ alignItems: 'flex-end' }}>
            <div className="campo"><label htmlFor="firmeza">Fecha en que quedó firme</label>
              <input id="firmeza" type="date" min={e.resolucion.firmada_en.slice(0, 10)} max={hoy()} value={fecha} onChange={(ev) => setFecha(ev.target.value)} /></div>
            <button type="button" className="boton toga" onClick={() => confirm('¿Registrar la firmeza y cerrar el expediente? El cierre es definitivo.')
              && intentar(() => firma.firmeza(e.id, fecha).then(alCambiar), setError)}>Registrar firmeza y cerrar</button>
          </div>
        ) : <p className="estado aceptada" style={{ alignSelf: 'flex-start' }}>Expediente cerrado · firme desde {e.resolucion.fecha_firmeza}</p>}
      </>
    ));
  }

  if (e.estado === 'ADMITIDO') {
    return tarjeta('Emplazamiento y contestación', e.fecha_emplazamiento_validado ? (
      <>
        <p>Emplazamiento validado el <strong>{e.fecha_emplazamiento_validado}</strong>. Plazo para contestar hasta <strong>{e.fecha_limite_contestacion}</strong> (15 días naturales).</p>
        <button type="button" className="boton toga" disabled={!plazoVencido} onClick={() => intentar(() => firma.tramite(e.id).then(alCambiar), setError)}>
          Continuar a trámite
        </button>
        {!plazoVencido && <span className="pequeno texto-2">Disponible al vencer el plazo o al registrarse la contestación.</span>}
      </>
    ) : (
      <div className="fila" style={{ alignItems: 'flex-end' }}>
        <div className="campo"><label htmlFor="empl">Fecha del emplazamiento válido</label>
          <input id="empl" type="date" max={hoy()} value={fecha} onChange={(ev) => setFecha(ev.target.value)} /></div>
        <button type="button" className="boton toga" onClick={() => intentar(() => firma.emplazar(e.id, fecha).then(alCambiar), setError)}>Registrar emplazamiento</button>
      </div>
    ));
  }

  if (!['EN_REVISION', 'PREVENIDO', 'EN_TRAMITE'].includes(e.estado)) return null;
  return tarjeta(e.estado === 'EN_TRAMITE' ? 'Resolución' : 'Desechar la demanda', (
    <>
      {e.estado === 'EN_TRAMITE' && (
        <div className="campo"><label htmlFor="r-tipo">Tipo</label>
          <select id="r-tipo" value={tipo} onChange={(ev) => setTipo(ev.target.value as typeof tipo)}><option value="SENTENCIA">Sentencia</option></select></div>
      )}
      <div className="campo"><label htmlFor="r-res">Sentido de la resolución</label>
        <input id="r-res" value={resultado} maxLength={300} onChange={(ev) => setResultado(ev.target.value)}
          placeholder={e.estado === 'EN_TRAMITE' ? 'Ej. Se condena al pago de la cantidad reclamada' : 'Ej. Se desecha por improcedente'} /></div>
      <div className="campo"><label htmlFor="r-texto">Considerandos y puntos resolutivos</label>
        <textarea id="r-texto" rows={6} value={texto} onChange={(ev) => setTexto(ev.target.value)} /></div>
      <button type="button" className="boton toga" disabled={resultado.length < 5 || texto.length < 50} onClick={() => setFirmando(true)}>Firmar y emitir resolución</button>
      <VentanaFirma abierta={firmando} titulo="Firmar resolución" pedirMfa alCerrar={() => setFirmando(false)}
        descripcion="La resolución se firmará con tu certificado, recibirá sello de tiempo y se guardará de forma inmutable. Se notificará a las partes."
        alFirmar={async (c) => { await firma.resolucion(e.id, { tipo: e.estado === 'EN_TRAMITE' ? 'SENTENCIA' : 'DESECHAMIENTO', resultado, texto, ...c }); setFirmando(false); alCambiar(); }} />
    </>
  ));
}
