"""Procesos en segundo plano del núcleo (documento §11.1.4). Ejecutar: uv run python -m tareas"""
import logging
import time

from compartido.config import config
from modulos.documentos import indexacion
from tareas import envio_notificaciones, vencimiento_invitaciones

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("tareas")


def main() -> None:
    intervalo = config().intervalo_tareas_s
    ultima_diaria = 0.0
    log.info("Tareas iniciadas (intervalo %ss)", intervalo)
    while True:
        try:
            if (n := envio_notificaciones.despachar_lote()):
                log.info("Avisos enviados: %s", n)
            if (n := indexacion.procesar_lote()):
                log.info("Documentos indexados: %s", n)
            if time.time() - ultima_diaria > 3600:  # revisión horaria; las fechas límite son diarias
                ultima_diaria = time.time()
                if (n := vencimiento_invitaciones.ejecutar()):
                    log.info("Invitaciones vencidas: %s", n)
        except Exception:  # noqa: BLE001 — una falla no debe detener el despacho
            log.exception("Error en ciclo de tareas")
        time.sleep(intervalo)


if __name__ == "__main__":
    main()
