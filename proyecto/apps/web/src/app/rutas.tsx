import { lazy, Suspense, type ReactNode } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { LayoutInstitucional, RutaProtegida } from '@/compartido/componentes/Layouts';
import { Cargando } from '@/compartido/componentes';
import { useSesion } from '@/compartido/servicios/sesion';
import Login from '@/portales/publico/Login';

// Carga diferida por pantalla (RNF2.2: code-splitting).
const MisAsuntos = lazy(() => import('@/portales/ciudadano/MisAsuntos'));
const Orientacion = lazy(() => import('@/portales/ciudadano/Orientacion'));
const SalaNegociacion = lazy(() => import('@/portales/ciudadano/SalaNegociacion'));
const DemandaAsistida = lazy(() => import('@/portales/ciudadano/DemandaAsistida'));
const Convenio = lazy(() => import('@/portales/ciudadano/Convenio'));
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
  {
    path: '/ciudadano',
    element: <RutaProtegida rol="CIUDADANO" />,
    children: [
      { index: true, element: conCarga(<MisAsuntos />) },
      { path: 'orientacion', element: conCarga(<Orientacion />) },
      { path: 'negociacion/:folio', element: conCarga(<SalaNegociacion />) },
      { path: 'demanda/:folio', element: conCarga(<DemandaAsistida />) },
      { path: 'convenio/:folio', element: conCarga(<Convenio />) },
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
      ]} />,
      children: [{ index: true, element: conCarga(<TableroIndicadores />) }],
    }],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);
