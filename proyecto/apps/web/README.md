# Interfaz web (React)

Una sola SPA con los cuatro portales (ciudadanía, mediación, juez y administración), basada en el diseño **Concordia**. Hoy las pantallas usan datos sintéticos; la lógica de negocio real vive en `core-api`.

**Stack:** React 18 + TypeScript + Vite + React Router. Sin librerías de UI: los estilos están en `src/compartido/estilos/global.css`.

## Ejecutar

```bash
cd proyecto/apps/web
npm install
npm run dev        # http://localhost:5173
```

En la pantalla de inicio de sesión cualquier correo y contraseña funcionan (modo simulado). Para el acceso institucional se elige el perfil y el código MFA debe tener 6 dígitos.

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
| `/ciudadano/negociacion/:folio` | Sala de negociación | CIUDADANO |
| `/ciudadano/demanda/:folio` | Demanda asistida | CIUDADANO |
| `/ciudadano/convenio/:folio` | Convenio PDF y aviso por correo | CIUDADANO |
| `/mediador` | Portal del mediador | MEDIADOR |
| `/juez`, `/juez/busqueda` | Bandeja, dictamen y búsqueda RAG | JUEZ |
| `/admin` | Tablero de indicadores | ADMINISTRADOR |

## Cómo conectar con core-api

1. Copia `.env.example` a `.env` y pon `VITE_USAR_MOCKS=false`.
2. En `src/compartido/servicios/index.ts` cada función tiene un `TODO` con el endpoint esperado; reemplaza `simular(...)` por `http(...)`.
3. Vite reenvía `/api` a `http://localhost:8000` (FastAPI) en desarrollo.

Los `TODO` dentro de las pantallas marcan las acciones que hoy solo cambian el estado local (enviar propuesta, firmar dictamen, registrar conclusión, etc.).

## Reglas de interfaz a conservar

- Todo contenido de IA va dentro de `<CajaIA>`: identificado y editable.
- Las acciones irreversibles piden confirmación explícita.
- Jade (círculo) = ruta ODR; toga (cuadro) = ruta judicial.
- Lo que se muestra de la mediación nunca aparece en pantallas judiciales.
- La protección por rol del cliente es solo de navegación; la autorización real la aplica `core-api`.
