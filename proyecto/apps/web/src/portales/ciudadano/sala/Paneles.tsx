// Paneles laterales de la sala. Se completan con la gestión de mediadores y el asistente de IA.
import type { Mediacion } from '@/compartido/tipos';

export function PanelSugerencia(_: { mediacionId: string; usar: (texto: string) => void }) {
  return null;
}

export function PanelMediador(_: { mediacion: Mediacion; alCambiar: () => void; alError: (m: string) => void }) {
  return null;
}
