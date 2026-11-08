// RF1.1 · Registro ciudadano con CURP. El servidor valida formato, dígito verificador y unicidad.
import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { MensajeError } from '@/compartido/componentes';
import { identidad } from '@/compartido/servicios';
import { useSesion } from '@/compartido/servicios/sesion';
import { MarcoPublico } from './MarcoPublico';

// Mismas reglas que valida el servidor (compartido/validacion.py), para avisar antes de enviar.
const ALFABETO_CURP = '0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ';
function problemaCurp(curp: string): string | null {
  const v = curp.trim().toUpperCase();
  if (v.length !== 18) return `La CURP debe tener 18 caracteres (llevas ${v.length}).`;
  if (!/^[A-Z][AEIOUX][A-Z]{2}[0-9]{6}[HM][A-Z]{5}[A-Z0-9][0-9]$/.test(v)) return 'La CURP no tiene el formato correcto.';
  const suma = [...v.slice(0, 17)].reduce((s, c, i) => s + ALFABETO_CURP.indexOf(c) * (18 - i), 0);
  if (Number(v[17]) !== (10 - (suma % 10)) % 10) return 'El último dígito de la CURP no coincide (dígito verificador).';
  return null;
}

function pendientes(d: { nombre: string; correo: string; curp: string; contrasena: string; repetir: string }): string[] {
  const p: string[] = [];
  if (!d.nombre.trim()) p.push('Escribe tu nombre completo.');
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(d.correo.trim())) p.push('Escribe un correo válido.');
  const c = problemaCurp(d.curp);
  if (c) p.push(c);
  if (d.contrasena.length < 12) p.push(`La contraseña necesita al menos 12 caracteres (llevas ${d.contrasena.length}).`);
  else if (/^[A-Za-zÀ-ÿ]+$/.test(d.contrasena) || /^\d+$/.test(d.contrasena)) p.push('Combina letras con números o símbolos en la contraseña.');
  if (d.contrasena !== d.repetir) p.push('Las contraseñas no coinciden.');
  return p;
}

export default function Registro() {
  const { entrar } = useSesion();
  const navegar = useNavigate();
  const [params] = useSearchParams();
  const [d, setD] = useState({ nombre: '', correo: params.get('correo') ?? '', curp: '', contrasena: '', repetir: '' });
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [intentado, setIntentado] = useState(false);
  const faltan = pendientes(d);
  const campo = (k: keyof typeof d) => ({ value: d[k], onChange: (e: React.ChangeEvent<HTMLInputElement>) => setD({ ...d, [k]: e.target.value }) });

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setIntentado(true);
    setError('');
    if (faltan.length) return;
    setEnviando(true);
    try {
      const r = await identidad.registrar({ nombre: d.nombre, correo: d.correo, curp: d.curp.toUpperCase(), contrasena: d.contrasena });
      entrar(r.token, r.usuario);
      const volver = params.get('volver');
      navegar(volver && volver.startsWith('/') && !volver.startsWith('//') ? volver : '/ciudadano');
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
        {intentado && faltan.length > 0 && (
          <div role="alert" className="aviso-confidencial">
            <span><strong>Antes de crear tu cuenta:</strong>
              <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>{faltan.map((f) => <li key={f}>{f}</li>)}</ul>
            </span>
          </div>
        )}
        <button type="submit" className="boton" disabled={enviando}>{enviando ? 'Creando cuenta…' : 'Crear cuenta'}</button>
        <span className="pequeno texto-2">¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link></span>
      </form>
    </MarcoPublico>
  );
}
