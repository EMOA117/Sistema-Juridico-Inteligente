import sys
import unittest
from datetime import date
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from modulos.estado.modelo import (Conflicto, EstadoInvalido, EvidenciaConflicto,
                                  EvidenciaExpediente, Expediente, limite_contestacion,
                                  validar_conflicto, validar_expediente)
from modulos.identidad.autorizacion import AccesoDenegado, Principal, Rol, exigir_acceso


class FlujoTest(unittest.TestCase):
    def test_captura_debe_tener_partes_y_relato(self):
        with self.assertRaises(EstadoInvalido):
            validar_conflicto(Conflicto.CAPTURA, Conflicto.ORIENTADO,
                              EvidenciaConflicto(narrativa_inicial=True, orientacion_confirmada=True))
        validar_conflicto(Conflicto.CAPTURA, Conflicto.ORIENTADO,
                          EvidenciaConflicto(partes_completas=True, narrativa_inicial=True, orientacion_confirmada=True))

    def test_acuerdo_parcial_nunca_concluye_conflicto(self):
        e = EvidenciaConflicto(resultado_mediacion="ACUERDO_PARCIAL", convenio_formalizado=True)
        with self.assertRaises(EstadoInvalido):
            validar_conflicto(Conflicto.EN_MEDIACION, Conflicto.CONCLUIDO, e)
        validar_conflicto(Conflicto.EN_MEDIACION, Conflicto.EN_ESPERA_DECISION, e)

    def test_cierre_judicial_exige_solucion_y_firmeza(self):
        incompleta = EvidenciaExpediente(resolucion_firmada=True, resultado_explicito=True, sello_tiempo=True)
        with self.assertRaises(EstadoInvalido):
            validar_expediente(Expediente.RESUELTO, Expediente.CERRADO, incompleta)
        validar_expediente(Expediente.RESUELTO, Expediente.CERRADO,
                           EvidenciaExpediente(**{**incompleta.__dict__, "firmeza": True}))

    def test_15_dias_naturales(self):
        self.assertEqual(limite_contestacion(date(2026, 10, 28)), date(2026, 11, 12))


class AutorizacionTest(unittest.TestCase):
    def test_juez_solo_ve_su_expediente_y_requiere_mfa(self):
        juez, otro = uuid4(), uuid4()
        with self.assertRaises(AccesoDenegado):
            exigir_acceso(Principal(juez, Rol.JUEZ), "ver_expediente", juez_id=juez)
        exigir_acceso(Principal(juez, Rol.JUEZ, mfa_verificado=True), "ver_expediente", juez_id=juez)
        with self.assertRaises(AccesoDenegado):
            exigir_acceso(Principal(juez, Rol.JUEZ, mfa_verificado=True), "ver_expediente", juez_id=otro)

    def test_rol_secretario_no_existe(self):
        self.assertNotIn("SECRETARIO", [rol.value for rol in Rol])


if __name__ == "__main__":
    unittest.main()
