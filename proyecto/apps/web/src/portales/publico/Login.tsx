// P1 · Inicio de sesión: ciudadano (correo + contraseña) e institucional (MFA obligatorio).
import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { IconoCandado, IconoFlecha, Logo } from '@/compartido/componentes';
import { identidad } from '@/compartido/servicios';
import { useSesion } from '@/compartido/servicios/sesion';
import type { Rol } from '@/compartido/tipos';

const destinos: Record<Rol, string> = { CIUDADANO: '/ciudadano', MEDIADOR: '/mediador', JUEZ: '/juez', ADMINISTRADOR: '/admin' };

export default function Login() {
  const { entrar } = useSesion();
  const [params] = useSearchParams();
  const navegar = useNavigate();
  const [verContrasena, setVerContrasena] = useState(false);
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);

  // rol: 'CIUDADANO' para el acceso ciudadano; cualquier otro valor = acceso institucional.
  async function acceder(e: FormEvent<HTMLFormElement>, rol: Rol) {
    e.preventDefault();
    const datos = new FormData(e.currentTarget);
    const correo = String(datos.get('correo') ?? '');
    const contrasena = String(datos.get('contrasena') ?? '');
    const mfa = String(datos.get('mfa') ?? '').replace(/\s/g, '');
    if (!correo || !contrasena) return setError('Escribe tu correo y contraseña.');
    if (rol !== 'CIUDADANO' && mfa && !/^\d{6}$/.test(mfa)) return setError('El código MFA debe tener 6 dígitos.');
    setError('');
    setEnviando(true);
    try {
      const r = await identidad.iniciarSesion(correo, contrasena, mfa);
      if (rol === 'CIUDADANO' && r.usuario.rol !== 'CIUDADANO') return setError('Usa el acceso institucional.');
      if (rol !== 'CIUDADANO' && r.usuario.rol === 'CIUDADANO') return setError('Usa el acceso ciudadano.');
      entrar(r.token, r.usuario);
      navegar(r.debe_cambiar_password ? '/cambiar-contrasena' : r.requiere_alta_mfa ? '/mfa' : destinos[r.usuario.rol]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No pudimos iniciar sesión.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexWrap: 'wrap' }}>
      <aside style={{ flex: '1 1 420px', background: 'var(--tinta)', color: 'var(--cal)', padding: '48px 56px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: 48, borderRight: '3px solid var(--laton)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Logo />
          <span className="marca" style={{ fontSize: 22 }}>Plataforma Jurídica Inteligente</span>
        </div>
        <div className="columna" style={{ gap: 20, maxWidth: 520 }}>
          <h1 className="titulo-serif" style={{ fontSize: 'clamp(36px, 5vw, 56px)', lineHeight: 1.05 }}>
            Antes de un juicio, <em style={{ color: '#D9C08C' }}>un acuerdo</em>.
          </h1>
          <p style={{ fontSize: 18, color: '#C8CFDA' }}>
            Describe tu conflicto, conoce tus opciones y negocia en línea con la otra parte. Si no se llega a un acuerdo,
            continúa a la vía judicial sin empezar de cero.
          </p>
        </div>
        <span className="pequeno" style={{ color: '#AEB8C7' }}>Conexión protegida · Datos sintéticos de demostración</span>
      </aside>

      <main style={{ flex: '1 1 520px', padding: '48px 56px', display: 'flex', flexDirection: 'column', gap: 24, justifyContent: 'center' }}>
        {params.get('motivo') === 'inactividad' && !error && (
          <p role="status" className="estado pendiente" style={{ alignSelf: 'flex-start' }}>Cerramos tu sesión por inactividad.</p>
        )}
        {error && <p role="alert" className="estado rechazada" style={{ alignSelf: 'flex-start' }}>{error}</p>}

        <form className="tarjeta" aria-labelledby="h-ciu" onSubmit={(e) => acceder(e, 'CIUDADANO')} noValidate>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 12 }}>
            <h2 id="h-ciu" className="titulo-serif" style={{ fontSize: 32 }}>Entra a tu cuenta</h2>
            <span className="texto-2">¿Primera vez? <Link to="/registro">Crea una cuenta</Link></span>
          </div>
          <div className="campo">
            <label htmlFor="c-mail">Correo electrónico</label>
            <input id="c-mail" name="correo" type="email" autoComplete="email" />
          </div>
          <div className="campo">
            <label htmlFor="c-pass">Contraseña</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input id="c-pass" name="contrasena" type={verContrasena ? 'text' : 'password'} autoComplete="current-password" style={{ flex: 1 }} />
              <button type="button" className="boton secundario" onClick={() => setVerContrasena((v) => !v)}>
                {verContrasena ? 'Ocultar' : 'Mostrar'}
              </button>
            </div>
          </div>
          <button type="submit" className="boton bloque" disabled={enviando}>Entrar <IconoFlecha /></button>
          <span className="pequeno texto-2">Por seguridad, tu sesión se cierra tras 15 minutos sin actividad.</span>
        </form>

        <form className="tarjeta suave" aria-labelledby="h-inst" onSubmit={(e) => acceder(e, 'JUEZ')} noValidate>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <h2 id="h-inst" style={{ fontSize: 17 }}>Acceso institucional</h2>
            <span className="mono pequeno texto-2" style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}><IconoCandado />MFA OBLIGATORIO</span>
          </div>
          <p className="pequeno texto-2">Jueces, mediadores y personal administrativo. Tu perfil se toma de tu cuenta institucional.</p>
          <div className="fila">
            <div className="campo crece" style={{ minWidth: 200 }}>
              <label htmlFor="i-mail">Correo institucional</label>
              <input id="i-mail" name="correo" type="email" />
            </div>
            <div className="campo crece" style={{ minWidth: 160 }}>
              <label htmlFor="i-pass">Contraseña</label>
              <input id="i-pass" name="contrasena" type="password" />
            </div>
            <div className="campo" style={{ width: 160 }}>
              <label htmlFor="i-mfa">Código MFA</label>
              <input id="i-mfa" name="mfa" inputMode="numeric" maxLength={7} className="mono" />
            </div>
          </div>
          <button type="submit" className="boton secundario bloque" disabled={enviando}>Verificar y entrar</button>
        </form>
      </main>
    </div>
  );
}
