import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Logo } from '@/compartido/componentes';

/** Marco sencillo para pantallas fuera de los portales (registro, MFA, invitación, verificación). */
export function MarcoPublico({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div className="pagina">
      <header className="encabezado">
        <Link to="/login" style={{ display: 'flex', alignItems: 'center', gap: 12, textDecoration: 'none' }}>
          <Logo /><span className="marca">Plataforma Jurídica Inteligente</span>
        </Link>
      </header>
      <main className="contenedor" style={{ maxWidth: 640 }}>
        <h1 className="titulo-serif" style={{ fontSize: 36 }}>{titulo}</h1>
        {children}
      </main>
    </div>
  );
}
