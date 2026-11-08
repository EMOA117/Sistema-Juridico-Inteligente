// Cliente HTTP mínimo hacia core-api. Cuando VITE_USAR_MOCKS=true los servicios
// responden con datos simulados; el equipo reemplaza cada función por la llamada real.
const BASE = import.meta.env.VITE_API_URL ?? '/api';
export const USAR_MOCKS = (import.meta.env.VITE_USAR_MOCKS ?? 'false') === 'true';

export async function http<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem('token');
  const resp = await fetch(`${BASE}${ruta}`, {
    ...opciones,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...opciones.headers,
    },
  });
  if (!resp.ok) {
    if (resp.status === 401) window.dispatchEvent(new Event('sesion-expirada'));
    const error = await resp.json().catch(() => ({}));
    throw new Error(typeof error.detail === 'string' ? error.detail : `No se pudo completar la operación (${resp.status}).`);
  }
  return resp.json() as Promise<T>;
}

/** Simula latencia de red para los datos de prueba. */
export function simular<T>(datos: T, ms = 250): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(structuredClone(datos)), ms));
}
