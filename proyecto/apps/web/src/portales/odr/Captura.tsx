import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { Riel } from '@/compartido/componentes';
import { cargarODR, enviar } from '@/compartido/servicios/odr';
import { useSesion } from '@/compartido/servicios/sesion';

export default function Captura() {
  const { usuario } = useSesion();
  const navegar = useNavigate();
  const [params] = useSearchParams();
  const [id, setId] = useState(params.get('asunto'));
  const [paso, setPaso] = useState(id ? 1 : 0);
  const [datos, setDatos] = useState<Record<string,string>>({titulo:'',nombre:usuario?.nombre ?? '',correo:usuario?.correo ?? '',domicilio:'',otroNombre:'',otroCorreo:'',otroDomicilio:''});
  const [error, setError] = useState('');
  const [ocupado, setOcupado] = useState(false);
  useEffect(() => {
    if (id) cargarODR(id).then(d => {
      if (d.conflicto.estado !== 'CAPTURA') navegar(`/ciudadano/negociacion/${id}`, { replace:true });
      setDatos(prev => ({...prev,titulo:d.conflicto.titulo}));
    }).catch(e => setError(e.message));
  }, [id, navegar]);
  async function partes(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setError(''); setOcupado(true);
    try {
      const result = await enviar<{id:string}>('/conflictos', {titulo:datos.titulo,
        demandante:{nombre:datos.nombre,correo:datos.correo,domicilio_notificaciones:datos.domicilio},
        demandado:{nombre:datos.otroNombre,correo:datos.otroCorreo,domicilio_notificaciones:datos.otroDomicilio}});
      setId(result.id); setPaso(1); navegar(`/ciudadano/orientacion?asunto=${result.id}`,{replace:true});
    } catch(e) { setError((e as Error).message); } finally { setOcupado(false); }
  }
  async function orientar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); const f=new FormData(e.currentTarget); setOcupado(true); setError('');
    try {
      await enviar(`/conflictos/${id}/orientacion`, {narrativa:f.get('narrativa'),materia:f.get('materia'),mediable:f.get('mediable')==='si',confirmacion:true});
      navegar(`/ciudadano/negociacion/${id}`);
    } catch(e) { setError((e as Error).message); } finally { setOcupado(false); }
  }
  const campo=(clave:string,titulo:string,tipo='text',min=2) => <div className="campo" key={clave}><label htmlFor={clave}>{titulo}</label><input id={clave} type={tipo} required minLength={min} maxLength={clave.toLowerCase().includes('domicilio') ? 500 : 160} value={datos[clave]} readOnly={clave==='correo'} onChange={e=>setDatos({...datos,[clave]:e.target.value})}/></div>;
  return <div className="pagina"><EncabezadoCiudadano titulo="Nuevo asunto" volverA="/ciudadano"/><main className="contenedor odr-estrecho">
    <h1 className="titulo-serif">Cuéntanos qué ocurre</h1><Riel etapas={['Identificar partes','Relato y orientación','Elegir ruta']} actual={paso}/>
    {error && <p role="alert" className="odr-error">{error}</p>}
    {paso===0 ? <form className="tarjeta" onSubmit={partes}><h2>Primero, las partes</h2>{campo('titulo','Título del asunto','text',5)}
      <div className="odr-dos"><fieldset><legend>Solicitante</legend>{campo('nombre','Tu nombre')}{campo('correo','Tu correo','email')}{campo('domicilio','Domicilio para notificaciones','text',5)}</fieldset>
      <fieldset><legend>Contraparte</legend>{campo('otroNombre','Nombre de la contraparte')}{campo('otroCorreo','Correo de la contraparte','email')}{campo('otroDomicilio','Domicilio de la contraparte','text',5)}</fieldset></div>
      <p className="texto-2">Usa datos inventados. La contraparte necesitará una cuenta con el correo indicado para consultar y responder la invitación.</p><button className="boton jade" disabled={ocupado}>Guardar partes y continuar</button></form>
    : <form className="tarjeta" onSubmit={orientar}><h2>{datos.titulo}</h2><div className="campo"><label htmlFor="narrativa">Describe los hechos iniciales</label><textarea id="narrativa" name="narrativa" required minLength={30} maxLength={10000} rows={7}/></div>
      <p className="aviso-confidencial">Orientación manual de demostración. Esta iteración no clasifica jurídicamente mediante IA. La materia y la posibilidad de mediar deben revisarse antes de usar casos reales.</p>
      <div className="campo"><label htmlFor="materia">Materia del escenario sintético</label><select id="materia" name="materia"><option value="CIVIL">Civil</option><option value="FAMILIAR">Familiar</option></select></div>
      <div className="campo"><label htmlFor="mediable">¿El escenario permite mediación voluntaria?</label><select name="mediable" id="mediable"><option value="si">Sí, explorar mediación</option><option value="no">No, mostrar vía judicial</option></select></div>
      <label className="odr-check"><input type="checkbox" required/>Revisé la información y confirmo que este es un escenario sintético.</label>
      <button className="boton jade" disabled={ocupado}>Guardar orientación y elegir ruta</button></form>}
  </main></div>;
}
