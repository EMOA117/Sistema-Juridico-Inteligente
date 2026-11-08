// RF1.2–RF1.3 · Alta y baja de personal institucional. La contraseña temporal se muestra una sola vez.
import { useState, type FormEvent } from 'react';
import { Cargando, Estado, MensajeError, t } from '@/compartido/componentes';
import { identidad } from '@/compartido/servicios';
import { intentar, useDatos } from '@/compartido/servicios/useDatos';

const roles = { JUEZ: 'Juez', MEDIADOR: 'Mediador', ADMINISTRADOR: 'Administrativo' } as const;

export default function Usuarios() {
  const { datos, error: errorCarga, recargar } = useDatos(() => identidad.personal());
  const [nuevo, setNuevo] = useState({ nombre: '', correo: '', rol: 'MEDIADOR', cargo: '' });
  const [temporal, setTemporal] = useState<string | null>(null);
  const [error, setError] = useState('');

  async function alta(e: FormEvent) {
    e.preventDefault();
    await intentar(async () => {
      const r = await identidad.altaPersonal({ ...nuevo, cargo: nuevo.cargo || undefined });
      setTemporal(r.contrasena_temporal);
      setNuevo({ nombre: '', correo: '', rol: 'MEDIADOR', cargo: '' });
      recargar();
    }, setError);
  }

  async function cambiar(id: string, activo: boolean, nombre: string) {
    if (!confirm(`¿${activo ? 'Reactivar' : 'Desactivar'} la cuenta de ${nombre}?`)) return;
    if (await intentar(() => identidad.estadoPersonal(id, activo), setError)) recargar();
  }

  return (
    <>
      <h1 className="titulo-serif" style={{ fontSize: 40 }}>Personal institucional</h1>
      <MensajeError>{errorCarga || error}</MensajeError>
      <form className="tarjeta" onSubmit={alta} aria-labelledby="h-alta">
        <h2 id="h-alta" className="titulo-seccion">Dar de alta</h2>
        <div className="fila" style={{ alignItems: 'flex-end' }}>
          <div className="campo crece" style={{ minWidth: 200 }}><label htmlFor="u-nom">Nombre</label><input id="u-nom" value={nuevo.nombre} onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} /></div>
          <div className="campo crece" style={{ minWidth: 200 }}><label htmlFor="u-cor">Correo institucional</label><input id="u-cor" type="email" value={nuevo.correo} onChange={(e) => setNuevo({ ...nuevo, correo: e.target.value })} /></div>
          <div className="campo"><label htmlFor="u-rol">Perfil</label>
            <select id="u-rol" value={nuevo.rol} onChange={(e) => setNuevo({ ...nuevo, rol: e.target.value })}>
              {Object.entries(roles).map(([v, n]) => <option key={v} value={v}>{n}</option>)}
            </select></div>
          <div className="campo crece" style={{ minWidth: 200 }}><label htmlFor="u-car">Cargo (opcional)</label><input id="u-car" value={nuevo.cargo} onChange={(e) => setNuevo({ ...nuevo, cargo: e.target.value })} /></div>
          <button type="submit" className="boton" disabled={nuevo.nombre.length < 5 || !nuevo.correo}>Dar de alta</button>
        </div>
        {temporal && (
          <div className="aviso-confidencial" role="status">
            <span>Contraseña temporal (se muestra una sola vez): <code className="mono">{temporal}</code>. Al entrar deberá cambiarla y activar su MFA.</span>
          </div>
        )}
      </form>
      {!datos ? <Cargando /> : (
        <div className="tabla-scroll">
          <table className="tabla">
            <thead><tr><th scope="col">Nombre</th><th scope="col">Correo</th><th scope="col">Perfil</th><th scope="col">MFA</th><th scope="col">Estado</th><th scope="col"><span className="solo-lector">Acciones</span></th></tr></thead>
            <tbody>
              {datos.map((u) => (
                <tr key={u.id + u.rol} style={{ cursor: 'default' }}>
                  <td>{u.nombre}<br /><span className="pequeno texto-2">{u.cargo}</span></td>
                  <td>{u.correo}</td>
                  <td>{roles[u.rol as keyof typeof roles] ?? t(u.rol)}</td>
                  <td>{u.mfa_habilitado ? 'Activo' : 'Pendiente'}</td>
                  <td><Estado tono={u.activo ? 'aceptada' : 'rechazada'}>{u.activo ? 'Activa' : 'Inactiva'}</Estado></td>
                  <td><button type="button" className="boton secundario" style={{ minHeight: 40 }} onClick={() => cambiar(u.id, !u.activo, u.nombre)}>{u.activo ? 'Desactivar' : 'Reactivar'}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
