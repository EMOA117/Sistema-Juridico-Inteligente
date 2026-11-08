// P1 · Inicio de sesión: ciudadano (correo + contraseña) e institucional (MFA obligatorio).
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { IconoCandado, IconoFlecha, Logo } from '@/compartido/componentes';
import { identidad } from '@/compartido/servicios';
import { useSesion } from '@/compartido/servicios/sesion';
import type { Rol } from '@/compartido/tipos';

const destinos: Record<Rol, string> = { CIUDADANO: '/ciudadano', MEDIADOR: '/mediador', JUEZ: '/juez', ADMINISTRADOR: '/admin' };

export default function Login() {
  const { entrar } = useSesion();
  const navegar = useNavigate();
  const [verContrasena, setVerContrasena] = useState(false);
  const [perfil, setPerfil] = useState<Exclude<Rol, 'CIUDADANO'>>('JUEZ');
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);

  async function acceder(e: FormEvent<HTMLFormElement>, rol: Rol) {
    e.preventDefault();
    const datos = new FormData(e.currentTarget);
    const correo = String(datos.get('correo') ?? '');
    const contrasena = String(datos.get('contrasena') ?? '');
    const mfa = String(datos.get('mfa') ?? '').replace(/\s/g, '');
    if (!correo || !contrasena) return setError('Escribe tu correo y contraseña.');
    if (rol !== 'CIUDADANO' && !/^\d{6}$/.test(mfa)) return setError('El código MFA debe tener 6 dígitos.');
    setError('');
    setEnviando(true);
    try {
      const usuario = await identidad.iniciarSesion(correo, contrasena, rol, mfa);
      entrar(usuario);
      navegar(destinos[usuario.rol]);
    } catch {
      setError('No pudimos iniciar sesión. Revisa tus datos.');
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
        <span className="pequeno" style={{ color: '#AEB8C7' }}>Entorno local · Datos sintéticos de demostración</span>
      </aside>

      <main style={{ flex: '1 1 520px', padding: '48px 56px', display: 'flex', flexDirection: 'column', gap: 24, justifyContent: 'center' }}>
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
          <span className="pequeno texto-2">La sesión expira 15 minutos después del acceso. Guarda tus cambios antes de salir.</span>
        </form>

        <form className="tarjeta suave" aria-labelledby="h-inst" onSubmit={(e) => acceder(e, perfil)} noValidate>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <h2 id="h-inst" style={{ fontSize: 17 }}>Acceso institucional</h2>
            <span className="mono pequeno texto-2" style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}><IconoCandado />MFA OBLIGATORIO</span>
          </div>
          <fieldset style={{ border: 0, padding: 0, margin: 0, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            <legend className="solo-lector">Perfil</legend>
            {([['JUEZ', 'Juez'], ['MEDIADOR', 'Mediador'], ['ADMINISTRADOR', 'Administrativo']] as const).map(([valor, texto]) => (
              <label key={valor} style={{ display: 'flex', alignItems: 'center', gap: 6, minHeight: 44, fontWeight: 700 }}>
                <input type="radio" name="perfil" checked={perfil === valor} onChange={() => setPerfil(valor)} />{texto}
              </label>
            ))}
          </fieldset>
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
