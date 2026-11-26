"""P3 / P13: invitación con token, aceptación, rechazo, vencimiento y avisos sin contenido ODR."""
import re

from modulos.odr.invitaciones import hash_token


def _invitar(actor, otra, cid):
    r = actor.post(f"/conflictos/{cid}/mediacion", {"plazo_dias": 7})
    assert r.status_code == 201, r.text
    return r.json()["mediacion_id"]


def _token_de(owner, mediacion_id):
    """Recupera el token desde el enlace cifrado de la notificación (como haría el correo)."""
    from compartido.cifrado import descifrar
    n = owner.execute("SELECT n.enlace_cifrado, n.entidad_id FROM nucleo_comun.notificacion n"
                      " JOIN schema_odr.invitacion i ON i.id = n.entidad_id WHERE i.mediacion_id=%s", (mediacion_id,)).fetchone()
    return descifrar(n["enlace_cifrado"], f"enlace:{n['entidad_id']}").rsplit("/", 1)[1]


def test_token_no_se_guarda_en_claro(owner, conflicto_orientado):
    actor, otra, cid = conflicto_orientado()
    mid = _invitar(actor, otra, cid)
    token = _token_de(owner, mid)
    assert len(token) == 43
    fila = owner.execute("SELECT token_hash FROM schema_odr.invitacion WHERE mediacion_id=%s", (mid,)).fetchone()
    assert fila["token_hash"] == hash_token(token)
    assert not owner.execute("SELECT 1 FROM nucleo_comun.notificacion WHERE enlace LIKE %s", (f"%{token}%",)).fetchone()


def test_aceptar_abre_negociacion_y_avisa(owner, app, conflicto_orientado, crear_usuario):
    actor, otra, cid = conflicto_orientado()
    mid = _invitar(actor, otra, cid)
    token = _token_de(owner, mid)
    publico = app.get(f"/invitaciones/{token}").json()
    assert publico["estado"] == "ENVIADA" and "narrativa" not in publico
    assert actor.post(f"/invitaciones/{token}/responder", {"acepta": True}).status_code == 409   # no se auto-acepta
    assert otra.post(f"/invitaciones/{token}/responder", {"acepta": True}).status_code == 200
    assert otra.get(f"/mediaciones/{mid}").json()["estado"] == "EN_NEGOCIACION"
    assert otra.post(f"/invitaciones/{token}/responder", {"acepta": True}).status_code == 409   # un solo uso
    tipos = [a["tipo"] for a in actor.get("/notificaciones").json()["avisos"]]
    assert "INVITACION_ACEPTADA" in tipos

    otra.post(f"/mediaciones/{mid}/mensajes", {"texto": "Propongo pagar en dos partes, texto confidencial"})
    avisos = actor.get("/notificaciones").json()["avisos"]
    assert avisos[0]["tipo"] == "MENSAJE_NUEVO"
    assert "confidencial" not in str(avisos)


def test_rechazo_deja_conflicto_en_espera(owner, conflicto_orientado):
    actor, otra, cid = conflicto_orientado()
    mid = _invitar(actor, otra, cid)
    assert otra.post(f"/invitaciones/{_token_de(owner, mid)}/responder", {"acepta": False}).status_code == 200
    estado = [c for c in actor.get("/conflictos").json() if c["id"] == cid][0]["estado"]
    assert estado == "EN_ESPERA_DECISION"
    # Ruta judicial por invitación no aceptada: origen NO_ACEPTADA.
    did = actor.post(f"/conflictos/{cid}/canalizar").json()["demanda_id"]
    assert actor.get(f"/demandas/{did}").json()["origen"] == "NO_ACEPTADA"


def test_vencimiento_de_invitacion(owner, conflicto_orientado):
    actor, otra, cid = conflicto_orientado()
    mid = _invitar(actor, otra, cid)
    owner.execute("ALTER TABLE schema_odr.invitacion DISABLE TRIGGER ALL")
    owner.execute("UPDATE schema_odr.invitacion SET creado_en = now() - interval '20 days', fecha_limite = CURRENT_DATE - 1"
                  " WHERE mediacion_id=%s", (mid,))
    owner.execute("ALTER TABLE schema_odr.invitacion ENABLE TRIGGER ALL")
    from tareas import vencimiento_invitaciones
    assert vencimiento_invitaciones.ejecutar() >= 1
    assert actor.get(f"/mediaciones/{mid}").json()["resultado"] == "NO_ACEPTADA"
    assert "INVITACION_VENCIDA" in [a["tipo"] for a in actor.get("/notificaciones").json()["avisos"]]


def test_correo_enviado_sin_contenido_odr(owner, conflicto_orientado):
    import httpx
    actor, otra, cid = conflicto_orientado()
    _invitar(actor, otra, cid)
    from tareas import envio_notificaciones
    envio_notificaciones.despachar_lote(200)
    msgs = httpx.get("http://localhost:8025/api/v1/search", params={"query": f"to:{otra.correo}"}).json()["messages"]
    assert msgs, "Mailpit no recibió la invitación"
    cuerpo = httpx.get(f"http://localhost:8025/api/v1/message/{msgs[0]['ID']}").json()["Text"]
    assert re.search(r"/invitacion/[A-Za-z0-9_-]{43}", cuerpo)
    assert "presté" not in cuerpo  # la narrativa no viaja por correo
