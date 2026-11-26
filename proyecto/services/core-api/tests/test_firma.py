"""RF4.3–RF4.4, RF9.1–RF9.5: firma PAdES con sello de tiempo, almacenamiento WORM, verificación y cierre."""
from datetime import date, timedelta
from io import BytesIO

import pyotp
import pytest
from botocore.exceptions import ClientError
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext

from compartido.firma.pki_local import certificado_ca_asn1


def _firmas_validas(pdf: bytes) -> list:
    vc = ValidationContext(trust_roots=[certificado_ca_asn1()], allow_fetching=False)
    return [validate_pdf_signature(s, vc) for s in PdfFileReader(BytesIO(pdf)).embedded_signatures]


def _cred(u):
    return {"contrasena": u.password, "codigo_mfa": u.secreto and pyotp.TOTP(u.secreto).now()}


def _convenio_aprobado(negociacion, crear_usuario, owner, tipo="TOTAL"):
    owner.execute("UPDATE schema_odr.mediador SET activo=false")
    med = crear_usuario("MEDIADOR", "CIVIL")
    actor, otra, mid = negociacion()
    actor.post(f"/mediaciones/{mid}/solicitar-mediador")
    owner.execute("UPDATE schema_odr.mediador SET activo=true")
    borrador = {"tipo": tipo, "terminos": "Primera. El deudor pagará $10,000 a la firma con recibo firmado.",
                "puntos_pendientes": ["Intereses moratorios"] if tipo == "PARCIAL" else []}
    assert med.put(f"/mediaciones/{mid}/convenio", borrador).status_code == 200
    return actor, otra, med, mid


def test_convenio_total_firmado_formalizado_y_verificable(app, negociacion, crear_usuario, owner):
    actor, otra, med, mid = _convenio_aprobado(negociacion, crear_usuario, owner)
    assert actor.post(f"/mediaciones/{mid}/convenio/firmar", _cred(actor)).status_code == 422   # falta aprobación
    actor.post(f"/mediaciones/{mid}/convenio/aprobar")
    otra.post(f"/mediaciones/{mid}/convenio/aprobar")
    assert actor.post(f"/mediaciones/{mid}/convenio/firmar", {"contrasena": "incorrecta-1234"}).status_code == 422
    assert actor.post(f"/mediaciones/{mid}/convenio/firmar", _cred(actor)).json()["formalizado"] is False
    assert med.put(f"/mediaciones/{mid}/convenio", {"tipo": "TOTAL", "terminos": "Cambio posterior a la primera firma."}).status_code == 409
    assert otra.post(f"/mediaciones/{mid}/convenio/firmar", _cred(otra)).json()["formalizado"] is False
    fin = med.post(f"/mediaciones/{mid}/convenio/firmar", _cred(med)).json()
    assert fin["formalizado"] is True

    v = actor.get(f"/mediaciones/{mid}/convenio").json()
    assert v["formalizado_en"] and v["hash_sha256"] == fin["hash_sha256"]
    pdf = actor.app.get(f"/documentos/{v['documento_id']}", headers=actor.h).content
    estados = _firmas_validas(pdf)
    assert len(estados) == 3 and all(s.intact and s.valid and s.trusted and s.timestamp_validity for s in estados)

    assert app.get(f"/verificar/{fin['hash_sha256']}").json()["valido"] is True
    assert app.get(f"/verificar/{'0' * 64}").json()["valido"] is False
    conflictos = [c for c in actor.get("/conflictos").json() if c["folio"] == v["folio"]]
    assert conflictos[0]["estado"] == "CONCLUIDO"
    assert actor.get(f"/mediaciones/{mid}").json()["resultado"] == "ACUERDO_TOTAL"


def test_documento_formalizado_es_inmutable(negociacion, crear_usuario, owner):
    from compartido.documentos import almacen
    actor, otra, med, mid = _convenio_aprobado(negociacion, crear_usuario, owner)
    actor.post(f"/mediaciones/{mid}/convenio/aprobar"); otra.post(f"/mediaciones/{mid}/convenio/aprobar")
    for u in (actor, otra, med):
        u.post(f"/mediaciones/{mid}/convenio/firmar", _cred(u))
    d = owner.execute("SELECT d.clave_objeto, d.version_objeto FROM nucleo_comun.documento d"
                      " JOIN schema_odr.convenio v ON v.documento_id=d.id WHERE v.mediacion_id=%s", (mid,)).fetchone()
    with pytest.raises(ClientError):
        almacen.borrar_inmutable(d["clave_objeto"], d["version_objeto"])
    with pytest.raises(Exception):
        owner.execute("UPDATE schema_odr.convenio SET puntos_pendientes='{}' WHERE mediacion_id=%s", (mid,))


def test_convenio_parcial_permite_canalizar_solo_pendientes(negociacion, crear_usuario, owner):
    actor, otra, med, mid = _convenio_aprobado(negociacion, crear_usuario, owner, "PARCIAL")
    actor.post(f"/mediaciones/{mid}/convenio/aprobar"); otra.post(f"/mediaciones/{mid}/convenio/aprobar")
    for u in (actor, otra, med):
        u.post(f"/mediaciones/{mid}/convenio/firmar", _cred(u))
    cid = actor.get(f"/mediaciones/{mid}").json()["conflicto_id"]
    d = actor.get(f"/demandas/{actor.post(f'/conflictos/{cid}/canalizar').json()['demanda_id']}").json()
    assert d["origen"] == "ACUERDO_PARCIAL" and d["puntos_pendientes"] == ["Intereses moratorios"]
    assert "10,000" not in str(d)       # los términos acordados no viajan a la vía judicial


def test_ruta_judicial_hasta_cierre_con_resolucion_firmada(conflicto_orientado, crear_usuario, owner):
    actor, _, cid = conflicto_orientado()
    did = actor.post(f"/conflictos/{cid}/canalizar").json()["demanda_id"]
    texto = actor.post(f"/demandas/{did}/borrador", {"pretension": "Pago de lo prestado", "tipo_juicio": "Juicio oral civil"}).json()["texto"]
    eid = actor.post(f"/demandas/{did}/confirmar", {"texto": texto}).json()["expediente_id"]
    admin, juez = crear_usuario("ADMINISTRADOR"), crear_usuario("JUEZ")
    admin.post(f"/admin/expedientes/{eid}/asignar", {"juez_id": str(juez.id)})
    juez.post(f"/expedientes/{eid}/dictamen", {"decision": "ADMITIR"})
    assert juez.post(f"/expedientes/{eid}/firmeza", {"fecha": date.today().isoformat()}).status_code == 422  # sin resolución
    assert juez.post(f"/expedientes/{eid}/emplazamiento", {"fecha": (date.today() - timedelta(days=20)).isoformat()}).status_code == 200
    assert juez.post(f"/expedientes/{eid}/tramite").status_code == 200
    resolucion = {"tipo": "SENTENCIA", "resultado": "Se condena al pago de la cantidad reclamada",
                  "texto": "Considerando que la parte actora acreditó el préstamo con las pruebas documentales ofrecidas... " * 2}
    assert juez.post(f"/expedientes/{eid}/resolucion", {**resolucion, "contrasena": juez.password, "codigo_mfa": "000000"}).status_code == 422
    r = juez.post(f"/expedientes/{eid}/resolucion", {**resolucion, **_cred(juez)})
    assert r.status_code == 201, r.text
    assert juez.post(f"/expedientes/{eid}/firmeza", {"fecha": (date.today() - timedelta(days=5)).isoformat()}).status_code == 422
    assert juez.post(f"/expedientes/{eid}/firmeza", {"fecha": date.today().isoformat()}).status_code == 200
    e = actor.get(f"/expedientes/{eid}").json()
    assert e["estado"] == "CERRADO" and e["resolucion"]["fecha_firmeza"]
    pdf = actor.app.get(f"/documentos/{e['resolucion']['documento_id']}", headers=actor.h).content
    assert all(s.valid and s.trusted for s in _firmas_validas(pdf))
    assert [c for c in actor.get("/conflictos").json() if c["id"] == cid][0]["estado"] == "CONCLUIDO"
