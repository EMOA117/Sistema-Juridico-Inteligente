"""P4: negociación asíncrona. Todo el contenido se cifra (AES-256-GCM) y nunca sale del dominio ODR."""
from uuid import UUID

from psycopg import Connection

from compartido.auditoria.bitacora import registrar
from compartido.bd import RolBD, transaccion
from compartido.cifrado import cifrar, descifrar
from compartido.errores import NoEncontrado, ReglaNegocio
from modulos.identidad.autorizacion import Principal

ACTIVOS = ("EN_NEGOCIACION", "CON_MEDIADOR")


def _mediacion(c: Connection, mediacion_id: UUID, *, bloquear: bool = False) -> dict:
    m = c.execute("SELECT m.*, c.folio, c.materia, c.estado AS estado_conflicto, c.solicitante_id"
                  " FROM schema_odr.mediacion m JOIN nucleo_comun.conflicto c ON c.id = m.conflicto_id"
                  " WHERE m.id = %s" + (" FOR UPDATE OF m" if bloquear else ""), (mediacion_id,)).fetchone()
    if not m:  # RLS: solo partes y mediador asignado
        raise NoEncontrado("Mediación no encontrada")
    return m


def _nombres(c: Connection, conflicto_id: UUID) -> dict:
    return {r["usuario_id"]: r["nombre"] for r in c.execute(
        "SELECT usuario_id, nombre FROM nucleo_comun.parte WHERE conflicto_id=%s AND usuario_id IS NOT NULL", (conflicto_id,))}


def listar(p: Principal) -> list[dict]:
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        filas = c.execute(
            "SELECT m.id, m.estado, m.resultado, c.folio, c.materia, c.id conflicto_id,"
            " (SELECT string_agg(x.nombre, ' vs. ' ORDER BY x.rol DESC) FROM nucleo_comun.parte x WHERE x.conflicto_id=c.id) partes,"
            " (SELECT count(*) FROM schema_odr.propuesta pr WHERE pr.mediacion_id=m.id) propuestas"
            " FROM schema_odr.mediacion m JOIN nucleo_comun.conflicto c ON c.id=m.conflicto_id ORDER BY c.creado_en DESC").fetchall()
    return [{**f, "id": str(f["id"]), "conflicto_id": str(f["conflicto_id"])} for f in filas]


def detalle(p: Principal, mediacion_id: UUID) -> dict:
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        m = _mediacion(c, mediacion_id)
        nombres = _nombres(c, m["conflicto_id"])
        msgs = c.execute("SELECT id, autor_id, contenido_cifrado, creado_en FROM schema_odr.mensaje"
                         " WHERE mediacion_id=%s ORDER BY creado_en", (mediacion_id,)).fetchall()
        props = c.execute("SELECT id, autor_id, contenido_cifrado, estado, creado_en FROM schema_odr.propuesta"
                          " WHERE mediacion_id=%s ORDER BY creado_en", (mediacion_id,)).fetchall()
        inv = c.execute("SELECT estado, fecha_limite FROM schema_odr.invitacion WHERE mediacion_id=%s"
                        " ORDER BY creado_en DESC LIMIT 1", (mediacion_id,)).fetchone()
        partes = c.execute("SELECT rol, nombre FROM nucleo_comun.parte WHERE conflicto_id=%s ORDER BY rol DESC",
                           (m["conflicto_id"],)).fetchall()

    def autor(uid):
        return "yo" if uid == p.usuario_id else ("mediador" if uid == m["mediador_id"] else "otra_parte")

    return {
        "id": str(m["id"]), "folio": m["folio"], "materia": m["materia"], "estado": m["estado"],
        "resultado": m["resultado"], "conflicto_id": str(m["conflicto_id"]),
        "soy_mediador": m["mediador_id"] == p.usuario_id, "tiene_mediador": m["mediador_id"] is not None,
        "invitacion": inv, "partes": partes,
        "mensajes": [{"id": str(x["id"]), "autor": autor(x["autor_id"]), "nombre": nombres.get(x["autor_id"], "Mediador"),
                      "texto": descifrar(x["contenido_cifrado"], f"mensaje:{mediacion_id}"), "fecha": x["creado_en"]} for x in msgs],
        "propuestas": [{"id": str(x["id"]), "numero": i + 1, "autor": autor(x["autor_id"]), "estado": x["estado"],
                        "resumen": descifrar(x["contenido_cifrado"], f"propuesta:{mediacion_id}"), "fecha": x["creado_en"]}
                       for i, x in enumerate(props)],
    }


def _exigir_activa(m: dict) -> None:
    if m["estado"] not in ACTIVOS:
        raise ReglaNegocio("La negociación no está abierta")


def enviar_mensaje(p: Principal, mediacion_id: UUID, texto: str) -> None:
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        _exigir_activa(_mediacion(c, mediacion_id))
        c.execute("INSERT INTO schema_odr.mensaje (mediacion_id, autor_id, contenido_cifrado) VALUES (%s,%s,%s)",
                  (mediacion_id, p.usuario_id, cifrar(texto, f"mensaje:{mediacion_id}")))


def enviar_propuesta(p: Principal, mediacion_id: UUID, texto: str) -> None:
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        m = _mediacion(c, mediacion_id)
        _exigir_activa(m)
        if m["mediador_id"] == p.usuario_id:
            raise ReglaNegocio("Las propuestas formales las hacen las partes")
        pid = c.execute("INSERT INTO schema_odr.propuesta (mediacion_id, autor_id, contenido_cifrado) VALUES (%s,%s,%s) RETURNING id",
                        (mediacion_id, p.usuario_id, cifrar(texto, f"propuesta:{mediacion_id}"))).fetchone()["id"]
        registrar(c, usuario_id=p.usuario_id, entidad="propuesta", entidad_id=pid, accion="PROPUESTA_ENVIADA")
        despues_de_propuesta(c, m, p.usuario_id)


def despues_de_propuesta(c: Connection, m: dict, autor_id: UUID) -> None:
    """Punto de extensión para notificaciones (fase 2)."""


def responder_propuesta(p: Principal, propuesta_id: UUID, estado: str) -> None:
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        pr = c.execute("SELECT * FROM schema_odr.propuesta WHERE id=%s FOR UPDATE", (propuesta_id,)).fetchone()
        if not pr:
            raise NoEncontrado("Propuesta no encontrada")
        m = _mediacion(c, pr["mediacion_id"])
        _exigir_activa(m)
        if pr["autor_id"] == p.usuario_id or m["mediador_id"] == p.usuario_id:
            raise ReglaNegocio("Solo la otra parte puede responder esta propuesta")
        if pr["estado"] != "PENDIENTE":
            raise ReglaNegocio("La propuesta ya fue respondida")
        c.execute("UPDATE schema_odr.propuesta SET estado=%s, respondida_por=%s WHERE id=%s", (estado, p.usuario_id, propuesta_id))
        registrar(c, usuario_id=p.usuario_id, entidad="propuesta", entidad_id=propuesta_id, accion=f"PROPUESTA_{estado}",
                  estado_anterior="PENDIENTE", estado_nuevo=estado)
        if estado == "ACEPTADA" and m["estado"] == "EN_NEGOCIACION":
            c.execute("UPDATE schema_odr.mediacion SET estado='PENDIENTE_FORMALIZACION' WHERE id=%s", (m["id"],))


def concluir(c: Connection, actor: UUID, m: dict, resultado: str) -> None:
    """Cierra la mediación (RF3.6). El conflicto queda en espera de la decisión del solicitante."""
    c.execute("UPDATE schema_odr.mediacion SET estado='CONCLUIDA', resultado=%s, concluida_en=now() WHERE id=%s",
              (resultado, m["id"]))
    registrar(c, usuario_id=actor, entidad="mediacion", entidad_id=m["id"], accion="MEDIACION_CONCLUIDA",
              estado_anterior=m["estado"], estado_nuevo=resultado)
    if resultado in ("SIN_ACUERDO", "DESISTIMIENTO", "NO_ACEPTADA"):
        c.execute("UPDATE nucleo_comun.conflicto SET estado='EN_ESPERA_DECISION' WHERE id=%s", (m["conflicto_id"],))
        registrar(c, usuario_id=actor, entidad="conflicto", entidad_id=m["conflicto_id"], accion="ESPERA_DECISION",
                  estado_anterior="EN_MEDIACION", estado_nuevo="EN_ESPERA_DECISION")


def terminar_por_parte(p: Principal, mediacion_id: UUID, resultado: str) -> None:
    if resultado not in ("SIN_ACUERDO", "DESISTIMIENTO"):
        raise ReglaNegocio("Una parte solo puede terminar sin acuerdo o desistir")
    with transaccion(RolBD.ODR, p.usuario_id) as c:
        m = _mediacion(c, mediacion_id, bloquear=True)
        if m["mediador_id"] == p.usuario_id:
            raise ReglaNegocio("El mediador registra la conclusión desde su portal")
        _exigir_activa(m)
        concluir(c, p.usuario_id, m, resultado)
