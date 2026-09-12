"""
Configuración de pytest para el patrón FACTORY METHOD.

Añade esta carpeta al `sys.path` para poder importar `factory_method.py`
directamente.
"""

import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
if CARPETA not in sys.path:
    sys.path.insert(0, CARPETA)
