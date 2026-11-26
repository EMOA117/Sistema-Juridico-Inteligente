"""Puebla la demostración con expedientes sintéticos en todos los estados judiciales (decisión 003).

Recorre la API real (orientación, invitación, mediación, canalización, demanda, turno, dictamen, emplazamiento,
trámite, resolución firmada y firmeza) para que historial, notificaciones, documentos y firmas sean coherentes.
Ejecutar desde services/core-api/src después de `herramientas.sembrar`:

    uv run --project .. python -m herramientas.poblar_demo

Agrega cuentas nuevas a infrastructure/local/credenciales-demo.txt. Ningún dato corresponde a personas reales.
"""
import secrets
import sys
from datetime import date, timedelta

import pyotp
from fastapi.testclient import TestClient

from compartido.cifrado import cifrar
from compartido.config import config
from modulos.identidad.credenciales import hash_password
from herramientas.sembrar import INFRA, conectar

CREDENCIALES = INFRA / "credenciales-demo.txt"
HOY = date.today()

JUECES_NUEVOS = [  # correo, nombre, cargo, materia, juzgado
    ("juez.mercantil@demo.test", "Mtro. Andrés Lara (sintético)", "Juez 5.º de Proceso Oral Mercantil", "MERCANTIL",
     "Juzgado 5.º de Proceso Oral Mercantil (sintético)"),
    ("juez.laboral@demo.test", "Mtra. Sofía Núñez (sintética)", "Jueza 2.º del Tribunal Laboral", "LABORAL",
     "Tribunal Laboral 2.º (sintético)"),
]

# Cada caso: actor, contraparte, materia, narrativa, pretensión, tipo de juicio, origen, juez, estado final, anexos.
CASOS = [
    # ---------- Juez civil: un expediente en cada estado ----------
    dict(actor="Roberto Sánchez Villa", otra="Patricia Luna Herrera", materia="CIVIL", origen="DIRECTA", juez="civil", fin="EN_REVISION", dias=2,
         narrativa="Rente un departamento durante dos años y al entregarlo la arrendadora se negó a devolverme el depósito de $12,000. "
                   "Entregué el inmueble limpio y sin daños, con fotografías y el acta de entrega firmada por el portero.",
         pretension="Devolución del depósito en garantía de $12,000 más intereses legales", tipo="Juicio oral civil",
         anexos={"Acta_entrega_inmueble.txt": "ACTA DE ENTREGA (sintética). El 30 de septiembre se entrega el departamento 302 sin daños visibles, "
                 "con llaves completas y medidores al corriente. Firma el encargado del edificio como testigo."}),
    dict(actor="Daniela Ortiz Campos", otra="Fernando Ríos Medina", materia="CIVIL", origen="NO_ACEPTADA", juez="civil", fin="EN_REVISION", dias=3,
         narrativa="Un vecino chocó mi automóvil estacionado al salir de su cochera. Reconoció el daño frente a testigos pero no ha pagado "
                   "la reparación cotizada en $18,500 y no aceptó resolverlo por mediación.",
         pretension="Pago de $18,500 por la reparación del vehículo", tipo="Juicio oral civil",
         anexos={"Cotizacion_taller.txt": "COTIZACIÓN (sintética). Taller Mecánico Demo: reparación de defensa trasera, calavera y pintura. "
                 "Total $18,500 IVA incluido. Vigencia 30 días."}),
    dict(actor="Miguel Ángel Herrera Paz", otra="Gustavo Peña Lozano", materia="CIVIL", origen="SIN_ACUERDO", juez="civil", fin="EN_REVISION", dias=4,
         narrativa="Le presté $25,000 a un excompañero de trabajo con un pagaré simple. Intentamos mediar pero no llegamos a un acuerdo "
                   "sobre el plazo de pago y desde entonces ya no responde.",
         pretension="Pago de $25,000 del préstamo y gastos", tipo="Juicio oral civil"),
    dict(actor="Alejandra Vargas Ruiz", otra="Autos Seminuevos del Valle (sintética)", materia="CIVIL", origen="DIRECTA", juez="civil", fin="CORREGIDO", dias=6,
         narrativa="Compré un auto usado que a las dos semanas presentó una falla grave en la transmisión. El vendedor ocultó la falla "
                   "y se niega a responder por los vicios ocultos; la reparación cuesta $32,000.",
         pretension="Rescisión de la compraventa y devolución del precio pagado", tipo="Juicio ordinario civil",
         prevencion="Precise el precio pagado, la fecha de la compraventa y exhiba el contrato o el comprobante de pago.",
         correccion="Se precisa: la compraventa se celebró el 4 de agosto por $145,000 pagados por transferencia; se exhibe el comprobante."),
    dict(actor="Jorge Luis Castañeda", otra="María Elena Robles", materia="CIVIL", origen="DIRECTA", juez="civil", fin="PREVENIDO", dias=7,
         narrativa="Pagué un anticipo de $60,000 por un terreno y la vendedora no ha firmado la escritura ni me devuelve el dinero.",
         pretension="Otorgamiento y firma de escritura o devolución del anticipo", tipo="Juicio ordinario civil",
         prevencion="Señale la ubicación y medidas del terreno y exhiba el recibo del anticipo; aclare cuál de las dos pretensiones es la principal."),
    dict(actor="Sofía Mendoza Aguirre", otra="Ricardo Islas Fuentes", materia="CIVIL", origen="DIRECTA", juez="civil", fin="ADMITIDO", dias=9,
         narrativa="Realicé el diseño arquitectónico de una casa por encargo y el cliente no pagó los honorarios pactados de $40,000.",
         pretension="Pago de honorarios por $40,000", tipo="Juicio oral civil",
         anexos={"Contrato_servicios.txt": "CONTRATO DE PRESTACIÓN DE SERVICIOS (sintético). Diseño de casa habitación, honorarios $40,000 "
                 "pagaderos a la entrega de planos. Entregados el 15 de julio según correo de acuse."}),
    dict(actor="Héctor Ramírez Solís", otra="Constructora Alameda (sintética)", materia="CIVIL", origen="DIRECTA", juez="civil", fin="EMPLAZADO", dias=12, emplazado_hace=4,
         narrativa="La constructora que remodeló mi cocina dejó la obra inconclusa después de cobrar el 80% del presupuesto.",
         pretension="Terminación de la obra o devolución de $56,000", tipo="Juicio oral civil"),
    dict(actor="Carmen Delgado Ibarra", otra="Óscar Treviño Lara", materia="CIVIL", origen="DIRECTA", juez="civil", fin="EN_TRAMITE", dias=25, emplazado_hace=20,
         narrativa="El inquilino de mi local comercial dejó de pagar cinco meses de renta por un total de $45,000 y sigue ocupándolo.",
         pretension="Pago de rentas vencidas y desocupación del local", tipo="Juicio oral civil",
         anexos={"Contrato_arrendamiento.txt": "CONTRATO DE ARRENDAMIENTO (sintético). Local 4, renta mensual $9,000, pago los primeros cinco días."}),
    dict(actor="Luis Fernando Cortés", otra="Graciela Pineda Ochoa", materia="CIVIL", origen="SIN_ACUERDO", juez="civil", fin="EN_TRAMITE", dias=30, emplazado_hace=22,
         narrativa="Una filtración del departamento de arriba dañó el techo y muebles de mi casa. La vecina no quiso pagar la reparación.",
         pretension="Pago de daños por $21,000", tipo="Juicio oral civil"),
    dict(actor="Verónica Salinas Mora", otra="Arturo Benítez Gil", materia="CIVIL", origen="DIRECTA", juez="civil", fin="RESUELTO", dias=45, emplazado_hace=35,
         narrativa="Presté $30,000 a un conocido con un reconocimiento de adeudo firmado y no los ha devuelto en el plazo pactado.",
         pretension="Pago de $30,000 e intereses", tipo="Juicio oral civil",
         resolucion=("SENTENCIA", "Se condena al demandado al pago de $30,000 más intereses legales",
                     "VISTOS los autos. CONSIDERANDO que la parte actora acreditó el préstamo con el reconocimiento de adeudo exhibido, "
                     "documento no objetado por el demandado, y que este no acreditó el pago. RESUELVE: PRIMERO. Se condena al demandado al "
                     "pago de $30,000 más intereses legales. SEGUNDO. Notifíquese.")),
    dict(actor="Andrés Molina Rangel", otra="Lorena Figueroa Paz", materia="CIVIL", origen="DIRECTA", juez="civil", fin="DESECHADO", dias=20,
         narrativa="Quiero que mi vecina deje de estacionarse frente a mi casa porque me molesta.",
         pretension="Que la vecina deje de estacionarse frente a mi domicilio", tipo="Juicio oral civil",
         prevencion="Precise el derecho que considera afectado y el fundamento de su pretensión.",
         resolucion=("DESECHAMIENTO", "Se desecha la demanda por no desahogar la prevención",
                     "VISTO el estado de los autos y CONSIDERANDO que la parte actora no desahogó la prevención en el plazo concedido, "
                     "pues no precisó el derecho afectado ni el fundamento de su pretensión. RESUELVE: ÚNICO. Se desecha la demanda.")),
    dict(actor="Isabel Cruz Navarro", otra="Ernesto Galindo Ríos", materia="CIVIL", origen="DIRECTA", juez="civil", fin="CERRADO", dias=60, emplazado_hace=50,
         narrativa="Pagué por adelantado la fabricación de unos muebles de cocina que nunca se entregaron. El carpintero no devuelve $22,000.",
         pretension="Devolución de $22,000", tipo="Juicio oral civil",
         resolucion=("SENTENCIA", "Se condena a la devolución de $22,000",
                     "VISTOS los autos. CONSIDERANDO que se acreditó el pago anticipado mediante transferencias y que el demandado no "
                     "probó la entrega de los muebles. RESUELVE: PRIMERO. Se condena a devolver $22,000. SEGUNDO. Notifíquese.")),
    # ---------- Juez familiar ----------
    dict(actor="Mariana López Treviño", otra="Javier Ochoa Martínez", materia="FAMILIAR", origen="NO_ACEPTADA", juez="familiar", fin="EN_REVISION", dias=3,
         narrativa="Mi expareja dejó de pagar la pensión alimenticia de nuestros dos hijos hace cuatro meses y no aceptó la mediación.",
         pretension="Fijación de pensión alimenticia y pago de pensiones vencidas", tipo="Controversia del orden familiar"),
    dict(actor="Gabriela Fuentes Soto", otra="Rodrigo Aranda Vela", materia="FAMILIAR", origen="DIRECTA", juez="familiar", fin="ADMITIDO", dias=10,
         narrativa="Necesito fijar un régimen de convivencias con mi hija porque el padre la cambia de escuela sin avisarme.",
         pretension="Régimen de convivencias y acuerdo sobre la escuela", tipo="Juicio oral familiar"),
    dict(actor="Patricio Reyes Alcántara", otra="Lilia Guzmán Ortega", materia="FAMILIAR", origen="SIN_ACUERDO", juez="familiar", fin="EN_TRAMITE", dias=28, emplazado_hace=21,
         narrativa="Tras el divorcio no logramos acordar el uso de la vivienda familiar ni la guarda de nuestros hijos.",
         pretension="Guarda y custodia y uso de la vivienda familiar", tipo="Controversia del orden familiar"),
    dict(actor="Elena Paredes Quiroz", otra="Tomás Escobar Lima", materia="FAMILIAR", origen="DIRECTA", juez="familiar", fin="RESUELTO", dias=50, emplazado_hace=40,
         narrativa="El padre de mi hijo tiene ingresos fijos y solo aporta $1,000 al mes; solicito una pensión proporcional.",
         pretension="Pensión alimenticia del 20% de los ingresos", tipo="Juicio oral familiar",
         resolucion=("SENTENCIA", "Se fija pensión alimenticia del 20% de los ingresos del demandado",
                     "VISTOS los autos. CONSIDERANDO la necesidad del menor y la capacidad económica acreditada con los recibos de nómina. "
                     "RESUELVE: PRIMERO. Se fija pensión del 20% de los ingresos ordinarios y extraordinarios del demandado.")),
    # ---------- Juez mercantil ----------
    dict(actor="Distribuidora Norte (sintética)", otra="Abarrotes La Esperanza (sintética)", materia="MERCANTIL", origen="DIRECTA", juez="mercantil", fin="EN_REVISION", dias=2,
         narrativa="Un cliente comercial firmó tres pagarés por mercancía entregada y no ha pagado ninguno; el adeudo es de $84,000.",
         pretension="Pago de tres pagarés por $84,000 e intereses moratorios", tipo="Juicio ejecutivo mercantil"),
    dict(actor="Servicios Gráficos Delta (sintética)", otra="Eventos Prisma (sintética)", materia="MERCANTIL", origen="SIN_ACUERDO", juez="mercantil", fin="ADMITIDO", dias=8,
         narrativa="Imprimimos material publicitario para una empresa de eventos que no pagó las facturas por $46,000; la mediación no prosperó.",
         pretension="Pago de facturas por $46,000", tipo="Juicio oral mercantil"),
    dict(actor="Ferretería El Tornillo (sintética)", otra="Construcciones Bravo (sintética)", materia="MERCANTIL", origen="DIRECTA", juez="mercantil", fin="EN_TRAMITE", dias=26, emplazado_hace=20,
         narrativa="Un proveedor nos vendió material defectuoso y se niega a reponerlo o reembolsar $38,000.",
         pretension="Reembolso de $38,000 por mercancía defectuosa", tipo="Juicio oral mercantil"),
    # ---------- Juez laboral ----------
    dict(actor="Ramón Gutiérrez Pérez", otra="Logística Express (sintética)", materia="LABORAL", origen="NO_ACEPTADA", juez="laboral", fin="EN_REVISION", dias=1,
         narrativa="Me despidieron sin causa después de seis años de trabajo y el patrón no me pagó el finiquito ni la liquidación.",
         pretension="Indemnización constitucional, salarios caídos y prestaciones", tipo="Procedimiento ordinario laboral"),
    dict(actor="Adriana Medina Cruz", otra="Restaurante El Fogón (sintética)", materia="LABORAL", origen="DIRECTA", juez="laboral", fin="ADMITIDO", dias=9,
         narrativa="Trabajé como mesera un año y no me pagaron aguinaldo, vacaciones ni horas extra al renunciar.",
         pretension="Pago de aguinaldo, vacaciones, prima vacacional y horas extra", tipo="Procedimiento ordinario laboral"),
    dict(actor="Saúl Domínguez Rivas", otra="Manufacturas Omega (sintética)", materia="LABORAL", origen="SIN_ACUERDO", juez="laboral", fin="RESUELTO", dias=40, emplazado_hace=30,
         narrativa="La empresa no me pagó las últimas tres quincenas de salario antes de cerrar la planta.",
         pretension="Pago de salarios devengados", tipo="Procedimiento especial laboral",
         resolucion=("SENTENCIA", "Se condena al pago de los salarios devengados",
                     "VISTOS los autos. CONSIDERANDO que la parte trabajadora acreditó la relación laboral con recibos de nómina y la empresa "
                     "no acreditó el pago de las quincenas reclamadas. RESUELVE: ÚNICO. Se condena al pago de los salarios devengados.")),
    # ---------- Sin juez: pendientes de turno para el portal de administración ----------
    dict(actor="Teresa Valdez Pineda", otra="Hugo Carrillo Ramos", materia="CIVIL", origen="DIRECTA", juez=None, fin="EN_TURNO", dias=0,
         narrativa="Mi exsocio se quedó con herramientas de mi propiedad valuadas en $15,000 y se niega a devolverlas.",
         pretension="Restitución de herramientas o pago de su valor", tipo="Juicio oral civil"),
    dict(actor="Pablo Estrada León", otra="Comercializadora Sol (sintética)", materia="MERCANTIL", origen="DIRECTA", juez=None, fin="EN_TURNO", dias=0,
         narrativa="Un cliente pagó con un cheque sin fondos por $27,000 mercancía que ya recibió.",
         pretension="Pago del cheque por $27,000 e indemnización", tipo="Juicio ejecutivo mercantil"),
    dict(actor="Norma Ibáñez Silva", otra="Clínica Dental Sonrisa (sintética)", materia="LABORAL", origen="DIRECTA", juez=None, fin="EN_TURNO", dias=0,
         narrativa="Trabajé como asistente sin contrato y sin seguro social; me despidieron al informar que estaba embarazada.",
         pretension="Reinstalación, salarios caídos e inscripción retroactiva al IMSS", tipo="Procedimiento ordinario laboral"),
]


def _correo(nombre: str) -> str:
    base = "".join(ch for ch in nombre.lower().split("(")[0] if ch.isalnum() or ch == " ").split()
    tabla = str.maketrans("áéíóúñü", "aeiounu")
    return (".".join(base[:2]).translate(tabla)) + "@demo.test"


class Cliente:
    def __init__(self, app, correo, password, secreto=None):
        self.app, self.correo, self.password, self.secreto, self._h = app, correo, password, secreto, None

    def cred(self):
        return {"contrasena": self.password, "codigo_mfa": self.secreto and pyotp.TOTP(self.secreto).now()}

    @property
    def h(self):
        if not self._h:
            r = self.app.post("/auth/login", json={"correo": self.correo, "contrasena": self.password,
                                                   "codigo_mfa": self.secreto and pyotp.TOTP(self.secreto).now()})
            assert r.status_code == 200, f"{self.correo}: {r.text}"
            self._h = {"Authorization": "Bearer " + r.json()["token"]}
        return self._h

    def _ok(self, r):
        assert r.status_code < 300, f"{r.request.method} {r.request.url.path} → {r.status_code} {r.text}"
        return r.json() if r.content else None

    def get(self, ruta):
        return self._ok(self.app.get(ruta, headers=self.h))

    def post(self, ruta, json=None):
        return self._ok(self.app.post(ruta, json=json, headers=self.h))

    def put(self, ruta, json):
        return self._ok(self.app.put(ruta, json=json, headers=self.h))


def _leer_credenciales() -> dict[str, tuple[str, str | None]]:
    datos = {}
    for linea in CREDENCIALES.read_text(encoding="utf-8").splitlines():
        partes = linea.split()
        if "contraseña:" in partes:
            correo = partes[1]
            password = partes[partes.index("contraseña:") + 1]
            secreto = partes[partes.index("TOTP:") + 1] if "TOTP:" in partes else None
            datos[correo] = (password, secreto)
    return datos


def main() -> None:
    config().ia_url = "http://localhost:9"   # textos de plantilla: rápidos y reproducibles (la IA sigue activa en la API)
    from api.main import crear_app
    app = TestClient(crear_app())
    creds = _leer_credenciales()
    nuevas: list[str] = []

    with conectar() as conn:
        conn.autocommit = True
        c = conn.cursor()

        def usuario(correo, nombre, rol, cargo=None):
            if correo in creds:
                return creds[correo]
            password = secrets.token_urlsafe(12)
            existe = c.execute("SELECT id FROM nucleo_comun.usuario WHERE correo=%s", (correo,)).fetchone()
            if existe:   # quedó de una corrida interrumpida: se le asigna contraseña nueva
                uid = existe["id"]
                c.execute("UPDATE nucleo_comun.usuario SET password_hash=%s WHERE id=%s", (hash_password(password), uid))
            else:
                uid = c.execute("INSERT INTO nucleo_comun.usuario (correo, nombre, password_hash, cargo) VALUES (%s,%s,%s,%s) RETURNING id",
                                (correo, nombre, hash_password(password), cargo)).fetchone()["id"]
                c.execute("INSERT INTO nucleo_comun.usuario_rol VALUES (%s,%s)", (uid, rol))
            secreto = None
            linea = f"{rol:<14} {correo:<34} contraseña: {password}"
            if rol != "CIUDADANO":
                secreto = pyotp.random_base32()
                c.execute("UPDATE nucleo_comun.usuario SET mfa_habilitado=true, mfa_secreto_cifrado=%s WHERE id=%s",
                          (cifrar(secreto, f"mfa:{uid}"), uid))
                linea += f"  secreto TOTP: {secreto}"
            with CREDENCIALES.open("a", encoding="utf-8") as f:
                if not nuevas:
                    f.write("\n# Cuentas agregadas por poblar_demo\n")
                f.write(linea + "\n")
            nuevas.append(linea)
            creds[correo] = (password, secreto)
            return creds[correo]

        for correo, nombre, cargo, materia, juzgado in JUECES_NUEVOS:
            if correo not in creds:
                usuario(correo, nombre, "JUEZ", cargo)
                uid = c.execute("SELECT id FROM nucleo_comun.usuario WHERE correo=%s", (correo,)).fetchone()["id"]
                if not c.execute("SELECT 1 FROM schema_judicial.juez_adscripcion WHERE juez_id=%s", (uid,)).fetchone():
                    j = c.execute("INSERT INTO schema_judicial.juzgado (nombre, materia) VALUES (%s,%s) ON CONFLICT (nombre) DO UPDATE"
                                  " SET materia=EXCLUDED.materia RETURNING id", (juzgado, materia)).fetchone()["id"]
                    c.execute("INSERT INTO schema_judicial.juez_adscripcion VALUES (%s,%s,%s)", (uid, j, materia))
        c.execute("UPDATE schema_odr.mediador SET especialidades=ARRAY['CIVIL','FAMILIAR','MERCANTIL','LABORAL']"
                  " WHERE usuario_id=(SELECT id FROM nucleo_comun.usuario WHERE correo='mediadora@demo.test')")

        def cliente(correo):
            p, s = creds[correo]
            return Cliente(app, correo, p, s)

        admin = cliente("admin@demo.test")
        jueces = {k: cliente(f"juez.{k}@demo.test") for k in ("civil", "familiar", "mercantil", "laboral")}
        ids_juez = {k: c.execute("SELECT id FROM nucleo_comun.usuario WHERE correo=%s", (j.correo,)).fetchone()["id"] for k, j in jueces.items()}

        def token_invitacion(mid):
            from compartido.cifrado import descifrar
            n = c.execute("SELECT n.enlace_cifrado, n.entidad_id FROM nucleo_comun.notificacion n"
                          " JOIN schema_odr.invitacion i ON i.id = n.entidad_id WHERE i.mediacion_id=%s", (mid,)).fetchone()
            return descifrar(n["enlace_cifrado"], f"enlace:{n['entidad_id']}").rsplit("/", 1)[1]

        def anexo(eid, conflicto_id, autor_id, nombre, texto):
            from compartido.documentos import almacen
            c.execute("SELECT set_config('app.usuario_id', %s, false)", (str(autor_id),))
            datos = texto.encode()
            huella = almacen.sha256(datos)
            clave = f"expedientes/semilla/{huella}-{nombre}"
            version = almacen.guardar_inmutable(clave, datos, "text/plain")
            doc = c.execute("INSERT INTO nucleo_comun.documento (dominio, conflicto_id, expediente_id, tipo, nombre, clave_objeto,"
                            " version_objeto, hash_sha256, paginas, subido_por) VALUES ('JUDICIAL',%s,%s,'ANEXO',%s,%s,%s,%s,1,%s) RETURNING id",
                            (conflicto_id, eid, nombre, clave, version, huella, autor_id)).fetchone()["id"]
            c.execute("INSERT INTO schema_judicial.indexacion (expediente_id, documento_id, tipo) VALUES (%s,%s,'ANEXO')", (eid, doc))

        for n, caso in enumerate(CASOS, 1):
            if c.execute("SELECT 1 FROM nucleo_comun.parte WHERE nombre=%s AND rol='DEMANDANTE'", (caso["actor"],)).fetchone():
                print(f"  (ya existe) {caso['actor']}")
                continue
            ca, co = _correo(caso["actor"]), _correo(caso["otra"])
            usuario(ca, caso["actor"], "CIUDADANO")
            actor = cliente(ca)
            otra = None
            if caso["origen"] != "DIRECTA":
                usuario(co, caso["otra"], "CIUDADANO")
                otra = cliente(co)

            cid = actor.post("/conflictos", {"solicitante": {"nombre": caso["actor"], "correo": ca},
                                             "contraparte": {"nombre": caso["otra"], "correo": co,
                                                             "domicilio": f"Calle Sintética {100 + n}, Col. Demo, CDMX"}})["id"]
            actor.put(f"/conflictos/{cid}/narrativa", {"narrativa": caso["narrativa"]})
            actor.post(f"/conflictos/{cid}/confirmar", {"materia": caso["materia"]})

            if caso["origen"] in ("NO_ACEPTADA", "SIN_ACUERDO"):
                mid = actor.post(f"/conflictos/{cid}/mediacion", {"plazo_dias": 7})["mediacion_id"]
                acepta = caso["origen"] == "SIN_ACUERDO"
                otra.post(f"/invitaciones/{token_invitacion(mid)}/responder", {"acepta": acepta})
                if acepta:
                    actor.post(f"/mediaciones/{mid}/mensajes", {"texto": "Propongo que lo resolvamos con pagos mensuales."})
                    otra.post(f"/mediaciones/{mid}/mensajes", {"texto": "No estoy de acuerdo con el monto que reclamas."})
                    actor.post(f"/mediaciones/{mid}/terminar", {"resultado": "SIN_ACUERDO"})

            did = actor.post(f"/conflictos/{cid}/canalizar")["demanda_id"]
            texto = actor.post(f"/demandas/{did}/borrador", {"pretension": caso["pretension"], "tipo_juicio": caso["tipo"]})["texto"]
            eid = actor.post(f"/demandas/{did}/confirmar", {"texto": texto})["expediente_id"]
            autor = c.execute("SELECT id FROM nucleo_comun.usuario WHERE correo=%s", (ca,)).fetchone()["id"]
            for nombre, contenido in caso.get("anexos", {}).items():
                anexo(eid, cid, autor, nombre, contenido)

            if caso["juez"]:
                juez = jueces[caso["juez"]]
                admin.post(f"/admin/expedientes/{eid}/asignar", {"juez_id": str(ids_juez[caso["juez"]])})
                fin = caso["fin"]
                if caso.get("prevencion"):
                    juez.post(f"/expedientes/{eid}/dictamen", {"decision": "PREVENIR", "texto": caso["prevencion"]})
                    if caso.get("correccion"):
                        actor.post(f"/expedientes/{eid}/correccion", {"texto": texto + "\n\nCORRECCIÓN: " + caso["correccion"]})
                if fin in ("ADMITIDO", "EMPLAZADO", "EN_TRAMITE", "RESUELTO", "CERRADO"):
                    juez.post(f"/expedientes/{eid}/dictamen", {"decision": "ADMITIR",
                                                               "texto": "La demanda reúne los requisitos legales; se admite y se ordena emplazar."})
                if caso.get("emplazado_hace"):
                    juez.post(f"/expedientes/{eid}/emplazamiento", {"fecha": (HOY - timedelta(days=caso["emplazado_hace"])).isoformat()})
                if fin in ("EN_TRAMITE", "RESUELTO", "CERRADO"):
                    juez.post(f"/expedientes/{eid}/tramite")
                if caso.get("resolucion"):
                    tipo, resultado, texto_res = caso["resolucion"]
                    juez.post(f"/expedientes/{eid}/resolucion", {"tipo": tipo, "resultado": resultado, "texto": texto_res, **juez.cred()})
                if fin == "CERRADO":
                    juez.post(f"/expedientes/{eid}/firmeza", {"fecha": HOY.isoformat()})

            # Fecha de ingreso escalonada para que la bandeja se vea como una carga real.
            if caso["dias"]:
                c.execute("UPDATE schema_judicial.expediente SET creado_en = creado_en - make_interval(days => %s) WHERE id=%s", (caso["dias"], eid))
            estado = c.execute("SELECT numero, estado FROM schema_judicial.expediente WHERE id=%s", (eid,)).fetchone()
            print(f"  {estado['numero']:>8}  {caso['materia']:<9} {estado['estado']:<11} {caso['actor']}")

        escenarios_usuarios_prueba(c, cliente, admin, jueces, ids_juez, token_invitacion)

    print(f"Listo: {len(CASOS)} expedientes y {len(ESCENARIOS)} escenarios de cuentas de prueba. Credenciales en {CREDENCIALES}")


# Asuntos de las cuentas de prueba (ana, carlos, lucia, mediadora, mediador) para que cada portal tenga trabajo visible.
# La narrativa identifica el escenario: si ya existe, no se vuelve a crear.
ESCENARIOS = [
    dict(clave="mediacion_mediadora", actor="ana", otra="carlos", materia="CIVIL",
         narrativa="Le vendí a un conocido mi bicicleta de montaña en $9,000; pagó $4,000 y quedó de liquidar el resto en un mes, "
                   "pero ya pasaron tres y dice que la bicicleta tenía detalles que no le mencioné."),
    dict(clave="mediacion_mediador", actor="lucia", otra="carlos", materia="FAMILIAR",
         narrativa="Mi expareja y yo necesitamos acordar los horarios de convivencia de nuestro hijo durante las vacaciones de verano, "
                   "porque cada quien quiere llevarlo de viaje en las mismas fechas."),
    dict(clave="convenio_por_aprobar", actor="carlos", otra="ana", materia="MERCANTIL",
         narrativa="Le surtí a un pequeño negocio 40 cajas de producto a crédito por $18,000 y solo me han pagado la mitad; "
                   "queremos acordar un calendario de pagos sin dejar de trabajar juntos."),
    dict(clave="convenio_firmado", actor="lucia", otra="ana", materia="CIVIL",
         narrativa="Una vecina me pidió prestada mi lavadora durante un mes y me la devolvió con el motor dañado; la reparación "
                   "cuesta $3,200 y queremos dividir el gasto."),
    dict(clave="sin_acuerdo_a_juzgado", actor="ana", otra="lucia", materia="LABORAL",
         narrativa="Trabajé ocho meses como asistente administrativa en un despacho y al terminar la relación no me pagaron "
                   "vacaciones, prima vacacional ni la parte proporcional del aguinaldo."),
    dict(clave="invitacion_pendiente", actor="lucia", otra="carlos", materia="CIVIL",
         narrativa="Contraté a un conocido para pintar mi departamento, le adelanté $5,000 y dejó el trabajo a medias con manchas "
                   "en el piso y los muebles."),
    dict(clave="orientado", actor="ana", otra=None, materia="MERCANTIL",
         narrativa="Compré mercancía para mi tienda en línea a un proveedor que me entregó piezas distintas a las de la factura y "
                   "no responde a mis reclamos."),
    dict(clave="prevenida_por_corregir", actor="lucia", otra=None, materia="FAMILIAR",
         narrativa="El padre de mi hija no ha cubierto los gastos escolares acordados verbalmente desde el inicio del ciclo y "
                   "necesito que se fije una pensión por escrito."),
    dict(clave="concluida_por_mediador", actor="carlos", otra="lucia", materia="FAMILIAR",
         narrativa="Mi hermana y yo no nos ponemos de acuerdo sobre quién cuida a nuestra madre los fines de semana ni cómo "
                   "repartir los gastos de sus medicamentos."),
]

NOMBRES = {"ana": "Ana Pérez López", "carlos": "Carlos Méndez Ruiz", "lucia": "Lucía Torres Gómez"}


def escenarios_usuarios_prueba(c, cliente, admin, jueces, ids_juez, token_invitacion) -> None:
    from datetime import datetime, timezone
    yo = {k: cliente(f"{k}@demo.test") for k in NOMBRES}
    mediadora, mediador = cliente("mediadora@demo.test"), cliente("mediador@demo.test")
    uid = lambda correo: str(c.execute("SELECT id FROM nucleo_comun.usuario WHERE correo=%s", (correo,)).fetchone()["id"])

    def en_unos_dias(dias, hora):
        d = datetime.now(timezone.utc).astimezone().replace(hour=hora, minute=0, second=0, microsecond=0)
        return (d + timedelta(days=dias)).isoformat()

    def propuesta_aceptada(mid, autor, otra, texto):
        autor.post(f"/mediaciones/{mid}/propuestas", {"texto": texto})
        pid = next(p["id"] for p in otra.get(f"/mediaciones/{mid}")["propuestas"] if p["estado"] == "PENDIENTE")
        otra.post(f"/mediaciones/propuestas/{pid}/responder", {"estado": "ACEPTADA"})

    def con_mediador(mid, actor, quien):
        actor.post(f"/mediaciones/{mid}/solicitar-mediador")
        admin.post(f"/admin/asignaciones/{mid}", {"mediador_id": uid(quien.correo)})

    def a_juzgado(actor, cid, pretension, tipo, juez, decision, texto_dictamen):
        did = actor.post(f"/conflictos/{cid}/canalizar")["demanda_id"]
        texto = actor.post(f"/demandas/{did}/borrador", {"pretension": pretension, "tipo_juicio": tipo})["texto"]
        eid = actor.post(f"/demandas/{did}/confirmar", {"texto": texto})["expediente_id"]
        admin.post(f"/admin/expedientes/{eid}/asignar", {"juez_id": str(ids_juez[juez])})
        jueces[juez].post(f"/expedientes/{eid}/dictamen", {"decision": decision, "texto": texto_dictamen})
        return eid

    for e in ESCENARIOS:
        if c.execute("SELECT 1 FROM nucleo_comun.conflicto WHERE narrativa_inicial=%s", (e["narrativa"],)).fetchone():
            print(f"  (ya existe) {e['clave']}")
            continue
        actor, otra = yo[e["actor"]], yo.get(e["otra"])
        contraparte = ({"nombre": NOMBRES[e["otra"]], "correo": otra.correo} if otra else
                       {"nombre": "Contraparte sintética", "correo": "contraparte@demo.test", "domicilio": "Calle Sintética 7, Col. Demo, CDMX"})
        cid = actor.post("/conflictos", {"solicitante": {"nombre": NOMBRES[e["actor"]], "correo": actor.correo},
                                         "contraparte": contraparte})["id"]
        actor.put(f"/conflictos/{cid}/narrativa", {"narrativa": e["narrativa"]})
        actor.post(f"/conflictos/{cid}/confirmar", {"materia": e["materia"]})
        clave = e["clave"]

        if otra:
            mid = actor.post(f"/conflictos/{cid}/mediacion", {"plazo_dias": 10})["mediacion_id"]
            if clave != "invitacion_pendiente":
                otra.post(f"/invitaciones/{token_invitacion(mid)}/responder", {"acepta": True})
                actor.post(f"/mediaciones/{mid}/mensajes", {"texto": "Gracias por aceptar. Me gustaría que lo resolviéramos pronto."})
                otra.post(f"/mediaciones/{mid}/mensajes", {"texto": "De acuerdo, revisemos opciones que nos funcionen a ambos."})

        if clave == "mediacion_mediadora":
            con_mediador(mid, actor, mediadora)
            mediadora.post(f"/mediaciones/{mid}/sesiones", {"inicio": en_unos_dias(2, 10), "modalidad": "VIDEOLLAMADA_CONJUNTA",
                                                            "enlace": "https://meet.demo.test/sala-bicicleta"})
            mediadora.post(f"/mediaciones/{mid}/notas", {"texto": "Ambas partes reconocen la venta; la diferencia está en el estado de la bicicleta. Explorar descuento por reparación."})
        elif clave == "mediacion_mediador":
            con_mediador(mid, actor, mediador)
            mediador.post(f"/mediaciones/{mid}/sesiones", {"inicio": en_unos_dias(1, 17), "modalidad": "SESION_PRIVADA"})
            mediador.post(f"/mediaciones/{mid}/notas", {"texto": "Proponer alternar quincenas de vacaciones y que el viaje se avise con un mes de anticipación."})
        elif clave == "convenio_por_aprobar":
            propuesta_aceptada(mid, actor, otra, "Pago del saldo de $9,000 en tres quincenas de $3,000")
            actor.put(f"/mediaciones/{mid}/convenio", {"tipo": "TOTAL", "terminos":
                      "La parte compradora pagará el saldo de $9,000 en tres pagos quincenales de $3,000 por transferencia, "
                      "a partir del día 15 del mes en curso. El proveedor mantendrá el crédito vigente mientras se cumpla el calendario."})
            actor.post(f"/mediaciones/{mid}/convenio/aprobar")
        elif clave == "convenio_firmado":
            propuesta_aceptada(mid, actor, otra, "Dividir al 50% el costo de la reparación de $3,200")
            actor.put(f"/mediaciones/{mid}/convenio", {"tipo": "TOTAL", "terminos":
                      "Las partes dividen en partes iguales el costo de reparación del motor de la lavadora, $1,600 cada una. "
                      "La vecina entregará su parte en efectivo a más tardar el viernes siguiente a la firma."})
            for parte in (actor, otra):
                parte.post(f"/mediaciones/{mid}/convenio/aprobar")
            for parte in (actor, otra):
                parte.post(f"/mediaciones/{mid}/convenio/firmar", parte.cred())
        elif clave == "sin_acuerdo_a_juzgado":
            con_mediador(mid, actor, mediadora)
            mediadora.post(f"/mediaciones/{mid}/notas", {"texto": "Sesión realizada. La parte empleadora niega la relación laboral; no hay base para acuerdo."})
            mediadora.post(f"/mediaciones/{mid}/concluir", {"resultado": "SIN_ACUERDO"})
            a_juzgado(actor, cid, "Pago de vacaciones, prima vacacional y aguinaldo proporcional", "Procedimiento ordinario laboral",
                      "laboral", "ADMITIR", "La demanda reúne los requisitos legales; se admite y se ordena emplazar.")
        elif clave == "prevenida_por_corregir":
            a_juzgado(actor, cid, "Fijación de pensión alimenticia para gastos escolares", "Controversia del orden familiar",
                      "familiar", "PREVENIR", "Precise el monto de los gastos escolares, la edad de la menor y exhiba comprobantes de pago.")
        elif clave == "concluida_por_mediador":
            con_mediador(mid, actor, mediador)
            mediador.post(f"/mediaciones/{mid}/notas", {"texto": "Dos sesiones sin avance; las partes prefieren consultar a un abogado."})
            mediador.post(f"/mediaciones/{mid}/concluir", {"resultado": "SIN_ACUERDO"})
        print(f"  escenario {clave}")


if __name__ == "__main__":
    sys.exit(main())
