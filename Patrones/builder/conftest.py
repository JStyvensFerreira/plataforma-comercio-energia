"""
Configuración de pytest para el patrón BUILDER.

Añade esta carpeta al `sys.path` para poder importar `builder.py` directamente.
"""

import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
if CARPETA not in sys.path:
    sys.path.insert(0, CARPETA)
