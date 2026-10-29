# Sistema Jurídico Inteligente

Proyecto integrador de la materia **Ingeniería de Software para Sistemas Inteligentes** de la **Escuela Superior de Cómputo (ESCOM)** del Instituto Politécnico Nacional.

El proyecto propone una plataforma de apoyo para la mediación y resolución de conflictos civiles y familiares. Contempla orientación inicial asistida por inteligencia artificial, mediación en línea, canalización controlada a la vía judicial y seguimiento del caso hasta una solución documentada.

## Contenido

- [Documentación revisada](Sistema_Juridico_Inteligente_revisado.docx): versión vigente de la propuesta.
- [Estructura del proyecto](proyecto/README.md): componentes y responsabilidades.
- [Revisión de arquitectura](proyecto/docs/arquitectura.md): viabilidad para el MVP y decisiones de diseño.
- [Decisiones previas a la implementación](proyecto/docs/decisiones/001-estados-y-contratos.md): estados, contratos, confidencialidad y datos de demostración.
- `Sistema_Juridico_Inteligente.docx` y `Sistema_Juridico_Inteligente.pdf`: versiones de referencia previas a la revisión.

La propuesta del DOCX describe la arquitectura objetivo. Las decisiones en `proyecto/docs/decisiones/` precisan cómo se implementará primero la demostración local de ESCOM con datos sintéticos. La carpeta `proyecto/` incluye ahora reglas de estado, autorización y migraciones PostgreSQL; todavía no hay una aplicación HTTP ejecutable.
