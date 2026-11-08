// P5 / P13 · Consulta de convenio PDF y vista previa del aviso por correo.
// El PDF real lo genera core-api; aquí solo se muestra la vista previa.
import { useParams } from 'react-router-dom';
import { Folio } from '@/compartido/componentes';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { useSesion } from '@/compartido/servicios/sesion';

export default function Convenio() {
  const { folio = '' } = useParams();
  const { usuario } = useSesion();
  const f = decodeURIComponent(folio);

  return (
    <div className="pagina">
      <EncabezadoCiudadano titulo="Convenio y notificaciones" etiqueta="RUTA ODR" volverA="/ciudadano" />
      <div className="contenedor">
        <div className="fila">
          <section className="columna" aria-labelledby="h-mail" style={{ flex: '1 1 380px' }}>
            <h2 id="h-mail" className="titulo-seccion">Notificación por correo · P13</h2>
            <div className="tarjeta">
              <span className="pequeno texto-2">Para: {usuario?.correo}</span>
              <strong>Hay una actualización en tu asunto {f}</strong>
              <Folio ruta="odr">{f}</Folio>
              <p>Entra a la plataforma para consultarla. Por tu privacidad, este correo no incluye el contenido de mensajes, propuestas ni resoluciones.</p>
              <p className="pequeno texto-2">Nunca te pediremos tu contraseña por correo.</p>
            </div>
          </section>

          <section className="columna" aria-labelledby="h-conv" style={{ flex: '2 1 560px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <h2 id="h-conv" className="titulo-seccion">Convenio de mediación · P5</h2>
              {/* TODO: GET /convenios/{folio}/pdf */}
              <button type="button" className="boton secundario" onClick={() => window.print()}>Descargar PDF</button>
            </div>
            <article className="tarjeta" style={{ fontFamily: 'var(--fuente-titulo)', fontSize: 17, padding: '40px 48px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                <span><span className="mono pequeno">CENTRO DE JUSTICIA ALTERNATIVA</span><h3 style={{ fontSize: 28, fontWeight: 500 }}>Convenio de mediación</h3></span>
                <span className="mono pequeno">{f}<br />ACUERDO PARCIAL</span>
              </div>
              <p><strong>ANA PÉREZ LÓPEZ</strong>, «la Acreedora», y <strong>CARLOS MÉNDEZ R.</strong>, «el Deudor», con la intervención de la mediadora certificada Lic. Mariana Soto.</p>
              <p><strong>Primera.</strong> El Deudor reconoce adeudar a la Acreedora la cantidad de $15,000.00.</p>
              <p><strong>Segunda.</strong> El Deudor pagará $10,000.00 a la firma y $5,000.00 a más tardar el 20 de enero de 2028.</p>
              <p><strong>Tercera.</strong> La Acreedora expedirá recibo firmado por cada pago recibido.</p>
              <div className="aviso-confidencial" style={{ fontFamily: 'var(--fuente-ui)' }}>
                <span><strong>Punto pendiente · canalizable a vía judicial:</strong> pago de intereses moratorios generados desde el vencimiento original.</span>
              </div>
              <span className="mono pequeno texto-2">SHA-256 [huella] · Resguardo inmutable (WORM)</span>
            </article>
          </section>
        </div>
      </div>
    </div>
  );
}
