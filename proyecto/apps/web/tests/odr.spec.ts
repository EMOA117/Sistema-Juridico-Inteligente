// Recorrido ODR completo con dos personas en navegadores separados (adaptado de feature/modulo-ODR a las pantallas actuales).
import { test, expect, type Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';

const MAILPIT = process.env.MAILPIT_URL ?? 'http://localhost:8025';
const CONTRASENA = 'Prueba-navegador-2026!';

// CURP sintética con dígito verificador válido (mismas reglas que compartido/validacion.py).
function curpSintetica(): string {
  const alfabeto = '0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ';
  const letras = () => Array.from({ length: 2 }, () => 'BCDFGHJKLMNPRSTVZ'[Math.floor(Math.random() * 17)]).join('');
  const base = `PE${letras()}9${Math.floor(Math.random() * 10)}0101HDFRRN0`;
  const suma = [...base].reduce((s, c, i) => s + alfabeto.indexOf(c) * (18 - i), 0);
  return base + ((10 - (suma % 10)) % 10);
}

async function registrar(p: Page, nombre: string, correo: string) {
  await p.goto('/registro');
  await p.getByLabel('Nombre completo').fill(nombre);
  await p.getByLabel('Correo electrónico').fill(correo);
  await p.getByLabel('CURP').fill(curpSintetica());
  await p.getByLabel('Contraseña', { exact: true }).fill(CONTRASENA);
  await p.getByLabel('Repite la contraseña').fill(CONTRASENA);
  await p.getByRole('button', { name: 'Crear cuenta' }).click();
  await expect(p).toHaveURL(/\/ciudadano$/);
}

// El correo de invitación llega a Mailpit; se toma la ruta del enlace para abrirla en el mismo servidor de pruebas.
async function enlaceInvitacion(correo: string): Promise<string> {
  for (let i = 0; i < 30; i++) {
    const r = await fetch(`${MAILPIT}/api/v1/search?query=${encodeURIComponent(`to:${correo}`)}`).then((x) => x.json());
    if (r.messages?.length) {
      const m = await fetch(`${MAILPIT}/api/v1/message/${r.messages[0].ID}`).then((x) => x.json());
      const url = (m.Text as string).match(/https?:\/\/\S+\/invitacion\/\S+/)?.[0];
      if (url) return new URL(url).pathname;
    }
    await new Promise((ok) => setTimeout(ok, 1000));
  }
  throw new Error('No llegó el correo de invitación');
}

async function firmar(p: Page) {
  await p.getByRole('button', { name: 'Firmar convenio' }).click();
  await p.getByLabel('Confirma tu contraseña').fill(CONTRASENA);
  await p.getByRole('button', { name: 'Firmar', exact: true }).click();
}

test('dos partes negocian, firman y formalizan un convenio total', async ({ browser }, info) => {
  const ctxA = await browser.newContext(), ctxB = await browser.newContext();
  const a = await ctxA.newPage(), b = await ctxB.newPage();
  const errores: string[] = [];
  for (const p of [a, b]) {
    p.on('pageerror', (e) => errores.push(e.message));
    p.on('dialog', (d) => d.accept());
  }
  const sufijo = randomUUID().slice(0, 8);
  const correoA = `solicitante-${sufijo}@e2e.test`, correoB = `contraparte-${sufijo}@e2e.test`;

  try {
    await registrar(a, 'Solicitante Sintética', correoA);
    await a.getByRole('link', { name: 'Nuevo asunto' }).click();
    await a.getByLabel('Tu nombre completo').fill('Solicitante Sintética');
    await a.getByLabel('Nombre de la otra parte').fill('Contraparte Sintética');
    await a.getByLabel('Correo de la otra parte').fill(correoB);
    await a.getByRole('button', { name: 'Continuar' }).click();
    await a.getByLabel('En tus palabras, sin tecnicismos').fill('Le presté dinero a mi vecino y no me ha pagado nada en seis meses.');
    await a.getByRole('button', { name: 'Analizar mi caso' }).click();
    await a.getByLabel('¿Es correcta la materia?').selectOption('CIVIL');
    await a.getByRole('button', { name: 'Confirmar orientación' }).click();
    await a.getByRole('button', { name: /^Invitar a / }).click();
    await a.getByRole('button', { name: 'Enviar invitación' }).click();
    await expect(a).toHaveURL(/\/ciudadano\/negociacion\//);
    const sala = new URL(a.url()).pathname;

    await registrar(b, 'Contraparte Sintética', correoB);
    await b.goto(await enlaceInvitacion(correoB));
    await b.getByRole('button', { name: 'Aceptar y entrar a la sala' }).click();
    await expect(b).toHaveURL(new RegExp(sala));

    await a.reload();
    await a.getByLabel('Escribe tu mensaje').fill('Propongo revisar juntos un calendario.');
    await a.getByRole('button', { name: 'Enviar', exact: true }).click();
    await b.reload();
    await expect(b.getByText('Propongo revisar juntos un calendario.')).toBeVisible();

    await a.getByRole('tab', { name: 'Propuesta formal' }).click();
    await a.getByLabel('Describe tu propuesta').fill('Tres pagos de $500 los días 5 de cada mes');
    await a.getByRole('button', { name: 'Enviar', exact: true }).click();
    await b.reload();
    await b.getByRole('button', { name: 'Aceptar', exact: true }).click();
    await b.getByRole('link', { name: 'Revisar convenio' }).click();

    await b.getByLabel('Cláusulas acordadas').fill('Primera. La parte deudora pagará tres exhibiciones de $500 los días 5 de cada mes.');
    await b.getByRole('button', { name: 'Preparar convenio' }).click();
    await b.getByRole('button', { name: 'Aprobar texto del convenio' }).click();
    await a.goto(sala.replace('negociacion', 'convenio'));
    await a.getByRole('button', { name: 'Aprobar texto del convenio' }).click();

    await firmar(a);
    await b.reload();
    await firmar(b);
    await expect(b.getByRole('button', { name: 'Abrir convenio PDF firmado' })).toBeVisible();
    await a.reload();
    await expect(a.getByText('Formalizado', { exact: true })).toBeVisible();

    await a.screenshot({ path: info.outputPath('convenio-escritorio.png'), fullPage: true });
    await a.setViewportSize({ width: 390, height: 844 });
    await a.screenshot({ path: info.outputPath('convenio-movil.png'), fullPage: true });
    expect(await a.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    expect(errores).toEqual([]);
  } finally {
    await ctxA.close();
    await ctxB.close();
  }
});
