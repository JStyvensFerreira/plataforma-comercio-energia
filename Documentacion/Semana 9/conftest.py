"""
Configuración de pytest para los patrones BRIDGE y FACADE (Semana 9).

Añade esta carpeta al `sys.path` para poder importar `bridge.py` y
`facade.py` directamente.
"""

import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
if CARPETA not in sys.path:
    sys.path.insert(0, CARPETA)
