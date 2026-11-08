"""P1: registro ciudadano, alta de MFA, cambio de contraseña y alta de personal (RF1.1–RF1.3)."""
import secrets
from io import BytesIO
from uuid import UUID, uuid4

import pyotp
import segno

from compartido.auditoria.bitacora import registrar
from compartido.bd import RolBD, transaccion
from compartido.cifrado import cifrar
from compartido.config import config
from compartido.errores import ReglaNegocio
from compartido.seguridad.dependencias import exigir_rol
from modulos.identidad.autorizacion import Principal, Rol
from modulos.identidad.credenciales import emitir_token, hash_password, verificar_password
from modulos.identidad.servicio import perfil, totp_valido

EMISOR = "Plataforma Jurídica Inteligente (demo)"


def _token(usuario_id: UUID, mfa: bool) -> str:
    return emitir_token(usuario_id, clave=config().jwt_clave, mfa_verificado=mfa, duracion_minutos=config().duracion_sesion_min)


def registrar_ciudadano(nombre: str, correo: str, curp: str, password: str) -> dict:
    uid = uuid4()
    with transaccion(RolBD.AUTH, None) as c:
        if c.execute("SELECT 1 FROM nucleo_comun.usuario WHERE correo=%s OR curp=%s", (correo, curp)).fetchone():
            raise ReglaNegocio("Ya existe una cuenta con ese correo o CURP")
    with transaccion(RolBD.NUCLEO, uid) as c:
        c.execute("INSERT INTO nucleo_comun.usuario (id, correo, nombre, password_hash, curp) VALUES (%s,%s,%s,%s,%s)",
                  (uid, correo, nombre.strip(), hash_password(password), curp))
        c.execute("INSERT INTO nucleo_comun.usuario_rol VALUES (%s,'CIUDADANO')", (uid,))
        registrar(c, usuario_id=uid, entidad="usuario", entidad_id=uid, accion="REGISTRO_CIUDADANO")
    token = _token(uid, False)
    return {"token": token, "usuario": perfil(token), "requiere_alta_mfa": False, "debe_cambiar_password": False}


def iniciar_alta_mfa(p: Principal) -> dict:
    if p.rol == Rol.CIUDADANO:
        raise ReglaNegocio("El segundo factor es obligatorio solo para personal institucional")
    secreto = pyotp.random_base32()
    with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
        u = c.execute("SELECT correo, mfa_habilitado FROM nucleo_comun.usuario WHERE id=%s", (p.usuario_id,)).fetchone()
        if u["mfa_habilitado"]:
            raise ReglaNegocio("Tu segundo factor ya está activo")
        c.execute("UPDATE nucleo_comun.usuario SET mfa_secreto_cifrado=%s WHERE id=%s",
                  (cifrar(secreto, f"mfa:{p.usuario_id}"), p.usuario_id))
    uri = pyotp.TOTP(secreto).provisioning_uri(name=u["correo"], issuer_name=EMISOR)
    svg = BytesIO()
    segno.make(uri, error="m").save(svg, kind="svg", scale=5, dark="#101C2E", xmldecl=False, svgns=True)
    return {"qr_svg": svg.getvalue().decode(), "secreto": secreto}


def confirmar_alta_mfa(p: Principal, codigo: str) -> dict:
    with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
        u = c.execute("SELECT mfa_secreto_cifrado, mfa_habilitado FROM nucleo_comun.usuario WHERE id=%s", (p.usuario_id,)).fetchone()
        if u["mfa_habilitado"]:
            raise ReglaNegocio("Tu segundo factor ya está activo")
        if not totp_valido(p.usuario_id, u["mfa_secreto_cifrado"], codigo):
            raise ReglaNegocio("El código no coincide. Revisa la hora de tu teléfono e intenta de nuevo.")
        c.execute("UPDATE nucleo_comun.usuario SET mfa_habilitado=true WHERE id=%s", (p.usuario_id,))
        registrar(c, usuario_id=p.usuario_id, entidad="usuario", entidad_id=p.usuario_id, accion="MFA_ACTIVADO")
    token = _token(p.usuario_id, True)  # el servidor decide mfa=true solo tras verificar el código
    return {"token": token, "usuario": perfil(token)}


def cambiar_password(p: Principal, actual: str, nueva: str) -> None:
    with transaccion(RolBD.NUCLEO, p.usuario_id) as c:
        u = c.execute("SELECT password_hash FROM nucleo_comun.usuario WHERE id=%s", (p.usuario_id,)).fetchone()
        if not verificar_password(actual, u["password_hash"]):
            raise ReglaNegocio("La contraseña actual no es correcta")
        if actual == nueva:
            raise ReglaNegocio("La nueva contraseña debe ser distinta")
        c.execute("UPDATE nucleo_comun.usuario SET password_hash=%s, debe_cambiar_password=false WHERE id=%s",
                  (hash_password(nueva), p.usuario_id))
        registrar(c, usuario_id=p.usuario_id, entidad="usuario", entidad_id=p.usuario_id, accion="PASSWORD_CAMBIADA")


def renovar(p: Principal) -> dict:
    token = _token(p.usuario_id, p.mfa_verificado)
    return {"token": token}


# --- Administración de personal (RF1.2, RF1.3) ---------------------------------------------------

def listar_personal(p: Principal) -> list[dict]:
    exigir_rol(p, Rol.ADMINISTRADOR)
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        filas = c.execute("SELECT u.id, u.nombre, u.correo, u.cargo, u.activo, u.mfa_habilitado, r.rol"
                          " FROM nucleo_comun.usuario u JOIN nucleo_comun.usuario_rol r ON r.usuario_id=u.id"
                          " WHERE r.rol <> 'CIUDADANO' ORDER BY r.rol, u.nombre").fetchall()
    return [{**f, "id": str(f["id"])} for f in filas]


def alta_personal(p: Principal, nombre: str, correo: str, rol: str, cargo: str | None) -> dict:
    exigir_rol(p, Rol.ADMINISTRADOR)
    temporal = secrets.token_urlsafe(12)
    uid = uuid4()
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        if c.execute("SELECT 1 FROM nucleo_comun.usuario WHERE correo=%s", (correo,)).fetchone():
            raise ReglaNegocio("Ya existe una cuenta con ese correo")
        c.execute("INSERT INTO nucleo_comun.usuario (id, correo, nombre, password_hash, cargo, debe_cambiar_password)"
                  " VALUES (%s,%s,%s,%s,%s,true)", (uid, correo, nombre.strip(), hash_password(temporal), cargo))
        c.execute("INSERT INTO nucleo_comun.usuario_rol VALUES (%s,%s)", (uid, rol))
        registrar(c, usuario_id=p.usuario_id, entidad="usuario", entidad_id=uid, accion=f"ALTA_{rol}")
    # La contraseña temporal se muestra una sola vez; debe cambiarse y activarse MFA en el primer acceso.
    return {"id": str(uid), "contrasena_temporal": temporal}


def cambiar_estado_personal(p: Principal, usuario_id: UUID, activo: bool) -> None:
    exigir_rol(p, Rol.ADMINISTRADOR)
    if usuario_id == p.usuario_id:
        raise ReglaNegocio("No puedes desactivar tu propia cuenta")
    with transaccion(RolBD.ADMIN, p.usuario_id) as c:
        if c.execute("UPDATE nucleo_comun.usuario SET activo=%s WHERE id=%s", (activo, usuario_id)).rowcount == 0:
            raise ReglaNegocio("Solo se puede cambiar el estado del personal institucional")
        registrar(c, usuario_id=p.usuario_id, entidad="usuario", entidad_id=usuario_id,
                  accion="ACTIVAR" if activo else "DESACTIVAR")
