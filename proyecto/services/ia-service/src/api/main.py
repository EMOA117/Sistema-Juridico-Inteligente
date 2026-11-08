"""Servicio interno de IA. Solo lo llama core-api con su secreto de servicio. Ejecutar:
    uv run uvicorn api.main:app --app-dir src --port 8001"""
import threading
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pymongo.errors import PyMongoError

from clasificacion import servicio as clasificacion
from compartido.ollama import IANoDisponible, precalentar
from compartido.seguridad import exigir_servicio
from generacion_demanda import servicio as demanda
from ingesta_conocimiento import servicio as ingesta
from rag import servicio as rag
from recomendacion_odr import servicio as recomendacion
from turno_judicial import servicio as turno


@asynccontextmanager
async def ciclo(_: FastAPI):
    threading.Thread(target=precalentar, daemon=True).start()
    yield


app = FastAPI(title="Sistema Jurídico Inteligente · ia-service", version="0.1.0", lifespan=ciclo,
              dependencies=[Depends(exigir_servicio)])


@app.exception_handler(IANoDisponible)
async def _ia(_: Request, e: IANoDisponible):
    return JSONResponse(status_code=503, content={"detail": "El asistente de IA no está disponible"})


@app.exception_handler(PyMongoError)
async def _mongo(_: Request, e: PyMongoError):
    return JSONResponse(status_code=503, content={"detail": "La base de conocimiento no está disponible"})


class Clasificar(BaseModel):
    narrativa: str = Field(min_length=10, max_length=4000)


class Recomendar(BaseModel):
    materia: Literal["CIVIL", "FAMILIAR"]
    narrativa: str = Field(max_length=4000)
    propuestas: list[str] = Field(default_factory=list, max_length=30)
    nombres: list[str] = Field(default_factory=list, max_length=10)


class Parte(BaseModel):
    nombre: str
    correo: str | None = None
    domicilio_notificaciones: str | None = None


class Demanda(BaseModel):
    materia: Literal["CIVIL", "FAMILIAR"]
    origen: str
    narrativa: str = Field(max_length=4000)
    puntos_pendientes: list[str] = Field(default_factory=list)
    pretension: str = Field(max_length=500)
    tipo_juicio: str = Field(max_length=80)
    demandante: Parte
    demandado: Parte


class Candidato(BaseModel):
    juzgado_id: str
    juez_id: str
    especialidad: Literal["CIVIL", "FAMILIAR"]
    expedientes_activos: int = Field(ge=0)


class Turno(BaseModel):
    expediente_id: str
    materia: Literal["CIVIL", "FAMILIAR"]
    candidatos: list[Candidato]


class Consulta(BaseModel):
    expediente_id: str
    materia: Literal["CIVIL", "FAMILIAR"]
    juez_id: str
    pregunta: str = Field(min_length=5, max_length=500)
    incluir_expediente: bool = True
    incluir_publico: bool = True


class Pagina(BaseModel):
    numero: int | None = None
    texto: str = Field(max_length=200_000)


class Ingesta(BaseModel):
    documento: str
    acceso: Literal["PUBLICO", "EXPEDIENTE"]
    materia: Literal["CIVIL", "FAMILIAR"]
    expediente_id: str | None = None
    documento_id: str | None = None
    nombres: list[str] = Field(default_factory=list)
    paginas: list[Pagina]


@app.post("/interno/clasificar")
def clasificar(d: Clasificar):
    return clasificacion.clasificar(d.narrativa)


@app.post("/interno/acuerdos/sugerir")
def sugerir_acuerdo(d: Recomendar):
    return recomendacion.sugerir(d.materia, d.narrativa, d.propuestas, d.nombres)


@app.post("/interno/demanda/borrador")
def borrador(d: Demanda):
    return demanda.redactar(d.model_dump())


@app.post("/interno/turnos/sugerir")
def sugerir_turno(d: Turno):
    return turno.sugerir(d.expediente_id, d.materia, [c.model_dump() for c in d.candidatos])


@app.post("/interno/rag/consultar")
def consultar(d: Consulta):
    return rag.consultar(d.expediente_id, d.materia, d.pregunta, d.incluir_expediente, d.incluir_publico, d.juez_id)


@app.post("/interno/ingesta")
def ingerir(d: Ingesta):
    n = ingesta.ingerir(d.documento, d.acceso, d.materia, [p.model_dump() for p in d.paginas],
                        expediente_id=d.expediente_id, documento_id=d.documento_id, nombres=d.nombres)
    return {"fragmentos": n}


@app.get("/salud")
def salud():
    return {"estado": "ok"}
