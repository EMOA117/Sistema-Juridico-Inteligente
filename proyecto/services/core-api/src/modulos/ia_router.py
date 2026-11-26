"""Funciones de IA expuestas al portal: siempre detrás de la autorización de core-api (RF8.6: solo apoyo)."""
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field

from compartido.auditoria.bitacora import registrar
from compartido.bd import RolBD, transaccion
from compartido.documentos import almacen
from compartido.errores import NoEncontrado, ReglaNegocio
from compartido.seguridad.dependencias import Sesion, exigir_rol
from modulos import ia_cliente
from modulos.documentos.indexacion import encolar_anexo, paginas_de
from modulos.identidad.autorizacion import AccesoDenegado, Rol
from modulos.odr.servicio import _mediacion

router = APIRouter(tags=["ia"])
MAX_ANEXO = 10 * 1024 * 1024


class Consulta(BaseModel):
    pregunta: str = Field(min_length=5, max_length=500)
    incluir_expediente: bool = True
    incluir_publico: bool = True


@router.get("/mediaciones/{mediacion_id}/sugerencia")
def sugerencia_acuerdo(mediacion_id: UUID, p: Sesion):
    """RF3.3: las partes ven una fórmula sugerida; la traza queda solo en ia_uso_odr."""
    from compartido.cifrado import descifrar
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        m = _mediacion(c, mediacion_id)
        narrativa = c.execute("SELECT narrativa_inicial FROM nucleo_comun.conflicto WHERE id=%s", (m["conflicto_id"],)).fetchone()["narrativa_inicial"]
        propuestas = [descifrar(x["contenido_cifrado"], f"propuesta:{mediacion_id}") for x in c.execute(
            "SELECT contenido_cifrado FROM schema_odr.propuesta WHERE mediacion_id=%s ORDER BY creado_en", (mediacion_id,))]
        nombres = [x["nombre"] for x in c.execute("SELECT nombre FROM nucleo_comun.parte WHERE conflicto_id=%s", (m["conflicto_id"],))]
    r = ia_cliente.sugerir_acuerdo(m["materia"], narrativa or "", propuestas, nombres)
    if r is None:
        return {"disponible": False}
    return {"disponible": True, **r}


@router.get("/admin/expedientes/{expediente_id}/sugerencia-turno")
def sugerencia_turno(expediente_id: UUID, p: Sesion):
    """RF7.2: puntaje y justificación; la asignación la confirma el personal administrativo."""
    exigir_rol(p, Rol.ADMINISTRADOR)
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        e = c.execute("SELECT e.id, d.materia FROM schema_judicial.expediente e JOIN schema_judicial.demanda d ON d.id=e.demanda_id"
                      " WHERE e.id=%s", (expediente_id,)).fetchone()
        if not e:
            raise NoEncontrado("Expediente no encontrado")
        carga = c.execute("SELECT juez_id, juzgado_id, especialidad, expedientes_activos FROM schema_judicial.v_carga_jueces").fetchall()
    candidatos = [{k: (str(v) if k.endswith("_id") else v) for k, v in x.items()} for x in carga]
    r = ia_cliente.sugerir_turno(str(expediente_id), e["materia"], candidatos)
    return {"disponible": r is not None, **(r or {"sugerencias": []})}


@router.post("/expedientes/{expediente_id}/consulta")
def consulta_rag(expediente_id: UUID, datos: Consulta, p: Sesion):
    """P11: se verifica que el juez sea el titular ANTES de invocar la búsqueda (403 si no)."""
    exigir_rol(p, Rol.JUEZ)
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        e = c.execute("SELECT e.id, e.juez_id, d.materia FROM schema_judicial.expediente e"
                      " JOIN schema_judicial.demanda d ON d.id=e.demanda_id WHERE e.id=%s", (expediente_id,)).fetchone()
        if not e or e["juez_id"] != p.usuario_id:
            raise AccesoDenegado("Solo el juez titular puede consultar este expediente")
        registrar(c, usuario_id=p.usuario_id, entidad="expediente", entidad_id=expediente_id, accion="CONSULTA_RAG")
    r = ia_cliente.consultar_rag({"expediente_id": str(expediente_id), "materia": e["materia"], "juez_id": str(p.usuario_id),
                                  "pregunta": datos.pregunta, "incluir_expediente": datos.incluir_expediente,
                                  "incluir_publico": datos.incluir_publico})
    if r is None:
        return {"disponible": False, "sintesis": None, "fragmentos": []}
    return {"disponible": True, **r}


@router.post("/expedientes/{expediente_id}/documentos", status_code=201)
async def subir_anexo(expediente_id: UUID, p: Sesion, archivo: Annotated[UploadFile, File()]):
    """RF6.2: anexos al expediente (PDF o texto). Se guardan inmutables y se indexan en segundo plano."""
    nombre = archivo.filename or "anexo"
    if not nombre.lower().endswith((".pdf", ".txt")):
        raise ReglaNegocio("Solo se aceptan archivos PDF o de texto")
    datos = await archivo.read(MAX_ANEXO + 1)
    if len(datos) > MAX_ANEXO:
        raise ReglaNegocio("El archivo supera 10 MB")
    try:
        paginas = len(paginas_de(nombre, datos))
    except Exception as e:  # noqa: BLE001 — PDF corrupto
        raise ReglaNegocio("No se pudo leer el archivo") from e
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        e = c.execute("SELECT e.id, e.numero, e.estado, d.conflicto_id FROM schema_judicial.expediente e"
                      " JOIN schema_judicial.demanda d ON d.id=e.demanda_id WHERE e.id=%s", (expediente_id,)).fetchone()
        if not e:
            raise NoEncontrado("Expediente no encontrado")
        if e["estado"] == "CERRADO":
            raise ReglaNegocio("El expediente está cerrado: no admite documentos nuevos")
        huella = almacen.sha256(datos)
        clave = f"expedientes/{e['numero'].replace('/', '-')}/anexos/{huella}-{nombre}"
        version = almacen.guardar_inmutable(clave, datos, "application/pdf" if nombre.lower().endswith(".pdf") else "text/plain")
        doc_id = uuid4()
        c.execute("INSERT INTO nucleo_comun.documento (id, dominio, conflicto_id, expediente_id, tipo, nombre, clave_objeto,"
                  " version_objeto, hash_sha256, paginas, subido_por) VALUES (%s,'JUDICIAL',%s,%s,'ANEXO',%s,%s,%s,%s,%s,%s)",
                  (doc_id, e["conflicto_id"], expediente_id, nombre, clave, version, huella, paginas, p.usuario_id))
        encolar_anexo(c, expediente_id, doc_id)
        registrar(c, usuario_id=p.usuario_id, entidad="documento", entidad_id=doc_id, accion="ANEXO_CARGADO")
    return {"id": str(doc_id), "hash_sha256": huella}
