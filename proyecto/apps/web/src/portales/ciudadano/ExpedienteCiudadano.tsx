// Consulta del expediente por la parte (RF6) y corrección de una demanda prevenida (RF7.4).
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Cargando, Estado, Folio, MensajeError, t, tonoDe } from '@/compartido/componentes';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { judicial } from '@/compartido/servicios';
import { intentar, useDatos } from '@/compartido/servicios/useDatos';
import { ListaExpediente } from '@/portales/juez/ListaExpediente';

export default function ExpedienteCiudadano() {
  const { id = '' } = useParams();
  const { datos: e, error: errorCarga, recargar } = useDatos(() => judicial.expediente(id), [id]);
  const [texto, setTexto] = useState('');
  const [error, setError] = useState('');
  useEffect(() => { if (e) setTexto(e.texto_final ?? ''); }, [e]);

  if (!e) return <div className="pagina"><EncabezadoCiudadano titulo="Expediente" volverA="/ciudadano" />
    <div className="contenedor">{errorCarga ? <MensajeError>{errorCarga}</MensajeError> : <Cargando />}</div></div>;

  const prevencion = [...e.actuaciones].reverse().find((a) => a.tipo === 'DICTAMEN_PREVENIR');

  async function reenviar() {
    if (!confirm('¿Reenviar la demanda corregida al juzgado?')) return;
    if (await intentar(() => judicial.corregir(id, texto), setError)) recargar();
  }

  return (
    <div className="pagina">
      <EncabezadoCiudadano titulo={`Expediente ${e.numero}`} etiqueta="RUTA JUDICIAL" volverA="/ciudadano" />
      <div className="contenedor">
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <Folio ruta="judicial">EXP {e.numero}</Folio>
          <Estado tono={tonoDe(e.estado)}>{t(e.estado)}</Estado>
          <span className="texto-2">{e.partes} · {t(e.materia)}</span>
        </div>
        <MensajeError>{error}</MensajeError>
        {e.estado === 'PREVENIDO' && (
          <section className="tarjeta" aria-labelledby="h-prev">
            <h2 id="h-prev" className="titulo-serif" style={{ fontSize: 24 }}>El juzgado pide correcciones</h2>
            {prevencion?.texto && <p className="aviso-confidencial">{prevencion.texto}</p>}
            <div className="campo">
              <label htmlFor="corr">Demanda corregida</label>
              <textarea id="corr" rows={14} value={texto} onChange={(ev) => setTexto(ev.target.value)} />
            </div>
            <button type="button" className="boton toga" disabled={texto.trim().length < 100} onClick={reenviar}>Reenviar corrección</button>
          </section>
        )}
        <ListaExpediente expediente={e} alCambiar={recargar} />
      </div>
    </div>
  );
}
