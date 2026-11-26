"""Migración 011: escenarios aportados por feature/modulo-ODR (idempotencia por clave, evento de canalización,
mensajes y notas de solo adición, notas ligadas a la asignación vigente)."""
import uuid

import psycopg
import pytest


def _canalizar(usuario, cid, clave):
    return usuario.app.post(f"/conflictos/{cid}/canalizar", headers={**usuario.h, "Idempotency-Key": str(clave)})


def test_misma_clave_misma_demanda_y_no_se_reutiliza_en_otro_conflicto(conflicto_orientado):
    actor, _, cid = conflicto_orientado()
    clave = uuid.uuid4()
    a = _canalizar(actor, cid, clave)
    assert a.status_code == 201, a.text
    assert _canalizar(actor, cid, clave).json()["demanda_id"] == a.json()["demanda_id"]

    otro_actor, _, otro = conflicto_orientado()
    assert _canalizar(otro_actor, otro, clave).status_code >= 400   # la clave ya pertenece a otra operación


def test_canalizacion_encola_un_evento_sin_contenido_y_la_tarea_avisa(conflicto_orientado, owner):
    from tareas import eventos_pendientes

    actor, _, cid = conflicto_orientado()
    _canalizar(actor, cid, uuid.uuid4())
    _canalizar(actor, cid, uuid.uuid4())       # reintento con otra clave: misma demanda, un solo evento
    eventos = owner.execute("SELECT * FROM nucleo_comun.evento_pendiente WHERE conflicto_id=%s", (cid,)).fetchall()
    assert len(eventos) == 1 and eventos[0]["tipo"] == "DemandaBorradorCreada"
    assert set(eventos[0]) == {"id", "tipo", "conflicto_id", "referencia_id", "creado_en", "procesado_en"}

    eventos_pendientes.procesar()
    assert owner.execute("SELECT procesado_en FROM nucleo_comun.evento_pendiente WHERE conflicto_id=%s", (cid,)).fetchone()["procesado_en"]
    avisos = [a["tipo"] for a in actor.get("/notificaciones").json()["avisos"]]
    assert avisos.count("DEMANDA_BORRADOR_LISTA") == 1
    eventos_pendientes.procesar()               # no duplica el aviso
    assert [a["tipo"] for a in actor.get("/notificaciones").json()["avisos"]].count("DEMANDA_BORRADOR_LISTA") == 1


def test_mensajes_y_notas_son_de_solo_adicion(negociacion, crear_usuario, owner):
    owner.execute("UPDATE schema_odr.mediador SET activo=false")
    med = crear_usuario("MEDIADOR", "CIVIL")
    actor, _, mid = negociacion()
    actor.post(f"/mediaciones/{mid}/solicitar-mediador")
    owner.execute("UPDATE schema_odr.mediador SET activo=true")
    assert actor.post(f"/mediaciones/{mid}/mensajes", {"texto": "Mensaje sintético"}).status_code == 201
    assert med.post(f"/mediaciones/{mid}/notas", {"texto": "Nota sintética"}).status_code == 201

    for tabla in ("mensaje", "nota_mediador"):
        with pytest.raises(psycopg.errors.RaiseException):
            owner.execute(f"UPDATE schema_odr.{tabla} SET contenido_cifrado=contenido_cifrado WHERE mediacion_id=%s", (mid,))
        with pytest.raises(psycopg.errors.RaiseException):
            owner.execute(f"DELETE FROM schema_odr.{tabla} WHERE mediacion_id=%s", (mid,))


def test_mediador_reasignado_deja_de_ver_sus_notas(negociacion, crear_usuario, owner):
    owner.execute("UPDATE schema_odr.mediador SET activo=false")
    anterior = crear_usuario("MEDIADOR", "CIVIL")
    actor, _, mid = negociacion()
    actor.post(f"/mediaciones/{mid}/solicitar-mediador")
    owner.execute("UPDATE schema_odr.mediador SET activo=true")
    assert anterior.post(f"/mediaciones/{mid}/notas", {"texto": "Nota previa a la reasignación"}).status_code == 201

    nuevo = crear_usuario("MEDIADOR", "CIVIL")
    owner.execute("UPDATE schema_odr.mediacion SET mediador_id=%s WHERE id=%s", (nuevo.id, mid))
    r = anterior.get(f"/mediaciones/{mid}/notas")
    assert r.status_code != 200 or r.json() == []
    assert nuevo.get(f"/mediaciones/{mid}/notas").json() == []    # las notas son personales del autor
