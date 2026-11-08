import { useCallback, useEffect, useState } from 'react';

/** Carga datos de la API con estado de carga, error y recarga manual. */
export function useDatos<T>(cargar: () => Promise<T>, deps: unknown[] = []) {
  const [datos, setDatos] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  const recargar = useCallback(async () => {
    setCargando(true);
    try {
      setDatos(await cargar());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error inesperado');
    } finally {
      setCargando(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { recargar(); }, [recargar]);
  return { datos, error, cargando, recargar, setDatos };
}

/** Ejecuta una acción mostrando su error; devuelve true si salió bien. */
export async function intentar(accion: () => Promise<unknown>, alError: (m: string) => void): Promise<boolean> {
  try {
    await accion();
    return true;
  } catch (e) {
    alError(e instanceof Error ? e.message : 'Error inesperado');
    return false;
  }
}
