import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { Cargando, Estado } from '@/compartido/componentes';
import { http } from '@/compartido/servicios/api';
import { enviar, etiqueta, fecha, type AsuntoODR, type AvisoODR } from '@/compartido/servicios/odr';
import { useSesion } from '@/compartido/servicios/sesion';

export default function Asuntos() {
  const { usuario } = useSesion();
  const mediador = usuario?.rol === 'MEDIADOR';
  const [asuntos, setAsuntos] = useState<AsuntoODR[] | null>(null);
  const [avisos, setAvisos] = useState<AvisoODR[]>([]);
  const [error, setError] = useState('');
  async function cargar() {
    try {
      const [a, n] = await Promise.all([http<AsuntoODR[]>('/conflictos/mios'), http<AvisoODR[]>('/notificaciones')]);
      setAsuntos(a); setAvisos(n); setError('');
    } catch (e) { setError((e as Error).message); }
  }
  useEffect(() => { void cargar(); }, []);
  async function leer(id: string) {
    try { await enviar(`/notificaciones/${id}/leer`); await cargar(); } catch(e) { setError((e as Error).message); }
  }
  return <div className="pagina">{!mediador && <EncabezadoCiudadano />}
    <div className="contenedor">
      <div className="fila odr-entre"><div><p className="titulo-seccion">{mediador ? 'Mediación asignada' : 'Portal ciudadano'} · ODR</p><h1 className="titulo-serif">Hola, {usuario?.nombre.split(' ')[0]}</h1></div>
        {!mediador && <Link className="boton jade" to="/ciudadano/orientacion">Nuevo asunto</Link>}<button className="boton secundario" onClick={cargar}>Actualizar</button></div>
      <p className="aviso-confidencial">Demostración con datos sintéticos. Los avisos están disponibles en esta plataforma; no se envían correos externos en esta iteración.</p>
      {error && <div role="alert" className="tarjeta"><p>{error}</p><button className="boton secundario" onClick={cargar}>Reintentar</button></div>}
      <div className="fila"><main className="columna" style={{flex:'2 1 540px'}}>
        {!asuntos && !error && <Cargando />}
        {asuntos?.length === 0 && <div className="tarjeta"><h2>{mediador ? 'No tienes mediaciones asignadas' : 'Tus acuerdos empiezan aquí'}</h2><p>{mediador ? 'Cuando una parte solicite intervención, el sistema asignará un mediador disponible.' : 'Registra las partes y describe un conflicto para elegir la ruta de atención.'}</p></div>}
        {asuntos?.map(a => <article key={a.id} className="tarjeta">
          <div className="fila odr-entre"><span className="mono pequeno">{a.id.slice(0,8).toUpperCase()} · {a.materia ?? 'Por orientar'}</span><Estado tono={a.estado === 'CONCLUIDO' ? 'aceptada' : 'pendiente'}>{etiqueta(a.estado)}</Estado></div>
          <h2 className="titulo-serif">{a.titulo}</h2><p className="texto-2">{a.estado_mediacion ? etiqueta(a.estado_mediacion) : 'Captura y orientación'}{a.resultado ? ` · ${etiqueta(a.resultado)}` : ''}</p>
          <Link className="boton jade" to={mediador ? `/mediador/negociacion/${a.id}` : a.estado === 'CAPTURA' && a.solicitante_id === usuario?.id ? `/ciudadano/orientacion?asunto=${a.id}` : `/ciudadano/negociacion/${a.id}`}>Abrir asunto</Link>
        </article>)}
      </main>{!mediador && <aside className="tarjeta" style={{flex:'1 1 300px'}}><h2 className="titulo-seccion">Notificaciones</h2>
        {!avisos.length && <p className="texto-2">Sin actividad reciente.</p>}
        {avisos.map(n => <div key={n.id} className="columna odr-aviso"><Link to={`/ciudadano/negociacion/${n.conflicto_id}`}>{etiqueta(n.evento)}</Link><span className="pequeno texto-2">{fecha(n.creado_en)}</span>{!n.leida && <button className="boton secundario" onClick={() => leer(n.id)}>Marcar como leída</button>}</div>)}
      </aside>}</div>
    </div></div>;
}
