// P2 · Asistente de orientación: captura secuencial (caso → datos) y resultado de la clasificación.
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CajaIA } from '@/compartido/componentes';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { orientacion as servicio } from '@/compartido/servicios';
import type { Orientacion as TOrientacion } from '@/compartido/tipos';

const pasos = ['Tu caso', 'Tus datos', 'Orientación'];

export default function Orientacion() {
  const [paso, setPaso] = useState(0);
  const [narrativa, setNarrativa] = useState('');
  const [solicitante, setSolicitante] = useState('');
  const [otraParte, setOtraParte] = useState('');
  const [resultado, setResultado] = useState<TOrientacion | null>(null);
  const [analizando, setAnalizando] = useState(false);

  async function analizar() {
    setAnalizando(true);
    setResultado(await servicio.clasificar(narrativa));
    setAnalizando(false);
    setPaso(2);
  }

  const folio = encodeURIComponent(resultado?.folio ?? '');

  return (
    <div className="pagina">
      <EncabezadoCiudadano titulo="Asistente de orientación" etiqueta="PORTAL CIUDADANO" volverA="/ciudadano" />
      <div className="contenedor">
        <ol aria-label="Pasos del asistente" style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          {pasos.map((p, i) => (
            <li key={p} aria-current={i === paso ? 'step' : undefined} style={{ fontWeight: i === paso ? 700 : 400, color: i <= paso ? 'var(--texto)' : 'var(--texto-2)' }}>
              <span className="mono">{i + 1}.</span> {p}
            </li>
          ))}
        </ol>

        {paso === 0 && (
          <section className="tarjeta" aria-labelledby="h-caso">
            <h1 id="h-caso" className="titulo-serif" style={{ fontSize: 32 }}>Cuéntanos qué pasó</h1>
            <div className="campo">
              <label htmlFor="narrativa">En tus palabras, sin tecnicismos</label>
              <textarea id="narrativa" rows={6} value={narrativa} onChange={(e) => setNarrativa(e.target.value)} />
              <span className="ayuda">{narrativa.length}/2000 caracteres. Puedes adjuntar pruebas después.</span>
            </div>
            {/* TODO: carga de anexos (PDF o imagen) al repositorio de objetos */}
            <button type="button" className="boton" disabled={narrativa.trim().length < 20} onClick={() => setPaso(1)}>Continuar</button>
          </section>
        )}

        {paso === 1 && (
          <section className="tarjeta" aria-labelledby="h-datos">
            <h1 id="h-datos" className="titulo-serif" style={{ fontSize: 32 }}>Tus datos y los de la otra parte</h1>
            <div className="fila">
              <div className="campo crece" style={{ minWidth: 240 }}>
                <label htmlFor="sol">Tu nombre completo</label>
                <input id="sol" value={solicitante} onChange={(e) => setSolicitante(e.target.value)} />
              </div>
              <div className="campo crece" style={{ minWidth: 240 }}>
                <label htmlFor="otra">Nombre de la otra parte</label>
                <input id="otra" value={otraParte} onChange={(e) => setOtraParte(e.target.value)} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button type="button" className="boton secundario" onClick={() => setPaso(0)}>Atrás</button>
              <button type="button" className="boton" disabled={!solicitante || !otraParte || analizando} onClick={analizar}>
                {analizando ? 'Analizando…' : 'Analizar mi caso'}
              </button>
            </div>
          </section>
        )}

        {paso === 2 && resultado && (
          <>
            <CajaIA titulo={`Orientación asistida por IA · ${resultado.folio}`}>
              <h1 className="titulo-serif" style={{ fontSize: 30 }}>
                Tu caso parece un asunto <strong>{resultado.materia.toLowerCase()}</strong>
                {resultado.mediable && ', y es de los que suelen resolverse con un acuerdo'}.
              </h1>
              <dl className="fila" style={{ margin: 0 }}>
                <div className="crece"><dt className="texto-2">Certeza de la clasificación</dt><dd style={{ margin: 0, fontWeight: 700 }}>{Math.round(resultado.certeza * 100)}%</dd></div>
                <div className="crece"><dt className="texto-2">Complejidad estimada</dt><dd style={{ margin: 0, fontWeight: 700 }}>{resultado.complejidad}</dd></div>
                <div className="crece"><dt className="texto-2">¿Se puede mediar?</dt><dd style={{ margin: 0, fontWeight: 700 }}>{resultado.mediable ? 'Sí' : 'No'} · {resultado.motivo}</dd></div>
              </dl>
              {/* TODO: permitir corregir la materia (revisión humana del resultado) */}
            </CajaIA>

            <section aria-labelledby="h-alt" className="columna">
              <h2 id="h-alt" className="titulo-serif" style={{ fontSize: 26 }}>¿Cómo quieres continuar?</h2>
              <span className="texto-2">La decisión es tuya. Puedes cambiar de ruta después.</span>
              <div className="fila">
                <article className="tarjeta crece" style={{ minWidth: 280, borderColor: 'var(--jade)' }}>
                  <h3 style={{ color: 'var(--jade)' }}>Mediación en línea {resultado.mediable && <span className="estado aceptada">Recomendada</span>}</h3>
                  <p>Semanas · Deciden ustedes con apoyo de un mediador · Sin costo · Confidencial</p>
                  <Link className="boton jade" to={`/ciudadano/negociacion/${folio}`}>Invitar a {otraParte.split(' ')[0]} a mediar</Link>
                </article>
                <article className="tarjeta crece" style={{ minWidth: 280, borderColor: 'var(--toga)' }}>
                  <h3 style={{ color: 'var(--toga)' }}>Vía judicial</h3>
                  <p>Meses · Decide un juez · Puede requerir abogado · Expediente judicial</p>
                  <Link className="boton toga" to={`/ciudadano/demanda/${folio}`}>Preparar mi demanda</Link>
                </article>
              </div>
              <p className="pequeno texto-2">Esta orientación es informativa y no sustituye la asesoría de un abogado. Ninguna decisión jurídica se toma de forma automática.</p>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
