"""
Patrón Proxy — control de acceso al generador de reportes energéticos.

Problema: generar el reporte energético de un usuario (patrón Builder,
Semana 5) implica recolectar lecturas, calcular balances y armar varias
secciones; no es gratis repetirlo en cada clic. Además, cualquier cliente de
la API podría pedir el reporte de OTRO usuario si nada lo evita, y nadie
queda registrado pidiendo reportes ajenos.

Solución (Proxy): `ReporteProxy` implementa la misma interfaz que el
generador real (`GeneradorReportes`) y se pone delante de él para resolver,
sin tocar la lógica de construcción del reporte:

    - Protection Proxy: solo el propio usuario puede pedir su reporte; si
      alguien más lo intenta, se rechaza con PermissionError antes de tocar
      el generador real.
    - Caching Proxy: si ya se generó un reporte reciente con el mismo
      formato, se devuelve esa copia en vez de reconstruirlo.
    - Logging Proxy: cada intento (permitido, denegado o servido desde
      caché) queda registrado para auditoría.

El cliente programa contra `GeneradorReportes` y no necesita saber si está
hablando con el objeto real o con el proxy.

Ejecutar este archivo directamente corre una demo por consola:
    python "Documentacion/Semana 10/proxy.py"
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ===========================================================================
# SUBJECT — interfaz común para el objeto real y el proxy
# ===========================================================================
class GeneradorReportes(ABC):
    @abstractmethod
    def generar(self, solicitante_id: str, usuario_id: str, formato: str = "resumen") -> dict:
        raise NotImplementedError


# ===========================================================================
# REAL SUBJECT — construcción "costosa" del reporte
# ===========================================================================
@dataclass
class GeneradorReportesReal(GeneradorReportes):
    """
    Simula la construcción real del reporte (en la app, esto es el
    DirectorReportes del patrón Builder armando el reporte paso a paso).
    Cuenta cuántas veces se construyó de verdad, para que la demo pueda
    mostrar cuántas construcciones evitó el proxy.
    """

    construcciones: int = 0

    def generar(self, solicitante_id: str, usuario_id: str, formato: str = "resumen") -> dict:
        self.construcciones += 1
        return {
            "usuario": usuario_id,
            "formato": formato,
            "generado_en": time.time(),
            "balance_kwh": 12.5,
        }


# ===========================================================================
# PROXY — protección + caché + auditoría
# ===========================================================================
@dataclass
class ReporteProxy(GeneradorReportes):
    real: GeneradorReportes
    ttl_segundos: float = 60.0
    _cache: dict[tuple[str, str], tuple[float, dict]] = field(default_factory=dict)
    auditoria: list[dict] = field(default_factory=list)

    def generar(self, solicitante_id: str, usuario_id: str, formato: str = "resumen") -> dict:
        ahora = time.time()

        # --- Protection Proxy: solo el dueño del reporte puede pedirlo. ---
        if solicitante_id != usuario_id:
            self._registrar(solicitante_id, usuario_id, formato, "denegado")
            raise PermissionError(
                f"'{solicitante_id}' no puede solicitar el reporte de '{usuario_id}'"
            )

        # --- Caching Proxy: reutiliza un reporte reciente del mismo formato. ---
        clave = (usuario_id, formato)
        if clave in self._cache:
            generado_en, reporte = self._cache[clave]
            if ahora - generado_en <= self.ttl_segundos:
                self._registrar(solicitante_id, usuario_id, formato, "cache")
                return reporte

        # --- Delegar al objeto real y cachear el resultado. ---
        reporte = self.real.generar(solicitante_id, usuario_id, formato)
        self._cache[clave] = (ahora, reporte)
        self._registrar(solicitante_id, usuario_id, formato, "generado")
        return reporte

    def _registrar(self, solicitante_id: str, usuario_id: str, formato: str, resultado: str) -> None:
        self.auditoria.append(
            {
                "solicitante": solicitante_id,
                "usuario": usuario_id,
                "formato": formato,
                "resultado": resultado,
                "timestamp": time.time(),
            }
        )


if __name__ == "__main__":
    real = GeneradorReportesReal()
    proxy = ReporteProxy(real=real)

    print("1) Ana pide su propio reporte (primera vez: se construye de verdad).")
    proxy.generar("ana", "ana", "resumen")
    print(f"   Construcciones reales hasta ahora: {real.construcciones}")

    print("2) Ana vuelve a pedir el mismo reporte (debería venir de caché).")
    proxy.generar("ana", "ana", "resumen")
    print(f"   Construcciones reales hasta ahora: {real.construcciones} (no debió subir)")

    print("3) Luis intenta pedir el reporte de Ana (debe ser rechazado).")
    try:
        proxy.generar("luis", "ana", "resumen")
    except PermissionError as exc:
        print(f"   Rechazado correctamente: {exc}")

    print("\nAuditoría completa:")
    for entrada in proxy.auditoria:
        print(" -", entrada)
