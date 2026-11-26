// RF6.2 · Carga de anexos (PDF o texto) al expediente: se guardan inmutables y se indexan para la búsqueda.
import { useRef, useState } from 'react';
import { ia } from '@/compartido/servicios';
import { MensajeError } from './index';

export function SubirAnexo({ expedienteId, alSubir }: { expedienteId: string; alSubir: () => void }) {
  const entrada = useRef<HTMLInputElement>(null);
  const [error, setError] = useState('');
  const [subiendo, setSubiendo] = useState(false);

  async function subir(archivo: File) {
    setSubiendo(true);
    setError('');
    try { await ia.subirAnexo(expedienteId, archivo); alSubir(); }
    catch (e) { setError(e instanceof Error ? e.message : 'No se pudo subir'); }
    setSubiendo(false);
    if (entrada.current) entrada.current.value = '';
  }

  return (
    <div className="campo">
      <label htmlFor={`anexo-${expedienteId}`}>Agregar anexo (PDF o texto, máx. 10 MB)</label>
      <input ref={entrada} id={`anexo-${expedienteId}`} type="file" accept="application/pdf,text/plain" disabled={subiendo}
        style={{ paddingTop: 10 }} onChange={(e) => { const f = e.target.files?.[0]; if (f) subir(f); }} />
      {subiendo && <span className="ayuda" role="status">Subiendo y registrando huella…</span>}
      <MensajeError>{error}</MensajeError>
    </div>
  );
}
