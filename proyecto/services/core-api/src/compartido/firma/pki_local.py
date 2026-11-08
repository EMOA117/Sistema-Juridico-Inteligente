"""PKI local de demostración: CA raíz + TSA propias, certificado X.509 por firmante y firma PAdES con sello de tiempo.

NO es una firma con validez legal. Las llaves de la CA y la TSA viven en infrastructure/local/pki (ignorado por git);
la llave privada de cada firmante se guarda cifrada con AES-256-GCM en la BD, como lo haría un HSM.
"""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from uuid import UUID

from asn1crypto import keys as asn1_keys, x509 as asn1_x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from psycopg import Connection
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import fields, signers
from pyhanko.sign.timestamps.dummy_client import DummyTimeStamper
from pyhanko_certvalidator.registry import SimpleCertificateStore

from compartido.cifrado import cifrar, descifrar
from compartido.config import config
from compartido.firma import ResultadoFirma

VIGENCIA = timedelta(days=365)


def _dir() -> Path:
    return Path(config().pki_dir)


def _nombre(cn: str, ou: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COUNTRY_NAME, "MX"),
                      x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Sistema Jurídico Inteligente · DEMOSTRACIÓN ESCOM"),
                      x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, ou),
                      x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def inicializar(forzar: bool = False) -> Path:
    """Crea la CA raíz y el certificado de la TSA locales (herramientas/pki_init)."""
    d = _dir()
    d.mkdir(parents=True, exist_ok=True)
    if (d / "ca.crt").exists() and not forzar:
        return d
    ahora = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    ca_nombre = _nombre("AC Raíz de Demostración (sin validez legal)", "Autoridad certificadora de prueba")
    ca = (x509.CertificateBuilder().subject_name(ca_nombre).issuer_name(ca_nombre).public_key(ca_key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(ahora).not_valid_after(ahora + timedelta(days=3650))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
          .sign(ca_key, hashes.SHA256()))
    tsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    tsa = (x509.CertificateBuilder().subject_name(_nombre("TSA de Demostración", "Sellado de tiempo de prueba"))
           .issuer_name(ca_nombre).public_key(tsa_key.public_key()).serial_number(x509.random_serial_number())
           .not_valid_before(ahora).not_valid_after(ahora + timedelta(days=3650))
           .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.TIME_STAMPING]), critical=True)
           .sign(ca_key, hashes.SHA256()))
    pem = serialization.Encoding.PEM
    sin_cifrar = serialization.NoEncryption()
    for nombre, obj in (("ca.crt", ca), ("tsa.crt", tsa)):
        (d / nombre).write_bytes(obj.public_bytes(pem))
    for nombre, llave in (("ca.key", ca_key), ("tsa.key", tsa_key)):
        datos = llave.private_bytes(pem, serialization.PrivateFormat.PKCS8, sin_cifrar)
        (d / nombre).write_bytes(cifrar(datos.decode(), f"pki:{nombre}"))
        (d / nombre).chmod(0o600)
    _materiales.cache_clear()
    return d


@lru_cache
def _materiales():
    d = _dir()
    if not (d / "ca.crt").exists():
        inicializar()
    leer_llave = lambda n: serialization.load_pem_private_key(descifrar((d / n).read_bytes(), f"pki:{n}").encode(), None)
    return (x509.load_pem_x509_certificate((d / "ca.crt").read_bytes()), leer_llave("ca.key"),
            x509.load_pem_x509_certificate((d / "tsa.crt").read_bytes()), leer_llave("tsa.key"))


def certificado_ca_asn1() -> asn1_x509.Certificate:
    return asn1_x509.Certificate.load(_materiales()[0].public_bytes(serialization.Encoding.DER))


def _a_asn1(cert: x509.Certificate, llave) -> tuple[asn1_x509.Certificate, asn1_keys.PrivateKeyInfo]:
    der = llave.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    return asn1_x509.Certificate.load(cert.public_bytes(serialization.Encoding.DER)), asn1_keys.PrivateKeyInfo.load(der)


class PkiLocal:
    def _certificado(self, c: Connection, usuario_id: UUID, nombre: str):
        fila = c.execute("SELECT num_serie, cert_pem, llave_cifrada FROM nucleo_comun.certificado"
                         " WHERE usuario_id=%s AND NOT revocado AND vence_en > now()", (usuario_id,)).fetchone()
        if fila:
            cert = x509.load_pem_x509_certificate(fila["cert_pem"].encode())
            llave = serialization.load_pem_private_key(descifrar(fila["llave_cifrada"], f"llave:{usuario_id}").encode(), None)
            return cert, llave
        ca, ca_key, _, _ = _materiales()
        ahora = datetime.now(timezone.utc)
        llave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cert = (x509.CertificateBuilder().subject_name(_nombre(nombre, "Firmante")).issuer_name(ca.subject)
                .public_key(llave.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(ahora - timedelta(minutes=1)).not_valid_after(ahora + VIGENCIA)
                .add_extension(x509.KeyUsage(True, True, False, False, False, False, False, False, False), critical=True)
                .add_extension(x509.SubjectAlternativeName([x509.UniformResourceIdentifier(f"urn:uuid:{usuario_id}")]), critical=False)
                .sign(ca_key, hashes.SHA256()))
        pem_llave = llave.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                        serialization.NoEncryption()).decode()
        c.execute("INSERT INTO nucleo_comun.certificado (usuario_id, num_serie, cert_pem, llave_cifrada, vence_en)"
                  " VALUES (%s,%s,%s,%s,%s)",
                  (usuario_id, format(cert.serial_number, "X"), cert.public_bytes(serialization.Encoding.PEM).decode(),
                   cifrar(pem_llave, f"llave:{usuario_id}"), ahora + VIGENCIA))
        return cert, llave

    def firmar_pdf(self, c: Connection, usuario_id: UUID, nombre: str, pdf: bytes, campo: str) -> ResultadoFirma:
        cert, llave = self._certificado(c, usuario_id, nombre)
        ca, _, tsa, tsa_key = _materiales()
        cert_asn1, llave_asn1 = _a_asn1(cert, llave)
        ca_asn1 = certificado_ca_asn1()
        tsa_asn1, tsa_llave_asn1 = _a_asn1(tsa, tsa_key)
        firmante = signers.SimpleSigner(signing_cert=cert_asn1, signing_key=llave_asn1,
                                        cert_registry=SimpleCertificateStore.from_certs([ca_asn1]))
        sellador = DummyTimeStamper(tsa_cert=tsa_asn1, tsa_key=tsa_llave_asn1, certs_to_embed=SimpleCertificateStore.from_certs([ca_asn1]))
        escritor = IncrementalPdfFileWriter(BytesIO(pdf))
        meta = signers.PdfSignatureMetadata(field_name=campo, md_algorithm="sha256",
                                            subfilter=fields.SigSeedSubFilter.PADES, reason="Firma electrónica (demostración)",
                                            location="Ciudad de México")
        salida = signers.PdfSigner(meta, signer=firmante, timestamper=sellador).sign_pdf(escritor)
        return ResultadoFirma(pdf=salida.getvalue(), num_serie=format(cert.serial_number, "X"),
                              sello_tiempo=datetime.now(timezone.utc))
