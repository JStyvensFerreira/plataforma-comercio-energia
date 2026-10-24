"""
Genera el ejecutable de Voltia con PyInstaller.

Uso (desde la raíz del repositorio):
    pip install -r plataforma-energia-app/backend/requirements.txt pyinstaller==6.11.1
    python plataforma-energia-app/ejecutable/construir.py

El resultado queda en Ejecutables/ en la raíz del repositorio. PyInstaller
solo genera binarios para el sistema operativo donde se ejecuta: corre este
script en Windows para el .exe, en Linux o macOS para sus binarios.
"""

import os
import platform
import shutil

import PyInstaller.__main__

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
RAIZ = os.path.dirname(APP)
SALIDA = os.path.join(RAIZ, "Ejecutables")
TEMP = os.path.join(AQUI, "build")

sistema = {"Windows": "windows", "Darwin": "macos"}.get(platform.system(), "linux")
nombre = f"Voltia-{sistema}"
sep = os.pathsep  # ';' en Windows, ':' en Linux/macOS

PyInstaller.__main__.run([
    os.path.join(AQUI, "lanzador.py"),
    "--onefile",
    "--name", nombre,
    "--distpath", SALIDA,
    "--workpath", TEMP,
    "--specpath", TEMP,
    "--paths", os.path.join(APP, "backend"),
    "--add-data", f"{os.path.join(APP, 'frontend')}{sep}frontend",
    # uvicorn carga estos módulos dinámicamente
    "--collect-submodules", "uvicorn",
    "--hidden-import", "main",
    "--noconfirm",
    "--clean",
])

shutil.rmtree(TEMP, ignore_errors=True)
print(f"\nEjecutable generado en: {SALIDA}")
