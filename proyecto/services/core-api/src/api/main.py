"""Núcleo transaccional (core-api). Ejecutar: uvicorn api.main:app --app-dir src --port 8000"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from compartido import errores
from compartido.bd import cerrar_pools
from compartido.config import config
from modulos.administracion.router import router as administracion
from modulos.canalizacion.router import router as canalizacion
from modulos.identidad.router import admin as personal, router as identidad
from modulos.judicial.router import router as judicial
from modulos.odr.router import router as odr
from modulos.orientacion.router import router as orientacion

ROUTERS = [identidad, personal, orientacion, odr, canalizacion, judicial, administracion]


@asynccontextmanager
async def ciclo(_: FastAPI):
    yield
    cerrar_pools()


def crear_app() -> FastAPI:
    app = FastAPI(title="Sistema Jurídico Inteligente · core-api", version="0.2.0", lifespan=ciclo)
    app.add_middleware(CORSMiddleware, allow_origins=[config().origen_web], allow_credentials=False,
                       allow_methods=["*"], allow_headers=["Authorization", "Content-Type"])
    errores.instalar(app)
    for r in ROUTERS:
        app.include_router(r)

    @app.get("/salud")
    def salud():
        return {"estado": "ok"}

    return app


app = crear_app()
