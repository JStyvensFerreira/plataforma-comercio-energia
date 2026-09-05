#!/usr/bin/env python3
"""
Validador de las pruebas de los patrones SINGLETON y FACTORY METHOD.

Ejecuta la batería de pruebas de:
    - src/singleton/test_singleton.py             (patrón Singleton)
    - src/factory_method/test_factory_method.py   (patrón Factory Method)

y muestra un resumen claro con el resultado de cada patrón.

Uso:
    python validar_pruebas.py            # ejecuta ambos patrones
    python validar_pruebas.py singleton  # solo Singleton
    python validar_pruebas.py factory    # solo Factory Method
    python validar_pruebas.py -v         # salida detallada de pytest
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

SUITES = {
    "singleton": {
        "titulo": "Patron SINGLETON",
        "archivo": RAIZ / "src" / "singleton" / "test_singleton.py",
    },
    "factory": {
        "titulo": "Patron FACTORY METHOD",
        "archivo": RAIZ / "src" / "factory_method" / "test_factory_method.py",
    },
}


def _asegurar_pytest() -> None:
    try:
        import pytest  # noqa: F401
    except ImportError:
        print("pytest no esta instalado. Instalando desde requirements-dev.txt ...\n")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(RAIZ / "requirements-dev.txt")],
            check=True,
        )


def _correr_suite(clave: str, detallado: bool) -> bool:
    suite = SUITES[clave]
    archivo = suite["archivo"]

    print("=" * 70, flush=True)
    print(f"  {suite['titulo']}", flush=True)
    print(f"  {archivo.relative_to(RAIZ)}", flush=True)
    print("=" * 70, flush=True)

    if not archivo.exists():
        print(f"  ERROR: no se encontro {archivo}\n")
        return False

    args = [sys.executable, "-m", "pytest", str(archivo)]
    args.append("-v" if detallado else "-q")

    resultado = subprocess.run(args, cwd=RAIZ)
    ok = resultado.returncode == 0
    print(f"\n  Resultado: {'OK - todas las pruebas pasaron' if ok else 'FALLO'}\n", flush=True)
    return ok


def main(argv: list[str]) -> int:
    detallado = "-v" in argv or "--verbose" in argv
    seleccion = [a for a in argv if not a.startswith("-")]

    if not seleccion:
        claves = list(SUITES)
    else:
        claves = []
        for arg in seleccion:
            arg = arg.lower()
            if arg.startswith("singleton"):
                claves.append("singleton")
            elif arg.startswith("factory") or arg.startswith("fabrica"):
                claves.append("factory")
            else:
                print(f"Argumento no reconocido: {arg}")
                print(__doc__)
                return 2

    _asegurar_pytest()

    resultados = {clave: _correr_suite(clave, detallado) for clave in claves}

    print("#" * 70)
    print("  RESUMEN FINAL")
    print("#" * 70)
    for clave, ok in resultados.items():
        estado = "PASO " if ok else "FALLO"
        print(f"  [{estado}] {SUITES[clave]['titulo']}")
    print("#" * 70)

    return 0 if all(resultados.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
