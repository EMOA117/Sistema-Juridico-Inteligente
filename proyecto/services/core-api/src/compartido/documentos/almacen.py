"""Repositorio de objetos (S3). Los documentos oficiales firmados se guardan con retención COMPLIANCE (WORM)."""
import hashlib
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

from compartido.config import config


@lru_cache
def _s3():
    c = config()
    cliente = boto3.client("s3", endpoint_url=c.s3_url, aws_access_key_id=c.s3_access_key,
                           aws_secret_access_key=c.s3_secret_key, region_name="us-east-1")
    for bucket, bloqueo in ((c.bucket_documentos, True), (c.bucket_trabajo, False)):
        try:
            cliente.head_bucket(Bucket=bucket)
        except ClientError:
            cliente.create_bucket(Bucket=bucket, ObjectLockEnabledForBucket=bloqueo)
    return cliente


def sha256(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def guardar_inmutable(clave: str, datos: bytes, tipo: str = "application/pdf") -> str:
    """Escribe una sola vez; nadie puede sobrescribir ni borrar la versión antes de que venza la retención."""
    c = config()
    r = _s3().put_object(Bucket=c.bucket_documentos, Key=clave, Body=datos, ContentType=tipo,
                         ObjectLockMode="COMPLIANCE",
                         ObjectLockRetainUntilDate=datetime.now(timezone.utc) + timedelta(days=c.retencion_dias))
    return r.get("VersionId", "")


def guardar_trabajo(clave: str, datos: bytes) -> None:
    _s3().put_object(Bucket=config().bucket_trabajo, Key=clave, Body=datos, ContentType="application/pdf")


def leer(clave: str, *, trabajo: bool = False, version: str | None = None) -> bytes:
    c = config()
    extra = {"VersionId": version} if version else {}
    return _s3().get_object(Bucket=c.bucket_trabajo if trabajo else c.bucket_documentos, Key=clave, **extra)["Body"].read()


def borrar_inmutable(clave: str, version: str) -> None:
    """Solo para comprobar en pruebas que la retención lo impide."""
    _s3().delete_object(Bucket=config().bucket_documentos, Key=clave, VersionId=version)
