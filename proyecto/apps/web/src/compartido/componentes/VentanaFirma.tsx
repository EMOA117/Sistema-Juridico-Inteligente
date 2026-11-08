// RF4.3 / RF9.5 · Confirmación de identidad antes de firmar: contraseña y, para el personal, código MFA.
import { useEffect, useRef, useState, type FormEvent } from 'react';
import type { Credenciales } from '@/compartido/servicios';
import { MensajeError } from './index';

export function VentanaFirma({ abierta, titulo, descripcion, pedirMfa, alCerrar, alFirmar }: {
  abierta: boolean; titulo: string; descripcion: string; pedirMfa: boolean;
  alCerrar: () => void; alFirmar: (c: Credenciales) => Promise<void>;
}) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const [contrasena, setContrasena] = useState('');
  const [codigo, setCodigo] = useState('');
  const [error, setError] = useState('');
  const [firmando, setFirmando] = useState(false);

  useEffect(() => {
    const d = dialogo.current;
    if (!d) return;
    if (abierta && !d.open) d.showModal();
    if (!abierta && d.open) d.close();
  }, [abierta]);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setFirmando(true);
    setError('');
    try {
      await alFirmar({ contrasena, codigo_mfa: pedirMfa ? codigo : undefined });
      setContrasena('');
      setCodigo('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo firmar.');
    } finally {
      setFirmando(false);
    }
  }

  return (
    <dialog ref={dialogo} onClose={alCerrar} aria-labelledby="firma-titulo"
      style={{ border: '1px solid var(--linea)', borderRadius: 8, padding: 0, maxWidth: 460, width: 'calc(100% - 32px)' }}>
      <form onSubmit={enviar} className="tarjeta" style={{ border: 0 }}>
        <h2 id="firma-titulo" className="titulo-serif" style={{ fontSize: 24 }}>{titulo}</h2>
        <p className="pequeno">{descripcion}</p>
        <MensajeError>{error}</MensajeError>
        <div className="campo">
          <label htmlFor="firma-pass">Confirma tu contraseña</label>
          <input id="firma-pass" type="password" autoComplete="current-password" value={contrasena} onChange={(e) => setContrasena(e.target.value)} />
        </div>
        {pedirMfa && (
          <div className="campo">
            <label htmlFor="firma-mfa">Código MFA</label>
            <input id="firma-mfa" inputMode="numeric" autoComplete="one-time-code" maxLength={6} className="mono"
              value={codigo} onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ''))} />
          </div>
        )}
        <p className="pequeno texto-2">Firma de demostración con certificado de prueba y sello de tiempo local. No tiene validez legal.</p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
          <button type="button" className="boton secundario" onClick={alCerrar}>Cancelar</button>
          <button type="submit" className="boton" disabled={firmando || !contrasena || (pedirMfa && codigo.length !== 6)}>
            {firmando ? 'Firmando…' : 'Firmar'}
          </button>
        </div>
      </form>
    </dialog>
  );
}
