"""
Configuración de pytest para los patrones OBSERVER, STATE y VISITOR (Semana 14).

Añade esta carpeta al `sys.path` para poder importar `observer.py`,
`state.py` y `visitor.py` directamente.
"""

import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
if CARPETA not in sys.path:
    sys.path.insert(0, CARPETA)
