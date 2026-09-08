"""
Configuración de pytest para el patrón SINGLETON.

Añade esta carpeta al `sys.path` para poder importar `plataforma_energia.py`
directamente y expone un fixture que reinicia el estado del Singleton entre
pruebas.
"""

import os
import sys

import pytest

CARPETA = os.path.dirname(os.path.abspath(__file__))
if CARPETA not in sys.path:
    sys.path.insert(0, CARPETA)


@pytest.fixture(autouse=True)
def _reiniciar_singleton():
    """
    El Singleton guarda su instancia en `SingletonMeta._instances`.
    Cada prueba debe empezar desde cero, así que limpiamos ese registro
    antes y después de ejecutarla.
    """
    from plataforma_energia import SingletonMeta

    SingletonMeta._instances.clear()
    yield
    SingletonMeta._instances.clear()
