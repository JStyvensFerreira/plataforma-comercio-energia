"""
Plataforma de Comercio de Energía — liquidación del periodo (patrón Template
Method). Consumido por plataforma.py (liquidar_periodo).

`LiquidacionPeriodo.liquidar` fija el orden de los pasos para todos los
roles; `LiquidacionComprador` y `LiquidacionVendedor` solo completan los
pasos variables: qué transacciones son suyas, qué importe cuenta (el
comprador liquida el `total` que pagó, ya con los ajustes del Decorator; el
vendedor, el `subtotal`, que es el valor de su energía), qué cargos del
periodo aplican y si se suman o se descuentan.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

PATRON_PERIODO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


# ---------------------------------------------------------------------------
# ABSTRACT CLASS — método plantilla
# ---------------------------------------------------------------------------
class LiquidacionPeriodo(ABC):
    rol: str = ""

    def liquidar(self, transacciones: list[dict], usuario: str, periodo: str) -> dict:
        """MÉTODO PLANTILLA: mismos pasos, en el mismo orden, para cada rol."""
        self._validar_periodo(periodo)
        propias = [tx for tx in self._del_periodo(transacciones, periodo) if self._es_suya(tx, usuario)]
        bruto = self._bruto(propias)
        cargos = self._cargos(bruto)
        neto = round(bruto + self._signo_neto() * sum(c["valor"] for c in cargos), 2)
        return self._resumen(usuario, periodo, propias, bruto, cargos, neto)

    # ---- pasos comunes ----
    @staticmethod
    def _validar_periodo(periodo: str) -> None:
        if not PATRON_PERIODO.match(periodo):
            raise ValueError("El periodo debe tener el formato AAAA-MM")

    @staticmethod
    def _del_periodo(transacciones: list[dict], periodo: str) -> list[dict]:
        return [tx for tx in transacciones if tx["timestamp"].startswith(periodo)]

    def _bruto(self, propias: list[dict]) -> float:
        return round(sum(self._importe(tx) for tx in propias), 2)

    def _resumen(self, usuario, periodo, propias, bruto, cargos, neto) -> dict:
        return {
            "usuario": usuario,
            "rol": self.rol,
            "periodo": periodo,
            "concepto": self._concepto(),
            "movimientos": len(propias),
            "energia_kwh": round(sum(tx["cantidad_kwh"] for tx in propias), 6),
            "bruto": bruto,
            "cargos": cargos,
            "neto": neto,
            "detalle": [
                {
                    "contraparte": tx["vendedor"] if self.rol == "comprador" else tx["comprador"],
                    "cantidad_kwh": tx["cantidad_kwh"],
                    "importe": self._importe(tx),
                    "timestamp": tx["timestamp"],
                }
                for tx in propias
            ],
        }

    # ---- pasos abstractos ----
    @abstractmethod
    def _es_suya(self, tx: dict, usuario: str) -> bool: ...

    @abstractmethod
    def _importe(self, tx: dict) -> float: ...

    @abstractmethod
    def _concepto(self) -> str: ...

    # ---- ganchos ----
    def _cargos(self, bruto: float) -> list[dict]:
        return []

    def _signo_neto(self) -> int:
        return 1


# ---------------------------------------------------------------------------
# CONCRETE CLASSES
# ---------------------------------------------------------------------------
class LiquidacionComprador(LiquidacionPeriodo):
    rol = "comprador"
    CONTRIBUCION_SOLIDARIA = 0.02

    def _es_suya(self, tx, usuario):
        return tx["comprador"] == usuario

    def _importe(self, tx):
        return tx["total"]  # lo que pagó, con los ajustes de precio

    def _concepto(self):
        return "Total a pagar"

    def _cargos(self, bruto):
        return [{"concepto": "Contribución solidaria del periodo (2 %)", "valor": round(bruto * self.CONTRIBUCION_SOLIDARIA, 2)}]


class LiquidacionVendedor(LiquidacionPeriodo):
    rol = "vendedor"
    COMISION = 0.03
    RETENCION = 0.01

    def _es_suya(self, tx, usuario):
        return tx["vendedor"] == usuario

    def _importe(self, tx):
        return tx["subtotal"]  # valor de su energía, sin los cargos del comprador

    def _concepto(self):
        return "Total a recibir"

    def _cargos(self, bruto):
        return [
            {"concepto": "Comisión de la plataforma (3 %)", "valor": round(bruto * self.COMISION, 2)},
            {"concepto": "Retención en la fuente (1 %)", "valor": round(bruto * self.RETENCION, 2)},
        ]

    def _signo_neto(self):
        return -1


LIQUIDACIONES_DISPONIBLES: dict[str, type[LiquidacionPeriodo]] = {
    c.rol: c for c in (LiquidacionComprador, LiquidacionVendedor)
}


def crear_liquidacion(rol: str) -> LiquidacionPeriodo:
    try:
        return LIQUIDACIONES_DISPONIBLES[rol]()
    except KeyError:
        raise ValueError(
            f"Rol '{rol}' no soportado. Disponibles: {', '.join(LIQUIDACIONES_DISPONIBLES)}"
        ) from None
