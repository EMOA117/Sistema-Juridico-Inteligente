// RF10.3 · Avisos en plataforma: contador de no leídos y lista desplegable. Se actualiza cada 30 s.
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { notificaciones } from '@/compartido/servicios';
import { useSesion } from '@/compartido/servicios/sesion';
import type { Aviso } from '@/compartido/tipos';
import { IconoCampana } from './Iconos';

export function destinoDeAviso(a: Aviso, rol: string): string {
  if (rol === 'JUEZ') return '/juez';
  if (rol === 'MEDIADOR') return a.entidad === 'mediacion' ? `/mediador?m=${a.entidad_id}` : '/mediador';
  if (rol === 'ADMINISTRADOR') return '/admin/turno';
  if (a.entidad === 'mediacion') return `/ciudadano/negociacion/${a.entidad_id}`;
  if (a.entidad === 'expediente') return `/ciudadano/expediente/${a.entidad_id}`;
  return '/ciudadano';
}

export function Campana({ alinear = 'derecha' }: { alinear?: 'derecha' | 'izquierda' }) {
  const { usuario } = useSesion();
  const navegar = useNavigate();
  const [datos, setDatos] = useState<{ sin_leer: number; avisos: Aviso[] }>({ sin_leer: 0, avisos: [] });
  const [abierta, setAbierta] = useState(false);
  const caja = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let vivo = true;
    const cargar = () => notificaciones.bandeja().then((d) => vivo && setDatos(d)).catch(() => {});
    cargar();
    const reloj = window.setInterval(cargar, 30_000);
    return () => { vivo = false; window.clearInterval(reloj); };
  }, []);

  useEffect(() => {
    if (!abierta) return;
    const cerrar = (e: MouseEvent) => { if (!caja.current?.contains(e.target as Node)) setAbierta(false); };
    document.addEventListener('mousedown', cerrar);
    return () => document.removeEventListener('mousedown', cerrar);
  }, [abierta]);

  async function abrir(a: Aviso) {
    setAbierta(false);
    if (!a.leida_en) await notificaciones.leidas([a.id]).catch(() => {});
    setDatos((d) => ({ sin_leer: Math.max(0, d.sin_leer - (a.leida_en ? 0 : 1)), avisos: d.avisos.map((x) => x.id === a.id ? { ...x, leida_en: 'ahora' } : x) }));
    navegar(destinoDeAviso(a, usuario?.rol ?? 'CIUDADANO'));
  }

  return (
    <div ref={caja} style={{ position: 'relative' }}>
      <button type="button" className="boton secundario" style={{ minHeight: 40 }} aria-expanded={abierta}
        aria-label={`Notificaciones, ${datos.sin_leer} sin leer`} onClick={() => setAbierta((v) => !v)}>
        <IconoCampana />{datos.sin_leer > 0 && <span className="mono">{datos.sin_leer}</span>}
      </button>
      {abierta && (
        <div className="tarjeta" role="dialog" aria-label="Notificaciones"
          style={{ position: 'absolute', [alinear === 'derecha' ? 'right' : 'left']: 0, top: 48, width: 340, maxHeight: 420, overflowY: 'auto', zIndex: 10, padding: 12, gap: 4, color: 'var(--texto)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <strong>Notificaciones</strong>
            {datos.sin_leer > 0 && <button type="button" className="boton secundario" style={{ minHeight: 32, fontSize: 13, padding: '0 10px' }}
              onClick={() => notificaciones.leidas().then(() => setDatos((d) => ({ sin_leer: 0, avisos: d.avisos.map((x) => ({ ...x, leida_en: x.leida_en ?? 'ahora' })) })))}>Marcar todo leído</button>}
          </div>
          {datos.avisos.length === 0 && <p className="texto-2 pequeno">No tienes avisos.</p>}
          {datos.avisos.map((a) => (
            <button key={a.id} type="button" onClick={() => abrir(a)}
              style={{ textAlign: 'left', border: 0, borderBottom: '1px solid var(--linea)', background: a.leida_en ? 'transparent' : 'var(--laton-tinte)', padding: '10px 8px', cursor: 'pointer', borderRadius: 4 }}>
              <strong style={{ fontSize: 14 }}>{a.texto}</strong><br />
              <span className="mono pequeno texto-2">{a.folio ?? ''} · {new Date(a.creado_en).toLocaleString('es-MX')}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
