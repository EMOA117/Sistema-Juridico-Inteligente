// RF4.1 · Redacción del convenio: términos pactados y, en uno parcial, los puntos que siguen pendientes.
import { useState } from 'react';
import { odr } from '@/compartido/servicios';
import { intentar } from '@/compartido/servicios/useDatos';
import type { Convenio } from '@/compartido/tipos';
import { MensajeError } from './index';

export function EditorConvenio({ mediacionId, actual, sugerencia, alGuardar }: {
  mediacionId: string; actual: Convenio | null; sugerencia?: string; alGuardar: () => void;
}) {
  const [tipo, setTipo] = useState<'TOTAL' | 'PARCIAL'>(actual?.tipo ?? 'TOTAL');
  const [terminos, setTerminos] = useState(actual?.terminos ?? sugerencia ?? '');
  const [pendientes, setPendientes] = useState((actual?.puntos_pendientes ?? []).join('\n'));
  const [error, setError] = useState('');

  async function guardar() {
    const lista = pendientes.split('\n').map((x) => x.trim()).filter(Boolean);
    if (actual && !confirm('Guardar cambios reinicia las aprobaciones de las partes. ¿Continuar?')) return;
    if (await intentar(() => odr.redactarConvenio(mediacionId, { tipo, terminos, puntos_pendientes: tipo === 'PARCIAL' ? lista : [] }), setError)) alGuardar();
  }

  return (
    <div className="columna">
      <MensajeError>{error}</MensajeError>
      <fieldset style={{ border: 0, padding: 0, margin: 0, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <legend className="rotulo" style={{ fontWeight: 700, marginBottom: 6 }}>Tipo de acuerdo</legend>
        {(['TOTAL', 'PARCIAL'] as const).map((v) => (
          <label key={v} style={{ display: 'flex', gap: 6, alignItems: 'center', minHeight: 44 }}>
            <input type="radio" name="tipo-convenio" checked={tipo === v} onChange={() => setTipo(v)} />
            {v === 'TOTAL' ? 'Acuerdo total' : 'Acuerdo parcial (quedan puntos pendientes)'}
          </label>
        ))}
      </fieldset>
      <div className="campo">
        <label htmlFor="conv-terminos">Cláusulas acordadas</label>
        <textarea id="conv-terminos" rows={8} value={terminos} onChange={(e) => setTerminos(e.target.value)}
          placeholder="Primera. El deudor reconoce adeudar… Segunda. Pagará…" />
      </div>
      {tipo === 'PARCIAL' && (
        <div className="campo">
          <label htmlFor="conv-pend">Puntos pendientes (uno por línea)</label>
          <textarea id="conv-pend" rows={3} value={pendientes} onChange={(e) => setPendientes(e.target.value)} />
          <span className="ayuda">Solo estos puntos podrán llevarse a la vía judicial; los términos acordados nunca se transfieren.</span>
        </div>
      )}
      <button type="button" className="boton jade" disabled={terminos.trim().length < 20} onClick={guardar}>
        {actual ? 'Guardar cambios al convenio' : 'Preparar convenio'}
      </button>
    </div>
  );
}
