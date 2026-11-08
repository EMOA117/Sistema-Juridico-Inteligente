import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { ProveedorSesion } from '@/compartido/servicios/sesion';
import { router } from '@/app/rutas';
import '@/compartido/estilos/global.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ProveedorSesion>
      <RouterProvider router={router} />
    </ProveedorSesion>
  </StrictMode>,
);
