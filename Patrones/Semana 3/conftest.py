"""
Configuración de pytest para la Semana 3 (patrones FACTORY METHOD y ABSTRACT
FACTORY).

Añade esta carpeta al `sys.path` para poder importar `factory_method.py` y
`abstract_factory.py` directamente.
"""

import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
if CARPETA not in sys.path:
    sys.path.insert(0, CARPETA)
