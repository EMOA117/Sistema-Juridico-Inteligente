// Línea de tiempo del expediente: historial de estados, actuaciones y documentos con su huella SHA-256.
import { t } from '@/compartido/componentes';
import type { Expediente } from '@/compartido/tipos';

const textoActuacion: Record<string, string> = {
  DICTAMEN_ADMITIR: 'Demanda admitida', DICTAMEN_PREVENIR: 'Demanda prevenida', DICTAMEN_DESECHAR: 'Demanda desechada',
  CORRECCION: 'Corrección presentada', NOTA: 'Nota',
};

export function ListaExpediente({ expediente: e }: { expediente: Expediente }) {
  const eventos = [
    ...e.historial.map((h) => ({ fecha: h.ocurrido_en, titulo: `${t(h.estado_anterior)} → ${t(h.estado_nuevo)}`, detalle: '' })),
    ...e.actuaciones.map((a) => ({ fecha: a.ocurrido_en, titulo: textoActuacion[a.tipo] ?? a.tipo, detalle: a.texto ?? '' })),
  ].sort((a, b) => a.fecha.localeCompare(b.fecha));

  return (
    <div className="fila">
      <section className="tarjeta" aria-labelledby="h-linea" style={{ flex: '1 1 360px' }}>
        <h3 id="h-linea" className="titulo-seccion">Línea de tiempo</h3>
        <ol className="lista-tiempo">
          <li><span><strong>Expediente creado</strong><br /><span className="pequeno texto-2">{new Date(e.creado_en).toLocaleString('es-MX')} · origen: {t(e.origen)}</span></span></li>
          {eventos.map((ev, i) => (
            <li key={i}><span><strong>{ev.titulo}</strong>{ev.detalle && <><br /><span className="pequeno">{ev.detalle}</span></>}
              <br /><span className="pequeno texto-2">{new Date(ev.fecha).toLocaleString('es-MX')}</span></span></li>
          ))}
        </ol>
      </section>
      <section className="tarjeta" aria-labelledby="h-docs" style={{ flex: '1 1 360px' }}>
        <h3 id="h-docs" className="titulo-seccion">Documentos</h3>
        {e.documentos.length === 0 && <p className="texto-2">Sin documentos digitales todavía.</p>}
        {e.documentos.map((d) => (
          <div key={d.id} className="columna" style={{ gap: 2 }}>
            <a href={`/api/documentos/${d.id}`} target="_blank" rel="noreferrer">{d.nombre}</a>
            <span className="mono pequeno texto-2">{t(d.tipo)} · SHA-256 {d.hash_sha256.slice(0, 8)}…{d.hash_sha256.slice(-4)}</span>
          </div>
        ))}
      </section>
    </div>
  );
}
