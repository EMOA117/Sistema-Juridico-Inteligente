"""Firma electrónica institucional (RNF5.1). `ProveedorFirma` aísla el mecanismo: hoy una PKI local de prueba;
en producción, el proveedor de firma del Tribunal sin cambiar los módulos de negocio."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from psycopg import Connection


@dataclass(frozen=True)
class ResultadoFirma:
    pdf: bytes
    num_serie: str
    sello_tiempo: datetime


class ProveedorFirma(Protocol):
    def firmar_pdf(self, conn: Connection, usuario_id: UUID, nombre: str, pdf: bytes, campo: str) -> ResultadoFirma: ...


def proveedor() -> ProveedorFirma:
    from compartido.firma.pki_local import PkiLocal
    return PkiLocal()
