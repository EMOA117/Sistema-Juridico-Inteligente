// Datos sintéticos para la demostración local (ver docs/decisiones/003-busqueda-y-datos.md).
// Ningún dato corresponde a personas o expedientes reales.
import type {
  Actividad, Asunto, ExpedienteResumen, Fragmento, Mediacion, Mensaje, Orientacion, Propuesta, Usuario,
} from '@/compartido/tipos';

export const usuarios: Record<string, Usuario> = {
  ciudadano: { id: 'u-ana', nombre: 'Ana Pérez López', correo: 'ana.perez@correo.com', rol: 'CIUDADANO' },
  mediador: { id: 'u-mariana', nombre: 'Lic. Mariana Soto', correo: 'm.soto@cja.example', rol: 'MEDIADOR', cargo: 'Mediadora certificada · Cert. 0482' },
  juez: { id: 'u-jorge', nombre: 'Mtro. Jorge Ramírez', correo: 'j.ramirez@tribunal.example', rol: 'JUEZ', cargo: 'Juez 14.º Civil de Proceso Oral' },
  admin: { id: 'u-admin', nombre: 'Personal administrativo', correo: 'admin@tribunal.example', rol: 'ADMINISTRADOR' },
};

export const asuntos: Asunto[] = [
  { id: 'a1', folio: 'CF-2027-000123', ruta: 'odr', titulo: 'Préstamo no pagado con Carlos Méndez', materia: 'Mercantil', estadoTexto: 'En negociación', aviso: 'Carlos envió una contrapropuesta. Responde antes del 30 de noviembre.' },
  { id: 'a2', folio: 'EXP 412/2027', ruta: 'judicial', titulo: 'Daños en vivienda arrendada', materia: 'Civil', estadoTexto: 'Demanda prevenida', aviso: 'El juzgado pide aclarar el monto reclamado y anexar el contrato. Quedan 5 días hábiles.' },
  { id: 'a3', folio: 'CF-2027-000098', ruta: 'odr', titulo: 'Pensión alimenticia · acuerdo total', materia: 'Familiar', estadoTexto: 'Convenio firmado' },
];

export const actividad: Actividad[] = [
  { titulo: 'Nueva contrapropuesta', detalle: '$10,000 ahora y el resto en 2 meses', referencia: 'CF-…123 · hace 2 h' },
  { titulo: 'Tu demanda fue prevenida', detalle: 'Juzgado 14.º Civil', referencia: 'EXP 412/2027 · ayer' },
  { titulo: 'Carlos aceptó la invitación', detalle: 'La negociación está abierta', referencia: 'CF-…123 · 12 nov' },
  { titulo: 'Convenio firmado por ambas partes', referencia: 'CF-…098 · 2 sep' },
];

export const orientacion: Orientacion = {
  folio: 'CF-2027-000123',
  materia: 'Mercantil',
  certeza: 0.91,
  complejidad: 'Media',
  mediable: true,
  motivo: 'Monto determinado y pruebas documentales',
};

export const mensajes: Mensaje[] = [
  { id: 'm1', autor: 'otra_parte', texto: 'Reconozco la deuda. Ahora no tengo el total, pero quiero resolverlo.', fecha: '13 nov, 10:24' },
  { id: 'm2', autor: 'yo', texto: 'Necesito al menos una parte ya. Puedo aceptar pagos si el primero es mayor.', fecha: '14 nov, 18:02' },
];

export const propuestas: Propuesta[] = [
  { id: 'p2', numero: 2, autor: 'otra_parte', resumen: '$10,000 ahora + $5,000 en 2 meses', estado: 'PENDIENTE' },
  { id: 'p1', numero: 1, autor: 'otra_parte', resumen: '$15,000 en 3 mensualidades', estado: 'RECHAZADA' },
];

export const sugerenciaAcuerdo = {
  texto: '$10,000 al firmar el convenio y $5,000 a 60 días, con recibo firmado por cada pago.',
  fundamento: 'En 37 convenios anonimizados similares, los acuerdos con un primer pago mayor al 60% se cumplieron con más frecuencia.',
};

export const expedientes: ExpedienteResumen[] = [
  { id: 'e458', numero: '458/2027', partes: 'Pérez vs. Méndez', materia: 'Mercantil', estado: 'EN_REVISION', origen: 'Mediación sin acuerdo', plazoDias: 2 },
  { id: 'e452', numero: '452/2027', partes: 'Luna vs. Castro', materia: 'Civil', estado: 'EN_REVISION', origen: 'Directa', plazoDias: 3 },
  { id: 'e412', numero: '412/2027', partes: 'Torres vs. Inm. Sur', materia: 'Civil', estado: 'PREVENIDO', origen: 'Acuerdo parcial', plazoDias: 5 },
  { id: 'e398', numero: '398/2027', partes: 'Gómez vs. Herrera', materia: 'Mercantil', estado: 'EN_TURNO', origen: 'Invitación no aceptada', plazoDias: 6 },
  { id: 'e377', numero: '377/2027', partes: 'Ruiz vs. Ortega', materia: 'Familiar', estado: 'EN_TRAMITE', origen: 'Directa', plazoDias: 12 },
  { id: 'e350', numero: '350/2027', partes: 'Díaz vs. Fuentes', materia: 'Civil', estado: 'RESUELTO', origen: 'Directa', plazoDias: 0 },
];

export const fragmentos: Fragmento[] = [
  { id: 'f1', documento: 'Contestacion.pdf', pagina: 'pág. 3', puntaje: 0.87, texto: '…niego la cantidad reclamada en su totalidad, toda vez que el día 10 de junio de 2027 entregué a la actora la suma de $5,000.00, como se acredita con el recibo que se exhibe…' },
  { id: 'f2', documento: 'Anexo_Recibo.pdf', pagina: 'pág. 1', puntaje: 0.81, texto: 'Recibí la cantidad de $5,000.00 por concepto de abono. Ciudad de México, junio de 2027. [sin firma legible]' },
  { id: 'f3', documento: 'Marco normativo vigente', pagina: '[artículo aplicable]', puntaje: 0.78, texto: '…los documentos privados sólo harán prueba plena contra su autor cuando fueren reconocidos legalmente…' },
];

export const mediaciones: Mediacion[] = [
  { id: 'md123', folio: 'CF-2027-000123', partes: 'Pérez vs. Méndez', materia: 'Mercantil', estadoTexto: 'Intervención solicitada', detalle: '2 propuestas · plazo 30 nov' },
  { id: 'md117', folio: 'CF-2027-000117', partes: 'Ruiz vs. Ortega', materia: 'Familiar', estadoTexto: 'Sesión hoy 12:00', detalle: 'Régimen de convivencias' },
  { id: 'md109', folio: 'CF-2027-000109', partes: 'Torres vs. Inmobiliaria Sur', materia: 'Civil', estadoTexto: 'Convenio en revisión', detalle: 'Acuerdo parcial · 1 punto pendiente' },
  { id: 'md101', folio: 'CF-2027-000101', partes: 'Gómez vs. Herrera', materia: 'Mercantil', estadoTexto: 'Esperando respuesta', detalle: 'Invitación vence en 3 días' },
];

export const indicadores = {
  kpis: [
    { nombre: 'Conflictos recibidos', valor: '412', nota: '▲ 18% vs. 2026' },
    { nombre: 'Mediaciones iniciadas', valor: '268', nota: '65% de los recibidos' },
    { nombre: 'Tasa de acuerdo', valor: '61%', nota: '▲ 13 pts desde enero' },
    { nombre: 'Canalizados a juicio', valor: '97', nota: 'desde mediación' },
    { nombre: 'Días promedio al cierre', valor: '74', nota: '▼ 9 días' },
  ],
  porMateria: [
    { materia: 'Mercantil', total: 171 },
    { materia: 'Civil', total: 128 },
    { materia: 'Familiar', total: 113 },
  ],
  tasaMensual: [48, 52, 55, 58, 57, 61, 63, 62, 66],
};
