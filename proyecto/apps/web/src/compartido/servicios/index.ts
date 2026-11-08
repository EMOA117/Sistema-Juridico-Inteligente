// Identidad real y servicios heredados de las vistas previas. ODR usa ./odr.ts.
import * as mock from '@/compartido/datos/mock';
import type { Rol, Usuario } from '@/compartido/tipos';
import { http, simular, USAR_MOCKS } from './api';

export const identidad = {
  // El servidor determina el rol y verifica TOTP institucional.
  async iniciarSesion(correo: string, _contrasena: string, _rol: Rol, _mfa?: string): Promise<Usuario> {
    const sesion = await http<{ token: string; usuario: Usuario }>('/auth/login', { method: 'POST', body: JSON.stringify({ correo, contrasena: _contrasena, codigo_mfa: _mfa || null }) });
    sessionStorage.setItem('token', sesion.token);
    return sesion.usuario;
  },
};

export const ciudadano = {
  // TODO: GET /conflictos/mios
  misAsuntos: () => (USAR_MOCKS ? simular(mock.asuntos) : http<typeof mock.asuntos>('/conflictos/mios')),
  // TODO: GET /notificaciones
  actividad: () => (USAR_MOCKS ? simular(mock.actividad) : http<typeof mock.actividad>('/notificaciones')),
};

export const orientacion = {
  // TODO: POST /orientacion  -> core-api llama a ia-service/clasificacion
  clasificar: (_narrativa: string) => (USAR_MOCKS ? simular(mock.orientacion, 800) : http<typeof mock.orientacion>('/orientacion', { method: 'POST', body: JSON.stringify({ narrativa: _narrativa }) })),
};

export const odr = {
  // TODO: GET /odr/{folio}/mensajes, /odr/{folio}/propuestas, /odr/{folio}/sugerencia
  mensajes: () => simular(mock.mensajes),
  propuestas: () => simular(mock.propuestas),
  sugerencia: () => simular(mock.sugerenciaAcuerdo, 600),
  mediaciones: () => simular(mock.mediaciones),
};

export const judicial = {
  // TODO: GET /expedientes?juez=me
  bandeja: () => simular(mock.expedientes),
  // TODO: POST /busqueda  (RAG restringido al expediente)
  buscar: (_expediente: string, _pregunta: string) => simular(mock.fragmentos, 900),
};

export const analitica = {
  // TODO: GET /analitica/indicadores
  indicadores: () => simular(mock.indicadores),
};
