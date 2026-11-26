// P14 · Tablero de indicadores. Solo metadatos agregados, sin contenido confidencial.
import { Cargando, MensajeError, t } from '@/compartido/componentes';
import { administracion } from '@/compartido/servicios';
import { useDatos } from '@/compartido/servicios/useDatos';

export default function TableroIndicadores() {
  const { datos, error } = useDatos(() => administracion.indicadores());
  if (error) return <MensajeError>{error}</MensajeError>;
  if (!datos) return <Cargando />;
  const kpis = [
    { nombre: 'Conflictos recibidos', valor: datos.conflictos_recibidos },
    { nombre: 'Mediaciones iniciadas', valor: datos.mediaciones_iniciadas },
    { nombre: 'Tasa de acuerdo', valor: datos.tasa_acuerdo === null ? '—' : `${datos.tasa_acuerdo}%` },
    { nombre: 'Canalizados desde mediación', valor: datos.canalizados },
    { nombre: 'Expedientes', valor: datos.expedientes },
  ];
  const max = Math.max(1, ...datos.por_materia.map((m) => m.total));
  const maxE = Math.max(1, ...datos.expedientes_por_estado.map((m) => m.total));

  return (
    <>
      <div>
        <h1 className="titulo-serif" style={{ fontSize: 40 }}>Indicadores operativos</h1>
        <span className="texto-2">Solo metadatos agregados · sin contenido confidencial · datos sintéticos de demostración</span>
      </div>
      <div className="fila">
        {kpis.map((k) => (
          <div key={k.nombre} className="tarjeta kpi crece" style={{ minWidth: 180 }}>
            <span className="texto-2 pequeno">{k.nombre}</span>
            <span className="valor">{k.valor}</span>
          </div>
        ))}
      </div>
      <div className="fila">
        <Barras titulo="Conflictos por materia" filas={datos.por_materia.map((m) => ({ e: t(m.materia), n: m.total }))} max={max} color="var(--toga)" />
        <Barras titulo="Expedientes por estado" filas={datos.expedientes_por_estado.map((m) => ({ e: t(m.estado), n: m.total }))} max={maxE} color="var(--jade)" />
      </div>
    </>
  );
}

function Barras({ titulo, filas, max, color }: { titulo: string; filas: { e: string; n: number }[]; max: number; color: string }) {
  return (
    <section className="tarjeta" style={{ flex: '1 1 360px' }}>
      <h2 className="titulo-seccion">{titulo}</h2>
      {filas.length === 0 && <p className="texto-2">Sin datos.</p>}
      {filas.map((f) => (
        <div key={f.e} style={{ display: 'grid', gridTemplateColumns: '120px 1fr 48px', gap: 12, alignItems: 'center' }}>
          <span>{f.e}</span>
          <span style={{ height: 14, background: 'var(--gris-suave)', borderRadius: 4 }}>
            <span style={{ display: 'block', height: '100%', width: `${(f.n / max) * 100}%`, background: color, borderRadius: 4 }} />
          </span>
          <span className="mono">{f.n}</span>
        </div>
      ))}
    </section>
  );
}
