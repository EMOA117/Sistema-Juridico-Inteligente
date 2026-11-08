// P7 · Demanda asistida (ruta judicial). Solo recibe partes, hechos y materia por canalización.
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CajaIA, Folio } from '@/compartido/componentes';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';

const hechosIniciales =
  'El 15 de marzo de 2027 la actora prestó $15,000 al demandado, quien se comprometió a pagar en tres meses. A la fecha no ha realizado pago alguno.';

export default function DemandaAsistida() {
  const { folio = '' } = useParams();
  const navegar = useNavigate();
  const [pretension, setPretension] = useState('Pago de $15,000 más intereses legales');
  const [domicilio, setDomicilio] = useState('');
  const [borrador, setBorrador] = useState(generarBorrador('Pago de $15,000 más intereses legales', ''));
  const [revisado, setRevisado] = useState(false);

  function regenerar() {
    // TODO: POST ia-service/generacion_demanda vía core-api
    setBorrador(generarBorrador(pretension, domicilio));
    setRevisado(false);
  }

  function presentar() {
    if (!confirm('¿Confirmas presentar la demanda? Esta acción no se puede deshacer.')) return;
    // TODO: POST /demandas  -> crea expediente EN_TURNO
    alert('Demanda presentada (simulado).');
    navegar('/ciudadano');
  }

  return (
    <div className="pagina">
      <EncabezadoCiudadano titulo="Demanda asistida" etiqueta="RUTA JUDICIAL" volverA="/ciudadano" />
      <div className="contenedor">
        <div className="tarjeta" style={{ flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px' }}>
          <span style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <Folio ruta="odr">{decodeURIComponent(folio)}</Folio> →
            <Folio ruta="judicial">Demanda en borrador</Folio>
          </span>
          <span className="pequeno texto-2" style={{ maxWidth: 460 }}>
            Solo se transfirieron partes, hechos y materia. Los mensajes y propuestas de la mediación no pasan al juzgado.
          </span>
        </div>

        <div className="fila">
          <section className="tarjeta" aria-labelledby="h-datos" style={{ flex: '1 1 400px', minWidth: 0 }}>
            <h2 id="h-datos" className="titulo-serif" style={{ fontSize: 24 }}>Datos del caso</h2>
            <div className="fila">
              <div className="tarjeta suave crece" style={{ padding: 14, gap: 2, minWidth: 160 }}>
                <span className="pequeno texto-2">Demandante</span><strong>Ana Pérez López</strong>
              </div>
              <div className="tarjeta suave crece" style={{ padding: 14, gap: 2, minWidth: 160 }}>
                <span className="pequeno texto-2">Demandado</span><strong>Carlos Méndez R.</strong>
              </div>
            </div>
            <div className="campo">
              <label htmlFor="dom">Domicilio del demandado <span style={{ color: 'var(--bermellon)' }}>*</span></label>
              <input id="dom" value={domicilio} onChange={(e) => setDomicilio(e.target.value)} />
              {!domicilio && <span className="error">Falta domicilio</span>}
            </div>
            <div className="campo">
              <span className="rotulo">Hechos <span className="pequeno texto-2">· desde tu orientación</span></span>
              <p className="aviso-confidencial">{hechosIniciales}</p>
            </div>
            <div className="campo">
              <label htmlFor="pre">Lo que pides al juez <span style={{ color: 'var(--bermellon)' }}>*</span></label>
              <input id="pre" value={pretension} onChange={(e) => setPretension(e.target.value)} />
            </div>
            <div className="campo">
              <label htmlFor="tipo">Tipo de juicio</label>
              <select id="tipo"><option>Oral civil</option><option>Oral mercantil</option><option>Familiar</option></select>
              <span className="ayuda" style={{ color: 'var(--laton-texto)' }}>Sugerido por IA según materia y monto</span>
            </div>
            <div className="campo">
              <label htmlFor="anexos">Pruebas y anexos · PDF o imagen</label>
              {/* TODO: subir al repositorio de objetos y registrar huella SHA-256 */}
              <input id="anexos" type="file" multiple accept="application/pdf,image/*" style={{ paddingTop: 10 }} />
            </div>
          </section>

          <section aria-labelledby="h-doc" className="columna" style={{ flex: '2 1 560px', minWidth: 0 }}>
            <CajaIA titulo="Borrador generado por IA · editable">
              <label htmlFor="borrador" id="h-doc" className="solo-lector">Borrador de demanda</label>
              <textarea id="borrador" value={borrador} onChange={(e) => setBorrador(e.target.value)} rows={18}
                style={{ width: '100%', padding: '32px 40px', border: '1px solid var(--linea)', borderRadius: 4, background: '#fff', fontFamily: 'var(--fuente-titulo)', fontSize: 17, lineHeight: 1.7 }} />
            </CajaIA>
          </section>
        </div>
      </div>

      <footer style={{ position: 'sticky', bottom: 0, background: '#fff', borderTop: '1px solid var(--linea)', padding: '16px 32px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 12, minHeight: 44 }}>
          <input type="checkbox" checked={revisado} onChange={(e) => setRevisado(e.target.checked)} style={{ width: 22, height: 22 }} />
          <span>Revisé y edité el contenido. Entiendo que <strong>la demanda no se presenta sin mi confirmación</strong>.</span>
        </label>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button type="button" className="boton secundario" onClick={regenerar}>Regenerar borrador</button>
          <button type="button" className="boton toga" disabled={!revisado || !domicilio} onClick={presentar}>Confirmar y presentar demanda</button>
        </div>
      </footer>
    </div>
  );
}

function generarBorrador(pretension: string, domicilio: string) {
  return `Ciudad de México, a [fecha]

C. JUEZ DE LO CIVIL DE PROCESO ORAL EN TURNO
P R E S E N T E

ANA PÉREZ LÓPEZ, por mi propio derecho, ante Usted comparezco para demandar de CARLOS MÉNDEZ R., con domicilio en ${domicilio || '[falta domicilio]'}, las siguientes

P R E S T A C I O N E S

A) ${pretension}.

H E C H O S

1. ${hechosIniciales}`;
}
