// RF4.3–RF4.4 · Firma del convenio por cada parte y el mediador; al completarse queda formalizado e inmutable.
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Estado, MensajeError } from '@/compartido/componentes';
import { VentanaFirma } from '@/compartido/componentes/VentanaFirma';
import { abrirDocumento, firma } from '@/compartido/servicios';
import { useSesion } from '@/compartido/servicios/sesion';
import { useDatos } from '@/compartido/servicios/useDatos';
import type { Convenio } from '@/compartido/tipos';

export function PanelFirmaConvenio({ mediacionId, convenio: v, alCambiar }: { mediacionId: string; convenio: Convenio; alCambiar: () => void }) {
  const { usuario } = useSesion();
  const { datos: firmas, recargar } = useDatos(() => firma.firmasConvenio(mediacionId), [mediacionId, v.formalizado_en]);
  const [abierta, setAbierta] = useState(false);
  const [error, setError] = useState('');

  if (!v.aprobado_por_todas && !v.formalizado_en) return null;
  const yo = firmas?.find((f) => f.soy_yo);

  return (
    <div className="columna" style={{ gap: 8 }}>
      <span className="titulo-seccion">Firmas electrónicas</span>
      {firmas?.map((f) => (
        <div key={f.nombre} className="columna" style={{ gap: 0 }}>
          <span style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
            <span>{f.nombre}{f.soy_yo && ' (tú)'}</span>
            <Estado tono={f.firmo ? 'aceptada' : 'pendiente'}>{f.firmo ? '✓ Firmó' : '◷ Pendiente'}</Estado>
          </span>
          {f.firmo && <span className="mono pequeno texto-2">Serie {f.num_serie} · {new Date(f.sello_tiempo!).toLocaleString('es-MX')}</span>}
        </div>
      ))}
      <MensajeError>{error}</MensajeError>
      {!v.formalizado_en && yo && !yo.firmo && (
        <button type="button" className="boton jade" onClick={() => setAbierta(true)}>Firmar convenio</button>
      )}
      {v.formalizado_en && v.documento_id && (
        <>
          <button type="button" className="boton secundario" onClick={() => abrirDocumento(v.documento_id!).catch((e) => setError(e.message))}>Abrir convenio PDF firmado</button>
          <span className="mono pequeno texto-2" style={{ wordBreak: 'break-all' }}>SHA-256 {v.hash_sha256}</span>
          <Link to={`/verificar/${v.hash_sha256}`}>Verificar autenticidad</Link>
        </>
      )}
      <VentanaFirma abierta={abierta} titulo="Firmar convenio" pedirMfa={usuario?.rol !== 'CIUDADANO'} alCerrar={() => setAbierta(false)}
        descripcion="Al firmar aceptas el texto del convenio. Cuando firmen todas las personas, quedará formalizado y no podrá modificarse."
        alFirmar={async (c) => { await firma.firmarConvenio(mediacionId, c); setAbierta(false); recargar(); alCambiar(); }} />
    </div>
  );
}
