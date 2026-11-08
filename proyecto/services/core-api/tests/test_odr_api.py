"""Aceptación HTTP contra PostgreSQL real. Cada ejecución crea una base aislada."""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import pyotp
import pytest

from api.main import crear_app
from compartido.seguridad.configuracion import Configuracion, Cifrado
from modulos.identidad.credenciales import hash_password

PASSWORD = 'Prueba-sintetica-2026!'


@pytest.fixture(scope='module')
def entorno():
    base = os.getenv('TEST_DATABASE_URL')
    if not base:
        pytest.skip('Define TEST_DATABASE_URL para ejecutar pruebas de PostgreSQL')
    nombre = 'odr_test_' + uuid4().hex
    with psycopg.connect(base, autocommit=True) as db:
        db.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(nombre)))
    dsn = make_conninfo(base, dbname=nombre)
    config = Configuracion(dsn, 'clave-jwt-de-pruebas-'*3, base64.urlsafe_b64encode(os.urandom(32)).decode(), True)
    try:
        with psycopg.connect(dsn, autocommit=True) as db:
            for ruta in sorted((Path(__file__).resolve().parents[3] / 'persistence/postgres').glob('[0-9]*.sql')):
                db.execute(ruta.read_text(encoding='utf-8'))
        with TestClient(crear_app(config)) as cliente:
            yield cliente, config
    finally:
        with psycopg.connect(base, autocommit=True) as db:
            db.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(nombre)))


def post(cliente, ruta, datos, cab=None, codigo=200):
    r = cliente.post('/api'+ruta, json=datos, headers=cab or {})
    assert r.status_code == codigo, r.text
    return r.json()


def cuenta(cliente):
    correo = f'{uuid4().hex}@example.test'
    s = post(cliente,'/auth/registro',{'nombre':'Persona sintética','correo':correo,'contrasena':PASSWORD},codigo=201)
    return {'Authorization': 'Bearer '+s['token']}, s['usuario']


def operador(entorno, rol='MEDIADOR'):
    cliente, config = entorno
    uid, correo, secreto = uuid4(), f'{uuid4().hex}@example.test', pyotp.random_base32()
    cifrado = base64.b64encode(Cifrado(config.encryption_key).cifrar(secreto,str(uid))).decode()
    with psycopg.connect(config.database_url) as db:
        db.execute('INSERT INTO nucleo_comun.usuario(id,correo,nombre,password_hash,mfa_habilitado,mfa_secreto) VALUES (%s,%s,%s,%s,true,%s)',
                   (uid,correo,'Operador sintético',hash_password(PASSWORD),cifrado))
        db.execute('INSERT INTO nucleo_comun.usuario_rol VALUES (%s,%s)',(uid,rol))
    s = post(cliente,'/auth/login',{'correo':correo,'contrasena':PASSWORD,'codigo_mfa':pyotp.TOTP(secreto).now()})
    return {'Authorization':'Bearer '+s['token']}, s['usuario']


def caso(entorno, aceptar=True, mediable=True, registrado=True):
    cliente, _ = entorno
    a, ua = cuenta(cliente)
    if registrado:
        b, ub = cuenta(cliente)
    else:
        b, ub = None, {'correo':f'{uuid4().hex}@example.test'}
    def parte(u):
        return {'nombre':'Parte sintética','correo':u['correo'],'domicilio_notificaciones':'Calle de prueba 123'}
    cid = post(cliente,'/conflictos',{'titulo':'Adeudo de renta sintético','demandante':parte(ua),'demandado':parte(ub)},a,201)['id']
    post(cliente,f'/conflictos/{cid}/orientacion',{'narrativa':'Existe un adeudo de renta y queremos acordar un calendario de pago.','materia':'CIVIL','mediable':mediable,'confirmacion':True},a)
    if mediable:
        post(cliente,f'/conflictos/{cid}/invitacion',{'plazo_dias':7},a)
        if aceptar and registrado:
            post(cliente,f'/odr/{cid}/invitacion/responder',{'aceptar':True},b)
    return cid,a,b,ua,ub


def ver(cliente,cid,cab):
    r = cliente.get('/api/odr/'+cid,headers=cab)
    assert r.status_code==200, r.text
    return r.json()


def redactar(cliente,cid,a,tipo='TOTAL'):
    datos = {'tipo':tipo,'terminos':'Pagar en tres exhibiciones según calendario revisado por ambas partes.',
             'puntos_pendientes':['Determinar responsabilidad por daño pendiente'] if tipo=='PARCIAL' else [],
             'pendientes_revisados':True}
    r = cliente.put(f'/api/odr/{cid}/convenio',headers=a,json=datos)
    assert r.status_code==200, r.text
    return ver(cliente,cid,a)['convenio']


def firmar(cliente,cid,cab,v,codigo=200,clave=None):
    return post(cliente,f'/odr/{cid}/convenio/firmas',{'hash_sha256':v['hash_sha256'],'confirmacion':True},
                {**cab,'Idempotency-Key':clave or str(uuid4())},codigo)


def canalizar(cliente,cid,a,codigo=200,extra=None):
    return post(cliente,f'/conflictos/{cid}/canalizar',{'confirmacion':True,**(extra or {})},
                {**a,'Idempotency-Key':str(uuid4())},codigo)


def test_autenticacion_y_contratos(entorno):
    cliente,_ = entorno
    assert cliente.get('/api/conflictos/mios').status_code==401
    post(cliente,'/auth/registro',{'nombre':'Prueba','correo':'bad','contrasena':'sensible'},codigo=422)
    a,u=cuenta(cliente)
    post(cliente,'/auth/login',{'correo':u['correo'],'contrasena':'incorrecta'},codigo=401)
    post(cliente,'/auth/registro',{'nombre':'Prueba','correo':'x@example.test','contrasena':PASSWORD,'rol':'JUEZ'},codigo=422)
    m,um=operador(entorno)
    post(cliente,'/auth/login',{'correo':um['correo'],'contrasena':PASSWORD,'codigo_mfa':'000000'},codigo=401)


def test_negociacion_cifrado_y_aislamiento(entorno):
    cliente,config=entorno
    cid,a,b,ua,ub=caso(entorno)
    tercero,_=cuenta(cliente)
    juez,_=operador(entorno,'JUEZ')
    assert cliente.get('/api/odr/'+cid,headers=tercero).status_code==404
    assert cliente.get('/api/odr/'+cid,headers=juez).status_code==403
    post(cliente,f'/odr/{cid}/mensajes',{'texto':'SECRETO_NEGOCIACION'},a,201)
    p=post(cliente,f'/odr/{cid}/propuestas',{'texto':'Oferta confidencial','monto':'1200.50'},a,201)
    post(cliente,f'/odr/{cid}/propuestas/{p["id"]}/responder',{'estado':'ACEPTADA'},a,403)
    post(cliente,f'/odr/{cid}/propuestas',{'texto':'Contraoferta','responde_a_id':p['id']},b,201)
    post(cliente,f'/odr/{cid}/propuestas/{p["id"]}/responder',{'estado':'ACEPTADA'},b)
    assert ver(cliente,cid,b)['mensajes'][0]['texto']=='SECRETO_NEGOCIACION'
    canalizar(cliente,cid,a,409)
    canalizar(cliente,cid,a,422,{'mensajes':['filtración']})
    with psycopg.connect(config.database_url) as db:
        raw=db.execute('SELECT contenido_cifrado FROM schema_odr.mensaje').fetchall()
        assert all(b'SECRETO_NEGOCIACION' not in bytes(f[0]) for f in raw)
        db.execute('SET LOCAL ROLE rol_app_judicial')
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            db.execute('SELECT * FROM schema_odr.mensaje')


def test_total_pdf_firmas_y_cierre(entorno):
    cliente,_=entorno
    cid,a,b,_,_=caso(entorno)
    v=redactar(cliente,cid,a)
    documento=cliente.get(f'/api/odr/{cid}/convenio/documento',headers=a)
    assert documento.content.startswith(b'%PDF')
    assert sha256(documento.content).hexdigest()==v['hash_sha256']
    firmar(cliente,cid,a,{**v,'hash_sha256':'0'*64},409)
    clave=str(uuid4())
    assert not firmar(cliente,cid,a,v,clave=clave)['formalizado']
    assert not firmar(cliente,cid,a,v,clave=clave)['formalizado']
    assert ver(cliente,cid,a)['conflicto']['estado']=='EN_MEDIACION'
    assert firmar(cliente,cid,b,v)['formalizado']
    final=ver(cliente,cid,a)
    assert final['conflicto']['estado']=='CONCLUIDO'
    assert len(final['convenio']['firmas'])==2
    post(cliente,f'/odr/{cid}/mensajes',{'texto':'Ya cerrado'},a,409)
    canalizar(cliente,cid,a,409)


def test_parcial_canalizacion_idempotente_y_sin_filtracion(entorno):
    cliente,config=entorno
    cid,a,b,_,_=caso(entorno)
    post(cliente,f'/odr/{cid}/mensajes',{'texto':'NO_EXPORTAR_CONVERSACION'},a,201)
    v=redactar(cliente,cid,a,'PARCIAL')
    canalizar(cliente,cid,a,409)
    firmar(cliente,cid,a,v)
    firmar(cliente,cid,b,v)
    assert ver(cliente,cid,a)['conflicto']['estado']=='EN_ESPERA_DECISION'
    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados=list(pool.map(lambda _:canalizar(cliente,cid,a),range(2)))
    assert resultados[0]==resultados[1]
    d=cliente.get(f'/api/conflictos/{cid}/demanda-borrador',headers=a).json()
    assert d['origen']=='ACUERDO_PARCIAL'
    assert d['puntos_pendientes']==['Determinar responsabilidad por daño pendiente']
    assert 'NO_EXPORTAR_CONVERSACION' not in str(d)
    assert v['terminos'] not in str(d)
    assert set(d)=={'id','conflicto_id','estado','origen','narrativa_inicial','materia','puntos_pendientes'}
    with psycopg.connect(config.database_url) as db:
        audit=db.execute('SELECT accion,motivo FROM nucleo_comun.bitacora WHERE entidad_id=%s',(cid,)).fetchall()
        assert 'NO_EXPORTAR_CONVERSACION' not in str(audit)


def test_invitacion_registro_rechazo_y_plazo(entorno):
    cliente,config=entorno
    cid,a,_,_,ub=caso(entorno,aceptar=False,registrado=False)
    s=post(cliente,'/auth/registro',{'nombre':'Contraparte nueva','correo':ub['correo'],'contrasena':PASSWORD},codigo=201)
    b={'Authorization':'Bearer '+s['token']}
    assert ver(cliente,cid,b)['invitacion']['estado']=='ENVIADA'
    post(cliente,f'/odr/{cid}/invitacion/responder',{'aceptar':False},b)
    assert ver(cliente,cid,a)['mediacion']['resultado']=='NO_ACEPTADA'
    canalizar(cliente,cid,a)
    cid,a,b,_,_=caso(entorno,aceptar=False)
    with psycopg.connect(config.database_url) as db:
        db.execute('UPDATE schema_odr.invitacion SET fecha_limite=CURRENT_DATE-1 WHERE mediacion_id=(SELECT id FROM schema_odr.mediacion WHERE conflicto_id=%s)',(cid,))
    post(cliente,f'/odr/{cid}/invitacion/responder',{'aceptar':True},b,409)
    d=ver(cliente,cid,a)
    assert d['invitacion']['estado']=='VENCIDA'
    assert d['conflicto']['estado']=='EN_ESPERA_DECISION'


def test_mediador_sesiones_notas_y_firma_requerida(entorno):
    cliente,config=entorno
    m,um=operador(entorno)
    # Desactivar otros operadores sintéticos para asignación determinista del escenario.
    with psycopg.connect(config.database_url) as db:
        db.execute("UPDATE nucleo_comun.usuario SET activo=false WHERE id<>%s AND id IN (SELECT usuario_id FROM nucleo_comun.usuario_rol WHERE rol='MEDIADOR')",(um['id'],))
    cid,a,b,_,_=caso(entorno)
    asignado=post(cliente,f'/odr/{cid}/solicitar-mediador',{},a)
    assert asignado['mediador_id']==um['id']
    s=post(cliente,f'/odr/{cid}/sesiones',{'fecha_hora':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'enlace':'https://example.test/sala'},m,201)
    post(cliente,f'/odr/{cid}/sesiones/{s["id"]}/notas',{'texto':'NOTA_SOLO_MEDIADOR'},m,201)
    assert ver(cliente,cid,a)['notas']==[]
    assert ver(cliente,cid,m)['notas'][0]['texto']=='NOTA_SOLO_MEDIADOR'
    v=redactar(cliente,cid,m)
    firmar(cliente,cid,a,v)
    assert not firmar(cliente,cid,b,v)['formalizado']
    assert firmar(cliente,cid,m,v)['formalizado']


def test_desistimiento_y_ruta_directa(entorno):
    cliente,_=entorno
    cid,a,b,_,_=caso(entorno)
    post(cliente,f'/odr/{cid}/concluir',{'resultado':'DESISTIMIENTO','confirmacion':True},a)
    assert ver(cliente,cid,a)['conflicto']['estado']=='EN_ESPERA_DECISION'
    canalizar(cliente,cid,b,409)
    canalizar(cliente,cid,a)
    cid,a,_,_,_=caso(entorno,mediable=False)
    post(cliente,f'/conflictos/{cid}/invitacion',{'plazo_dias':7},a,409)
    assert ver(cliente,cid,a)['conflicto']['estado']=='ORIENTADO'
    canalizar(cliente,cid,a)


def test_recomendacion_sintetica_y_abstencion():
    from modulos.odr.recomendacion import recomendar
    assert recomendar('adeudo de renta','CIVIL')['fuente']=='SINT-CIV-01'
    assert recomendar('sin coincidencias','CIVIL')['fuente'] is None


def test_version_aceptada_inmutable_y_firma_demo_deshabilitada(entorno):
    cliente,config=entorno
    cid,a,b,_,_=caso(entorno)
    v=redactar(cliente,cid,a)
    sin_firma=Configuracion(config.database_url,config.jwt_secret,config.encryption_key,False)
    with TestClient(crear_app(sin_firma)) as otro:
        firmar(otro,cid,a,v,503)
    firmar(cliente,cid,a,v)
    r=cliente.put(f'/api/odr/{cid}/convenio',headers=b,json={'tipo':'TOTAL','terminos':'Cambio no aceptado','puntos_pendientes':[],'pendientes_revisados':True})
    assert r.status_code==409
    with psycopg.connect(config.database_url) as db:
        with pytest.raises(psycopg.errors.RaiseException):
            db.execute("UPDATE schema_odr.convenio SET hash_sha256=repeat('0',64) WHERE id=%s",(v['id'],))


def test_sin_acuerdo_y_evento_canalizacion(entorno):
    cliente,config=entorno
    m,um=operador(entorno)
    with psycopg.connect(config.database_url) as db:
        db.execute("UPDATE nucleo_comun.usuario SET activo=false WHERE id<>%s AND id IN (SELECT usuario_id FROM nucleo_comun.usuario_rol WHERE rol='MEDIADOR')",(um['id'],))
    cid,a,b,_,_=caso(entorno)
    post(cliente,f'/odr/{cid}/solicitar-mediador',{},a)
    post(cliente,f'/odr/{cid}/concluir',{'resultado':'SIN_ACUERDO','confirmacion':True},a,403)
    post(cliente,f'/odr/{cid}/concluir',{'resultado':'SIN_ACUERDO','confirmacion':True},m)
    assert ver(cliente,cid,a)['conflicto']['estado']=='EN_ESPERA_DECISION'
    clave=str(uuid4())
    cab={**a,'Idempotency-Key':clave}
    primera=post(cliente,f'/conflictos/{cid}/canalizar',{'confirmacion':True},cab)
    assert post(cliente,f'/conflictos/{cid}/canalizar',{'confirmacion':True},cab)==primera
    with psycopg.connect(config.database_url) as db:
        assert db.execute("SELECT count(*) FROM nucleo_comun.evento_pendiente WHERE conflicto_id=%s AND tipo='DemandaBorradorCreada'",(cid,)).fetchone()[0]==1
        assert db.execute('SELECT actor_id FROM nucleo_comun.operacion_canalizacion WHERE clave=%s',(clave,)).fetchone()


def test_notificaciones_no_incluyen_cuerpo_odr(entorno):
    cliente,_=entorno
    cid,a,b,_,_=caso(entorno)
    post(cliente,f'/odr/{cid}/mensajes',{'texto':'CONTENIDO_QUE_NO_DEBE_SALIR'},a,201)
    r=cliente.get('/api/notificaciones',headers=b)
    assert r.status_code==200
    assert 'CONTENIDO_QUE_NO_DEBE_SALIR' not in r.text
    aviso=next(n for n in r.json() if n['conflicto_id']==cid)
    tercero,_=cuenta(cliente)
    post(cliente,f'/notificaciones/{aviso["id"]}/leer',{},tercero,404)
    post(cliente,f'/notificaciones/{aviso["id"]}/leer',{},b)
