"""P1: registro con CURP, bloqueo por intentos, MFA obligatorio para personal y alta de personal."""
import random
import string
import uuid

import pyotp

from compartido.validacion import digito_curp


def curp_valida() -> str:
    base = ("PELA" + f"{random.randint(50, 99)}0101" + "M" + "DF" + "RPN" + random.choice(string.ascii_uppercase))
    return base + str(digito_curp(base))


def test_registro_y_login_ciudadano(app):
    correo = f"qa-{uuid.uuid4().hex[:8]}@pruebas.test"
    r = app.post("/auth/registro", json={"nombre": "Ciudadana QA", "correo": correo, "curp": curp_valida(),
                                         "contrasena": "una-clave-larga-2026"})
    assert r.status_code == 201, r.text
    assert r.json()["usuario"]["rol"] == "CIUDADANO"
    assert app.post("/auth/login", json={"correo": correo, "contrasena": "una-clave-larga-2026"}).status_code == 200


def test_registro_rechaza_curp_y_password_debiles(app):
    base = {"nombre": "Ciudadana QA", "correo": f"qa-{uuid.uuid4().hex[:8]}@pruebas.test"}
    assert app.post("/auth/registro", json={**base, "curp": "PELA900101MDFRPN00", "contrasena": "una-clave-larga-2026"}).status_code == 422
    assert app.post("/auth/registro", json={**base, "curp": curp_valida(), "contrasena": "corta1"}).status_code == 422


def test_bloqueo_tras_cinco_intentos(crear_usuario, app):
    u = crear_usuario()
    for _ in range(5):
        assert app.post("/auth/login", json={"correo": u.correo, "contrasena": "incorrecta-123"}).status_code == 422
    r = app.post("/auth/login", json={"correo": u.correo, "contrasena": u.password})
    assert r.status_code == 422 and "bloqueada" in r.json()["detail"]


def test_personal_requiere_codigo_mfa(crear_usuario, app):
    juez = crear_usuario("JUEZ")
    assert juez.login(codigo="000000").status_code == 422
    assert juez.login().status_code == 200
    assert juez.login().json()["usuario"]["mfa"] is True


def test_token_sin_mfa_no_accede_a_funciones_de_personal(crear_usuario, app):
    admin = crear_usuario("ADMINISTRADOR")
    alta = admin.app.post("/admin/usuarios", headers=admin.h,
                          json={"nombre": "Mediadora QA nueva", "correo": f"qa-{uuid.uuid4().hex[:8]}@pruebas.test", "rol": "MEDIADOR"})
    assert alta.status_code == 201, alta.text
    nuevo = {"correo": None, "contrasena": alta.json()["contrasena_temporal"]}
    lista = admin.get("/admin/usuarios").json()
    nuevo["correo"] = next(x["correo"] for x in lista if x["id"] == alta.json()["id"])

    r = app.post("/auth/login", json=nuevo).json()
    assert r["requiere_alta_mfa"] and r["debe_cambiar_password"]
    h = {"Authorization": "Bearer " + r["token"]}
    assert app.get("/mediaciones", headers=h).status_code == 403      # sin MFA no opera

    assert app.post("/auth/cambiar-contrasena", headers=h, json={"actual": nuevo["contrasena"], "nueva": "nueva-clave-segura-1"}).status_code == 200
    secreto = app.post("/auth/mfa/alta", headers=h).json()["secreto"]
    assert app.post("/auth/mfa/confirmar", headers=h, json={"codigo": "123456"}).status_code == 422
    ok = app.post("/auth/mfa/confirmar", headers=h, json={"codigo": pyotp.TOTP(secreto).now()})
    assert ok.status_code == 200 and ok.json()["usuario"]["mfa"] is True
    assert app.get("/mediaciones", headers={"Authorization": "Bearer " + ok.json()["token"]}).status_code == 200


def test_ciudadano_no_da_de_alta_personal(crear_usuario):
    c = crear_usuario()
    r = c.post("/admin/usuarios", {"nombre": "Intento QA", "correo": "x@pruebas.test", "rol": "JUEZ"})
    assert r.status_code == 403
