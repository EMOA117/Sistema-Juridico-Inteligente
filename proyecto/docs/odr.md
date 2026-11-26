# Módulo ODR: estado y criterios de terminación

Demostración local con **datos sintéticos** (decisión 003). Para levantar el entorno y correr las pruebas, consulta [infrastructure/local/README.md](../infrastructure/local/README.md); incluye la guía para Windows.

Este documento integra la evaluación de la rama `feature/modulo-ODR` (primera iteración ODR, 7 y 8 de noviembre de 2026) con la implementación actual de `develop`. De esa rama se incorporaron:

- mensajes y notas del mediador de solo adición, y notas visibles solo mientras el mediador siga asignado (migración `011`);
- canalización con clave de idempotencia (`Idempotency-Key`) y evento `DemandaBorradorCreada` en una cola sin contenido ODR, que consume la tarea en segundo plano;
- la prueba de navegador de dos partes con verificación móvil (`apps/web/tests/odr.spec.ts`) y sus escenarios de API como pruebas de integración.

## Recorrido de demostración

1. Registro ciudadano con CURP (dígito verificador) y contraseña de 12 o más caracteres.
2. Orientación: primero las partes y después el relato. La IA clasifica la materia y la mediabilidad (con reglas de respaldo si no responde) y la persona confirma o corrige.
3. Invitación por correo con enlace de un solo uso y plazo de 3 a 30 días. Los correos llegan a Mailpit (<http://localhost:8025>).
4. La contraparte se registra desde el enlace y acepta o rechaza. Las invitaciones vencen aunque nadie abra la pantalla.
5. Negociación: mensajes, propuestas formales, contrapropuestas y respuestas, todo cifrado (AES-256-GCM). La IA sugiere acuerdos a partir de casos sintéticos similares y se abstiene sin evidencia suficiente.
6. Mediador: asignación por especialidad y menor carga, reasignación por administración, agenda de sesiones y notas privadas.
7. Convenio total o parcial: el parcial exige puntos pendientes separados. Cada parte aprueba el texto y lo firma (PAdES con sello de tiempo de la PKI de prueba). El PDF final se guarda en almacenamiento WORM y se verifica en `/verificar`.
8. Un convenio total concluye el conflicto. Parcial, rechazo, vencimiento, desistimiento o sin acuerdo dejan `EN_ESPERA_DECISION`; la canalización la pide la persona solicitante y nunca sucede automáticamente.
9. A la vía judicial solo pasan partes, narrativa inicial, materia y, en un parcial formalizado, los puntos pendientes. No pasan mensajes, propuestas, notas, PDF ni términos acordados.

## Cobertura

| Requisitos | Estado en `develop` |
| --- | --- |
| RF1.1–1.4 | Registro con CURP, Argon2, JWT de 15 minutos, TOTP obligatorio para el personal, bloqueo tras 5 intentos, alta de personal y bitácora sin contenido ODR. |
| RF2.1–2.5 | Captura secuencial, clasificación y complejidad por IA con respaldo por reglas, corrección humana y decisión expresa de ruta. |
| RF3.1–3.8 | Negociación persistente y cifrada, sugerencia de acuerdos por IA, invitación con plazo, mediador, sesiones, notas y resultados. |
| RF4.1–4.4 | Convenio total o parcial, aprobación y firma de cada parte y del mediador, formalización y verificación pública. |
| RF10 | Avisos en plataforma y por correo, con reintentos e historial de entrega, sin contenido de la negociación. |

## Pendientes y criterios de terminación

Se mantiene la evaluación de la rama `feature/modulo-ODR`, actualizada con lo que ya está en `develop`.

| Trabajo | Estado | Criterio de aceptación |
| --- | --- | --- |
| Verificación de correo y ciclo de cuenta: enlace de verificación, recuperación de contraseña y revocación de sesiones. | **Pendiente.** La invitación ya exige el enlace del correo, pero el registro no verifica la propiedad del correo. | Una cuenta no se vincula a invitaciones ni consulta asuntos solo por declarar un correo ajeno; recuperación y cierre de sesiones se prueban en servidor. |
| Invitaciones y avisos externos. | Hecho con Mailpit. Falta un proveedor real de correo. | La contraparte recibe un enlace utilizable; los fallos se reintentan sin duplicar efectos. |
| Gestión de mediadores. | Hecho. La reasignación no pide motivo. | Toda reasignación registra actor y **motivo**; una solicitud sin mediador disponible queda en una bandeja atendible. |
| Asistencia inteligente. | Hecho con Ollama local. No cumple la latencia de RNF2.1/2.3 en la laptop de desarrollo; falta evaluar calidad con casos separados del corpus. | Fuentes y límites visibles, revisión humana registrada, abstención sin evidencia y sin bloqueo del trámite si la IA cae. |
| Formalización institucional. | Firma PAdES con PKI **de prueba**. | Integrar el proveedor de firma y sello de tiempo institucional detrás de `ProveedorFirma`, con la modalidad de demostración diferenciada. |
| Operación: HTTPS, credenciales por dominio, rotación de claves, respaldos y restauración. | **Pendiente.** | El entorno se instala y se recupera con datos y claves; ningún dominio obtiene permisos ajenos. |
| Aceptación y entrega: pruebas en CI, más recorridos de navegador, fallos, concurrencia y accesibilidad. | Parcial: pruebas de integración y un recorrido de navegador, sin CI. | Se verifican total, parcial, rechazo, vencimiento, desistimiento, sin acuerdo, mediador y canalización en cada cambio. |

Para cerrar el **MVP académico** basta con firma simulada y correo de pruebas, si ese alcance se acepta expresamente y se etiqueta en las evidencias. Una **operación institucional** requiere integrar y revisar con la institución la verificación de identidad, la firma y la retención; los resultados de este prototipo no acreditan esa aptitud.
