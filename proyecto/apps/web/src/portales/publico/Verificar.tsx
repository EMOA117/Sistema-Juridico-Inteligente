// Verificación pública de documentos oficiales por huella SHA-256 (sin revelar su contenido).
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Estado, MensajeError } from '@/compartido/componentes';
import { firma } from '@/compartido/servicios';
import { MarcoPublico } from './MarcoPublico';

async function sha256(archivo: File) {
  const digest = await crypto.subtle.digest('SHA-256', await archivo.arrayBuffer());
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export default function Verificar() {
  const { huella = '' } = useParams();
  const navegar = useNavigate();
  const [entrada, setEntrada] = useState(huella);
  const [r, setR] = useState<Awaited<ReturnType<typeof firma.verificar>> | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    setR(null);
    if (/^[0-9a-f]{64}$/i.test(huella)) firma.verificar(huella).then(setR).catch((e) => setError(e.message));
  }, [huella]);

  return (
    <MarcoPublico titulo="Verificar un documento">
      <section className="tarjeta">
        <p>Sube el PDF del convenio o la resolución, o escribe su huella SHA-256. Calculamos la huella en tu navegador: el archivo no se envía.</p>
        <MensajeError>{error}</MensajeError>
        <div className="campo">
          <label htmlFor="v-archivo">Documento PDF</label>
          <input id="v-archivo" type="file" accept="application/pdf" style={{ paddingTop: 10 }}
            onChange={async (e) => { const f = e.target.files?.[0]; if (f) navegar(`/verificar/${await sha256(f)}`); }} />
        </div>
        <form className="fila" style={{ alignItems: 'flex-end' }} onSubmit={(e) => { e.preventDefault(); navegar(`/verificar/${entrada.trim().toLowerCase()}`); }}>
          <div className="campo crece"><label htmlFor="v-hash">Huella SHA-256</label>
            <input id="v-hash" className="mono" value={entrada} onChange={(e) => setEntrada(e.target.value)} /></div>
          <button type="submit" className="boton" disabled={!/^[0-9a-f]{64}$/i.test(entrada.trim())}>Verificar</button>
        </form>
        {r && (r.valido ? (
          <div className="aviso-confidencial" role="status">
            <span><Estado tono="aceptada">✓ Documento auténtico</Estado><br />
              {r.tipo === 'CONVENIO' ? 'Convenio de mediación' : 'Resolución judicial'} · {r.referencia} · registrado el {new Date(r.creado_en!).toLocaleString('es-MX')} · {r.firmas} firma(s).</span>
          </div>
        ) : <p className="estado rechazada" role="status" style={{ alignSelf: 'flex-start' }}>✕ No hay un documento oficial con esa huella</p>)}
      </section>
    </MarcoPublico>
  );
}
