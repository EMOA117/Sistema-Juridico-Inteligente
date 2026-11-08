import { createContext, useContext, useState, type ReactNode } from 'react';
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
    return guardado ? (JSON.parse(guardado) as Usuario) : null;
  });

  const entrar = (u: Usuario) => {
    sessionStorage.setItem('usuario', JSON.stringify(u));
    setUsuario(u);
  };
  const salir = () => {
    sessionStorage.clear();
    setUsuario(null);
  };

  return <Ctx.Provider value={{ usuario, entrar, salir }}>{children}</Ctx.Provider>;
}

export function useSesion() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useSesion debe usarse dentro de <ProveedorSesion>');
  return ctx;
}
