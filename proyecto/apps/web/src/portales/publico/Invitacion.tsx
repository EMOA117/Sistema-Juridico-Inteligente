// RF3.7 · Página pública del enlace de invitación. Muestra datos mínimos; para responder hay que iniciar sesión.
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AvisoConfidencial, Cargando, Folio, MensajeError, t } from '@/compartido/componentes';
import { invitaciones } from '@/compartido/servicios';
import { useSesion } from '@/compartido/servicios/sesion';
import { useDatos } from '@/compartido/servicios/useDatos';
import { MarcoPublico } from './MarcoPublico';

export default function Invitacion() {
  const { token = '' } = useParams();
  const { usuario } = useSesion();
  const navegar = useNavigate();
  const { datos: inv, error: errorCarga } = useDatos(() => invitaciones.ver(token), [token]);
  const [error, setError] = useState('');
  const volver = encodeURIComponent(`/invitacion/${token}`);

  async function responder(acepta: boolean) {
    if (!acepta && !confirm('¿Rechazar la invitación? La otra parte podrá acudir a la vía judicial.')) return;
    try {
      const r = await invitaciones.responder(token, acepta);
      navegar(acepta ? `/ciudadano/negociacion/${r.mediacion_id}` : '/ciudadano');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo registrar tu respuesta.');
    }
  }

  return (
    <MarcoPublico titulo="Te invitaron a resolver un conflicto en línea">
      <MensajeError>{errorCarga || error}</MensajeError>
      {!inv && !errorCarga && <Cargando />}
      {inv && (
        <section className="tarjeta">
          <Folio ruta="odr">{inv.folio}</Folio>
          <p><strong>{inv.solicitante}</strong> te invita a buscar un acuerdo mediante mediación en línea sobre un asunto {t(inv.materia).toLowerCase()}.</p>
          <ul>
            <li>Negocian a su ritmo, sin estar conectados al mismo tiempo.</li>
            <li>Pueden pedir la ayuda de un mediador certificado.</li>
            <li>Si no llegan a un acuerdo, cada quien conserva su derecho a acudir a un juez.</li>
          </ul>
          <AvisoConfidencial>Lo que se converse en la mediación es confidencial y no pasa a un expediente judicial.</AvisoConfidencial>
          {inv.estado !== 'ENVIADA' ? (
            <p className="estado pendiente" style={{ alignSelf: 'flex-start' }}>Esta invitación ya no está disponible ({inv.estado.toLowerCase()}).</p>
          ) : !usuario ? (
            <>
              <p>Responde antes del <strong>{new Date(inv.fecha_limite + 'T12:00').toLocaleDateString('es-MX')}</strong>. Para hacerlo necesitas una cuenta.</p>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <Link className="boton jade" to={`/registro?volver=${volver}`}>Crear cuenta</Link>
                <Link className="boton secundario" to={`/login?volver=${volver}`}>Ya tengo cuenta</Link>
              </div>
            </>
          ) : (
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button type="button" className="boton jade" onClick={() => responder(true)}>Aceptar y entrar a la sala</button>
              <button type="button" className="boton peligro" onClick={() => responder(false)}>No acepto</button>
            </div>
          )}
        </section>
      )}
    </MarcoPublico>
  );
}
