"""API de la primera iteración ODR. Ejecutar con uvicorn api.main:app --factory."""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import base64

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import psycopg
import pyotp

from compartido.seguridad.configuracion import Configuracion, Cifrado, transaccion
from modulos.identidad.credenciales import emitir_token, leer_token, hash_password, verificar_password, TokenInvalido
from modulos.odr import contratos as dto
from modulos.odr import servicio as odr
from modulos.odr.recomendacion import recomendar


def crear_app(config: Configuracion):
    config.validar()
    cifrado = Cifrado(config.encryption_key)
    api = FastAPI(title='Concordia ODR', version='0.2.0')
    bearer = HTTPBearer(auto_error=False)

    @api.middleware('http')
    async def cabeceras(request, call_next):
        respuesta = await call_next(request)
        respuesta.headers['Cache-Control'] = 'no-store'
        respuesta.headers['X-Content-Type-Options'] = 'nosniff'
        return respuesta

    @api.exception_handler(RequestValidationError)
    async def validacion(request, exc):
        # No devolver contraseñas, cuerpos ODR ni inputs sensibles de Pydantic.
        return JSONResponse(status_code=422, content={'detail': 'Datos inválidos o campos no permitidos',
            'campos': ['.'.join(map(str, e['loc'])) for e in exc.errors()]})

    @api.exception_handler(psycopg.Error)
    async def error_bd(request, exc):
        # No filtrar SQL, parámetros ni contenido ODR a cliente/logs.
        codigo = 409 if isinstance(exc, (psycopg.IntegrityError, psycopg.errors.RaiseException)) else 503
        return JSONResponse(status_code=codigo, content={'detail': 'La operación no pudo completarse. Revisa el estado y vuelve a intentar.'})

    def usuario_actual(cred: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if not cred:
            raise HTTPException(401, 'Inicia sesión')
        try:
            uid, mfa = leer_token(cred.credentials, clave=config.jwt_secret)
        except TokenInvalido:
            raise HTTPException(401, 'Sesión inválida o expirada') from None
        with transaccion(config, 'rol_auth') as db:
            u = db.execute('''SELECT u.id,u.nombre,u.correo,u.activo,r.rol FROM nucleo_comun.usuario u
              JOIN nucleo_comun.usuario_rol r ON r.usuario_id=u.id WHERE u.id=%s''', (uid,)).fetchone()
        odr.exigir(u and u['activo'], 'Cuenta no disponible', 401)
        odr.exigir(u['rol'] == 'CIUDADANO' or mfa, 'MFA requerido', 403)
        return u

    def sesion(u, mfa=False):
        return {'token': emitir_token(u['id'], clave=config.jwt_secret, mfa_verificado=mfa, duracion_minutos=15),
                'usuario': {k: u[k] for k in ('id','nombre','correo','rol')}, 'expira_en_segundos': 900}

    def vencer():
        with transaccion(config, 'rol_tarea_odr') as db:
            db.execute('SELECT schema_odr.vencer_invitaciones()')

    @api.get('/api/health')
    def salud():
        with transaccion(config, 'rol_auth') as db:
            db.execute('SELECT 1')
        return {'estado': 'ok', 'modo': 'demostracion', 'firma_demo': config.firma_demo}

    @api.post('/api/auth/registro', status_code=201)
    def registrar(datos: dto.Registro):
        uid = uuid4()
        with transaccion(config, 'rol_app_nucleo', uid) as db:
            db.execute('INSERT INTO nucleo_comun.usuario(id,nombre,correo,password_hash) VALUES (%s,%s,%s,%s)',
                       (uid, datos.nombre, datos.correo, hash_password(datos.contrasena)))
            db.execute("INSERT INTO nucleo_comun.usuario_rol VALUES (%s,'CIUDADANO')", (uid,))
            db.execute('SELECT nucleo_comun.vincular_invitaciones()')
        return sesion({'id': uid, 'nombre': datos.nombre, 'correo': datos.correo, 'rol': 'CIUDADANO'})

    @api.post('/api/auth/login')
    def login(datos: dto.Login):
        with transaccion(config, 'rol_auth') as db:
            u = db.execute('''SELECT u.*,r.rol FROM nucleo_comun.usuario u
              JOIN nucleo_comun.usuario_rol r ON r.usuario_id=u.id WHERE u.correo=%s''', (datos.correo,)).fetchone()
        odr.exigir(u and u['activo'] and verificar_password(datos.contrasena, u['password_hash']), 'Credenciales inválidas', 401)
        mfa = False
        if u['rol'] != 'CIUDADANO':
            odr.exigir(u['mfa_habilitado'] and u['mfa_secreto'], 'MFA no configurado', 403)
            secreto = cifrado.abrir(base64.b64decode(u['mfa_secreto']), str(u['id'])).decode()
            mfa = pyotp.TOTP(secreto).verify(datos.codigo_mfa or '', valid_window=1)
            odr.exigir(mfa, 'Credenciales inválidas', 401)
        if u['rol'] == 'CIUDADANO':
            with transaccion(config, 'rol_app_nucleo', u['id']) as db:
                db.execute('SELECT nucleo_comun.vincular_invitaciones()')
        return sesion(u, mfa)

    @api.get('/api/auth/me')
    def me(u=Depends(usuario_actual)):
        return {k: u[k] for k in ('id','nombre','correo','rol')}

    @api.get('/api/conflictos/mios')
    def asuntos(u=Depends(usuario_actual)):
        odr.exigir(u['rol'] in ('CIUDADANO','MEDIADOR'), 'Acceso ODR denegado', 403)
        vencer()
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            return db.execute('''SELECT c.id,c.titulo,c.materia,c.estado,c.solicitante_id,c.creado_en,
              m.estado AS estado_mediacion,m.resultado,m.mediador_id
              FROM nucleo_comun.conflicto c LEFT JOIN schema_odr.mediacion m ON m.conflicto_id=c.id
              ORDER BY c.creado_en DESC''').fetchall()

    @api.post('/api/conflictos', status_code=201)
    def capturar(datos: dto.Captura, u=Depends(usuario_actual)):
        odr.exigir(u['rol'] == 'CIUDADANO', 'Requiere ciudadano', 403)
        odr.exigir(datos.demandante.correo == u['correo'] and datos.demandado.correo != u['correo'], 'Revisa los correos de las partes', 422)
        cid = uuid4()
        with transaccion(config, 'rol_app_nucleo', u['id']) as db:
            db.execute('INSERT INTO nucleo_comun.conflicto(id,solicitante_id,titulo) VALUES (%s,%s,%s)', (cid, u['id'], datos.titulo))
            otro = db.execute('SELECT nucleo_comun.ciudadano_por_correo(%s) AS id', (datos.demandado.correo,)).fetchone()['id']
            for rol, p, uid in [('DEMANDANTE', datos.demandante, u['id']), ('DEMANDADO', datos.demandado, otro)]:
                db.execute('''INSERT INTO nucleo_comun.parte(conflicto_id,usuario_id,rol,nombre,correo,domicilio_notificaciones)
                  VALUES (%s,%s,%s,%s,%s,%s)''', (cid, uid, rol, p.nombre, p.correo, p.domicilio_notificaciones))
            odr.auditar(db, u['id'], cid, 'CAPTURA', None, 'CAPTURA')
        return {'id': cid}

    @api.post('/api/conflictos/{cid}/orientacion')
    def orientar(cid: UUID, datos: dto.Orientar, u=Depends(usuario_actual)):
        odr.exigir(u['rol'] == 'CIUDADANO', 'Requiere ciudadano', 403)
        with transaccion(config, 'rol_app_nucleo', u['id']) as db:
            c = db.execute('SELECT * FROM nucleo_comun.conflicto WHERE id=%s FOR UPDATE', (cid,)).fetchone()
            odr.exigir(c and c['solicitante_id'] == u['id'], 'Asunto no disponible', 404)
            odr.exigir(c['estado'] == 'CAPTURA', 'La orientación ya fue registrada')
            db.execute("UPDATE nucleo_comun.conflicto SET narrativa_inicial=%s,materia=%s,mediable=%s,estado='ORIENTADO' WHERE id=%s",
                       (datos.narrativa, datos.materia, datos.mediable, cid))
            odr.auditar(db, u['id'], cid, 'ORIENTACION_MANUAL_DEMO', 'CAPTURA', 'ORIENTADO')
        return {'estado': 'ORIENTADO', 'origen': 'MANUAL_DEMOSTRACION'}

    @api.post('/api/conflictos/{cid}/invitacion')
    def invitar(cid: UUID, datos: dto.Invitar, u=Depends(usuario_actual)):
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            # El conflicto debe bloquearse antes de crear la única mediación.
            db.execute('SELECT id FROM nucleo_comun.conflicto WHERE id=%s FOR UPDATE', (cid,))
            c, partes, m = odr.cargar(db, cid, u)
            odr.exigir(c['solicitante_id'] == u['id'], 'Solo el solicitante puede invitar', 403)
            if m:
                return {'mediacion_id': m['id'], 'enlace': f'/ciudadano/negociacion/{cid}'}
            odr.exigir(c['estado'] == 'ORIENTADO' and c['mediable'], 'El asunto no está habilitado para mediación')
            contraparte = next(p for p in partes if p['rol'] == 'DEMANDADO')
            mid = uuid4()
            db.execute('INSERT INTO schema_odr.mediacion(id,conflicto_id) VALUES (%s,%s)', (mid,cid))
            db.execute('''INSERT INTO schema_odr.invitacion(mediacion_id,contraparte_id,fecha_limite)
              VALUES (%s,%s,CURRENT_DATE + %s)''', (mid,contraparte['id'],datos.plazo_dias))
            db.execute("UPDATE nucleo_comun.conflicto SET estado='EN_MEDIACION' WHERE id=%s", (cid,))
            odr.auditar(db,u['id'],cid,'INVITACION_ENVIADA','ORIENTADO','EN_MEDIACION')
            odr.notificar(db,cid,'INVITACION_ENVIADA')
        return {'mediacion_id': mid, 'enlace': f'/ciudadano/negociacion/{cid}'}

    @api.get('/api/odr/{cid}')
    def obtener(cid: UUID, u=Depends(usuario_actual)):
        vencer()
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            return odr.detalle(db,cid,u,cifrado)

    @api.post('/api/odr/{cid}/invitacion/responder')
    def responder_invitacion(cid: UUID, datos: dto.RespuestaInvitacion, u=Depends(usuario_actual)):
        vencer()
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            c, partes, m = odr.cargar(db,cid,u,True)
            odr.exigir(any(p['rol']=='DEMANDADO' and p['usuario_id']==u['id'] for p in partes), 'Solo la contraparte puede responder', 403)
            odr.exigir(m and m['estado']=='INVITACION_ENVIADA', 'La invitación ya no está pendiente')
            estado = 'ACEPTADA' if datos.aceptar else 'RECHAZADA'
            db.execute('UPDATE schema_odr.invitacion SET estado=%s,respondida_en=now() WHERE mediacion_id=%s', (estado,m['id']))
            if datos.aceptar:
                db.execute("UPDATE schema_odr.mediacion SET estado='EN_NEGOCIACION' WHERE id=%s", (m['id'],))
                odr.auditar(db,u['id'],cid,'INVITACION_ACEPTADA','INVITACION_ENVIADA','EN_NEGOCIACION')
                odr.notificar(db,cid,'INVITACION_ACEPTADA')
            else:
                odr.concluir(db,u,c,m,'NO_ACEPTADA')
        return {'estado': estado}

    @api.post('/api/odr/{cid}/mensajes', status_code=201)
    def mensaje(cid: UUID, datos: dto.Mensaje, u=Depends(usuario_actual)):
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            c, partes, m = odr.cargar(db,cid,u,True)
            odr.negociando(m)
            fila = db.execute('INSERT INTO schema_odr.mensaje(mediacion_id,autor_id,contenido_cifrado) VALUES (%s,%s,%s) RETURNING id',
                              (m['id'],u['id'],cifrado.cifrar(datos.texto,str(m['id'])))).fetchone()
            odr.auditar(db,u['id'],cid,'MENSAJE_CREADO')
            odr.notificar(db,cid,'MENSAJE_NUEVO')
            return fila

    @api.post('/api/odr/{cid}/propuestas', status_code=201)
    def propuesta(cid: UUID, datos: dto.Propuesta, u=Depends(usuario_actual)):
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            c, partes, m = odr.cargar(db,cid,u,True)
            odr.negociando(m)
            odr.solo_parte(u,partes)
            if datos.responde_a_id:
                anterior = db.execute('SELECT * FROM schema_odr.propuesta WHERE id=%s AND mediacion_id=%s', (datos.responde_a_id,m['id'])).fetchone()
                odr.exigir(anterior and anterior['autor_id']!=u['id'], 'La contrapropuesta debe responder a la otra parte')
            fila = db.execute('''INSERT INTO schema_odr.propuesta(mediacion_id,autor_id,contenido_cifrado,monto,responde_a_id)
              VALUES (%s,%s,%s,%s,%s) RETURNING id''', (m['id'],u['id'],cifrado.cifrar(datos.texto,str(m['id'])),datos.monto,datos.responde_a_id)).fetchone()
            odr.auditar(db,u['id'],cid,'PROPUESTA_CREADA')
            odr.notificar(db,cid,'PROPUESTA_NUEVA')
            return fila

    @api.post('/api/odr/{cid}/propuestas/{pid}/responder')
    def responder_propuesta(cid: UUID, pid: UUID, datos: dto.RespuestaPropuesta, u=Depends(usuario_actual)):
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            c, partes, m = odr.cargar(db,cid,u,True)
            odr.negociando(m)
            odr.solo_parte(u,partes)
            p = db.execute('SELECT * FROM schema_odr.propuesta WHERE id=%s AND mediacion_id=%s', (pid,m['id'])).fetchone()
            odr.exigir(p and p['autor_id']!=u['id'], 'No puedes responder tu propia propuesta', 403)
            odr.exigir(p['estado']=='PENDIENTE', 'Propuesta ya respondida')
            db.execute('UPDATE schema_odr.propuesta SET estado=%s,respondida_por=%s WHERE id=%s', (datos.estado,u['id'],pid))
            odr.auditar(db,u['id'],cid,'PROPUESTA_'+datos.estado)
            odr.notificar(db,cid,'PROPUESTA_RESPONDIDA')
        return {'estado': datos.estado}

    @api.post('/api/odr/{cid}/solicitar-mediador')
    def solicitar_mediador(cid: UUID, u=Depends(usuario_actual)):
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            c, partes, m = odr.cargar(db,cid,u,True)
            odr.negociando(m)
            odr.solo_parte(u,partes)
            fila = db.execute('SELECT schema_odr.asignar_mediador(%s) AS mediador_id', (m['id'],)).fetchone()
            odr.auditar(db,u['id'],cid,'MEDIADOR_SOLICITADO')
            odr.notificar(db,cid,'MEDIADOR_SOLICITADO')
            return fila

    @api.post('/api/odr/{cid}/sesiones', status_code=201)
    def sesion_mediacion(cid: UUID, datos: dto.Sesion, u=Depends(usuario_actual)):
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            c, partes, m = odr.cargar(db,cid,u,True)
            odr.negociando(m)
            odr.solo_mediador(u,m)
            odr.exigir(datos.fecha_hora > datetime.now(timezone.utc), 'La sesión debe programarse en el futuro', 422)
            fila = db.execute('INSERT INTO schema_odr.sesion(mediacion_id,fecha_hora,enlace) VALUES (%s,%s,%s) RETURNING id', (m['id'],datos.fecha_hora,datos.enlace)).fetchone()
            odr.auditar(db,u['id'],cid,'SESION_PROGRAMADA')
            odr.notificar(db,cid,'SESION_PROGRAMADA')
            return fila

    @api.post('/api/odr/{cid}/sesiones/{sid}/notas', status_code=201)
    def nota(cid: UUID, sid: UUID, datos: dto.Mensaje, u=Depends(usuario_actual)):
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            c, partes, m = odr.cargar(db,cid,u,True)
            odr.negociando(m)
            odr.solo_mediador(u,m)
            odr.exigir(db.execute('SELECT 1 FROM schema_odr.sesion WHERE id=%s AND mediacion_id=%s',(sid,m['id'])).fetchone(), 'Sesión no disponible',404)
            db.execute('INSERT INTO schema_odr.nota_mediador(mediacion_id,mediador_id,sesion_id,contenido_cifrado) VALUES (%s,%s,%s,%s)', (m['id'],u['id'],sid,cifrado.cifrar(datos.texto,str(m['id']))))
            odr.auditar(db,u['id'],cid,'NOTA_REGISTRADA')
        return {'registrada': True}

    @api.get('/api/odr/{cid}/recomendacion')
    def recomendacion(cid: UUID, u=Depends(usuario_actual)):
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            c, partes, m = odr.cargar(db,cid,u)
            odr.negociando(m)
            return recomendar(c['narrativa_inicial'], c['materia'])

    @api.put('/api/odr/{cid}/convenio')
    def convenio(cid: UUID, datos: dto.Convenio, u=Depends(usuario_actual)):
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            c, partes, m = odr.cargar(db,cid,u,True)
            odr.guardar_convenio(db,u,c,partes,m,datos,cifrado)
        return {'estado': 'PENDIENTE_FORMALIZACION'}

    @api.get('/api/odr/{cid}/convenio/documento')
    def documento(cid: UUID, u=Depends(usuario_actual)):
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            c, partes, m = odr.cargar(db,cid,u)
            odr.exigir(m, 'Convenio no disponible',404)
            v = db.execute('SELECT documento_cifrado FROM schema_odr.convenio WHERE mediacion_id=%s',(m['id'],)).fetchone()
            odr.exigir(v and v['documento_cifrado'], 'Convenio no disponible',404)
            datos = cifrado.abrir(v['documento_cifrado'],str(m['id']))
        return Response(datos, media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="convenio-{cid}.pdf"'})

    @api.post('/api/odr/{cid}/convenio/firmas')
    def firma(cid: UUID, datos: dto.Firma, idempotency_key: UUID = Header(), u=Depends(usuario_actual)):
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            c, partes, m = odr.cargar(db,cid,u,True)
            return odr.firmar(db,u,c,partes,m,datos,idempotency_key,config.firma_demo)

    @api.post('/api/odr/{cid}/concluir')
    def conclusion(cid: UUID, datos: dto.Conclusion, u=Depends(usuario_actual)):
        with transaccion(config, 'rol_app_odr', u['id']) as db:
            c, partes, m = odr.cargar(db,cid,u,True)
            odr.exigir(m and m['estado'] in ('INVITACION_ENVIADA','EN_NEGOCIACION'), 'No se puede concluir en este estado')
            if datos.resultado == 'DESISTIMIENTO':
                odr.solo_parte(u,partes)
            else:
                odr.solo_mediador(u,m)
                odr.negociando(m)
            if m['estado']=='INVITACION_ENVIADA':
                db.execute("UPDATE schema_odr.invitacion SET estado='RECHAZADA',respondida_en=now() WHERE mediacion_id=%s", (m['id'],))
            odr.concluir(db,u,c,m,datos.resultado)
        return {'estado': 'EN_ESPERA_DECISION'}

    @api.post('/api/conflictos/{cid}/canalizar')
    def canalizar(cid: UUID, datos: dto.Canalizar, idempotency_key: UUID = Header(), u=Depends(usuario_actual)):
        odr.exigir(u['rol']=='CIUDADANO', 'Requiere solicitante ciudadano',403)
        # Único cruce: función SQL con lista positiva; el rol no puede leer tablas ODR.
        with transaccion(config,'rol_canalizador',u['id']) as db:
            fila = db.execute('SELECT nucleo_comun.canalizar_odr(%s,%s,%s) AS demanda_id',(cid,u['id'],idempotency_key)).fetchone()
        return fila

    @api.get('/api/conflictos/{cid}/demanda-borrador')
    def demanda(cid: UUID, u=Depends(usuario_actual)):
        with transaccion(config,'rol_app_judicial',u['id']) as db:
            d = db.execute('''SELECT id,conflicto_id,estado,origen,narrativa_inicial,materia,puntos_pendientes
              FROM schema_judicial.demanda WHERE conflicto_id=%s''',(cid,)).fetchone()
            odr.exigir(d, 'Borrador no disponible',404)
            return d

    @api.get('/api/notificaciones')
    def notificaciones(u=Depends(usuario_actual)):
        with transaccion(config,'rol_app_nucleo',u['id']) as db:
            return db.execute('SELECT id,conflicto_id,evento,leida,creado_en FROM nucleo_comun.notificacion ORDER BY creado_en DESC LIMIT 100').fetchall()

    @api.post('/api/notificaciones/{nid}/leer')
    def leer_notificacion(nid: UUID, u=Depends(usuario_actual)):
        with transaccion(config,'rol_app_nucleo',u['id']) as db:
            fila = db.execute('UPDATE nucleo_comun.notificacion SET leida=true WHERE id=%s RETURNING id',(nid,)).fetchone()
            odr.exigir(fila, 'Notificación no disponible',404)
            return fila

    return api


def app():
    return crear_app(Configuracion.entorno())
