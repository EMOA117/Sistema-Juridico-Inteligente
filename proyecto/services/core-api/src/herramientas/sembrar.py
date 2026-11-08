"""Datos sintéticos de demostración (decisión 003). Ejecutar como propietario de la BD:

    uv run python -m herramientas.sembrar

Genera contraseñas y secretos TOTP aleatorios y los escribe en infrastructure/local/credenciales-demo.txt
(ignorado por git). Ningún dato corresponde a personas reales.
"""
import os
import secrets
from pathlib import Path

import psycopg
import pyotp
from psycopg.rows import dict_row

from compartido.cifrado import cifrar
from modulos.identidad.credenciales import hash_password

RAIZ = Path(__file__).resolve().parents[4]
INFRA = RAIZ / "infrastructure" / "local"

USUARIOS = [
    # correo, nombre, rol, cargo, curp
    ("admin@demo.test", "Administración Demo", "ADMINISTRADOR", "Personal administrativo", None),
    ("juez.civil@demo.test", "Mtro. Jorge Ramírez (sintético)", "JUEZ", "Juez 14.º Civil de Proceso Oral", None),
    ("juez.familiar@demo.test", "Mtra. Elena Cruz (sintética)", "JUEZ", "Jueza 3.º Familiar", None),
    ("mediadora@demo.test", "Lic. Mariana Soto (sintética)", "MEDIADOR", "Mediadora certificada · Cert. 0482", None),
    ("mediador@demo.test", "Lic. Tomás Vega (sintético)", "MEDIADOR", "Mediador certificado · Cert. 0517", None),
    ("ana@demo.test", "Ana Pérez López", "CIUDADANO", None, "PELA900101MDFRPN09"),
    ("carlos@demo.test", "Carlos Méndez Ruiz", "CIUDADANO", None, "MERC880505HDFNZR02"),
    ("lucia@demo.test", "Lucía Torres Gómez", "CIUDADANO", None, "TOGL920315MDFRMC05"),
]


def conectar() -> psycopg.Connection:
    env = dict(l.split("=", 1) for l in (INFRA / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
    return psycopg.connect(host="localhost", port=5433, dbname="sji", user="sji_propietario",
                           password=env["PG_PROPIETARIO_PASSWORD"], row_factory=dict_row)


def actor(c, uid) -> None:
    c.execute("SELECT set_config('app.usuario_id', %s, true)", (str(uid),))


def main() -> None:
    lineas = ["# Credenciales de la demostración local (datos sintéticos). No compartir ni versionar.", ""]
    ids: dict[str, object] = {}
    with conectar() as conn, conn.transaction():
        c = conn.cursor()
        if c.execute("SELECT 1 FROM nucleo_comun.usuario WHERE correo='admin@demo.test'").fetchone():
            print("La base ya tiene datos de demostración. Usa init-db.sh --reiniciar para empezar de cero.")
            return
        for correo, nombre, rol, cargo, curp in USUARIOS:
            password = secrets.token_urlsafe(12)
            uid = c.execute("INSERT INTO nucleo_comun.usuario (correo, nombre, password_hash, cargo, curp)"
                            " VALUES (%s,%s,%s,%s,%s) RETURNING id",
                            (correo, nombre, hash_password(password), cargo, curp)).fetchone()["id"]
            c.execute("INSERT INTO nucleo_comun.usuario_rol VALUES (%s,%s)", (uid, rol))
            linea = f"{rol:<14} {correo:<26} contraseña: {password}"
            if rol != "CIUDADANO":
                secreto = pyotp.random_base32()
                c.execute("UPDATE nucleo_comun.usuario SET mfa_habilitado=true, mfa_secreto_cifrado=%s WHERE id=%s",
                          (cifrar(secreto, f"mfa:{uid}"), uid))
                linea += f"  secreto TOTP: {secreto}"
            lineas.append(linea)
            ids[correo] = uid

        civil = c.execute("INSERT INTO schema_judicial.juzgado (nombre, materia) VALUES ('Juzgado 14.º Civil de Proceso Oral (sintético)','CIVIL') RETURNING id").fetchone()["id"]
        familiar = c.execute("INSERT INTO schema_judicial.juzgado (nombre, materia) VALUES ('Juzgado 3.º Familiar (sintético)','FAMILIAR') RETURNING id").fetchone()["id"]
        c.execute("INSERT INTO schema_judicial.juez_adscripcion VALUES (%s,%s,'CIVIL'), (%s,%s,'FAMILIAR')",
                  (ids["juez.civil@demo.test"], civil, ids["juez.familiar@demo.test"], familiar))

        c.execute("INSERT INTO schema_odr.mediador (usuario_id, num_certificacion, especialidades) VALUES"
                  " (%s,'CJA-0482',ARRAY['CIVIL','FAMILIAR']), (%s,'CJA-0517',ARRAY['FAMILIAR'])",
                  (ids["mediadora@demo.test"], ids["mediador@demo.test"]))

        ana, carlos, lucia = ids["ana@demo.test"], ids["carlos@demo.test"], ids["lucia@demo.test"]

        # Escenario 1: préstamo civil en negociación (Ana vs. Carlos).
        actor(c, ana)
        c1 = _conflicto(c, ana, "Ana Pérez López", "ana@demo.test", "Carlos Méndez Ruiz", "carlos@demo.test", carlos,
                        "Le presté $15,000 a un conocido en marzo. Quedamos en que me pagaría en tres meses mediante "
                        "transferencia, pero no ha pagado y ya no contesta mis mensajes.", "CIVIL")
        c.execute("UPDATE nucleo_comun.conflicto SET estado='EN_MEDIACION' WHERE id=%s", (c1,))
        m1 = c.execute("INSERT INTO schema_odr.mediacion (conflicto_id, estado) VALUES (%s,'EN_NEGOCIACION') RETURNING id",
                       (c1,)).fetchone()["id"]
        c.execute("INSERT INTO schema_odr.mensaje (mediacion_id, autor_id, contenido_cifrado) VALUES (%s,%s,%s), (%s,%s,%s)",
                  (m1, carlos, cifrar("Reconozco la deuda. Ahora no tengo el total, pero quiero resolverlo.", f"mensaje:{m1}"),
                   m1, ana, cifrar("Necesito al menos una parte ya. Acepto pagos si el primero es mayor.", f"mensaje:{m1}")))
        c.execute("INSERT INTO schema_odr.propuesta (mediacion_id, autor_id, contenido_cifrado, estado) VALUES (%s,%s,%s,'RECHAZADA')",
                  (m1, carlos, cifrar("$15,000 en 3 mensualidades", f"propuesta:{m1}")))
        c.execute("INSERT INTO schema_odr.propuesta (mediacion_id, autor_id, contenido_cifrado) VALUES (%s,%s,%s)",
                  (m1, carlos, cifrar("$10,000 ahora + $5,000 en 2 meses", f"propuesta:{m1}")))

        # Escenario 2: daños en vivienda arrendada, vía judicial directa, expediente en revisión con juez civil.
        actor(c, lucia)
        c2 = _conflicto(c, lucia, "Lucía Torres Gómez", "lucia@demo.test", "Inmobiliaria Sur S.A. (sintética)", "contacto@inmobiliaria-sur.test",
                        None, "La inmobiliaria no reparó la filtración del departamento que rento pese a tres avisos por escrito; "
                        "el agua dañó muebles y aparatos con valor aproximado de $28,000.", "CIVIL", mediable=True)
        c.execute("UPDATE nucleo_comun.parte SET domicilio_notificaciones='Av. Sintética 123, Col. Demo, CDMX' WHERE conflicto_id=%s", (c2,))
        c.execute("SET LOCAL ROLE rol_canalizador")
        d2 = c.execute("SELECT nucleo_comun.canalizar_conflicto(%s,%s) id", (c2, lucia)).fetchone()["id"]
        c.execute("RESET ROLE")
        c.execute("UPDATE schema_judicial.demanda SET estado='CONFIRMADA', texto_final=%s WHERE id=%s",
                  ("Demanda sintética de daños por falta de reparación del inmueble arrendado. " * 3, d2))
        e2 = c.execute("INSERT INTO schema_judicial.expediente (demanda_id) VALUES (%s) RETURNING id", (d2,)).fetchone()["id"]
        actor(c, ids["admin@demo.test"])
        c.execute("UPDATE schema_judicial.expediente SET juez_id=%s, juzgado_id=%s, estado='EN_REVISION' WHERE id=%s",
                  (ids["juez.civil@demo.test"], civil, e2))

        # Escenario 3: asunto familiar orientado por Lucía, aún sin ruta elegida.
        actor(c, lucia)
        _conflicto(c, lucia, "Lucía Torres Gómez", "lucia@demo.test", "Raúl Ortega (sintético)", "raul@demo.test", None,
                   "Necesito acordar la pensión alimenticia y el régimen de convivencias de nuestra hija tras la separación.",
                   "FAMILIAR")

    (INFRA / "credenciales-demo.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    os.chmod(INFRA / "credenciales-demo.txt", 0o600)
    print(f"Datos sintéticos creados. Credenciales en {INFRA / 'credenciales-demo.txt'}")


def _conflicto(c, solicitante, nom_a, correo_a, nom_b, correo_b, usuario_b, narrativa, materia, mediable=True):
    cid = c.execute("INSERT INTO nucleo_comun.conflicto (solicitante_id, narrativa_inicial, materia, mediable, complejidad,"
                    " confianza_clasificacion) VALUES (%s,%s,%s,%s,'MEDIA',0.9) RETURNING id",
                    (solicitante, narrativa, materia, mediable)).fetchone()["id"]
    c.execute("INSERT INTO nucleo_comun.parte (conflicto_id, usuario_id, rol, nombre, correo) VALUES"
              " (%s,%s,'DEMANDANTE',%s,%s), (%s,%s,'DEMANDADO',%s,%s)",
              (cid, solicitante, nom_a, correo_a, cid, usuario_b, nom_b, correo_b))
    c.execute("UPDATE nucleo_comun.conflicto SET estado='ORIENTADO' WHERE id=%s", (cid,))
    return cid


if __name__ == "__main__":
    main()
