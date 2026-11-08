"""Descarga de documentos oficiales (con RLS por dominio) y verificación pública por huella SHA-256."""
from uuid import UUID

from compartido.bd import RolBD, transaccion
from compartido.documentos import almacen
from compartido.errores import NoEncontrado
from modulos.identidad.autorizacion import Principal


def descargar(p: Principal, documento_id: UUID) -> tuple[str, bytes]:
    for rol in (RolBD.ODR, RolBD.JUDICIAL):  # cada rol solo ve los documentos de su dominio que le corresponden
        with transaccion(rol, p.usuario_id) as c:
            d = c.execute("SELECT nombre, clave_objeto, version_objeto, hash_sha256 FROM nucleo_comun.documento WHERE id=%s",
                          (documento_id,)).fetchone()
        if d:
            datos = almacen.leer(d["clave_objeto"], version=d["version_objeto"] or None)
            if almacen.sha256(datos) != d["hash_sha256"].strip():
                raise RuntimeError("La huella del documento no coincide con el registro")  # integridad (RF6.5)
            return d["nombre"], datos
    raise NoEncontrado("Documento no encontrado")


def verificar(huella: str) -> dict:
    with transaccion(RolBD.AUTH, None) as c:
        f = c.execute("SELECT * FROM nucleo_comun.verificar_documento(%s)", (huella,)).fetchone()
    return {"valido": bool(f), **(f or {})}
