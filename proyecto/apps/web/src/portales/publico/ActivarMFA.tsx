// RF1.2 · Alta del segundo factor (TOTP) obligatorio para jueces, mediadores y personal administrativo.
import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Cargando, MensajeError } from '@/compartido/componentes';
import { identidad } from '@/compartido/servicios';
import { useSesion } from '@/compartido/servicios/sesion';
import { MarcoPublico } from './MarcoPublico';

const destinos = { CIUDADANO: '/ciudadano', MEDIADOR: '/mediador', JUEZ: '/juez', ADMINISTRADOR: '/admin' } as const;

export default function ActivarMFA() {
  const { entrar } = useSesion();
  const navegar = useNavigate();
  const [alta, setAlta] = useState<{ qr_svg: string; secreto: string } | null>(null);
  const [codigo, setCodigo] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    identidad.altaMfa().then(setAlta).catch((e) => setError(e.message));
  }, []);

  async function confirmar(e: FormEvent) {
    e.preventDefault();
    try {
      const r = await identidad.confirmarMfa(codigo);
      entrar(r.token, r.usuario);
      navegar(destinos[r.usuario.rol]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Código incorrecto.');
    }
  }

  return (
    <MarcoPublico titulo="Activa tu segundo factor">
      <section className="tarjeta">
        <p>El acceso institucional exige autenticación multifactor. Instala <strong>Google Authenticator</strong> en tu teléfono (Android o iOS), escanea el código QR con la app y escribe el código de 6 dígitos que te muestre.</p>
        <MensajeError>{error}</MensajeError>
        {!alta && !error && <Cargando />}
        {alta && (
          <>
            <img alt="Código QR para Google Authenticator" width={220} height={220} style={{ alignSelf: 'center' }}
              src={`data:image/svg+xml;utf8,${encodeURIComponent(alta.qr_svg)}`} />
            <details>
              <summary style={{ cursor: 'pointer' }}>¿No puedes escanear? Escribe la clave manualmente</summary>
              <code className="mono" style={{ wordBreak: 'break-all' }}>{alta.secreto}</code>
            </details>
            <form onSubmit={confirmar} className="fila" style={{ alignItems: 'flex-end' }}>
              <div className="campo crece">
                <label htmlFor="mfa-cod">Código de 6 dígitos de Google Authenticator</label>
                <input id="mfa-cod" inputMode="numeric" autoComplete="one-time-code" maxLength={6} className="mono"
                  value={codigo} onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ''))} />
              </div>
              <button type="submit" className="boton" disabled={codigo.length !== 6}>Activar</button>
            </form>
          </>
        )}
      </section>
    </MarcoPublico>
  );
}
