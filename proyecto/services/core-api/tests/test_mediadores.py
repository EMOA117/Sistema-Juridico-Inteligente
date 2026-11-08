"""RF3.4–RF3.8, RF4.1–RF4.2: asignación de mediador, agenda, notas confidenciales y revisión del convenio."""
from datetime import datetime, timedelta, timezone

import psycopg
import pytest


def test_asignacion_automatica_por_menor_carga(negociacion, crear_usuario, owner):
    # Se desactivan los demás mediadores para que la elección sea determinista en la base compartida.
    owner.execute("UPDATE schema_odr.mediador SET activo=false")
    libre, ocupado = crear_usuario("MEDIADOR", "CIVIL"), crear_usuario("MEDIADOR", "CIVIL")
    a1, _, m1 = negociacion()
    owner.execute("UPDATE schema_odr.mediacion SET mediador_id=%s, estado='CON_MEDIADOR' WHERE id=%s", (ocupado.id, m1))
    actor, otra, mid = negociacion()
    r = actor.post(f"/mediaciones/{mid}/solicitar-mediador")
    assert r.status_code == 200, r.text
    det = otra.get(f"/mediaciones/{mid}").json()
    assert det["estado"] == "CON_MEDIADOR" and det["mediador"]["nombre"].startswith("QA Mediador")
    assert libre.get(f"/mediaciones/{mid}").json()["soy_mediador"] is True
    assert ocupado.get(f"/mediaciones/{mid}").status_code == 404     # otro mediador no la ve
    owner.execute("UPDATE schema_odr.mediador SET activo=true")


def test_agenda_notas_y_conclusion(negociacion, crear_usuario, owner):
    owner.execute("UPDATE schema_odr.mediador SET activo=false")
    med = crear_usuario("MEDIADOR", "CIVIL")
    actor, otra, mid = negociacion()
    actor.post(f"/mediaciones/{mid}/solicitar-mediador")
    owner.execute("UPDATE schema_odr.mediador SET activo=true")

    inicio = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    assert med.post(f"/mediaciones/{mid}/sesiones", {"inicio": inicio, "modalidad": "VIDEOLLAMADA_CONJUNTA"}).status_code == 201
    assert actor.post(f"/mediaciones/{mid}/sesiones", {"inicio": inicio, "modalidad": "VIDEOLLAMADA_CONJUNTA"}).status_code == 403
    assert len(otra.get(f"/mediaciones/{mid}").json()["sesiones"]) == 1
    assert "SESION_PROGRAMADA" in [a["tipo"] for a in actor.get("/notificaciones").json()["avisos"]]

    assert med.post(f"/mediaciones/{mid}/notas", {"texto": "Nota privada sintética"}).status_code == 201
    assert med.get(f"/mediaciones/{mid}/notas").json()[0]["texto"] == "Nota privada sintética"
    assert actor.get(f"/mediaciones/{mid}/notas").status_code == 403     # las partes no leen notas
    cifrada = owner.execute("SELECT contenido_cifrado FROM schema_odr.nota_mediador WHERE mediacion_id=%s", (mid,)).fetchone()
    assert b"Nota privada" not in bytes(cifrada["contenido_cifrado"])

    assert med.post(f"/mediaciones/{mid}/concluir", {"resultado": "SIN_ACUERDO"}).status_code == 200
    estado = [c for c in actor.get("/conflictos").json() if c["folio"] == otra.get(f"/mediaciones/{mid}").json()["folio"]][0]["estado"]
    assert estado == "EN_ESPERA_DECISION"


def test_convenio_requiere_propuesta_aceptada_y_aprobaciones(negociacion):
    actor, otra, mid = negociacion()
    borrador = {"tipo": "PARCIAL", "terminos": "El deudor pagará $10,000 a la firma del convenio.", "puntos_pendientes": ["Intereses moratorios"]}
    assert actor.put(f"/mediaciones/{mid}/convenio", borrador).status_code == 422          # sin propuesta aceptada
    otra.post(f"/mediaciones/{mid}/propuestas", {"texto": "$10,000 a la firma"})
    pid = actor.get(f"/mediaciones/{mid}").json()["propuestas"][0]["id"]
    assert actor.post(f"/mediaciones/propuestas/{pid}/responder", {"estado": "ACEPTADA"}).status_code == 200
    assert actor.put(f"/mediaciones/{mid}/convenio", {**borrador, "puntos_pendientes": []}).status_code == 422  # parcial sin pendientes
    assert actor.put(f"/mediaciones/{mid}/convenio", borrador).status_code == 200
    assert actor.post(f"/mediaciones/{mid}/convenio/aprobar").status_code == 200
    v = otra.get(f"/mediaciones/{mid}/convenio").json()
    assert v["tipo"] == "PARCIAL" and not v["aprobado_por_todas"]
    assert otra.post(f"/mediaciones/{mid}/convenio/aprobar").status_code == 200
    assert otra.get(f"/mediaciones/{mid}/convenio").json()["aprobado_por_todas"]
    # Editar reinicia las aprobaciones.
    actor.put(f"/mediaciones/{mid}/convenio", {**borrador, "terminos": borrador["terminos"] + " Con recibo."})
    assert not otra.get(f"/mediaciones/{mid}/convenio").json()["aprobado_por_todas"]


def test_administracion_ve_asignaciones_pero_no_contenido(crear_usuario, owner):
    admin = crear_usuario("ADMINISTRADOR")
    padron = admin.get("/admin/mediadores").json()
    assert "mediadores" in padron and "asignaciones" in padron
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with owner.transaction():
            owner.execute("SET LOCAL ROLE rol_app_admin")
            owner.execute("SELECT * FROM schema_odr.mensaje LIMIT 1")
