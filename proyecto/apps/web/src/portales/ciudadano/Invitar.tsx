// P3 / RF3.7 · Invitar a la contraparte a mediar, con plazo de respuesta configurable.
import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AvisoConfidencial, MensajeError } from '@/compartido/componentes';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { conflictos } from '@/compartido/servicios';

export default function Invitar() {
  const { conflictoId = '' } = useParams();
  const navegar = useNavigate();
  const [nombre, setNombre] = useState('');
  const [correo, setCorreo] = useState('');
  const [plazo, setPlazo] = useState(10);
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    conflictos.detalle(conflictoId).then((c) => {
      const otra = c.partes.find((p) => p.rol === 'DEMANDADO');
      setNombre(otra?.nombre ?? '');
      setCorreo(otra?.correo ?? '');
    }).catch((e) => setError(e.message));
  }, [conflictoId]);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!confirm(`¿Enviar la invitación a ${correo}?`)) return;
    setEnviando(true);
    try {
      const r = await conflictos.invitar(conflictoId, correo, plazo);
      navegar(`/ciudadano/negociacion/${r.mediacion_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo enviar la invitación.');
      setEnviando(false);
    }
  }

  return (
    <div className="pagina">
      <EncabezadoCiudadano titulo="Invitar a mediar" etiqueta="RUTA ODR" volverA="/ciudadano" />
      <form className="contenedor" style={{ maxWidth: 720 }} onSubmit={enviar}>
        <h1 className="titulo-serif" style={{ fontSize: 32 }}>Invita a {nombre || 'la otra parte'} a resolverlo en línea</h1>
        <MensajeError>{error}</MensajeError>
        <div className="tarjeta">
          <div className="campo">
            <label htmlFor="inv-correo">Correo de {nombre || 'la otra parte'}</label>
            <input id="inv-correo" type="email" value={correo} onChange={(e) => setCorreo(e.target.value)} />
            <span className="ayuda">Recibirá un enlace personal. Para aceptar deberá crear su cuenta o iniciar sesión.</span>
          </div>
          <div className="campo">
            <label htmlFor="inv-plazo">Plazo para responder (días)</label>
            <input id="inv-plazo" type="number" min={3} max={30} value={plazo} onChange={(e) => setPlazo(Number(e.target.value))} />
            <span className="ayuda">Si no responde a tiempo, podrás continuar por la vía judicial.</span>
          </div>
          <AvisoConfidencial>El correo solo dice que tienes un asunto pendiente con ella; no incluye lo que nos contaste.</AvisoConfidencial>
          <button type="submit" className="boton jade" disabled={enviando || !correo || plazo < 3 || plazo > 30}>Enviar invitación</button>
        </div>
      </form>
    </div>
  );
}
