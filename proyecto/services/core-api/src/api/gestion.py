"""Herramientas locales: aprovisionar base aislada, aplicar migraciones y cuentas demo."""
import argparse
import base64
from getpass import getpass
import os
from pathlib import Path
import re
import secrets
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import pyotp

from compartido.seguridad.configuracion import Configuracion, Cifrado, ROLES, transaccion
from modulos.identidad.credenciales import hash_password

MIGRACIONES = Path(__file__).resolve().parents[4] / 'persistence/postgres'


def preparar(admin_url, nombre, salida):
    if not re.fullmatch(r'odr_[a-z0-9_]{1,30}', nombre):
        raise ValueError('El nombre debe empezar por odr_ y usar minúsculas, números o guion bajo')
    ruta = Path(salida)
    if ruta.exists():
        raise ValueError('El archivo de configuración ya existe; no se sobrescribe')
    login = nombre + '_api'
    password = secrets.token_urlsafe(32)
    with psycopg.connect(admin_url, autocommit=True) as db:
        if db.execute('SELECT 1 FROM pg_database WHERE datname=%s',(nombre,)).fetchone():
            raise ValueError('La base ya existe; usa una base nueva para esta demostración')
        if db.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(login,)).fetchone():
            raise ValueError('El login ya existe; elige otro nombre de base')
        db.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(nombre)))
    dsn = make_conninfo(admin_url, dbname=nombre)
    with psycopg.connect(dsn, autocommit=True) as db:
        for archivo in sorted(MIGRACIONES.glob('[0-9]*.sql')):
            db.execute(archivo.read_text(encoding='utf-8'))
        db.execute(sql.SQL('CREATE ROLE {} LOGIN NOINHERIT PASSWORD {}').format(sql.Identifier(login),sql.Literal(password)))
        for rol in sorted(ROLES):
            db.execute(sql.SQL('GRANT {} TO {}').format(sql.Identifier(rol),sql.Identifier(login)))
    config = Configuracion(make_conninfo(admin_url,dbname=nombre,user=login,password=password),
                           secrets.token_urlsafe(48),base64.urlsafe_b64encode(os.urandom(32)).decode(),True)
    # Archivo local ignorado por Git; nunca contiene credenciales de una cuenta real.
    ruta.write_text('\n'.join([
        "DATABASE_URL='"+config.database_url+"'",
        'JWT_SECRET='+config.jwt_secret,
        'ODR_ENCRYPTION_KEY='+config.encryption_key,
        'ODR_FIRMA_DEMO=true',
    ])+'\n',encoding='utf-8')
    print(f'Base {nombre} preparada. Configuración local en {ruta}. No compartas ese archivo.')
    return dsn, config


def crear_operador(dsn, config, correo, nombre, rol, password):
    uid = uuid4()
    secreto = pyotp.random_base32()
    cifrado = base64.b64encode(Cifrado(config.encryption_key).cifrar(secreto,str(uid))).decode()
    with psycopg.connect(dsn) as db:
        db.execute('''INSERT INTO nucleo_comun.usuario(id,correo,nombre,password_hash,mfa_habilitado,mfa_secreto)
          VALUES (%s,%s,%s,%s,true,%s)''',(uid,correo.lower(),nombre,hash_password(password),cifrado))
        db.execute('INSERT INTO nucleo_comun.usuario_rol VALUES (%s,%s)',(uid,rol))
    # Se muestra solo durante el aprovisionamiento autorizado del operador.
    print('Configura tu autenticador TOTP con esta URI (no la compartas):')
    print(pyotp.TOTP(secreto).provisioning_uri(correo,issuer_name='Concordia local'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='comando',required=True)
    p = sub.add_parser('preparar')
    p.add_argument('--admin-url',required=True,help='Conexión local con permiso CREATE DATABASE/ROLE')
    p.add_argument('--nombre',default='odr_demo')
    p.add_argument('--env-file',default='.env')
    p.add_argument('--mediador-demo',action='store_true')
    p = sub.add_parser('operador')
    p.add_argument('--admin-url',required=True)
    p.add_argument('--correo',required=True)
    p.add_argument('--nombre',required=True)
    p.add_argument('--rol',choices=['MEDIADOR','JUEZ','ADMINISTRADOR'],default='MEDIADOR')
    sub.add_parser('vencer-invitaciones')
    args=parser.parse_args()
    if args.comando=='preparar':
        dsn,config=preparar(args.admin_url,args.nombre,args.env_file)
        if args.mediador_demo:
            crear_operador(dsn,config,'mediador@example.test','Mediador sintético','MEDIADOR',getpass('Contraseña para el mediador sintético (12+ caracteres): '))
    elif args.comando=='operador':
        crear_operador(args.admin_url,Configuracion.entorno(),args.correo,args.nombre,args.rol,getpass('Contraseña (12+ caracteres): '))
    else:
        with transaccion(Configuracion.entorno(),'rol_tarea_odr') as db:
            cantidad=db.execute('SELECT schema_odr.vencer_invitaciones() AS cantidad').fetchone()['cantidad']
        print(f'Invitaciones vencidas: {cantidad}')


if __name__=='__main__':
    main()
