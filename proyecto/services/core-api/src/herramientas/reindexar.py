"""Encola la indexación de las demandas de todos los expedientes (útil tras sembrar o reiniciar Mongo):
    uv run python -m herramientas.reindexar"""
from herramientas.sembrar import conectar

if __name__ == "__main__":
    with conectar() as c, c.transaction():
        n = c.execute("INSERT INTO schema_judicial.indexacion (expediente_id, tipo)"
                      " SELECT e.id, 'DEMANDA' FROM schema_judicial.expediente e"
                      " WHERE NOT EXISTS (SELECT 1 FROM schema_judicial.indexacion i WHERE i.expediente_id=e.id AND i.tipo='DEMANDA'"
                      " AND i.estado <> 'FALLIDA')").rowcount
        n += c.execute("INSERT INTO schema_judicial.indexacion (expediente_id, documento_id, tipo)"
                       " SELECT d.expediente_id, d.id, 'ANEXO' FROM nucleo_comun.documento d"
                       " WHERE d.dominio='JUDICIAL' AND d.tipo IN ('ANEXO','CONTESTACION') AND NOT EXISTS"
                       " (SELECT 1 FROM schema_judicial.indexacion i WHERE i.documento_id=d.id AND i.estado <> 'FALLIDA')").rowcount
    print(f"{n} documentos encolados; el proceso de tareas los enviará a ia-service.")
