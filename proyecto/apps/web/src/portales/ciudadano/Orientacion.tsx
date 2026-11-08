// P2 · Asistente de orientación: partes primero (RF2.1), después el relato, clasificación sugerida y ruta.
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CajaIA, MensajeError, t } from '@/compartido/componentes';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { conflictos } from '@/compartido/servicios';
import { useSesion } from '@/compartido/servicios/sesion';
import { intentar } from '@/compartido/servicios/useDatos';
import type { Materia, Orientacion as TOrientacion } from '@/compartido/tipos';

const pasos = ['Las partes', 'Tu caso', 'Orientación'];

export default function Orientacion() {
  const { usuario } = useSesion();
  const navegar = useNavigate();
  const [params] = useSearchParams();
  const [paso, setPaso] = useState(0);
  const [conflictoId, setConflictoId] = useState<string | null>(params.get('conflicto'));
  const [solicitante, setSolicitante] = useState(usuario?.nombre ?? '');
  const [otraParte, setOtraParte] = useState({ nombre: '', correo: '', domicilio: '' });
  const [narrativa, setNarrativa] = useState('');
  const [resultado, setResultado] = useState<TOrientacion | null>(null);
  const [materia, setMateria] = useState<Materia>('CIVIL');
  const [confirmado, setConfirmado] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState('');

  // Retoma un asunto ya iniciado desde "Mis asuntos".
  useEffect(() => {
    if (!conflictoId) return;
    conflictos.detalle(conflictoId).then((c) => {
      const otra = c.partes.find((p) => p.rol === 'DEMANDADO');
      setOtraParte({ nombre: otra?.nombre ?? '', correo: otra?.correo ?? '', domicilio: otra?.domicilio_notificaciones ?? '' });
      if (c.narrativa_inicial && c.materia) {
        setNarrativa(c.narrativa_inicial);
        setResultado({ materia: c.materia, confianza: Number(c.confianza_clasificacion ?? 0), complejidad: c.complejidad ?? 'MEDIA',
          mediable: !!c.mediable, motivo: '', origen: 'REGLAS' });
        setMateria(c.materia);
        setConfirmado(c.estado !== 'CAPTURA');
        setPaso(2);
      } else setPaso(1);
    }).catch((e) => setError(e.message));
  }, [conflictoId]);

  async function guardarPartes() {
    setOcupado(true);
    await intentar(async () => {
      const r = await conflictos.crear(
        { nombre: solicitante, correo: usuario?.correo },
        { nombre: otraParte.nombre, correo: otraParte.correo || undefined, domicilio: otraParte.domicilio || undefined });
      setConflictoId(r.id);
      setPaso(1);
    }, setError);
    setOcupado(false);
  }

  async function analizar() {
    if (!conflictoId) return;
    setOcupado(true);
    await intentar(async () => {
      const r = await conflictos.narrativa(conflictoId, narrativa);
      setResultado(r);
      setMateria(r.materia);
      setPaso(2);
    }, setError);
    setOcupado(false);
  }

  async function confirmar() {
    if (!conflictoId) return;
    if (await intentar(() => conflictos.confirmar(conflictoId, materia), setError)) setConfirmado(true);
  }

  async function irAJuicio() {
    if (!conflictoId || !confirm('¿Continuar por la vía judicial? Se preparará un borrador de demanda.')) return;
    await intentar(async () => {
      await conflictos.canalizar(conflictoId);
      navegar(`/ciudadano/demanda/${conflictoId}`);
    }, setError);
  }

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
        <MensajeError>{error}</MensajeError>

        {paso === 0 && (
          <section className="tarjeta" aria-labelledby="h-datos">
            <h1 id="h-datos" className="titulo-serif" style={{ fontSize: 32 }}>Primero, ¿quiénes participan?</h1>
            <div className="fila">
              <div className="campo crece" style={{ minWidth: 240 }}>
                <label htmlFor="sol">Tu nombre completo</label>
                <input id="sol" value={solicitante} onChange={(e) => setSolicitante(e.target.value)} />
              </div>
              <div className="campo crece" style={{ minWidth: 240 }}>
                <label htmlFor="otra">Nombre de la otra parte</label>
                <input id="otra" value={otraParte.nombre} onChange={(e) => setOtraParte({ ...otraParte, nombre: e.target.value })} />
              </div>
            </div>
            <div className="fila">
              <div className="campo crece" style={{ minWidth: 240 }}>
                <label htmlFor="otra-correo">Correo de la otra parte</label>
                <input id="otra-correo" type="email" value={otraParte.correo} onChange={(e) => setOtraParte({ ...otraParte, correo: e.target.value })} />
                <span className="ayuda">Lo usamos para invitarla a mediar.</span>
              </div>
              <div className="campo crece" style={{ minWidth: 240 }}>
                <label htmlFor="otra-dom">Domicilio de la otra parte (opcional)</label>
                <input id="otra-dom" value={otraParte.domicilio} onChange={(e) => setOtraParte({ ...otraParte, domicilio: e.target.value })} />
              </div>
            </div>
            <button type="button" className="boton" disabled={solicitante.length < 3 || otraParte.nombre.length < 3 || ocupado} onClick={guardarPartes}>
              Continuar
            </button>
          </section>
        )}

        {paso === 1 && (
          <section className="tarjeta" aria-labelledby="h-caso">
            <h1 id="h-caso" className="titulo-serif" style={{ fontSize: 32 }}>Cuéntanos qué pasó</h1>
            <div className="campo">
              <label htmlFor="narrativa">En tus palabras, sin tecnicismos</label>
              <textarea id="narrativa" rows={6} maxLength={2000} value={narrativa} onChange={(e) => setNarrativa(e.target.value)} />
              <span className="ayuda">{narrativa.length}/2000 caracteres.</span>
            </div>
            <button type="button" className="boton" disabled={narrativa.trim().length < 20 || ocupado} onClick={analizar}>
              {ocupado ? 'Analizando…' : 'Analizar mi caso'}
            </button>
          </section>
        )}

        {paso === 2 && resultado && (
          <>
            <CajaIA titulo={resultado.origen === 'IA' ? `Orientación asistida por IA · ${resultado.modelo ?? ''}` : 'Orientación automática · reglas de respaldo'}>
              <h1 className="titulo-serif" style={{ fontSize: 30 }}>
                Tu caso parece un asunto <strong>{t(resultado.materia).toLowerCase()}</strong>
                {resultado.mediable ? ', y es de los que suelen resolverse con un acuerdo.' : '.'}
              </h1>
              <dl className="fila" style={{ margin: 0 }}>
                <div className="crece"><dt className="texto-2">Certeza de la clasificación</dt><dd style={{ margin: 0, fontWeight: 700 }}>{Math.round(resultado.confianza * 100)}%</dd></div>
                <div className="crece"><dt className="texto-2">Complejidad estimada</dt><dd style={{ margin: 0, fontWeight: 700 }}>{resultado.complejidad.charAt(0) + resultado.complejidad.slice(1).toLowerCase()}</dd></div>
                <div className="crece"><dt className="texto-2">¿Se puede mediar?</dt><dd style={{ margin: 0, fontWeight: 700 }}>{resultado.mediable ? 'Sí' : 'No'}{resultado.motivo && ` · ${resultado.motivo}`}</dd></div>
              </dl>
              {!confirmado && (
                <div className="fila" style={{ alignItems: 'flex-end' }}>
                  <div className="campo" style={{ minWidth: 220 }}>
                    <label htmlFor="materia">¿Es correcta la materia?</label>
                    <select id="materia" value={materia} onChange={(e) => setMateria(e.target.value as Materia)}>
                      <option value="CIVIL">Civil</option><option value="FAMILIAR">Familiar</option>
                    </select>
                  </div>
                  <button type="button" className="boton" onClick={confirmar}>Confirmar orientación</button>
                </div>
              )}
            </CajaIA>

            {confirmado && (
              <section aria-labelledby="h-alt" className="columna">
                <h2 id="h-alt" className="titulo-serif" style={{ fontSize: 26 }}>¿Cómo quieres continuar?</h2>
                <span className="texto-2">La decisión es tuya.</span>
                <div className="fila">
                  <article className="tarjeta crece" style={{ minWidth: 280, borderColor: 'var(--jade)' }}>
                    <h3 style={{ color: 'var(--jade)' }}>Mediación en línea {resultado.mediable && <span className="estado aceptada">Recomendada</span>}</h3>
                    <p>Semanas · Deciden ustedes con apoyo de un mediador · Sin costo · Confidencial</p>
                    <button type="button" className="boton jade" disabled={!resultado.mediable} onClick={() => navegar(`/ciudadano/invitar/${conflictoId}`)}>
                      Invitar a {otraParte.nombre.split(' ')[0] || 'la otra parte'} a mediar
                    </button>
                  </article>
                  <article className="tarjeta crece" style={{ minWidth: 280, borderColor: 'var(--toga)' }}>
                    <h3 style={{ color: 'var(--toga)' }}>Vía judicial</h3>
                    <p>Meses · Decide un juez · Puede requerir abogado · Expediente judicial</p>
                    <button type="button" className="boton toga" onClick={irAJuicio}>Preparar mi demanda</button>
                  </article>
                </div>
              </section>
            )}
            <p className="pequeno texto-2">Esta orientación es informativa y no sustituye la asesoría de un abogado. Ninguna decisión jurídica se toma de forma automática.</p>
          </>
        )}
      </div>
    </div>
  );
}
