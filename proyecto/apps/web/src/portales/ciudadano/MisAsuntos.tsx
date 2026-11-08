// Mis asuntos: conflictos donde la persona es parte, con la acción que corresponde a su estado.
import { Link } from 'react-router-dom';
import { Cargando, Estado, Folio, MensajeError, Riel, t, tonoDe } from '@/compartido/componentes';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { conflictos, judicial, odr } from '@/compartido/servicios';
import { useSesion } from '@/compartido/servicios/sesion';
import { useDatos } from '@/compartido/servicios/useDatos';
import type { Conflicto, ExpedienteResumen, MediacionResumen } from '@/compartido/tipos';

const etapas = ['Orientación', 'Mediación', 'Decisión', 'Vía judicial', 'Concluido'];
const etapaDe: Record<string, number> = {
  CAPTURA: 0, ORIENTADO: 0, EN_MEDIACION: 1, EN_ESPERA_DECISION: 2, CANALIZADO: 3, CONCLUIDO: 4,
};

export default function MisAsuntos() {
  const { usuario } = useSesion();
  const { datos, error, cargando } = useDatos(async () => {
    const [cs, ms, es] = await Promise.all([conflictos.mios(), odr.mediaciones(), judicial.expedientes()]);
    return { cs, ms, es };
  });

  const nombre = usuario?.nombre.split(' ')[0] ?? '';
  const pendientes = datos?.cs.filter((c) => ['CAPTURA', 'ORIENTADO', 'EN_ESPERA_DECISION'].includes(c.estado) && c.soy_solicitante).length ?? 0;

  return (
    <div className="pagina">
      <EncabezadoCiudadano />
      <div className="contenedor">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 16 }}>
          <h1 className="titulo-serif" style={{ fontSize: 40 }}>
            Hola, {nombre}. <span className="texto-2" style={{ fontSize: 24 }}>
              {pendientes > 0 ? `Tienes ${pendientes} asunto(s) esperando tu decisión.` : 'No tienes decisiones pendientes.'}
            </span>
          </h1>
          <Link to="/ciudadano/orientacion" className="boton">Nuevo asunto</Link>
        </div>

        <MensajeError>{error}</MensajeError>
        {cargando && !datos && <Cargando />}
        {datos && datos.cs.length === 0 && (
          <div className="tarjeta"><p>Aún no tienes asuntos. Empieza contándonos tu conflicto.</p></div>
        )}
        <main className="columna" style={{ gap: 16 }}>
          {datos?.cs.map((c) => (
            <TarjetaAsunto key={c.id} c={c} mediacion={datos.ms.find((m) => m.conflicto_id === c.id)}
              expediente={datos.es.find((e) => e.folio === c.folio)} />
          ))}
        </main>
      </div>
    </div>
  );
}

function TarjetaAsunto({ c, mediacion, expediente }: { c: Conflicto; mediacion?: MediacionResumen; expediente?: ExpedienteResumen }) {
  const judicialRuta = c.estado === 'CANALIZADO' || !!expediente;
  return (
    <article className="tarjeta">
      <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
        <span style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <Folio ruta="odr">{c.folio}</Folio>
          {expediente && <Folio ruta="judicial">EXP {expediente.numero}</Folio>}
          <span className="texto-2">{t(c.materia)}</span>
        </span>
        <Estado tono={tonoDe(expediente?.estado ?? c.estado)}>
          {expediente ? `Expediente: ${t(expediente.estado)}` : mediacion && c.estado === 'EN_MEDIACION' ? t(mediacion.estado) : t(c.estado)}
        </Estado>
      </div>
      <h2 className="titulo-serif" style={{ fontSize: 24 }}>
        {c.soy_solicitante ? `${c.contraparte}` : `${c.solicitante}`} <span className="texto-2" style={{ fontSize: 16 }}>
          {c.soy_solicitante ? '(otra parte)' : '(te invitó)'}</span>
      </h2>
      <Riel etapas={etapas} actual={etapaDe[c.estado] ?? 0} ruta={judicialRuta ? 'judicial' : 'odr'} />
      {expediente?.estado === 'PREVENIDO' && (
        <p className="aviso-confidencial">El juzgado pidió correcciones a tu demanda. Revisa el expediente.</p>
      )}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {c.soy_solicitante && ['CAPTURA', 'ORIENTADO'].includes(c.estado) &&
          <Link className="boton" to={`/ciudadano/orientacion?conflicto=${c.id}`}>Continuar orientación</Link>}
        {mediacion && ['INVITACION_ENVIADA', 'EN_NEGOCIACION', 'CON_MEDIADOR', 'PENDIENTE_FORMALIZACION'].includes(mediacion.estado) &&
          <Link className="boton jade" to={`/ciudadano/negociacion/${mediacion.id}`}>Ir a la sala</Link>}
        {c.soy_solicitante && c.estado === 'EN_ESPERA_DECISION' &&
          <Link className="boton toga" to={`/ciudadano/demanda/${c.id}`}>Continuar a la vía judicial</Link>}
        {c.soy_solicitante && c.estado === 'CANALIZADO' && !expediente &&
          <Link className="boton toga" to={`/ciudadano/demanda/${c.id}`}>Preparar demanda</Link>}
        {expediente && <Link className="boton secundario" to={`/ciudadano/expediente/${expediente.id}`}>Ver expediente</Link>}
      </div>
    </article>
  );
}
