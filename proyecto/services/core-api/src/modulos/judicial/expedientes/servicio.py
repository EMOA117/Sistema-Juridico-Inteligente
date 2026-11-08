"""P8/P9: expediente digital, bandeja del juez y dictamen preliminar (RF6, RF7.3, RF7.4)."""
from uuid import UUID

from compartido.auditoria.bitacora import registrar
from compartido.bd import RolBD, transaccion
from compartido.errores import NoEncontrado, ReglaNegocio
from modulos.identidad.autorizacion import Principal, Rol, exigir_acceso

_LISTA = ("SELECT e.id, e.numero, e.estado, e.creado_en, e.juez_id, d.materia, d.origen, c.folio,"
          " (SELECT string_agg(p.nombre, ' vs. ' ORDER BY p.rol DESC) FROM nucleo_comun.parte p WHERE p.conflicto_id = d.conflicto_id) partes"
          " FROM schema_judicial.expediente e JOIN schema_judicial.demanda d ON d.id = e.demanda_id"
          " JOIN nucleo_comun.conflicto c ON c.id = d.conflicto_id")


def _limpiar(f: dict) -> dict:
    return {**f, "id": str(f["id"]), "juez_id": f["juez_id"] and str(f["juez_id"])}


def bandeja(p: Principal) -> list[dict]:
    """Juez: solo los asignados. Ciudadano: los de sus asuntos (RLS)."""
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        sql = _LISTA + (" WHERE e.juez_id = nucleo_comun.actor_id()" if p.rol == Rol.JUEZ else "") + " ORDER BY e.creado_en DESC"
        return [_limpiar(f) for f in c.execute(sql).fetchall()]


def detalle(p: Principal, expediente_id: UUID) -> dict:
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        e = c.execute(_LISTA + " WHERE e.id=%s", (expediente_id,)).fetchone()
        if not e:
            raise NoEncontrado("Expediente no encontrado")
        extra = c.execute("SELECT d.id demanda_id, d.texto_final, d.narrativa_inicial, d.puntos_pendientes,"
                          " e.fecha_emplazamiento_validado, e.fecha_limite_contestacion"
                          " FROM schema_judicial.expediente e JOIN schema_judicial.demanda d ON d.id=e.demanda_id WHERE e.id=%s",
                          (expediente_id,)).fetchone()
        historial = c.execute("SELECT estado_anterior, estado_nuevo, motivo, ocurrido_en FROM schema_judicial.historial_estado"
                              " WHERE expediente_id=%s ORDER BY ocurrido_en", (expediente_id,)).fetchall()
        actuaciones = c.execute("SELECT tipo, texto, ocurrido_en FROM schema_judicial.actuacion"
                                " WHERE expediente_id=%s ORDER BY ocurrido_en", (expediente_id,)).fetchall()
        documentos = c.execute("SELECT id, tipo, nombre, hash_sha256, creado_en FROM nucleo_comun.documento"
                               " WHERE expediente_id=%s ORDER BY creado_en", (expediente_id,)).fetchall()
    return {**_limpiar(e), **extra, "demanda_id": str(extra["demanda_id"]), "historial": historial,
            "actuaciones": actuaciones, "documentos": [{**d, "id": str(d["id"])} for d in documentos],
            "soy_juez": e["juez_id"] == p.usuario_id}


def dictaminar(p: Principal, expediente_id: UUID, decision: str, texto: str | None) -> dict:
    """ADMITIR o PREVENIR. DESECHAR exige resolución firmada (se habilita con la firma institucional)."""
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        e = c.execute("SELECT id, estado, juez_id FROM schema_judicial.expediente WHERE id=%s FOR UPDATE",
                      (expediente_id,)).fetchone()
        if not e:
            raise NoEncontrado("Expediente no encontrado")
        exigir_acceso(p, "resolver", juez_id=e["juez_id"])
        if e["estado"] != "EN_REVISION":
            raise ReglaNegocio("Solo se dictamina un expediente en revisión")
        if decision == "PREVENIR" and not (texto and texto.strip()):
            raise ReglaNegocio("La prevención requiere indicar qué debe corregirse")
        nuevo = {"ADMITIR": "ADMITIDO", "PREVENIR": "PREVENIDO"}[decision]
        c.execute("INSERT INTO schema_judicial.actuacion (expediente_id, usuario_id, tipo, texto) VALUES (%s,%s,%s,%s)",
                  (expediente_id, p.usuario_id, f"DICTAMEN_{decision}", texto))
        c.execute("UPDATE schema_judicial.expediente SET estado=%s WHERE id=%s", (nuevo, expediente_id))
        registrar(c, usuario_id=p.usuario_id, entidad="expediente", entidad_id=expediente_id, accion=f"DICTAMEN_{decision}",
                  estado_anterior="EN_REVISION", estado_nuevo=nuevo)
        despues_de_dictamen(c, expediente_id, nuevo, p.usuario_id)
    return {"estado": nuevo}


def _conflicto_de(c, expediente_id: UUID) -> dict:
    return c.execute("SELECT d.conflicto_id, c.folio, e.juez_id FROM schema_judicial.expediente e"
                     " JOIN schema_judicial.demanda d ON d.id=e.demanda_id JOIN nucleo_comun.conflicto c ON c.id=d.conflicto_id"
                     " WHERE e.id=%s", (expediente_id,)).fetchone()


def despues_de_dictamen(c, expediente_id: UUID, estado: str, actor: UUID) -> None:
    from modulos.notificaciones.servicio import notificar
    notificar(c, _conflicto_de(c, expediente_id)["conflicto_id"], f"DICTAMEN_{estado}", "expediente", expediente_id,
              excluir=actor, incluir_mediador=False)


def corregir(p: Principal, expediente_id: UUID, texto: str) -> None:
    with transaccion(RolBD.JUDICIAL, p.usuario_id) as c:
        c.execute("SELECT schema_judicial.reenviar_correccion(%s, %s)", (expediente_id, texto))
        registrar(c, usuario_id=p.usuario_id, entidad="expediente", entidad_id=expediente_id, accion="CORRECCION_REENVIADA",
                  estado_anterior="PREVENIDO", estado_nuevo="EN_REVISION")
        from modulos.notificaciones.servicio import notificar_usuario
        info = _conflicto_de(c, expediente_id)
        notificar_usuario(c, info["juez_id"], "CORRECCION_PRESENTADA", info["folio"], "expediente", expediente_id)
