"""Flujo base y pruebas obligatorias del límite ODR → judicial (decisión 002)."""
import psycopg
import pytest


def test_orientacion_exige_partes_antes_del_relato(crear_usuario):
    a = crear_usuario()
    r = a.post("/conflictos", {"solicitante": {"nombre": "Actor QA"}, "contraparte": {"nombre": "Otra QA"}})
    cid = r.json()["id"]
    res = a.put(f"/conflictos/{cid}/narrativa", {"narrativa": "Mi expareja no paga la pensión alimenticia de nuestros hijos."})
    assert res.status_code == 200
    assert res.json()["materia"] == "FAMILIAR"


def test_canalizacion_rechaza_campos_extra_y_es_idempotente(conflicto_orientado):
    actor, _, cid = conflicto_orientado()
    assert actor.post(f"/conflictos/{cid}/canalizar", {"mensajes": ["texto ODR"]}).status_code == 422
    a = actor.post(f"/conflictos/{cid}/canalizar").json()["demanda_id"]
    b = actor.post(f"/conflictos/{cid}/canalizar").json()["demanda_id"]
    assert a == b


def test_otra_persona_no_puede_canalizar(conflicto_orientado, crear_usuario):
    _, _, cid = conflicto_orientado()
    intruso = crear_usuario()
    assert intruso.post(f"/conflictos/{cid}/canalizar").status_code in (403, 409)


def test_mediacion_activa_no_se_canaliza(owner, conflicto_orientado):
    actor, _, cid = conflicto_orientado()
    owner.execute("SELECT set_config('app.usuario_id', %s, false)", (str(actor.id),))
    owner.execute("UPDATE nucleo_comun.conflicto SET estado='EN_MEDIACION' WHERE id=%s", (cid,))
    owner.execute("INSERT INTO schema_odr.mediacion (conflicto_id, estado) VALUES (%s,'EN_NEGOCIACION')", (cid,))
    assert actor.post(f"/conflictos/{cid}/canalizar").status_code == 409


def test_juez_sin_acceso_a_odr_en_bd(owner):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with owner.transaction():
            owner.execute("SET LOCAL ROLE rol_app_judicial")
            owner.execute("SELECT * FROM schema_odr.mensaje LIMIT 1")


def test_flujo_judicial_completo_y_juez_ajeno(conflicto_orientado, crear_usuario):
    actor, _, cid = conflicto_orientado()
    did = actor.post(f"/conflictos/{cid}/canalizar").json()["demanda_id"]
    texto = actor.post(f"/demandas/{did}/borrador", {"pretension": "Pago de lo prestado", "tipo_juicio": "Juicio oral civil"}).json()["texto"]
    exp = actor.post(f"/demandas/{did}/confirmar", {"texto": texto})
    assert exp.status_code == 201, exp.text
    eid = exp.json()["expediente_id"]

    admin, juez, otro_juez = crear_usuario("ADMINISTRADOR"), crear_usuario("JUEZ"), crear_usuario("JUEZ")
    assert admin.post(f"/admin/expedientes/{eid}/asignar", {"juez_id": str(juez.id)}).status_code == 200
    assert otro_juez.get(f"/expedientes/{eid}").status_code == 404           # RLS: no existe para otro juez
    assert otro_juez.post(f"/expedientes/{eid}/dictamen", {"decision": "ADMITIR"}).status_code in (403, 404)
    assert juez.post(f"/expedientes/{eid}/dictamen", {"decision": "PREVENIR"}).status_code == 422  # sin motivo
    assert juez.post(f"/expedientes/{eid}/dictamen", {"decision": "PREVENIR", "texto": "Anexe pruebas"}).json()["estado"] == "PREVENIDO"
    assert actor.post(f"/expedientes/{eid}/correccion", {"texto": texto + "\nCorrección."}).status_code == 200
    assert juez.post(f"/expedientes/{eid}/dictamen", {"decision": "ADMITIR"}).json()["estado"] == "ADMITIDO"
    hist = [h["estado_nuevo"] for h in juez.get(f"/expedientes/{eid}").json()["historial"]]
    assert hist == ["EN_REVISION", "PREVENIDO", "EN_REVISION", "ADMITIDO"]


def test_ciudadano_no_usa_portal_administrativo(crear_usuario):
    assert crear_usuario().get("/admin/indicadores").status_code == 403


def test_respuesta_a_propuesta_sin_modificar_contenido(negociacion, owner):
    actor, otra, mid = negociacion()
    otra.post(f"/mediaciones/{mid}/propuestas", {"texto": "Pago en dos partes"})
    pid = actor.get(f"/mediaciones/{mid}").json()["propuestas"][0]["id"]
    assert otra.post(f"/mediaciones/propuestas/{pid}/responder", {"estado": "ACEPTADA"}).status_code == 422  # el autor no responde
    assert actor.post(f"/mediaciones/propuestas/{pid}/responder", {"estado": "RECHAZADA"}).status_code == 200
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with owner.transaction():
            owner.execute("SET LOCAL ROLE rol_app_odr")
            owner.execute("UPDATE schema_odr.propuesta SET contenido_cifrado='\\x00' WHERE id=%s", (pid,))
