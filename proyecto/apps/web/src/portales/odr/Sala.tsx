import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AvisoConfidencial, Cargando, Estado, Riel } from '@/compartido/componentes';
import { EncabezadoCiudadano } from '@/compartido/componentes/Layouts';
import { http } from '@/compartido/servicios/api';
import { cargarODR, descargarConvenio, enviar, etiqueta, fecha, type DetalleODR, type ConvenioODR } from '@/compartido/servicios/odr';
import { useSesion } from '@/compartido/servicios/sesion';

type Accion = (trabajo: () => Promise<unknown>, aviso?: string) => Promise<boolean>;

export default function Sala() {
  const { folio: id = '' } = useParams();
  const { usuario } = useSesion();
  const mediador = usuario?.rol === 'MEDIADOR';
  const [detalle, setDetalle] = useState<DetalleODR | null>(null);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const [mensaje, setMensaje] = useState('');
  const [contra, setContra] = useState('');
  const [sugerencia, setSugerencia] = useState<{texto:string;fuente:string|null} | null>(null);
  const [borrador, setBorrador] = useState<{id:string;origen:string;narrativa_inicial:string;materia:string;puntos_pendientes:string[]|null} | null>(null);
  const recargar = useCallback(async () => { setDetalle(await cargarODR(id)); }, [id]);
  useEffect(() => {
    let vigente = true;
    const consultar = () => cargarODR(id).then(d => { if(vigente) setDetalle(d); }).catch(e => { if(vigente) setError(e.message); });
    void consultar();
    const timer = window.setInterval(() => { if(!document.hidden) void consultar(); }, 5000);
    return () => { vigente=false; clearInterval(timer); };
  }, [id]);
  const actuar: Accion = async (trabajo, texto = 'Cambios guardados.') => {
    setOcupado(true); setError(''); setAviso('');
    try { await trabajo(); await recargar(); setAviso(texto); return true; }
    catch(e) { setError((e as Error).message); return false; }
    finally { setOcupado(false); }
  };
  function confirmado(texto:string, trabajo:()=>Promise<unknown>) {
    if(window.confirm(texto)) void actuar(trabajo);
  }
  const comando = (ruta:string, datos:unknown={}) => enviar(`/odr/${id}/${ruta}`,datos);
  async function enviarMensaje(e:FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if(await actuar(() => comando('mensajes',{texto:mensaje}),'Mensaje enviado.')) setMensaje('');
  }
  async function propuesta(e:FormEvent<HTMLFormElement>) {
    e.preventDefault(); const form=e.currentTarget; const f=new FormData(form);
    if(await actuar(() => comando('propuestas',{texto:f.get('texto'),monto:f.get('monto') || null,responde_a_id:contra || null}))) { form.reset(); setContra(''); }
  }
  async function programar(e:FormEvent<HTMLFormElement>) {
    e.preventDefault(); const form=e.currentTarget; const f=new FormData(form);
    if(await actuar(() => comando('sesiones',{fecha_hora:new Date(String(f.get('fecha'))).toISOString(),enlace:f.get('enlace')}))) form.reset();
  }
  async function nota(e:FormEvent<HTMLFormElement>, sid:string) {
    e.preventDefault(); const form=e.currentTarget; const f=new FormData(form);
    if(await actuar(() => comando(`sesiones/${sid}/notas`,{texto:f.get('texto')}))) form.reset();
  }
  const c=detalle?.conflicto, m=detalle?.mediacion;
  const negociando=m?.estado==='EN_NEGOCIACION';
  const autor=(uid:string) => uid===usuario?.id ? 'Tú' : detalle?.partes.find(p=>p.usuario_id===uid)?.nombre ?? 'Mediador asignado';
  const contraparte=detalle?.partes.some(p=>p.rol==='DEMANDADO' && p.usuario_id===usuario?.id);
  const solicitante=c?.solicitante_id===usuario?.id;
  const base=mediador ? '/mediador' : '/ciudadano';
  return <div className="pagina">{!mediador && <EncabezadoCiudadano titulo="Sala de mediación" volverA={base}/>}
    <main className="contenedor">
      {mediador && <Link to={base}>← Mis mediaciones</Link>}
      <div className="odr-mensajes-estado" aria-live="polite">{error && <p role="alert" className="odr-error">{error}</p>}{aviso && <p role="status" className="aviso-confidencial">{aviso}</p>}</div>
      {!detalle ? <>{!error && <Cargando/>}<button className="boton secundario" onClick={()=>actuar(recargar,'Información actualizada.')}>Reintentar</button></> : <>
        <div className="fila odr-entre"><div><p className="mono pequeno">ASUNTO {id.slice(0,8).toUpperCase()} · {c?.materia ?? 'Captura'}</p><h1 className="titulo-serif">{c?.titulo}</h1></div><Estado tono={c?.estado==='CONCLUIDO'?'aceptada':'pendiente'}>{etiqueta(c?.estado ?? '')}</Estado></div>
        <AvisoConfidencial>Solo las partes y el mediador asignado pueden consultar esta sala. Los mensajes, propuestas y notas no se transfieren al proceso judicial.</AvisoConfidencial>
        <p className="pequeno texto-2">Demostración académica · Se actualiza cada 5 segundos · {detalle.partes.map(p=>p.nombre).join(' / ')}</p>
        <Riel etapas={['Orientación','Invitación','Negociación','Convenio']} actual={!m ? 0 : m.estado==='INVITACION_ENVIADA' ? 1 : m.estado==='EN_NEGOCIACION' ? 2 : 3}/>
        {c?.estado==='CAPTURA' && <div className="tarjeta"><h2>Captura pendiente</h2>{solicitante ? <Link className="boton" to={`/ciudadano/orientacion?asunto=${id}`}>Completar orientación</Link> : <p>El solicitante debe completar el relato inicial.</p>}</div>}
        {c?.estado==='ORIENTADO' && <section className="tarjeta"><h2>Elige cómo continuar</h2><p className="odr-texto">{c.narrativa_inicial}</p>
          {solicitante ? <>{c.mediable ? <form onSubmit={e=>{e.preventDefault(); const f=new FormData(e.currentTarget); void actuar(()=>enviar(`/conflictos/${id}/invitacion`,{plazo_dias:Number(f.get('dias'))}),'Invitación registrada. Comparte el enlace de esta sala con la contraparte.');}}>
            <div className="campo"><label htmlFor="dias">Días naturales para responder (1 a 30)</label><input id="dias" name="dias" type="number" min={1} max={30} defaultValue={7} required/></div><button className="boton jade" disabled={ocupado}>Invitar a mediación</button></form> : <p>Este escenario se registró como no mediable. Puedes solicitar la vía judicial.</p>}
          <button className="boton secundario" disabled={ocupado} onClick={()=>confirmado('¿Crear un borrador judicial con las partes y los hechos iniciales?',()=>enviar(`/conflictos/${id}/canalizar`,{confirmacion:true},'POST',true))}>Solicitar vía judicial</button></> : <p>El solicitante debe elegir la ruta.</p>}
        </section>}
        {m?.estado==='INVITACION_ENVIADA' && <section className="tarjeta"><h2>Invitación pendiente</h2><p>Fecha límite inclusiva: <strong>{detalle.invitacion?.fecha_limite}</strong> (Ciudad de México). La contraparte debe iniciar sesión con su correo registrado.</p>
          <label className="campo">Enlace para compartir<input readOnly value={`${window.location.origin}/ciudadano/negociacion/${id}`} onFocus={e=>e.target.select()}/></label>
          {contraparte && <div className="fila"><button className="boton jade" disabled={ocupado} onClick={()=>confirmado('¿Aceptas participar voluntariamente en la mediación?',()=>comando('invitacion/responder',{aceptar:true}))}>Aceptar invitación</button><button className="boton secundario" disabled={ocupado} onClick={()=>confirmado('¿Rechazar la invitación? El conflicto seguirá abierto.',()=>comando('invitacion/responder',{aceptar:false}))}>Rechazar invitación</button></div>}
        </section>}
        {m && m.estado!=='INVITACION_ENVIADA' && <div className="odr-dos odr-sala">
          <section className="tarjeta"><h2>Conversación confidencial</h2><div className="odr-chat" role="log" aria-label="Mensajes de mediación">
            {!detalle.mensajes.length && <p className="texto-2">Aún no hay mensajes. Escucha a la otra parte y comparte una propuesta concreta.</p>}
            {detalle.mensajes.map(msg=><article key={msg.id} className={`odr-burbuja ${msg.autor_id===usuario?.id?'propia':''}`}><strong>{autor(msg.autor_id)}</strong><p className="odr-texto">{msg.texto}</p><time className="pequeno texto-2">{fecha(msg.creado_en)}</time></article>)}
          </div>{negociando && <form onSubmit={enviarMensaje} className="columna"><label htmlFor="mensaje">Tu mensaje</label><textarea id="mensaje" required maxLength={10000} value={mensaje} onChange={e=>setMensaje(e.target.value)} rows={3}/><button className="boton jade" disabled={ocupado || !mensaje.trim()}>Enviar mensaje</button></form>}</section>
          <section className="tarjeta"><h2>Propuestas y contrapropuestas</h2>
            {!detalle.propuestas.length && <p className="texto-2">Todavía no hay propuestas.</p>}
            {detalle.propuestas.map((p,i)=><article className="odr-propuesta columna" key={p.id}><div className="fila odr-entre"><strong>Propuesta {i+1} · {autor(p.autor_id)}</strong><Estado tono={p.estado==='ACEPTADA'?'aceptada':p.estado==='RECHAZADA'?'rechazada':'pendiente'}>{etiqueta(p.estado)}</Estado></div>
              {p.responde_a_id && <p className="pequeno">Responde a propuesta {detalle.propuestas.findIndex(x=>x.id===p.responde_a_id)+1}</p>}<p className="odr-texto">{p.texto}</p>{p.monto && <p className="mono">Monto propuesto: ${p.monto} MXN</p>}
              {negociando && !mediador && p.autor_id!==usuario?.id && <div className="fila">{p.estado==='PENDIENTE' && <><button className="boton jade" disabled={ocupado} onClick={()=>confirmado('¿Aceptar esta propuesta? El convenio requerirá revisión y aceptación por separado.',()=>comando(`propuestas/${p.id}/responder`,{estado:'ACEPTADA'}))}>Aceptar propuesta</button><button className="boton secundario" disabled={ocupado} onClick={()=>actuar(()=>comando(`propuestas/${p.id}/responder`,{estado:'RECHAZADA'}))}>Rechazar</button></>}<button className="boton secundario" onClick={()=>setContra(p.id)}>Contraproponer</button></div>}
            </article>)}
            {negociando && !mediador && <form className="columna" onSubmit={propuesta}><h3>{contra?'Nueva contrapropuesta':'Nueva propuesta'}</h3>{contra && <button type="button" className="boton secundario" onClick={()=>setContra('')}>Cancelar contrapropuesta</button>}
              <div className="campo"><label htmlFor="propuesta">Términos propuestos</label><textarea id="propuesta" name="texto" required maxLength={10000} rows={3}/></div><div className="campo"><label htmlFor="monto">Monto en MXN (opcional)</label><input id="monto" name="monto" type="number" min="0" max="999999999999.99" step="0.01"/></div><button className="boton jade" disabled={ocupado}>Enviar propuesta</button></form>}
          </section>
        </div>}
        {negociando && <section className="tarjeta"><h2>Apoyo para avanzar</h2><p>{m?.mediador_id ? 'Mediador asignado. Puede leer la negociación y programar sesiones.' : m?.solicitud_mediador_en ? 'Solicitud registrada. No había mediadores disponibles; puedes volver a solicitar la asignación.' : 'Cualquiera de las partes puede solicitar un mediador.'}</p>
          <div className="fila">{!mediador && !m?.mediador_id && <button className="boton secundario" disabled={ocupado} onClick={()=>actuar(()=>comando('solicitar-mediador'))}>Solicitar mediador</button>}
            <button className="boton secundario" disabled={ocupado} onClick={()=>actuar(async()=>setSugerencia(await http(`/odr/${id}/recomendacion`)),'Ejemplo consultado.')}>Consultar ejemplo sintético</button></div>
          {sugerencia && <div className="odr-ejemplo"><strong>Ejemplo de demostración · Recuperación por palabras, sin IA jurídica</strong><p>{sugerencia.texto}</p>{sugerencia.fuente && <p className="mono pequeno">Fuente sintética: {sugerencia.fuente}. Requiere revisión humana.</p>}</div>}
        </section>}
        {(detalle.sesiones.length>0 || (mediador && negociando)) && <section className="tarjeta"><h2>Sesiones de mediación</h2>
          {detalle.sesiones.map(s=><article className="columna odr-propuesta" key={s.id}><strong>{fecha(s.fecha_hora)}</strong><a href={s.enlace} target="_blank" rel="noreferrer">Abrir sala virtual</a>
            {mediador && <>{detalle.notas.filter(n=>n.sesion_id===s.id).map(n=><p key={n.id} className="odr-texto">Nota privada: {n.texto}</p>)}{negociando && <form className="columna" onSubmit={e=>nota(e,s.id)}><label htmlFor={`nota-${s.id}`}>Nota privada del mediador</label><textarea id={`nota-${s.id}`} name="texto" required maxLength={10000}/><button className="boton secundario" disabled={ocupado}>Guardar nota</button></form>}</>}
          </article>)}
          {mediador && negociando && <form className="columna" onSubmit={programar}><div className="campo"><label htmlFor="fecha-sesion">Fecha y hora local</label><input id="fecha-sesion" name="fecha" type="datetime-local" required/></div><div className="campo"><label htmlFor="enlace-sesion">Enlace HTTPS de la sala</label><input id="enlace-sesion" name="enlace" type="url" pattern="https://.*" required maxLength={500}/></div><button className="boton jade" disabled={ocupado}>Programar sesión</button></form>}
        </section>}
        {(negociando || detalle.convenio) && <PanelConvenio key={detalle.convenio?.hash_sha256 ?? 'nuevo'} id={id} convenio={detalle.convenio} usuarioId={usuario?.id ?? ''} autor={autor} ocupado={ocupado} actuar={actuar}/>}
        {(negociando || m?.estado==='INVITACION_ENVIADA') && <section className="tarjeta"><h2>Concluir sin convenio</h2><p>El conflicto permanecerá abierto para que el solicitante decida si continúa judicialmente.</p><div className="fila">
          {!mediador && <button className="boton secundario" disabled={ocupado} onClick={()=>confirmado('¿Desistir de la mediación? No equivale a resolver el conflicto.',()=>comando('concluir',{resultado:'DESISTIMIENTO',confirmacion:true}))}>Desistir de la mediación</button>}
          {mediador && <button className="boton secundario" disabled={ocupado} onClick={()=>confirmado('¿Registrar conclusión sin acuerdo?',()=>comando('concluir',{resultado:'SIN_ACUERDO',confirmacion:true}))}>Registrar sin acuerdo</button>}
        </div></section>}
        {c?.estado==='EN_ESPERA_DECISION' && <section className="tarjeta"><h2>El conflicto sigue abierto</h2><p>Resultado: {etiqueta(m?.resultado ?? '')}. Solo se transferirán partes, hechos iniciales y materia; en acuerdo parcial, también los puntos pendientes revisados.</p>{solicitante && <button className="boton toga" disabled={ocupado} onClick={()=>confirmado('¿Solicitar canalización y crear un único borrador judicial?',()=>enviar(`/conflictos/${id}/canalizar`,{confirmacion:true},'POST',true))}>Continuar a vía judicial</button>}</section>}
        {c?.estado==='CANALIZADO' && <section className="tarjeta"><h2>Borrador judicial creado</h2><p>Esta iteración termina en la transferencia controlada. El trámite judicial posterior se implementará por separado.</p>{!mediador && <button className="boton secundario" disabled={ocupado} onClick={()=>actuar(async()=>setBorrador(await http(`/conflictos/${id}/demanda-borrador`)),'Transferencia consultada.')}>Ver datos transferidos</button>}
          {borrador && <div className="columna"><p className="mono">{borrador.id}</p><p>{borrador.materia} · {etiqueta(borrador.origen)}</p><p className="odr-texto">{borrador.narrativa_inicial}</p>{borrador.puntos_pendientes?.map((p,i)=><p key={i}>{p}</p>)}</div>}</section>}
      </>}
    </main></div>;
}

function PanelConvenio({id, convenio:v, usuarioId, autor, ocupado, actuar}:{id:string;convenio:ConvenioODR|null;usuarioId:string;autor:(id:string)=>string;ocupado:boolean;actuar:Accion}) {
  const [tipo,setTipo]=useState(v?.tipo ?? 'TOTAL');
  const [revisado,setRevisado]=useState(false);
  const puedeEditar=!v?.formalizado_en && !v?.firmas.length;
  async function guardar(e:FormEvent<HTMLFormElement>) {
    e.preventDefault(); const f=new FormData(e.currentTarget);
    await actuar(()=>enviar(`/odr/${id}/convenio`,{tipo,terminos:f.get('terminos'),puntos_pendientes:tipo==='PARCIAL'?String(f.get('pendientes')??'').split('\n').map(x=>x.trim()).filter(Boolean):[],pendientes_revisados:true},'PUT'),'Documento generado. Todas las personas deben revisar esta misma versión.');
  }
  return <section className="tarjeta"><h2>Convenio {v?.tipo.toLowerCase() ?? ''}</h2>
    <p className="aviso-confidencial">Aceptación de demostración, sin certificado ni sello de tiempo institucional. Se registra quién acepta y la huella del documento. Si hay mediador asignado, también debe aceptarlo.</p>
    {puedeEditar && <form className="columna" onSubmit={guardar}>
      <div className="campo"><label htmlFor="tipo-convenio">Tipo de acuerdo</label><select id="tipo-convenio" value={tipo} onChange={e=>setTipo(e.target.value as 'TOTAL'|'PARCIAL')}><option value="TOTAL">Total</option><option value="PARCIAL">Parcial</option></select></div>
      <div className="campo"><label htmlFor="terminos">Términos acordados para revisión</label><textarea id="terminos" name="terminos" defaultValue={v?.terminos} required maxLength={10000} rows={5}/></div>
      {tipo==='PARCIAL' && <div className="campo"><label htmlFor="pendientes">Puntos pendientes (uno por línea)</label><textarea id="pendientes" name="pendientes" defaultValue={v?.puntos_pendientes.join('\n')} required rows={3}/><p className="pequeno">Describe solo lo que queda por resolver. Excluye ofertas, notas y términos ya acordados.</p></div>}
      <label className="odr-check"><input type="checkbox" required/>Revisé los términos y la separación de los puntos pendientes.</label><button className="boton jade" disabled={ocupado}>{v?'Actualizar borrador':'Generar borrador de convenio'}</button>
    </form>}
    {v && <><h3>Versión para aceptación</h3><p className="odr-texto">{v.terminos}</p>{v.puntos_pendientes.length>0 && <><strong>Puntos pendientes</strong><ul>{v.puntos_pendientes.map((p,i)=><li key={i}>{p}</li>)}</ul></>}
      <p className="mono pequeno odr-hash">SHA-256: {v.hash_sha256}</p><button className="boton secundario" disabled={ocupado} onClick={()=>actuar(()=>descargarConvenio(id),'Documento descargado.')}>Descargar PDF para revisión</button>
      {v.firmas.map(f=><p key={f.usuario_id}>✓ {autor(f.usuario_id)} · Aceptación de demostración · {fecha(f.firmado_en)}</p>)}
      {v.formalizado_en ? <p className="estado aceptada odr-resultado">Formalización de demostración completada. {v.tipo==='PARCIAL'?'Los puntos pendientes siguen abiertos.':'El conflicto está concluido.'}</p>
      : !v.firmas.some(f=>f.usuario_id===usuarioId) && <><label className="odr-check"><input type="checkbox" checked={revisado} onChange={e=>setRevisado(e.target.checked)}/>Revisé esta versión y acepto sus términos para la demostración.</label><button className="boton jade" disabled={ocupado || !revisado} onClick={()=>{if(window.confirm('¿Registrar tu aceptación de esta versión? El documento quedará bloqueado para edición.')) void actuar(()=>enviar(`/odr/${id}/convenio/firmas`,{hash_sha256:v.hash_sha256,confirmacion:true},'POST',true));}}>Registrar aceptación de demostración</button></>}
    </>}
  </section>;
}
