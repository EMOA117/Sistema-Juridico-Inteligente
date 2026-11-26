// P5 · Revisión del convenio por las partes (RF4.2). La firma y el PDF se agregan con la firma institucional.
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AvisoConfidencial, Cargando, Estado, Folio, MensajeError, t } from '@/compartido/componentes';
import { EditorConvenio } from '@/compartido/componentes/EditorConvenio';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { odr } from '@/compartido/servicios';
import { intentar, useDatos } from '@/compartido/servicios/useDatos';
import { PanelFirmaConvenio } from './PanelFirmaConvenio';

export default function Convenio() {
  const { id = '' } = useParams();
  const { datos, error: errorCarga, recargar } = useDatos(async () => {
    const [m, v] = await Promise.all([odr.detalle(id), odr.convenio(id)]);
    return { m, v };
  }, [id]);
  const [error, setError] = useState('');

  if (!datos) return <div className="pagina"><EncabezadoCiudadano titulo="Convenio" volverA="/ciudadano" />
    <div className="contenedor">{errorCarga ? <MensajeError>{errorCarga}</MensajeError> : <Cargando />}</div></div>;
  const { m, v } = datos;
  const yo = v?.partes.find((p) => p.soy_yo);
  const aceptada = m.propuestas.find((p) => p.estado === 'ACEPTADA');
  const puedeRedactar = !m.mediador && !v?.formalizado_en && !!aceptada && ['EN_NEGOCIACION', 'PENDIENTE_FORMALIZACION'].includes(m.estado);

  async function aprobar() {
    if (!confirm('¿Apruebas el texto del convenio? Después se te pedirá firmarlo.')) return;
    if (await intentar(() => odr.aprobarConvenio(id), setError)) recargar();
  }

  return (
    <div className="pagina">
      <EncabezadoCiudadano titulo="Convenio de mediación" etiqueta="RUTA ODR" volverA={`/ciudadano/negociacion/${id}`} />
      <div className="contenedor">
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <Folio ruta="odr">{m.folio}</Folio>
          {v && <Estado tono={v.formalizado_en ? 'aceptada' : 'pendiente'}>{v.formalizado_en ? 'Formalizado' : 'En revisión'}</Estado>}
          <span className="texto-2">{t(m.materia)} · {m.partes.map((p) => p.nombre).join(' · ')}</span>
        </div>
        <MensajeError>{error}</MensajeError>

        {!v && !puedeRedactar && (
          <p className="tarjeta texto-2">{m.mediador ? 'El mediador está preparando el convenio.' : 'Cuando una propuesta sea aceptada podrán preparar el convenio.'}</p>
        )}
        {puedeRedactar && (
          <section className="tarjeta" aria-labelledby="h-red">
            <h2 id="h-red" className="titulo-serif" style={{ fontSize: 24 }}>{v ? 'Editar convenio' : 'Preparar convenio'}</h2>
            <EditorConvenio mediacionId={id} actual={v} sugerencia={aceptada ? `Primera. ${aceptada.resumen}.` : ''} alGuardar={recargar} />
          </section>
        )}

        {v && (
          <div className="fila">
            <article className="tarjeta" style={{ flex: '2 1 520px', fontFamily: 'var(--fuente-titulo)', fontSize: 17, padding: '32px 40px' }}>
              <span className="mono pequeno">CENTRO DE JUSTICIA ALTERNATIVA · {v.tipo === 'TOTAL' ? 'ACUERDO TOTAL' : 'ACUERDO PARCIAL'}</span>
              <h2 style={{ fontSize: 28, fontWeight: 500 }}>Convenio de mediación</h2>
              <p>Partes: {v.partes.map((p) => <strong key={p.nombre}>{p.nombre} </strong>)}{v.mediador && <>con la intervención de {v.mediador.nombre} (Cert. {v.mediador.num_certificacion})</>}.</p>
              <p style={{ whiteSpace: 'pre-wrap' }}>{v.terminos}</p>
              {v.puntos_pendientes.length > 0 && (
                <div className="aviso-confidencial" style={{ fontFamily: 'var(--fuente-ui)' }}>
                  <span><strong>Puntos pendientes · canalizables a vía judicial:</strong> {v.puntos_pendientes.join('; ')}</span>
                </div>
              )}
            </article>
            <aside className="tarjeta" style={{ flex: '1 1 300px' }} aria-labelledby="h-rev">
              <h2 id="h-rev" className="titulo-seccion">Revisión de las partes</h2>
              {v.partes.map((p) => (
                <div key={p.nombre} style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                  <span>{p.nombre}{p.soy_yo && ' (tú)'}</span>
                  <Estado tono={p.aprobo ? 'aceptada' : 'pendiente'}>{p.aprobo ? '✓ Aprobó' : '◷ Pendiente'}</Estado>
                </div>
              ))}
              {yo && !yo.aprobo && !v.formalizado_en && <button type="button" className="boton jade" onClick={aprobar}>Aprobar texto del convenio</button>}
              <PanelFirmaConvenio mediacionId={id} convenio={v} alCambiar={recargar} />
              <AvisoConfidencial>Los términos acordados no se transfieren al expediente judicial.</AvisoConfidencial>
              <Link to={`/ciudadano/negociacion/${id}`}>Volver a la sala</Link>
            </aside>
          </div>
        )}
      </div>
    </div>
  );
}
