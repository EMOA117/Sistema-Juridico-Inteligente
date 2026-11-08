import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { Usuario } from '@/compartido/tipos';
import { alExpirarSesion } from './api';

interface Sesion {
  usuario: Usuario | null;
  entrar: (token: string, u: Usuario) => void;
  salir: () => void;
}

const Ctx = createContext<Sesion | null>(null);

// El token vive en sessionStorage (se borra al cerrar la pestaña). Su expiración la controla core-api.
export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(() => {
    const guardado = sessionStorage.getItem('usuario');
    return guardado && sessionStorage.getItem('token') ? (JSON.parse(guardado) as Usuario) : null;
  });

  const entrar = (token: string, u: Usuario) => {
    sessionStorage.setItem('token', token);
    sessionStorage.setItem('usuario', JSON.stringify(u));
    setUsuario(u);
  };
  const salir = () => {
    sessionStorage.clear();
    setUsuario(null);
  };

  useEffect(() => alExpirarSesion(salir), []);

  return <Ctx.Provider value={{ usuario, entrar, salir }}>{children}</Ctx.Provider>;
}

export function useSesion() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useSesion debe usarse dentro de <ProveedorSesion>');
  return ctx;
}
