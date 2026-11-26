"""Traducción de errores de dominio y de base de datos a respuestas HTTP sin filtrar detalles internos."""
import logging

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from modulos.estado.modelo import EstadoInvalido
from modulos.identidad.autorizacion import AccesoDenegado
from modulos.identidad.credenciales import TokenInvalido

log = logging.getLogger("core-api")


class NoEncontrado(LookupError):
    pass


class ReglaNegocio(ValueError):
    """Error de validación que se puede mostrar a la persona usuaria."""


def instalar(app: FastAPI) -> None:
    def resp(codigo: int, detalle: str) -> JSONResponse:
        return JSONResponse(status_code=codigo, content={"detail": detalle})

    @app.exception_handler(TokenInvalido)
    async def _token(_: Request, e: TokenInvalido):
        return resp(401, "Sesión inválida o expirada")

    @app.exception_handler(AccesoDenegado)
    async def _acceso(_: Request, e: AccesoDenegado):
        return resp(403, str(e))

    @app.exception_handler(NoEncontrado)
    async def _no(_: Request, e: NoEncontrado):
        return resp(404, str(e) or "No encontrado")

    @app.exception_handler(ReglaNegocio)
    async def _regla(_: Request, e: ReglaNegocio):
        return resp(422, str(e))

    @app.exception_handler(EstadoInvalido)
    async def _estado(_: Request, e: EstadoInvalido):
        return resp(409, str(e))

    @app.exception_handler(psycopg.errors.InsufficientPrivilege)
    async def _priv(_: Request, e):
        return resp(403, "Acceso no autorizado al recurso")

    @app.exception_handler(psycopg.errors.RaiseException)
    async def _raise(_: Request, e: psycopg.errors.RaiseException):
        # Mensajes de reglas en triggers/funciones: son de negocio, no contienen datos.
        return resp(409, e.diag.message_primary or "Operación no permitida")

    @app.exception_handler(psycopg.errors.CheckViolation)
    async def _check(_: Request, e):
        return resp(422, "Los datos no cumplen las reglas del registro")

    @app.exception_handler(psycopg.errors.UniqueViolation)
    async def _uniq(_: Request, e):
        return resp(409, "El registro ya existe")
