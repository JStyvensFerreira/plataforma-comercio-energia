"""
Configuración de pytest para los patrones FLYWEIGHT y PROXY (Semana 10).

Añade esta carpeta al `sys.path` para poder importar `flyweight.py` y
`proxy.py` directamente.
"""

import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
if CARPETA not in sys.path:
    sys.path.insert(0, CARPETA)
