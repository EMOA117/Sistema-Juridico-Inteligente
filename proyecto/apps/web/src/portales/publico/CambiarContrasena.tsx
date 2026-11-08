// Primer acceso del personal: sustituye la contraseña temporal antes de activar el MFA.
import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { MensajeError } from '@/compartido/componentes';
import { identidad } from '@/compartido/servicios';
import { useSesion } from '@/compartido/servicios/sesion';
import { MarcoPublico } from './MarcoPublico';

export default function CambiarContrasena() {
  const { usuario } = useSesion();
  const navegar = useNavigate();
  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [error, setError] = useState('');

  async function enviar(e: FormEvent) {
    e.preventDefault();
    try {
      await identidad.cambiarContrasena(actual, nueva);
      navegar(usuario && usuario.rol !== 'CIUDADANO' && !usuario.mfa ? '/mfa' : '/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cambiar la contraseña.');
    }
  }

  return (
    <MarcoPublico titulo="Cambia tu contraseña temporal">
      <form className="tarjeta" onSubmit={enviar}>
        <MensajeError>{error}</MensajeError>
        <div className="campo"><label htmlFor="c-act">Contraseña temporal</label><input id="c-act" type="password" autoComplete="current-password" value={actual} onChange={(e) => setActual(e.target.value)} /></div>
        <div className="campo">
          <label htmlFor="c-nueva">Nueva contraseña</label>
          <input id="c-nueva" type="password" autoComplete="new-password" value={nueva} onChange={(e) => setNueva(e.target.value)} />
          <span className="ayuda">Al menos 12 caracteres, combinando letras con números o símbolos.</span>
        </div>
        <button type="submit" className="boton" disabled={!actual || nueva.length < 12}>Guardar</button>
      </form>
    </MarcoPublico>
  );
}
