"""
Lanzador de escritorio de Voltia.

Levanta la API FastAPI (backend/main.py) y sirve el frontend Vue desde el
mismo servidor en /app, luego abre el navegador. Es el punto de entrada que
PyInstaller empaqueta en un solo ejecutable (ver construir.py).
"""

import os
import socket
import sys
import threading
import time
import webbrowser

# Dentro del ejecutable los archivos se extraen en sys._MEIPASS;
# en desarrollo se usan las carpetas del repositorio.
BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(BASE, "backend")  # solo se usa en desarrollo; en el .exe los módulos ya vienen compilados
FRONTEND = os.path.join(BASE, "frontend")
sys.path.insert(0, BACKEND)

import uvicorn  # noqa: E402
from fastapi.responses import RedirectResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from main import app  # noqa: E402

app.mount("/app", StaticFiles(directory=FRONTEND, html=True), name="frontend")


@app.get("/inicio", include_in_schema=False)
def inicio():
    return RedirectResponse("/app/")


def puerto_libre(preferido=8000):
    """Usa el 8000 si está libre; si no, cualquiera que asigne el sistema."""
    for puerto in (preferido, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", puerto))
                return s.getsockname()[1]
            except OSError:
                continue


def abrir_navegador(url):
    time.sleep(1.5)
    webbrowser.open(url)


if __name__ == "__main__":
    puerto = puerto_libre()
    url = f"http://127.0.0.1:{puerto}/app/"
    print("=" * 60)
    print(" Voltia - Plataforma de Comercio de Energía")
    print(f" App:     {url}")
    print(f" API:     http://127.0.0.1:{puerto}/docs")
    print(" Cierra esta ventana para detener la aplicación.")
    print("=" * 60)
    threading.Thread(target=abrir_navegador, args=(url,), daemon=True).start()
    # log_config=None: sin logs de cada petición, la consola solo muestra el encabezado
    uvicorn.run(app, host="127.0.0.1", port=puerto, log_config=None)
