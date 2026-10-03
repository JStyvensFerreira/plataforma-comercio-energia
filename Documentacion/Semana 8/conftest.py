"""
Configuración de pytest para los patrones COMPOSITE y DECORATOR.

Añade esta carpeta al `sys.path` para poder importar `composite.py` y
`decorator.py` directamente.
"""

import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
if CARPETA not in sys.path:
    sys.path.insert(0, CARPETA)
