"""Cola de indexación documental (P8, P10, P15): el núcleo guarda el archivo al instante y la tarea en segundo
plano lo envía a ia-service. Solo documentos judiciales; el dominio ODR nunca se indexa (decisión 002)."""
from io import BytesIO
from uuid import UUID

from psycopg import Connection
from pypdf import PdfReader

from compartido.bd import RolBD, transaccion
from compartido.documentos import almacen
from modulos import ia_cliente


def encolar_demanda(c: Connection, expediente_id: UUID) -> None:
    c.execute("INSERT INTO schema_judicial.indexacion (expediente_id, tipo) VALUES (%s,'DEMANDA')", (expediente_id,))


def encolar_anexo(c: Connection, expediente_id: UUID, documento_id: UUID) -> None:
    c.execute("INSERT INTO schema_judicial.indexacion (expediente_id, documento_id, tipo) VALUES (%s,%s,'ANEXO')",
              (expediente_id, documento_id))


def paginas_de(nombre: str, datos: bytes) -> list[dict]:
    if nombre.lower().endswith(".pdf"):
        return [{"numero": i + 1, "texto": p.extract_text() or ""} for i, p in enumerate(PdfReader(BytesIO(datos)).pages)]
    return [{"numero": 1, "texto": datos.decode("utf-8", errors="replace")}]


def procesar_lote(limite: int = 5) -> int:
    hechas = 0
    with transaccion(RolBD.TAREAS, None) as c:
        pendientes = c.execute("SELECT id FROM schema_judicial.indexacion WHERE estado='PENDIENTE' AND intentos < 5"
                               " ORDER BY creado_en LIMIT %s FOR UPDATE SKIP LOCKED", (limite,)).fetchall()
        for fila in pendientes:
            m = c.execute("SELECT * FROM schema_judicial.material_indexacion(%s)", (fila["id"],)).fetchone()
            if m["tipo"] == "DEMANDA":
                paginas = [{"numero": 1, "texto": m["texto"] or ""}]
            else:
                paginas = paginas_de(m["documento"], almacen.leer(m["clave_objeto"], version=m["version_objeto"] or None))
            r = ia_cliente.ingerir({"documento": m["documento"], "acceso": "EXPEDIENTE", "materia": m["materia"],
                                    "expediente_id": str(m["expediente_id"]),
                                    "documento_id": m["documento_id"] and str(m["documento_id"]),
                                    "nombres": m["nombres"], "paginas": paginas})
            if r is None:
                c.execute("UPDATE schema_judicial.indexacion SET intentos=intentos+1,"
                          " estado=CASE WHEN intentos+1 >= 5 THEN 'FALLIDA' ELSE 'PENDIENTE' END WHERE id=%s", (fila["id"],))
                break  # ia-service caído: se reintenta en el siguiente ciclo
            c.execute("UPDATE schema_judicial.indexacion SET estado='HECHA', fragmentos=%s, procesado_en=now() WHERE id=%s",
                      (r["fragmentos"], fila["id"]))
            hechas += 1
    return hechas
