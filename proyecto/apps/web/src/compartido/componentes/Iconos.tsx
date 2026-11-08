// Íconos de trazo en línea (sin emojis), decorativos por defecto.
const base = { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true };

export const IconoIA = () => <svg {...base}><path d="M12 2l2.6 7.4L22 12l-7.4 2.6L12 22l-2.6-7.4L2 12l7.4-2.6z" /></svg>;
export const IconoCandado = () => <svg {...base}><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></svg>;
export const IconoFlecha = () => <svg {...base}><path d="M5 12h14M13 6l6 6-6 6" /></svg>;
export const IconoVolver = () => <svg {...base}><path d="M19 12H5M11 6l-6 6 6 6" /></svg>;
export const IconoCampana = () => <svg {...base}><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" /></svg>;

export const Logo = () => (
  <svg width="40" height="28" viewBox="0 0 44 30" fill="none" aria-hidden="true">
    <circle cx="15" cy="15" r="12" stroke="#C9922E" strokeWidth="2.5" />
    <circle cx="29" cy="15" r="12" stroke="#F3F1EC" strokeWidth="2.5" />
  </svg>
);
