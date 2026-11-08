import type { ReactNode } from 'react';
import { Link, NavLink, Navigate, Outlet, useNavigate } from 'react-router-dom';
import { useSesion } from '@/compartido/servicios/sesion';
import type { Rol } from '@/compartido/tipos';
import { Campana } from './Campana';
import { Logo } from './Iconos';

/** Protege un portal por rol. La autorización real (RBAC + ABAC) la aplica core-api. */
export function RutaProtegida({ rol }: { rol: Rol }) {
  const { usuario } = useSesion();
  if (!usuario) return <Navigate to="/login" replace />;
  if (usuario.rol !== rol) return <Navigate to="/" replace />;
  return <Outlet />;
}

function iniciales(nombre: string) {
  return nombre.replace(/^(Lic\.|Mtro\.)\s*/, '').split(' ').slice(0, 2).map((p) => p[0]).join('');
}

export function EncabezadoCiudadano({ titulo, etiqueta, volverA, derecha }: {
  titulo?: string; etiqueta?: string; volverA?: string; derecha?: ReactNode;
}) {
  const { usuario, salir } = useSesion();
  const navegar = useNavigate();
  return (
    <header className="encabezado">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        {volverA ? <Link to={volverA} aria-label="Volver">←</Link> : <Logo />}
        <span className="marca">{titulo ?? 'Plataforma Jurídica Inteligente'}</span>
        {etiqueta && <span className="etiqueta-portal">{etiqueta}</span>}
        {!titulo && (
          <nav aria-label="Principal">
            <NavLink to="/ciudadano" end className={({ isActive }) => (isActive ? 'activo' : '')}>Mis asuntos</NavLink>
            <NavLink to="/ciudadano/orientacion" className={({ isActive }) => (isActive ? 'activo' : '')}>Nueva orientación</NavLink>
          </nav>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {derecha}
        {usuario && <Campana />}
        {usuario && <span className="avatar" aria-hidden="true">{iniciales(usuario.nombre)}</span>}
        <button type="button" className="boton secundario" style={{ minHeight: 40 }} onClick={() => { salir(); navegar('/login'); }}>Salir</button>
      </div>
    </header>
  );
}

export interface EnlaceMenu { a: string; texto: string; contador?: number }

/** Layout de portales institucionales (mediador, juez, administración). */
export function LayoutInstitucional({ portal, enlaces }: { portal: string; enlaces: EnlaceMenu[] }) {
  const { usuario, salir } = useSesion();
  const navegar = useNavigate();
  return (
    <div className="portal-lateral">
      <nav className="barra-lateral" aria-label={portal}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, justifyContent: 'space-between' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}><Logo />
          <span style={{ display: 'flex', flexDirection: 'column' }}>
            <span className="marca">Concordia</span>
            <span className="mono pequeno" style={{ letterSpacing: '.12em', color: '#D9C08C' }}>{portal.toUpperCase()}</span>
          </span></span>
          <Campana alinear="izquierda" />
        </div>
        <div>
          {enlaces.map((e) => (
            <NavLink key={e.a} to={e.a} end className={({ isActive }) => (isActive ? 'activo' : '')}>
              {e.texto}{e.contador !== undefined && <span className="mono" style={{ float: 'right' }}>{e.contador}</span>}
            </NavLink>
          ))}
        </div>
        <div className="pie">
          <strong style={{ color: '#F3F1EC' }}>{usuario?.nombre}</strong>
          {usuario?.cargo && <span>{usuario.cargo}</span>}
          <span className="mono">MFA ACTIVA</span>
          <button type="button" className="boton secundario" style={{ marginTop: 12, minHeight: 40 }} onClick={() => { salir(); navegar('/login'); }}>Cerrar sesión</button>
        </div>
      </nav>
      <main><Outlet /></main>
    </div>
  );
}
