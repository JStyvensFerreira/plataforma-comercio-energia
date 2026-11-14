"""
Configuración de pytest para los patrones ITERATOR, MEDIATOR y MEMENTO (Semana 13).

Añade esta carpeta al `sys.path` para poder importar `iterator.py`,
`mediator.py` y `memento.py` directamente.
"""

import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
if CARPETA not in sys.path:
    sys.path.insert(0, CARPETA)
