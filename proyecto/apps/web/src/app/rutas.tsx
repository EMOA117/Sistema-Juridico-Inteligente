import { lazy, Suspense, type ReactNode } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { LayoutInstitucional, RutaProtegida } from '@/compartido/componentes/Layouts';
import { Cargando } from '@/compartido/componentes';
import { useSesion } from '@/compartido/servicios/sesion';
import Login from '@/portales/publico/Login';
const Registro = lazy(() => import('@/portales/publico/Registro'));
const ActivarMFA = lazy(() => import('@/portales/publico/ActivarMFA'));
const CambiarContrasena = lazy(() => import('@/portales/publico/CambiarContrasena'));
const Usuarios = lazy(() => import('@/portales/administracion/Usuarios'));
const Mediadores = lazy(() => import('@/portales/administracion/Mediadores'));
const Invitacion = lazy(() => import('@/portales/publico/Invitacion'));
const Invitar = lazy(() => import('@/portales/ciudadano/Invitar'));

// Carga diferida por pantalla (RNF2.2: code-splitting).
const MisAsuntos = lazy(() => import('@/portales/ciudadano/MisAsuntos'));
const Orientacion = lazy(() => import('@/portales/ciudadano/Orientacion'));
const SalaNegociacion = lazy(() => import('@/portales/ciudadano/SalaNegociacion'));
const DemandaAsistida = lazy(() => import('@/portales/ciudadano/DemandaAsistida'));
const Convenio = lazy(() => import('@/portales/ciudadano/Convenio'));
const ExpedienteCiudadano = lazy(() => import('@/portales/ciudadano/ExpedienteCiudadano'));
const Turno = lazy(() => import('@/portales/administracion/Turno'));
const PortalMediador = lazy(() => import('@/portales/mediador/PortalMediador'));
const BandejaJuez = lazy(() => import('@/portales/juez/BandejaJuez'));
const BusquedaSemantica = lazy(() => import('@/portales/juez/BusquedaSemantica'));
const TableroIndicadores = lazy(() => import('@/portales/administracion/TableroIndicadores'));

const conCarga = (n: ReactNode) => <Suspense fallback={<Cargando />}>{n}</Suspense>;

/** Redirige al portal que corresponde al rol de la sesión. */
function Inicio() {
  const { usuario } = useSesion();
  if (!usuario) return <Navigate to="/login" replace />;
  const destino = { CIUDADANO: '/ciudadano', MEDIADOR: '/mediador', JUEZ: '/juez', ADMINISTRADOR: '/admin' }[usuario.rol];
  return <Navigate to={destino} replace />;
}

export const router = createBrowserRouter([
  { path: '/', element: <Inicio /> },
  { path: '/login', element: <Login /> },
  { path: '/registro', element: conCarga(<Registro />) },
  { path: '/invitacion/:token', element: conCarga(<Invitacion />) },
  { path: '/mfa', element: conCarga(<ActivarMFA />) },
  { path: '/cambiar-contrasena', element: conCarga(<CambiarContrasena />) },
  {
    path: '/ciudadano',
    element: <RutaProtegida rol="CIUDADANO" />,
    children: [
      { index: true, element: conCarga(<MisAsuntos />) },
      { path: 'orientacion', element: conCarga(<Orientacion />) },
      { path: 'invitar/:conflictoId', element: conCarga(<Invitar />) },
      { path: 'negociacion/:id', element: conCarga(<SalaNegociacion />) },
      { path: 'demanda/:conflictoId', element: conCarga(<DemandaAsistida />) },
      { path: 'expediente/:id', element: conCarga(<ExpedienteCiudadano />) },
      { path: 'convenio/:id', element: conCarga(<Convenio />) },
    ],
  },
  {
    path: '/mediador',
    element: <RutaProtegida rol="MEDIADOR" />,
    children: [{
      element: <LayoutInstitucional portal="Mediación · CJA" enlaces={[
        { a: '/mediador', texto: 'Mis mediaciones' },
      ]} />,
      children: [{ index: true, element: conCarga(<PortalMediador />) }],
    }],
  },
  {
    path: '/juez',
    element: <RutaProtegida rol="JUEZ" />,
    children: [{
      element: <LayoutInstitucional portal="Portal judicial" enlaces={[
        { a: '/juez', texto: 'Bandeja' },
        { a: '/juez/busqueda', texto: 'Búsqueda jurídica' },
      ]} />,
      children: [
        { index: true, element: conCarga(<BandejaJuez />) },
        { path: 'busqueda', element: conCarga(<BusquedaSemantica />) },
      ],
    }],
  },
  {
    path: '/admin',
    element: <RutaProtegida rol="ADMINISTRADOR" />,
    children: [{
      element: <LayoutInstitucional portal="Administración" enlaces={[
        { a: '/admin', texto: 'Indicadores' },
        { a: '/admin/turno', texto: 'Turno de expedientes' },
        { a: '/admin/usuarios', texto: 'Personal' },
        { a: '/admin/mediadores', texto: 'Mediadores' },
      ]} />,
      children: [
        { index: true, element: conCarga(<TableroIndicadores />) },
        { path: 'turno', element: conCarga(<Turno />) },
        { path: 'usuarios', element: conCarga(<Usuarios />) },
        { path: 'mediadores', element: conCarga(<Mediadores />) },
      ],
    }],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);
