"""Pruebas de integración contra el PostgreSQL del compose (infrastructure/local). Se omiten si no está disponible."""
import secrets
import sys
import uuid
from pathlib import Path

import psycopg
import pyotp
import pytest
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

INFRA = Path(__file__).resolve().parents[3] / "infrastructure" / "local" / ".env"


def _owner():
    env = dict(l.split("=", 1) for l in INFRA.read_text().splitlines() if "=" in l and not l.startswith("#"))
    return psycopg.connect(host="localhost", port=5433, dbname="sji", user="sji_propietario",
                           password=env["PG_PROPIETARIO_PASSWORD"], row_factory=dict_row, autocommit=True)


@pytest.fixture(scope="session")
def owner():
    try:
        conn = _owner()
    except Exception as e:  # pragma: no cover
        pytest.skip(f"PostgreSQL local no disponible: {e}")
    yield conn
    conn.close()


def pytest_configure(config):
    config.addinivalue_line("markers", "ia_real: usa ia-service y Ollama reales (lentas)")


@pytest.fixture(autouse=True)
def ia_desactivada(request, monkeypatch):
    """Por defecto las pruebas no dependen de la latencia del modelo: la IA se simula caída y se usa el respaldo."""
    if request.node.get_closest_marker("ia_real"):
        return
    from compartido.config import config
    monkeypatch.setattr(config(), "ia_url", "http://localhost:9")


@pytest.fixture(scope="session")
def app():
    from fastapi.testclient import TestClient
    from api.main import crear_app
    from compartido.bd import cerrar_pools
    yield TestClient(crear_app())
    cerrar_pools()


class Usuario:
    def __init__(self, app, correo, password, secreto=None, uid=None):
        self.app, self.correo, self.password, self.secreto, self.id = app, correo, password, secreto, uid

    def login(self, codigo=None):
        return self.app.post("/auth/login", json={"correo": self.correo, "contrasena": self.password,
                                                   "codigo_mfa": codigo if codigo is not None else (self.secreto and pyotp.TOTP(self.secreto).now())})

    @property
    def h(self):
        r = self.login()
        assert r.status_code == 200, r.text
        return {"Authorization": "Bearer " + r.json()["token"]}

    def get(self, ruta):
        return self.app.get(ruta, headers=self.h)

    def post(self, ruta, json=None):
        return self.app.post(ruta, json=json, headers=self.h)

    def put(self, ruta, json):
        return self.app.put(ruta, json=json, headers=self.h)


@pytest.fixture(scope="session")
def crear_usuario(owner, app):
    from compartido.cifrado import cifrar
    from modulos.identidad.credenciales import hash_password

    def crear(rol="CIUDADANO", especialidad=None):
        correo = f"qa-{uuid.uuid4().hex[:10]}@pruebas.test"
        password = secrets.token_urlsafe(14)
        uid = owner.execute("INSERT INTO nucleo_comun.usuario (correo, nombre, password_hash) VALUES (%s,%s,%s) RETURNING id",
                            (correo, f"QA {rol.title()} sintético", hash_password(password))).fetchone()["id"]
        owner.execute("INSERT INTO nucleo_comun.usuario_rol VALUES (%s,%s)", (uid, rol))
        secreto = None
        if rol != "CIUDADANO":
            secreto = pyotp.random_base32()
            owner.execute("UPDATE nucleo_comun.usuario SET mfa_habilitado=true, mfa_secreto_cifrado=%s WHERE id=%s",
                          (cifrar(secreto, f"mfa:{uid}"), uid))
        if rol == "MEDIADOR":
            owner.execute("INSERT INTO schema_odr.mediador (usuario_id, num_certificacion, especialidades, max_casos)"
                          " VALUES (%s,%s,%s,50)", (uid, f"QA-{uuid.uuid4().hex[:8]}", [especialidad] if especialidad else ["CIVIL", "FAMILIAR"]))
        if rol == "JUEZ":
            j = owner.execute("INSERT INTO schema_judicial.juzgado (nombre, materia) VALUES (%s,%s) RETURNING id",
                              (f"Juzgado QA {uuid.uuid4().hex[:6]}", especialidad or "CIVIL")).fetchone()["id"]
            owner.execute("INSERT INTO schema_judicial.juez_adscripcion VALUES (%s,%s,%s)", (uid, j, especialidad or "CIVIL"))
        return Usuario(app, correo, password, secreto, uid)

    return crear


@pytest.fixture
def conflicto_orientado(crear_usuario):
    """Crea un conflicto civil orientado por un ciudadano nuevo; devuelve (ciudadano, contraparte, conflicto_id)."""
    def crear(contraparte=None):
        actor = crear_usuario()
        otra = contraparte or crear_usuario()
        r = actor.post("/conflictos", {"solicitante": {"nombre": "Actor QA", "correo": actor.correo},
                                       "contraparte": {"nombre": "Contraparte QA", "correo": otra.correo, "domicilio": "Calle QA 1"}})
        assert r.status_code == 201, r.text
        cid = r.json()["id"]
        assert actor.put(f"/conflictos/{cid}/narrativa", {"narrativa": "Le presté dinero a mi vecino y no me ha pagado nada en seis meses."}).status_code == 200
        assert actor.post(f"/conflictos/{cid}/confirmar", {"materia": "CIVIL"}).status_code == 200
        return actor, otra, cid
    return crear


@pytest.fixture
def negociacion(owner, conflicto_orientado):
    """Conflicto con la invitación aceptada: devuelve (actor, contraparte, mediacion_id)."""
    def crear():
        from tests.test_invitaciones import _invitar, _token_de
        actor, otra, cid = conflicto_orientado()
        mid = _invitar(actor, otra, cid)
        assert otra.post(f"/invitaciones/{_token_de(owner, mid)}/responder", {"acepta": True}).status_code == 200
        return actor, otra, mid
    return crear
