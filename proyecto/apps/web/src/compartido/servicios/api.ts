// Cliente HTTP hacia core-api (Vite reenvía /api → http://localhost:8000 en desarrollo).
const BASE = import.meta.env.VITE_API_URL ?? '/api';

export class ErrorApi extends Error {
  constructor(public estado: number, mensaje: string) {
    super(mensaje);
  }
}

let alExpirar: (() => void) | null = null;
/** La sesión registra aquí qué hacer ante un 401 (token vencido o inválido). */
export function alExpirarSesion(fn: () => void) {
  alExpirar = fn;
}

export async function http<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem('token');
  const resp = await fetch(`${BASE}${ruta}`, {
    ...opciones,
    headers: {
      ...(opciones.body && !(opciones.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...opciones.headers,
    },
  });
  if (resp.status === 401 && token && alExpirar) alExpirar();
  if (!resp.ok) {
    let mensaje = `Error ${resp.status}`;
    try {
      const cuerpo = await resp.json();
      mensaje = typeof cuerpo.detail === 'string'
        ? cuerpo.detail
        : Array.isArray(cuerpo.detail) ? 'Revisa los datos capturados' : mensaje;
    } catch { /* respuesta sin JSON */ }
    throw new ErrorApi(resp.status, mensaje);
  }
  const tipo = resp.headers.get('content-type') ?? '';
  return (tipo.includes('application/json') ? resp.json() : resp.blob()) as Promise<T>;
}

export const get = <T,>(ruta: string) => http<T>(ruta);
export const post = <T,>(ruta: string, cuerpo?: unknown) =>
  http<T>(ruta, { method: 'POST', body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo) });
export const put = <T,>(ruta: string, cuerpo: unknown) => http<T>(ruta, { method: 'PUT', body: JSON.stringify(cuerpo) });
export const patch = <T,>(ruta: string, cuerpo: unknown) => http<T>(ruta, { method: 'PATCH', body: JSON.stringify(cuerpo) });
