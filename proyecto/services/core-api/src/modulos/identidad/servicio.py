"""P1: verificación de contraseña y segundo factor antes de emitir el token."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pyotp

from compartido.auditoria.bitacora import registrar
from compartido.bd import RolBD, transaccion
from compartido.cifrado import descifrar
from compartido.config import config
from compartido.errores import ReglaNegocio
from compartido.seguridad.dependencias import cargar_principal
from modulos.identidad.autorizacion import Rol
from modulos.identidad.credenciales import emitir_token, verificar_password

MAX_INTENTOS = 5
BLOQUEO = timedelta(minutes=15)


class CredencialesInvalidas(ReglaNegocio):
    pass


def totp_valido(usuario_id: UUID, secreto_cifrado: bytes | None, codigo: str | None) -> bool:
    if not secreto_cifrado or not codigo:
        return False
    secreto = descifrar(secreto_cifrado, f"mfa:{usuario_id}")
    return pyotp.TOTP(secreto).verify(codigo.replace(" ", ""), valid_window=1)


def iniciar_sesion(correo: str, password: str, codigo_mfa: str | None) -> dict:
    correo = correo.strip().lower()
    with transaccion(RolBD.AUTH, None) as c:
        u = c.execute("SELECT id, nombre, correo, password_hash, activo, mfa_habilitado, mfa_secreto_cifrado,"
                      " intentos_fallidos, bloqueado_hasta, cargo, debe_cambiar_password"
                      " FROM nucleo_comun.usuario WHERE correo = %s FOR UPDATE", (correo,)).fetchone()
        ahora = datetime.now(timezone.utc)
        if not u or not u["activo"]:
            raise CredencialesInvalidas("Correo o contraseña incorrectos")
        if u["bloqueado_hasta"] and u["bloqueado_hasta"] > ahora:
            raise CredencialesInvalidas("Cuenta bloqueada temporalmente por intentos fallidos. Intenta en 15 minutos.")
        roles = {r["rol"] for r in c.execute("SELECT rol FROM nucleo_comun.usuario_rol WHERE usuario_id=%s", (u["id"],))}
        es_personal = bool(roles - {Rol.CIUDADANO.value})

        ok = verificar_password(password, u["password_hash"])
        mfa_ok = False
        if ok and es_personal:
            if not u["mfa_habilitado"]:
                ok = True  # primer acceso: puede entrar solo a dar de alta su MFA (token sin mfa)
            else:
                mfa_ok = totp_valido(u["id"], u["mfa_secreto_cifrado"], codigo_mfa)
                ok = mfa_ok
        if not ok:
            intentos = u["intentos_fallidos"] + 1
            c.execute("UPDATE nucleo_comun.usuario SET intentos_fallidos=%s, bloqueado_hasta=%s WHERE id=%s",
                      (0 if intentos >= MAX_INTENTOS else intentos,
                       ahora + BLOQUEO if intentos >= MAX_INTENTOS else None, u["id"]))
            registrar(c, usuario_id=u["id"], entidad="usuario", entidad_id=u["id"], accion="LOGIN_FALLIDO")
            if es_personal and verificar_password(password, u["password_hash"]) and u["mfa_habilitado"]:
                raise CredencialesInvalidas("Código MFA incorrecto")
            raise CredencialesInvalidas("Correo o contraseña incorrectos")
        c.execute("UPDATE nucleo_comun.usuario SET intentos_fallidos=0, bloqueado_hasta=NULL WHERE id=%s", (u["id"],))
        registrar(c, usuario_id=u["id"], entidad="usuario", entidad_id=u["id"], accion="LOGIN_OK")

    token = emitir_token(u["id"], clave=config().jwt_clave, mfa_verificado=mfa_ok,
                         duracion_minutos=config().duracion_sesion_min)
    return {"token": token, "usuario": perfil(token),
            "requiere_alta_mfa": es_personal and not u["mfa_habilitado"],
            "debe_cambiar_password": u["debe_cambiar_password"]}


def perfil(token: str) -> dict:
    p = cargar_principal(token)
    with transaccion(RolBD.AUTH, None) as c:
        u = c.execute("SELECT id, nombre, correo, cargo FROM nucleo_comun.usuario WHERE id=%s", (p.usuario_id,)).fetchone()
    return {**u, "id": str(u["id"]), "rol": p.rol.value, "mfa": p.mfa_verificado}
