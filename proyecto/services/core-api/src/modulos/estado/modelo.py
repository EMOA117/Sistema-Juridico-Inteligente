"""Reglas del MVP para cambios de estado; no realizan escrituras por sí mismas."""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class EstadoInvalido(ValueError):
    pass


class Conflicto(StrEnum):
    CAPTURA = "CAPTURA"
    ORIENTADO = "ORIENTADO"
    EN_MEDIACION = "EN_MEDIACION"
    EN_ESPERA_DECISION = "EN_ESPERA_DECISION"
    CANALIZADO = "CANALIZADO"
    CONCLUIDO = "CONCLUIDO"


class Expediente(StrEnum):
    EN_TURNO = "EN_TURNO"
    EN_REVISION = "EN_REVISION"
    PREVENIDO = "PREVENIDO"
    ADMITIDO = "ADMITIDO"
    EN_TRAMITE = "EN_TRAMITE"
    RESUELTO = "RESUELTO"
    DESECHADO = "DESECHADO"
    CERRADO = "CERRADO"


@dataclass(frozen=True)
class EvidenciaConflicto:
    partes_completas: bool = False
    narrativa_inicial: bool = False
    orientacion_confirmada: bool = False
    mediable: bool = False
    via_mediacion_elegida: bool = False
    resultado_mediacion: str | None = None
    convenio_formalizado: bool = False
    demanda_borrador_creada: bool = False
    expediente_cerrado: bool = False


@dataclass(frozen=True)
class EvidenciaExpediente:
    turno_confirmado: bool = False
    prevencion_registrada: bool = False
    correccion_presentada: bool = False
    admision_registrada: bool = False
    emplazamiento_validado: bool = False
    contestacion_registrada: bool = False
    plazo_vencido: bool = False
    resolucion_firmada: bool = False
    resultado_explicito: bool = False
    sello_tiempo: bool = False
    firmeza: bool = False


def validar_conflicto(actual: Conflicto, nuevo: Conflicto, e: EvidenciaConflicto) -> None:
    reglas = {
        (Conflicto.CAPTURA, Conflicto.ORIENTADO): e.partes_completas and e.narrativa_inicial and e.orientacion_confirmada,
        (Conflicto.ORIENTADO, Conflicto.EN_MEDIACION): e.mediable and e.via_mediacion_elegida,
        (Conflicto.ORIENTADO, Conflicto.CANALIZADO): e.demanda_borrador_creada,
        (Conflicto.EN_MEDIACION, Conflicto.CONCLUIDO): e.resultado_mediacion == "ACUERDO_TOTAL" and e.convenio_formalizado,
        (Conflicto.EN_MEDIACION, Conflicto.EN_ESPERA_DECISION): e.resultado_mediacion in {"NO_ACEPTADA", "SIN_ACUERDO", "DESISTIMIENTO"} or (e.resultado_mediacion == "ACUERDO_PARCIAL" and e.convenio_formalizado),
        (Conflicto.EN_ESPERA_DECISION, Conflicto.CANALIZADO): e.demanda_borrador_creada,
        (Conflicto.CANALIZADO, Conflicto.CONCLUIDO): e.expediente_cerrado,
    }
    if not reglas.get((actual, nuevo), False):
        raise EstadoInvalido(f"Transición de conflicto no permitida: {actual} -> {nuevo}")


def validar_expediente(actual: Expediente, nuevo: Expediente, e: EvidenciaExpediente) -> None:
    resolucion_completa = e.resolucion_firmada and e.resultado_explicito and e.sello_tiempo
    reglas = {
        (Expediente.EN_TURNO, Expediente.EN_REVISION): e.turno_confirmado,
        (Expediente.EN_REVISION, Expediente.PREVENIDO): e.prevencion_registrada,
        (Expediente.PREVENIDO, Expediente.EN_REVISION): e.correccion_presentada,
        (Expediente.EN_REVISION, Expediente.ADMITIDO): e.admision_registrada,
        (Expediente.EN_REVISION, Expediente.DESECHADO): resolucion_completa,
        (Expediente.PREVENIDO, Expediente.DESECHADO): resolucion_completa,
        (Expediente.ADMITIDO, Expediente.EN_TRAMITE): e.emplazamiento_validado and (e.contestacion_registrada or e.plazo_vencido),
        (Expediente.EN_TRAMITE, Expediente.RESUELTO): resolucion_completa,
        (Expediente.RESUELTO, Expediente.CERRADO): resolucion_completa and e.firmeza,
        (Expediente.DESECHADO, Expediente.CERRADO): resolucion_completa and e.firmeza,
    }
    if not reglas.get((actual, nuevo), False):
        raise EstadoInvalido(f"Transición de expediente no permitida: {actual} -> {nuevo}")


def limite_contestacion(emplazamiento_validado: date) -> date:
    return emplazamiento_validado + timedelta(days=15)
