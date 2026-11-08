import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { http } from './api';
import type { Usuario } from '@/compartido/tipos';

interface Sesion {
  usuario: Usuario | null;
  entrar: (u: Usuario) => void;
  salir: () => void;
}

const Ctx = createContext<Sesion | null>(null);

// Sesión en memoria + sessionStorage. La expiración (15 min) y el JWT reales los controla core-api.
export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(() => {
    const guardado = sessionStorage.getItem('usuario');
    try { return guardado ? (JSON.parse(guardado) as Usuario) : null; } catch { return null; }
  });

  const entrar = (u: Usuario) => {
    sessionStorage.setItem('usuario', JSON.stringify(u));
    setUsuario(u);
  };
  const salir = () => {
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('usuario');
    setUsuario(null);
  };

  useEffect(() => {
    const expirar = () => { sessionStorage.removeItem('token'); sessionStorage.removeItem('usuario'); setUsuario(null); };
    window.addEventListener('sesion-expirada', expirar);
    if (sessionStorage.getItem('token')) {
      http<Usuario>('/auth/me').then(setUsuario).catch(() => { /* Un fallo de red no borra credenciales. */ });
    } else expirar();
    return () => window.removeEventListener('sesion-expirada', expirar);
  }, []);
  return <Ctx.Provider value={{ usuario, entrar, salir }}>{children}</Ctx.Provider>;
}

export function useSesion() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useSesion debe usarse dentro de <ProveedorSesion>');
  return ctx;
}
