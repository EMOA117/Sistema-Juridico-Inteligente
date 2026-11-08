// P4 · Sala de negociación (ruta ODR). Todo lo de esta pantalla es confidencial.
import { useEffect, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AvisoConfidencial, CajaIA, Estado, Folio } from '@/compartido/componentes';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { odr } from '@/compartido/servicios';
import type { EstadoPropuesta, Mensaje, Propuesta } from '@/compartido/tipos';

const tonos: Record<EstadoPropuesta, 'pendiente' | 'aceptada' | 'rechazada'> = { PENDIENTE: 'pendiente', ACEPTADA: 'aceptada', RECHAZADA: 'rechazada' };
const textos: Record<EstadoPropuesta, string> = { PENDIENTE: '◷ Pendiente', ACEPTADA: '✓ Aceptada', RECHAZADA: '✕ Rechazada' };

export default function SalaNegociacion() {
  const { folio = '' } = useParams();
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [propuestas, setPropuestas] = useState<Propuesta[]>([]);
  const [sugerencia, setSugerencia] = useState<{ texto: string; fundamento: string } | null>(null);
  const [tipo, setTipo] = useState<'mensaje' | 'propuesta'>('mensaje');
  const [texto, setTexto] = useState('');

  useEffect(() => {
    odr.mensajes().then(setMensajes);
    odr.propuestas().then(setPropuestas);
    odr.sugerencia().then(setSugerencia);
  }, []);

  function cambiarEstado(id: string, estado: EstadoPropuesta) {
    // TODO: PATCH /odr/{folio}/propuestas/{id}  (requiere confirmación explícita)
    if (!confirm(`¿Confirmas ${estado === 'ACEPTADA' ? 'aceptar' : 'rechazar'} esta propuesta?`)) return;
    setPropuestas((ps) => ps.map((p) => (p.id === id ? { ...p, estado } : p)));
  }

  function enviar(e: FormEvent) {
    e.preventDefault();
    if (!texto.trim()) return;
    // TODO: POST /odr/{folio}/mensajes o /propuestas
    if (tipo === 'mensaje') {
      setMensajes((ms) => [...ms, { id: crypto.randomUUID(), autor: 'yo', texto, fecha: 'ahora' }]);
    } else {
      setPropuestas((ps) => [{ id: crypto.randomUUID(), numero: ps.length + 1, autor: 'yo', resumen: texto, estado: 'PENDIENTE' }, ...ps]);
    }
    setTexto('');
  }

  return (
    <div className="pagina">
      <EncabezadoCiudadano titulo="Sala de negociación" etiqueta="RUTA ODR" volverA="/ciudadano" />
      <div className="contenedor">
        <div className="tarjeta" style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px' }}>
          <span style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <Folio ruta="odr">{decodeURIComponent(folio)}</Folio>
            <Estado tono="pendiente">En negociación</Estado>
          </span>
          <span>Plazo para responder: <strong>30 nov 2027</strong></span>
        </div>

        <AvisoConfidencial>
          <strong>Espacio confidencial.</strong> Mensajes y propuestas no se transfieren al expediente judicial si deciden ir a juicio.
        </AvisoConfidencial>

        <div className="fila">
          <section className="tarjeta" aria-labelledby="h-conv" style={{ flex: '2 1 520px', minWidth: 0 }}>
            <h2 id="h-conv" className="titulo-serif" style={{ fontSize: 24 }}>Conversación</h2>
            <div className="columna" aria-live="polite">
              {mensajes.map((m) => (
                <div key={m.id} style={{ alignSelf: m.autor === 'yo' ? 'flex-end' : 'flex-start', maxWidth: '75%' }}>
                  <p style={{ padding: '10px 14px', borderRadius: 8, background: m.autor === 'yo' ? 'var(--jade-tinte)' : 'var(--gris-suave)' }}>{m.texto}</p>
                  <span className="pequeno texto-2">{m.autor === 'yo' ? 'Tú' : 'Otra parte'} · {m.fecha}</span>
                </div>
              ))}
            </div>
            <form onSubmit={enviar} className="columna">
              <div className="pestanas" role="tablist" aria-label="Tipo de envío">
                <button type="button" role="tab" aria-selected={tipo === 'mensaje'} onClick={() => setTipo('mensaje')}>Mensaje</button>
                <button type="button" role="tab" aria-selected={tipo === 'propuesta'} onClick={() => setTipo('propuesta')}>Propuesta formal</button>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <label htmlFor="msg" className="solo-lector">{tipo === 'mensaje' ? 'Escribe tu mensaje' : 'Describe tu propuesta'}</label>
                <input id="msg" value={texto} onChange={(e) => setTexto(e.target.value)} placeholder={tipo === 'mensaje' ? 'Escribe tu mensaje…' : 'Ej. $10,000 al firmar y $5,000 a 60 días'}
                  style={{ flex: 1, minHeight: 48, padding: '0 14px', border: '1.5px solid var(--borde-campo)', borderRadius: 4 }} />
                <button type="submit" className="boton jade">Enviar</button>
              </div>
            </form>
          </section>

          <aside className="columna" style={{ flex: '1 1 340px', gap: 16 }}>
            <section className="tarjeta" aria-labelledby="h-mesa">
              <h2 id="h-mesa" className="titulo-seccion">Mesa de propuestas</h2>
              {propuestas.map((p) => (
                <div key={p.id} className="columna" style={{ gap: 6, paddingBottom: 12, borderBottom: '1px solid var(--linea)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                    <span><strong>{p.resumen}</strong><br /><span className="pequeno texto-2">#{p.numero} · {p.autor === 'yo' ? 'tuya' : 'de la otra parte'}</span></span>
                    <Estado tono={tonos[p.estado]}>{textos[p.estado]}</Estado>
                  </div>
                  {p.estado === 'PENDIENTE' && p.autor === 'otra_parte' && (
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <button type="button" className="boton jade" onClick={() => cambiarEstado(p.id, 'ACEPTADA')}>Aceptar</button>
                      <button type="button" className="boton secundario" onClick={() => { setTipo('propuesta'); setTexto(p.resumen); }}>Contraproponer</button>
                      <button type="button" className="boton peligro" onClick={() => cambiarEstado(p.id, 'RECHAZADA')}>Rechazar</button>
                    </div>
                  )}
                </div>
              ))}
            </section>

            {sugerencia && (
              <CajaIA titulo="Sugerencia de acuerdo · IA">
                <p><strong>{sugerencia.texto}</strong></p>
                <p className="pequeno">{sugerencia.fundamento}</p>
                <span className="pequeno texto-2">No es una resolución. Pueden ignorarla o modificarla.</span>
                <button type="button" className="boton secundario" onClick={() => { setTipo('propuesta'); setTexto(sugerencia.texto); }}>
                  Usar como mi contrapropuesta
                </button>
              </CajaIA>
            )}

            <section className="tarjeta">
              <Link className="boton jade" to={`/ciudadano/convenio/${folio}`}>Formalizar convenio</Link>
              {/* TODO: POST /odr/{folio}/solicitar-mediador */}
              <button type="button" className="boton secundario" onClick={() => alert('Solicitud enviada (simulado).')}>Solicitar mediador certificado</button>
              <Link to={`/ciudadano/demanda/${folio}`}>Terminar sin acuerdo e ir a la vía judicial</Link>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}
