"""
Plataforma de Comercio de Energía — control de acceso al generador de
reportes energéticos (patrón Proxy). Consumido por main.py.

`ReporteProxy` implementa la misma interfaz que `GeneradorReportesReal` (que
delega en `PlataformaEnergia.generar_reporte`, el Builder de la Semana 5) y
se pone delante de él para: validar que solo el dueño pida su propio reporte
(Protection Proxy), evitar reconstruirlo si ya se generó uno reciente con el
mismo formato (Caching Proxy), y dejar registro de cada intento (Logging
Proxy) sin modificar PlataformaEnergia ni DirectorReportes.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from plataforma import PlataformaEnergia


class GeneradorReportes(ABC):
    @abstractmethod
    def generar(self, solicitante_id: str, usuario_id: str, formato: str = "resumen") -> dict:
        raise NotImplementedError


@dataclass
class GeneradorReportesReal(GeneradorReportes):
    """Envuelve a PlataformaEnergia.generar_reporte (Builder, Semana 5)."""

    plataforma: "PlataformaEnergia"
    construcciones: int = 0

    def generar(self, solicitante_id: str, usuario_id: str, formato: str = "resumen") -> dict:
        self.construcciones += 1
        return self.plataforma.generar_reporte(usuario_id, formato)


@dataclass
class ReporteProxy(GeneradorReportes):
    real: GeneradorReportes
    ttl_segundos: float = 30.0
    _cache: dict[tuple[str, str], tuple[float, dict]] = field(default_factory=dict)
    auditoria: list[dict] = field(default_factory=list)

    def generar(self, solicitante_id: str, usuario_id: str, formato: str = "resumen") -> dict:
        ahora = time.time()

        if solicitante_id != usuario_id:
            self._registrar(solicitante_id, usuario_id, formato, "denegado")
            raise PermissionError(
                f"'{solicitante_id}' no puede solicitar el reporte de '{usuario_id}'"
            )

        clave = (usuario_id, formato)
        if clave in self._cache:
            generado_en, reporte = self._cache[clave]
            if ahora - generado_en <= self.ttl_segundos:
                self._registrar(solicitante_id, usuario_id, formato, "cache")
                return reporte

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
                "timestamp": ahora_iso(),
            }
        )


def ahora_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")
