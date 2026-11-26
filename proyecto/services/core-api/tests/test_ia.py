"""Integración con ia-service: respaldo sin IA, autorización previa a RAG y aislamiento de trazas ODR."""
import httpx
import pytest


def _ia_disponible() -> bool:
    from compartido.config import config
    try:
        return httpx.get(f"{config().ia_url}/docs", timeout=2).status_code in (200, 401)
    except httpx.HTTPError:
        return False


def test_sin_ia_la_orientacion_usa_reglas(crear_usuario, monkeypatch):
    from compartido.config import config
    monkeypatch.setattr(config(), "ia_url", "http://localhost:9")        # puerto cerrado: IA no disponible
    a = crear_usuario()
    cid = a.post("/conflictos", {"solicitante": {"nombre": "Actor QA"}, "contraparte": {"nombre": "Otra QA"}}).json()["id"]
    r = a.put(f"/conflictos/{cid}/narrativa", {"narrativa": "No me pagan la renta del local desde hace dos meses."}).json()
    assert r["origen"] == "REGLAS" and r["materia"] == "CIVIL"


def test_sin_ia_la_demanda_usa_plantilla(conflicto_orientado, monkeypatch):
    from compartido.config import config
    monkeypatch.setattr(config(), "ia_url", "http://localhost:9")
    actor, _, cid = conflicto_orientado()
    did = actor.post(f"/conflictos/{cid}/canalizar").json()["demanda_id"]
    r = actor.post(f"/demandas/{did}/borrador", {"pretension": "Pago de lo prestado", "tipo_juicio": "Juicio oral civil"}).json()
    assert r["origen"] == "PLANTILLA" and "P R E S T A C I O N E S" in r["texto"]


def test_rag_rechaza_juez_no_titular_antes_de_llamar_a_la_ia(conflicto_orientado, crear_usuario, monkeypatch):
    llamadas = []
    from modulos import ia_cliente
    monkeypatch.setattr(ia_cliente, "consultar_rag", lambda d: llamadas.append(d) or {"sintesis": None, "fragmentos": []})
    actor, _, cid = conflicto_orientado()
    did = actor.post(f"/conflictos/{cid}/canalizar").json()["demanda_id"]
    texto = actor.post(f"/demandas/{did}/borrador", {"pretension": "Pago total", "tipo_juicio": "Juicio oral civil"}).json()["texto"]
    eid = actor.post(f"/demandas/{did}/confirmar", {"texto": texto}).json()["expediente_id"]
    admin, juez_a, juez_b = crear_usuario("ADMINISTRADOR"), crear_usuario("JUEZ"), crear_usuario("JUEZ")
    admin.post(f"/admin/expedientes/{eid}/asignar", {"juez_id": str(juez_a.id)})
    assert juez_b.post(f"/expedientes/{eid}/consulta", {"pregunta": "¿Qué pruebas hay del pago?"}).status_code == 403
    assert llamadas == []                                              # la IA ni siquiera se consultó
    assert actor.post(f"/expedientes/{eid}/consulta", {"pregunta": "¿Qué pruebas hay del pago?"}).status_code == 403
    assert juez_a.post(f"/expedientes/{eid}/consulta", {"pregunta": "¿Qué pruebas hay del pago?"}).status_code == 200
    assert llamadas and llamadas[0]["expediente_id"] == eid


@pytest.mark.ia_real
@pytest.mark.skipif(not _ia_disponible(), reason="ia-service no está corriendo")
def test_sugerencia_odr_se_registra_solo_en_ia_uso_odr(negociacion):
    from pymongo import MongoClient
    actor, otra, mid = negociacion()
    otra.post(f"/mediaciones/{mid}/propuestas", {"texto": "Pago de $10,000 en dos partes"})
    mongo = MongoClient("mongodb://localhost:27018/?directConnection=true")
    antes_judicial = mongo["ia_uso"]["interacciones_ia"].count_documents({"tipo": "RECOMENDACION_ODR"})
    r = actor.get(f"/mediaciones/{mid}/sugerencia").json()
    assert r["disponible"] is True
    assert mongo["ia_uso"]["interacciones_ia"].count_documents({"tipo": "RECOMENDACION_ODR"}) == antes_judicial == 0
    assert mongo["ia_uso_odr"]["interacciones_ia"].count_documents({"tipo": "RECOMENDACION_ODR"}) > 0
    # Ningún contenido de negociación llega al corpus del expediente judicial.
    assert mongo["ia_conocimiento"]["fragmentos"].count_documents({"texto": {"$regex": "dos partes"}}) == 0
