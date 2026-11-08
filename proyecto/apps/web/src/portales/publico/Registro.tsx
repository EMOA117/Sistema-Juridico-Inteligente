import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { enviar } from '@/compartido/servicios/odr';
import { useSesion } from '@/compartido/servicios/sesion';
import type { Usuario } from '@/compartido/tipos';

export default function Registro() {
  const { entrar }=useSesion(); const navegar=useNavigate();
  const [error,setError]=useState(''); const [ocupado,setOcupado]=useState(false);
  async function registrar(e:FormEvent<HTMLFormElement>) {
    e.preventDefault(); const f=new FormData(e.currentTarget); setOcupado(true); setError('');
    try {
      const s=await enviar<{token:string;usuario:Usuario}>('/auth/registro',{nombre:f.get('nombre'),correo:f.get('correo'),contrasena:f.get('contrasena')});
      sessionStorage.setItem('token',s.token); entrar(s.usuario); navegar('/ciudadano');
    } catch(e) { setError((e as Error).message); } finally { setOcupado(false); }
  }
  return <main className="contenedor odr-estrecho"><Link to="/login">← Volver al acceso</Link><h1 className="titulo-serif">Crea tu cuenta ciudadana</h1><p>Demostración con personas y correos sintéticos. No hay verificación de identidad institucional en esta iteración.</p>
    <form className="tarjeta" onSubmit={registrar}>{error && <p role="alert" className="odr-error">{error}</p>}
      <div className="campo"><label htmlFor="nombre">Nombre</label><input id="nombre" name="nombre" required minLength={2} maxLength={150} autoComplete="name"/></div>
      <div className="campo"><label htmlFor="correo">Correo</label><input id="correo" name="correo" type="email" required maxLength={254} autoComplete="email"/></div>
      <div className="campo"><label htmlFor="contrasena">Contraseña (mínimo 12 caracteres)</label><input id="contrasena" name="contrasena" type="password" required minLength={12} maxLength={128} autoComplete="new-password"/></div>
      <button className="boton jade" disabled={ocupado}>Crear cuenta</button>
    </form></main>;
}
