import sys
import unittest
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulos.identidad.credenciales import (TokenInvalido, emitir_token,
                                            hash_password, leer_token,
                                            verificar_password)


class CredencialesTest(unittest.TestCase):
    def test_hash_no_guarda_password_y_verifica(self):
        clave = "contrasena-sintetica-larga"
        guardado = hash_password(clave)
        self.assertNotEqual(guardado, clave)
        self.assertTrue(verificar_password(clave, guardado))
        self.assertFalse(verificar_password("otra-contrasena", guardado))

    def test_token_firmado_y_mfa(self):
        usuario = uuid4()
        token = emitir_token(usuario, clave="a" * 32, mfa_verificado=True)
        self.assertEqual(leer_token(token, clave="a" * 32), (usuario, True))
        with self.assertRaises(TokenInvalido):
            leer_token(token, clave="b" * 32)

    def test_no_acepta_secreto_debil(self):
        with self.assertRaises(ValueError):
            emitir_token(uuid4(), clave="corta", mfa_verificado=False)


if __name__ == "__main__":
    unittest.main()
