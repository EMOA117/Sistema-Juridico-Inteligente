// P14 · Tablero de indicadores. Solo metadatos agregados, sin contenido confidencial.
import { useEffect, useState } from 'react';
import { Cargando } from '@/compartido/componentes';
import { analitica } from '@/compartido/servicios';
import type { indicadores as TIndicadores } from '@/compartido/datos/mock';

const meses = ['E', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S'];

export default function TableroIndicadores() {
  const [datos, setDatos] = useState<typeof TIndicadores | null>(null);
  useEffect(() => { analitica.indicadores().then(setDatos); }, []);

  if (!datos) return <Cargando />;
  const maxMateria = Math.max(...datos.porMateria.map((m) => m.total));

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 className="titulo-serif" style={{ fontSize: 40 }}>Indicadores operativos</h1>
          <span className="texto-2">Solo metadatos agregados · sin contenido confidencial</span>
        </div>
        <div className="fila" style={{ alignItems: 'flex-end' }}>
          <div className="campo"><label htmlFor="per">Periodo</label><select id="per"><option>Ene–Sep 2027</option></select></div>
          <div className="campo"><label htmlFor="mat">Materia</label><select id="mat"><option>Todas</option><option>Civil</option><option>Familiar</option><option>Mercantil</option></select></div>
          {/* TODO: GET /analitica/reportes?formato=pdf|csv */}
          <button type="button" className="boton secundario">Exportar PDF</button>
          <button type="button" className="boton secundario">CSV</button>
        </div>
      </div>

      <div className="fila">
        {datos.kpis.map((k) => (
          <div key={k.nombre} className="tarjeta kpi crece" style={{ minWidth: 180 }}>
            <span className="texto-2 pequeno">{k.nombre}</span>
            <span className="valor">{k.valor}</span>
            <span className="pequeno">{k.nota}</span>
          </div>
        ))}
      </div>

      <div className="fila">
        <section className="tarjeta" aria-labelledby="h-mat" style={{ flex: '1 1 360px' }}>
          <h2 id="h-mat" className="titulo-seccion">Conflictos por materia</h2>
          {datos.porMateria.map((m) => (
            <div key={m.materia} style={{ display: 'grid', gridTemplateColumns: '100px 1fr 48px', gap: 12, alignItems: 'center' }}>
              <span>{m.materia}</span>
              <span style={{ height: 14, background: 'var(--gris-suave)', borderRadius: 4 }}>
                <span style={{ display: 'block', height: '100%', width: `${(m.total / maxMateria) * 100}%`, background: 'var(--toga)', borderRadius: 4 }} />
              </span>
              <span className="mono">{m.total}</span>
            </div>
          ))}
        </section>

        <section className="tarjeta" aria-labelledby="h-tasa" style={{ flex: '1 1 420px' }}>
          <h2 id="h-tasa" className="titulo-seccion">Tasa de acuerdo mensual</h2>
          <Linea valores={datos.tasaMensual} />
          <div style={{ display: 'flex', justifyContent: 'space-between' }} className="mono pequeno texto-2" aria-hidden="true">
            {meses.map((m, i) => <span key={i}>{m}</span>)}
          </div>
        </section>
      </div>
    </>
  );
}

function Linea({ valores }: { valores: number[] }) {
  const min = 40, max = 70, w = 560, h = 160;
  const puntos = valores.map((v, i) => `${(i / (valores.length - 1)) * w},${h - ((v - min) / (max - min)) * h}`).join(' ');
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} role="img" aria-label={`Tasa de acuerdo mensual: ${valores.join(', ')} por ciento`} preserveAspectRatio="none">
      <polyline points={puntos} fill="none" stroke="var(--jade)" strokeWidth="2.5" strokeLinejoin="round" />
    </svg>
  );
}
