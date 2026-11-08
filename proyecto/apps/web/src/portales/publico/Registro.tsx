// RF1.1 · Registro ciudadano con CURP. El servidor valida formato, dígito verificador y unicidad.
import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { MensajeError } from '@/compartido/componentes';
import { identidad } from '@/compartido/servicios';
import { useSesion } from '@/compartido/servicios/sesion';
import { MarcoPublico } from './MarcoPublico';

export default function Registro() {
  const { entrar } = useSesion();
  const navegar = useNavigate();
  const [params] = useSearchParams();
  const [d, setD] = useState({ nombre: '', correo: params.get('correo') ?? '', curp: '', contrasena: '', repetir: '' });
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);
  const campo = (k: keyof typeof d) => ({ value: d[k], onChange: (e: React.ChangeEvent<HTMLInputElement>) => setD({ ...d, [k]: e.target.value }) });

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (d.contrasena !== d.repetir) return setError('Las contraseñas no coinciden.');
    setEnviando(true);
    try {
      const r = await identidad.registrar({ nombre: d.nombre, correo: d.correo, curp: d.curp.toUpperCase(), contrasena: d.contrasena });
      entrar(r.token, r.usuario);
      navegar(params.get('volver') ?? '/ciudadano');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No pudimos crear tu cuenta.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <MarcoPublico titulo="Crea tu cuenta">
      <form className="tarjeta" onSubmit={enviar} noValidate>
        <MensajeError>{error}</MensajeError>
        <div className="campo"><label htmlFor="r-nombre">Nombre completo</label><input id="r-nombre" autoComplete="name" {...campo('nombre')} /></div>
        <div className="campo"><label htmlFor="r-correo">Correo electrónico</label><input id="r-correo" type="email" autoComplete="email" {...campo('correo')} /></div>
        <div className="campo">
          <label htmlFor="r-curp">CURP</label>
          <input id="r-curp" maxLength={18} className="mono" style={{ textTransform: 'uppercase' }} {...campo('curp')} />
          <span className="ayuda">18 caracteres. La usamos para validar tu identidad (datos sintéticos en esta demostración).</span>
        </div>
        <div className="campo">
          <label htmlFor="r-pass">Contraseña</label>
          <input id="r-pass" type="password" autoComplete="new-password" {...campo('contrasena')} />
          <span className="ayuda">Al menos 12 caracteres, combinando letras con números o símbolos.</span>
        </div>
        <div className="campo"><label htmlFor="r-pass2">Repite la contraseña</label><input id="r-pass2" type="password" autoComplete="new-password" {...campo('repetir')} /></div>
        <button type="submit" className="boton" disabled={enviando || !d.nombre || !d.correo || d.curp.length !== 18 || d.contrasena.length < 12}>Crear cuenta</button>
        <span className="pequeno texto-2">¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link></span>
      </form>
    </MarcoPublico>
  );
}
