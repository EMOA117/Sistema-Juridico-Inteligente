// P4 · Portal del mediador. La gestión completa (asignación, agenda, notas, conclusión) se agrega con mediadores.
import { Link } from 'react-router-dom';
import { Cargando, Estado, MensajeError, t, tonoDe } from '@/compartido/componentes';
import { odr } from '@/compartido/servicios';
import { useDatos } from '@/compartido/servicios/useDatos';

export default function PortalMediador() {
  const { datos, error } = useDatos(() => odr.mediaciones());
  return (
    <>
      <h1 className="titulo-serif" style={{ fontSize: 40 }}>Mis mediaciones</h1>
      <MensajeError>{error}</MensajeError>
      {!datos ? <Cargando /> : datos.length === 0 ? <p className="tarjeta texto-2">No tienes mediaciones asignadas.</p> :
        datos.map((m) => (
          <Link key={m.id} to={`/mediador/${m.id}`} className="tarjeta" style={{ textDecoration: 'none', color: 'inherit' }}>
            <span style={{ display: 'flex', justifyContent: 'space-between' }}><span className="mono">{m.folio}</span><Estado tono={tonoDe(m.estado)}>{t(m.estado)}</Estado></span>
            <strong>{m.partes} · {t(m.materia)}</strong>
          </Link>
        ))}
    </>
  );
}
