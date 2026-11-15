"""
Configuración de pytest para los patrones COMMAND, STRATEGY y TEMPLATE METHOD (Semana 15).

Añade esta carpeta al `sys.path` para poder importar `command.py`,
`strategy.py` y `template_method.py` directamente.
"""

import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
if CARPETA not in sys.path:
    sys.path.insert(0, CARPETA)
