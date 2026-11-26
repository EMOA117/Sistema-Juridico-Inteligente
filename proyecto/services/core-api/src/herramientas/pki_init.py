"""Crea la CA raíz y la TSA de demostración: uv run python -m herramientas.pki_init [--forzar]"""
import sys

from compartido.firma.pki_local import inicializar

if __name__ == "__main__":
    print("PKI de demostración en", inicializar(forzar="--forzar" in sys.argv))
