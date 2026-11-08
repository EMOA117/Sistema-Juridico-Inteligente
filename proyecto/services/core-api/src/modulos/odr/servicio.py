"""Operaciones ODR transaccionales. La fila de mediación serializa sus comandos."""
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException

from modulos.odr.documentos import generar_convenio


def exigir(condicion, detalle, codigo=409):
    if not condicion:
        raise HTTPException(codigo, detalle)


def auditar(db, actor, conflicto, accion, previo=None, nuevo=None, operacion=None):
    db.execute('''INSERT INTO nucleo_comun.bitacora
      (usuario_id,entidad,entidad_id,accion,estado_anterior,estado_nuevo,operacion_id)
      VALUES (%s,'conflicto',%s,%s,%s,%s,%s)''',
      (actor, conflicto, accion, previo, nuevo, operacion or uuid4()))


def notificar(db, conflicto, evento):
    # El aviso solo contiene metadatos. No se copian mensajes ni términos.
    db.execute('''INSERT INTO nucleo_comun.notificacion
      (destinatario_id,correo_destino,conflicto_id,evento)
      SELECT usuario_id,correo,conflicto_id,%s FROM nucleo_comun.parte WHERE conflicto_id=%s''',
      (evento, conflicto))


def cargar(db, cid, usuario, bloquear=False):
    exigir(usuario['rol'] in ('CIUDADANO', 'MEDIADOR'), 'Acceso ODR denegado', 403)
    c = db.execute('SELECT * FROM nucleo_comun.conflicto WHERE id=%s', (cid,)).fetchone()
    exigir(c, 'Asunto no disponible', 404)
    partes = db.execute('SELECT * FROM nucleo_comun.parte WHERE conflicto_id=%s ORDER BY rol', (cid,)).fetchall()
    m = db.execute('SELECT * FROM schema_odr.mediacion WHERE conflicto_id=%s' + (' FOR UPDATE' if bloquear else ''), (cid,)).fetchone()
    participantes = {p['usuario_id'] for p in partes if p['usuario_id']}
    es_parte = usuario['rol'] == 'CIUDADANO' and usuario['id'] in participantes
    es_mediador = usuario['rol'] == 'MEDIADOR' and m and m['mediador_id'] == usuario['id']
    exigir(es_parte or es_mediador, 'Acceso ODR denegado', 403)
    # El bloqueo pudo esperar otra transacción: volver a leer el estado común.
    if bloquear:
        c = db.execute('SELECT * FROM nucleo_comun.conflicto WHERE id=%s', (cid,)).fetchone()
    return c, partes, m


def negociando(m):
    exigir(m and m['estado'] == 'EN_NEGOCIACION', 'La mediación no está en negociación')


def solo_parte(usuario, partes):
    exigir(usuario['rol'] == 'CIUDADANO' and any(p['usuario_id'] == usuario['id'] for p in partes), 'Acción reservada a las partes', 403)


def solo_mediador(usuario, m):
    exigir(m and usuario['rol'] == 'MEDIADOR' and m['mediador_id'] == usuario['id'], 'Requiere mediador asignado', 403)


def concluir(db, usuario, c, m, resultado):
    db.execute("UPDATE schema_odr.mediacion SET estado='CONCLUIDA',resultado=%s,concluida_en=now() WHERE id=%s", (resultado, m['id']))
    nuevo = 'CONCLUIDO' if resultado == 'ACUERDO_TOTAL' else 'EN_ESPERA_DECISION'
    db.execute('UPDATE nucleo_comun.conflicto SET estado=%s WHERE id=%s', (nuevo, c['id']))
    auditar(db, usuario['id'], c['id'], resultado, c['estado'], nuevo)
    notificar(db, c['id'], resultado)


def detalle(db, cid, usuario, cifrado):
    c, partes, m = cargar(db, cid, usuario)
    resultado = {'conflicto': c, 'partes': partes, 'mediacion': m, 'invitacion': None,
                 'mensajes': [], 'propuestas': [], 'sesiones': [], 'notas': [], 'convenio': None}
    if not m:
        return resultado
    contexto = str(m['id'])
    resultado['invitacion'] = db.execute('SELECT * FROM schema_odr.invitacion WHERE mediacion_id=%s', (m['id'],)).fetchone()
    for tabla, campo, destino in [('mensaje','contenido_cifrado','mensajes'), ('propuesta','contenido_cifrado','propuestas')]:
        # tabla viene de la lista constante anterior, nunca de una solicitud.
        filas = db.execute(f'SELECT * FROM schema_odr.{tabla} WHERE mediacion_id=%s ORDER BY creado_en,id', (m['id'],)).fetchall()
        for fila in filas:
            fila['texto'] = cifrado.abrir(fila.pop(campo), contexto).decode()
        resultado[destino] = filas
    resultado['sesiones'] = db.execute('SELECT * FROM schema_odr.sesion WHERE mediacion_id=%s ORDER BY fecha_hora', (m['id'],)).fetchall()
    if usuario['rol'] == 'MEDIADOR':
        notas = db.execute('SELECT * FROM schema_odr.nota_mediador WHERE mediacion_id=%s ORDER BY creado_en', (m['id'],)).fetchall()
        for nota in notas:
            nota['texto'] = cifrado.abrir(nota.pop('contenido_cifrado'), contexto).decode()
        resultado['notas'] = notas
    v = db.execute('SELECT * FROM schema_odr.convenio WHERE mediacion_id=%s', (m['id'],)).fetchone()
    if v:
        v['terminos'] = cifrado.abrir(v.pop('terminos_acordados_cifrados'), contexto).decode()
        v.pop('documento_cifrado')
        v['firmas'] = db.execute('SELECT usuario_id,hash_sha256,modo,firmado_en FROM schema_odr.firma WHERE convenio_id=%s ORDER BY firmado_en', (v['id'],)).fetchall()
    resultado['convenio'] = v
    return resultado


def guardar_convenio(db, usuario, c, partes, m, entrada, cifrado):
    exigir(m and m['estado'] in ('EN_NEGOCIACION','PENDIENTE_FORMALIZACION'), 'No se puede redactar convenio en este estado')
    anterior = db.execute('SELECT * FROM schema_odr.convenio WHERE mediacion_id=%s', (m['id'],)).fetchone()
    if anterior:
        firmado = db.execute('SELECT 1 FROM schema_odr.firma WHERE convenio_id=%s', (anterior['id'],)).fetchone()
        exigir(not anterior['formalizado_en'] and not firmado, 'Un convenio aceptado no se puede reemplazar')
    documento = generar_convenio(c['id'], partes, entrada)
    huella = sha256(documento).hexdigest()
    contexto = str(m['id'])
    db.execute('''INSERT INTO schema_odr.convenio
      (mediacion_id,tipo,puntos_pendientes,terminos_acordados_cifrados,documento_id,hash_sha256,documento_cifrado,modo_firma)
      VALUES (%s,%s,%s,%s,%s,%s,%s,'DEMOSTRACION')
      ON CONFLICT(mediacion_id) DO UPDATE SET tipo=excluded.tipo,puntos_pendientes=excluded.puntos_pendientes,
      terminos_acordados_cifrados=excluded.terminos_acordados_cifrados,documento_id=excluded.documento_id,
      hash_sha256=excluded.hash_sha256,documento_cifrado=excluded.documento_cifrado''',
      (m['id'], entrada.tipo, entrada.puntos_pendientes, cifrado.cifrar(entrada.terminos, contexto),
       uuid4(), huella, cifrado.cifrar(documento, contexto)))
    db.execute("UPDATE schema_odr.mediacion SET estado='PENDIENTE_FORMALIZACION' WHERE id=%s", (m['id'],))
    auditar(db, usuario['id'], c['id'], 'CONVENIO_REDACTADO', m['estado'], 'PENDIENTE_FORMALIZACION')
    notificar(db, c['id'], 'CONVENIO_PARA_REVISION')


def firmar(db, usuario, c, partes, m, entrada, operacion, habilitado):
    exigir(habilitado, 'La aceptación de demostración no está habilitada; falta proveedor institucional', 503)
    exigir(m, 'No existe mediación')
    v = db.execute('SELECT * FROM schema_odr.convenio WHERE mediacion_id=%s', (m['id'],)).fetchone()
    exigir(v and entrada.hash_sha256 == v['hash_sha256'], 'El documento cambió; vuelve a revisarlo')
    previa = db.execute('SELECT * FROM schema_odr.firma WHERE convenio_id=%s AND usuario_id=%s', (v['id'], usuario['id'])).fetchone()
    if previa:
        return {'firmada': True, 'formalizado': bool(v['formalizado_en'])}
    exigir(m['estado'] == 'PENDIENTE_FORMALIZACION', 'El convenio no está pendiente de aceptación')
    db.execute('''INSERT INTO schema_odr.firma(convenio_id,usuario_id,hash_sha256,modo,operacion_id)
      VALUES (%s,%s,%s,'DEMOSTRACION',%s)''', (v['id'], usuario['id'], v['hash_sha256'], operacion))
    auditar(db, usuario['id'], c['id'], 'ACEPTACION_DEMO', operacion=operacion)
    firmas = {f['usuario_id'] for f in db.execute('SELECT usuario_id FROM schema_odr.firma WHERE convenio_id=%s', (v['id'],))}
    requeridas = {p['usuario_id'] for p in partes}
    if m['mediador_id']:
        requeridas.add(m['mediador_id'])
    formalizado = None not in requeridas and requeridas.issubset(firmas)
    if formalizado:
        db.execute("UPDATE schema_odr.convenio SET formalizado_en=now(),sello_tiempo=now(),num_serie_firma='DEMO-SIN-CERTIFICADO' WHERE id=%s", (v['id'],))
        concluir(db, usuario, c, m, 'ACUERDO_TOTAL' if v['tipo'] == 'TOTAL' else 'ACUERDO_PARCIAL')
    return {'firmada': True, 'formalizado': formalizado}
