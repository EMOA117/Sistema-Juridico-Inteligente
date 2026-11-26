import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { Usuario } from '@/compartido/tipos';
import { alExpirarSesion, post } from './api';

const INACTIVIDAD_MS = 15 * 60 * 1000;   // documento: sesión de tiempo limitado
const RENOVAR_MS = 10 * 60 * 1000;

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

  // Cierra la sesión tras 15 minutos sin actividad y renueva el token mientras se use la plataforma.
  useEffect(() => {
    if (!usuario) return;
    let ultima = Date.now();
    let renovado = Date.now();
    const actividad = () => { ultima = Date.now(); };
    const eventos = ['pointerdown', 'keydown', 'scroll'] as const;
    eventos.forEach((e) => window.addEventListener(e, actividad, { passive: true }));
    const reloj = window.setInterval(async () => {
      if (Date.now() - ultima > INACTIVIDAD_MS) {
        salir();
        window.location.assign('/login?motivo=inactividad');
      } else if (Date.now() - renovado > RENOVAR_MS && Date.now() - ultima < RENOVAR_MS) {
        renovado = Date.now();
        try {
          const r = await post<{ token: string }>('/auth/renovar');
          sessionStorage.setItem('token', r.token);
        } catch { /* el siguiente 401 cerrará la sesión */ }
      }
    }, 30_000);
    return () => {
      eventos.forEach((e) => window.removeEventListener(e, actividad));
      window.clearInterval(reloj);
    };
  }, [usuario]);

  return <Ctx.Provider value={{ usuario, entrar, salir }}>{children}</Ctx.Provider>;
}

export function useSesion() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useSesion debe usarse dentro de <ProveedorSesion>');
  return ctx;
}
