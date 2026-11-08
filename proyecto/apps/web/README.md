# Interfaz web (React)

Una sola SPA con los cuatro portales (ciudadanía, mediación, juez y administración), basada en el diseño **Concordia**. Consume la API de `core-api`; los datos son sintéticos (decisión 003).

**Stack:** React 18 + TypeScript + Vite + React Router. Sin librerías de UI: los estilos están en `src/compartido/estilos/global.css`.

## Ejecutar

```bash
cd proyecto/apps/web
npm install
npm run dev        # http://localhost:5173
```

Requiere `core-api` en el puerto 8000 (ver `infrastructure/local/README.md`). Vite reenvía `/api/*` a esa API. Las cuentas demo y sus secretos TOTP están en `infrastructure/local/credenciales-demo.txt`, que se genera al sembrar los datos.

## Estructura

```
src/
  app/rutas.tsx              Rutas, protección por rol y carga diferida por pantalla
  compartido/
    componentes/             Folio, Estado, CajaIA, AvisoConfidencial, Riel, layouts
    estilos/global.css       Tokens y clases del sistema Concordia
    servicios/               Un objeto por módulo de core-api (identidad, odr, judicial…) y la sesión
    tipos/                   Tipos de dominio (espejo de los enums de core-api)
  portales/
    publico/                 P1 Inicio de sesión
    ciudadano/               Mis asuntos, P2 Orientación, P4 Sala de negociación, P7 Demanda, P5/P13 Convenio
    mediador/                P4 Portal del mediador
    juez/                    P9/P12 Bandeja y dictamen, P11 Búsqueda semántica
    administracion/          P14 Tablero de indicadores
```

| Ruta | Pantalla | Rol |
| --- | --- | --- |
| `/login` | Inicio de sesión | — |
| `/ciudadano` | Mis asuntos y notificaciones | CIUDADANO |
| `/ciudadano/orientacion` | Asistente de orientación | CIUDADANO |
| `/ciudadano/negociacion/:id` | Sala de negociación (id de mediación) | CIUDADANO |
| `/ciudadano/demanda/:conflictoId` | Demanda asistida | CIUDADANO |
| `/ciudadano/expediente/:id` | Expediente y corrección de demanda prevenida | CIUDADANO |
| `/ciudadano/convenio/:id` | Convenio PDF y aviso por correo | CIUDADANO |
| `/mediador` | Portal del mediador | MEDIADOR |
| `/juez`, `/juez/busqueda` | Bandeja, dictamen y búsqueda RAG | JUEZ |
| `/admin`, `/admin/turno` | Tablero de indicadores y turno de expedientes | ADMINISTRADOR |

## Conexión con core-api

`src/compartido/servicios/index.ts` declara una función por endpoint. Los errores de la API se muestran con `MensajeError`; un 401 cierra la sesión.

## Reglas de interfaz a conservar

- Todo contenido de IA va dentro de `<CajaIA>`: identificado y editable.
- Las acciones irreversibles piden confirmación explícita.
- Jade (círculo) = ruta ODR; toga (cuadro) = ruta judicial.
- Lo que se muestra de la mediación nunca aparece en pantallas judiciales.
- La protección por rol del cliente es solo de navegación; la autorización real la aplica `core-api`.
