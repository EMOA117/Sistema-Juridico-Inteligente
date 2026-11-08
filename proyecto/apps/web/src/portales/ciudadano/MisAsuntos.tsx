// Mis asuntos y notificaciones del ciudadano.
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Cargando, Estado, Folio, IconoCampana, Riel } from '@/compartido/componentes';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { ciudadano } from '@/compartido/servicios';
import { useSesion } from '@/compartido/servicios/sesion';
import type { Actividad, Asunto } from '@/compartido/tipos';

export default function MisAsuntos() {
  const { usuario } = useSesion();
  const [asuntos, setAsuntos] = useState<Asunto[] | null>(null);
  const [actividad, setActividad] = useState<Actividad[]>([]);

  useEffect(() => {
    ciudadano.misAsuntos().then(setAsuntos);
    ciudadano.actividad().then(setActividad);
  }, []);

  const nombre = usuario?.nombre.split(' ')[0] ?? '';
  const pendientes = asuntos?.filter((a) => a.aviso).length ?? 0;

  return (
    <div className="pagina">
      <EncabezadoCiudadano derecha={
        <button type="button" className="boton secundario" style={{ minHeight: 40 }} aria-label={`Notificaciones, ${actividad.length} sin leer`}>
          <IconoCampana />{actividad.length}
        </button>
      } />
      <div className="contenedor">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 16 }}>
          <h1 className="titulo-serif" style={{ fontSize: 40 }}>
            Hola, {nombre}. <span className="texto-2" style={{ fontSize: 24 }}>
              {pendientes > 0 ? `Tienes ${pendientes} asunto(s) esperando tu respuesta.` : 'No tienes pendientes.'}
            </span>
          </h1>
          <Link to="/ciudadano/orientacion" className="boton">Nuevo asunto</Link>
        </div>

        <div className="fila">
          <main className="columna" style={{ flex: '2 1 560px', minWidth: 0, gap: 16 }}>
            {!asuntos && <Cargando />}
            {asuntos?.map((a) => <TarjetaAsunto key={a.id} asunto={a} />)}
          </main>

          <aside className="tarjeta" aria-labelledby="h-act" style={{ flex: '1 1 320px' }}>
            <h2 id="h-act" className="titulo-seccion">Actividad reciente</h2>
            <ol className="lista-tiempo">
              {actividad.map((n) => (
                <li key={n.titulo}>
                  <span className="columna" style={{ gap: 0 }}>
                    <strong>{n.titulo}</strong>
                    {n.detalle && <span className="texto-2">{n.detalle}</span>}
                    <span className="mono pequeno texto-2">{n.referencia}</span>
                  </span>
                </li>
              ))}
            </ol>
            <p className="pequeno texto-2">También te avisamos por correo a <strong>{usuario?.correo}</strong>.</p>
          </aside>
        </div>
      </div>
    </div>
  );
}

function TarjetaAsunto({ asunto: a }: { asunto: Asunto }) {
  const folioUrl = encodeURIComponent(a.folio);
  return (
    <article className="tarjeta">
      <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
        <span style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <Folio ruta={a.ruta}>{a.folio}</Folio>
          <span className="texto-2">{a.materia}</span>
        </span>
        <Estado tono={a.ruta === 'odr' ? (a.estadoTexto.includes('firmado') ? 'aceptada' : 'pendiente') : 'rechazada'}>{a.estadoTexto}</Estado>
      </div>
      <h2 className="titulo-serif" style={{ fontSize: 24 }}>{a.titulo}</h2>
      {a.ruta === 'odr' && a.estadoTexto === 'En negociación' && (
        <Riel etapas={['Orientación', 'Invitación', 'Negociación', 'Convenio']} actual={2} />
      )}
      {a.aviso && <p className="aviso-confidencial">{a.aviso}</p>}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {a.estadoTexto === 'En negociación' && <Link className="boton jade" to={`/ciudadano/negociacion/${folioUrl}`}>Ir a la sala</Link>}
        {a.ruta === 'judicial' && <Link className="boton toga" to={`/ciudadano/demanda/${folioUrl}`}>Corregir demanda</Link>}
        {a.estadoTexto === 'Convenio firmado' && <Link className="boton secundario" to={`/ciudadano/convenio/${folioUrl}`}>Ver convenio</Link>}
      </div>
    </article>
  );
}
