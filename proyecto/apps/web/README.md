# Interfaz web (React)

Una sola SPA con cuatro portales, basada en el diseño **Concordia**. Ciudadanía y mediación están conectadas a `core-api` y PostgreSQL. Juez y administración siguen como vistas previas identificadas. Todo el entorno utiliza datos sintéticos.

**Stack:** React 18 + TypeScript + Vite + React Router. Sin librerías de UI: los estilos están en `src/compartido/estilos/global.css`.

## Ejecutar

```bash
cd proyecto/apps/web
npm ci
npm run dev        # http://localhost:5173
```

El acceso valida credenciales reales de la base local. El registro público solo crea ciudadanos. Los operadores se aprovisionan por CLI y usan TOTP de un autenticador; no se acepta cualquier código de seis dígitos. Primero inicia la API siguiendo la [guía ODR](../../docs/odr-primera-iteracion.md).

## Estructura

```
src/
  app/rutas.tsx              Rutas, protección por rol y carga diferida por pantalla
  compartido/
    componentes/             Folio, Estado, CajaIA, AvisoConfidencial, Riel, layouts
    estilos/global.css       Tokens y clases del sistema Concordia
    servicios/               Un objeto por módulo de core-api (identidad, odr, judicial…)
    datos/mock.ts            Datos sintéticos de la demostración
    tipos/                   Tipos de dominio (espejo de los enums de core-api)
  portales/
    publico/                 P1 Inicio de sesión
    odr/                     Bandeja, captura y sala funcional de ciudadanía/mediador
    ciudadano/               Mis asuntos, P2 Orientación, P4 Sala de negociación, P7 Demanda, P5/P13 Convenio
    mediador/                P4 Portal del mediador
    juez/                    P9/P12 Bandeja y dictamen, P11 Búsqueda semántica
    administracion/          P14 Tablero de indicadores
```

| Ruta | Pantalla | Rol |
| --- | --- | --- |
| `/login` | Inicio de sesión | — |
| `/registro` | Registro ciudadano sintético | — |
| `/ciudadano` | Mis asuntos y notificaciones | CIUDADANO |
| `/ciudadano/orientacion` | Asistente de orientación | CIUDADANO |
| `/ciudadano/negociacion/:folio` | Sala de negociación | CIUDADANO |
| `/ciudadano/demanda/:folio` | Sala con datos de transferencia judicial | CIUDADANO |
| `/ciudadano/convenio/:folio` | Sala con convenio, PDF y aceptaciones de demostración | CIUDADANO |
| `/mediador` | Portal del mediador | MEDIADOR |
| `/mediador/negociacion/:folio` | Negociación, sesiones y notas privadas | MEDIADOR |
| `/juez`, `/juez/busqueda` | Bandeja, dictamen y búsqueda RAG | JUEZ |
| `/admin` | Tablero de indicadores | ADMINISTRADOR |

## Cómo conectar con core-api

1. ODR y autenticación usan la API. El cliente está en `src/compartido/servicios/odr.ts`.
2. Vite reenvía `/api` a `http://localhost:8000` en desarrollo. `.env.example` documenta la URL y desactiva simulaciones de servicios heredados.
3. Los errores de servidor se muestran en pantalla; un 401 elimina la sesión local. Los roles se validan otra vez en el backend.

Las pantallas originales en `portales/ciudadano` y `portales/mediador` quedan como referencia; las rutas ODR activas usan `portales/odr`. Los `TODO` judiciales/administrativos pertenecen a iteraciones posteriores. Ejecuta `npm run build` y, con API/web iniciadas, `npm run test:e2e` (requiere Chromium de Playwright o `PLAYWRIGHT_CHANNEL=msedge`).

## Reglas de interfaz a conservar

- Todo contenido de IA va dentro de `<CajaIA>`: identificado y editable.
- Las acciones irreversibles piden confirmación explícita.
- Jade (círculo) = ruta ODR; toga (cuadro) = ruta judicial.
- Lo que se muestra de la mediación nunca aparece en pantallas judiciales.
- La protección por rol del cliente es solo de navegación; la autorización real la aplica `core-api`.
