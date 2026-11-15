"""
Patrón Template Method — liquidación del periodo de un usuario.

Problema: al cerrar cada mes la plataforma liquida a cada usuario: cuánta
energía compró o vendió, cuánto vale, qué cargos o retenciones aplican y
cuál es el neto a pagar o a recibir. Comprador y vendedor siguen
EXACTAMENTE los mismos pasos (filtrar sus movimientos del periodo, sumar,
aplicar cargos, calcular el neto, armar el resumen) y solo cambian algunos
detalles: qué movimientos le corresponden, qué cargos se le aplican y si
el neto es un pago o un ingreso. Si cada liquidación repitiera el
algoritmo completo, una corrección en un paso común (por ejemplo, cómo se
redondea o cómo se filtra el periodo) habría que hacerla en cada copia.

Solución (Template Method):

    - Abstract Class `LiquidacionPeriodo`: define el método plantilla
      `liquidar(transacciones, usuario, periodo)` con el orden fijo de los
      pasos. Implementa los pasos comunes (`_del_periodo`, `_bruto`,
      `_resumen`) y declara los pasos variables:
        * abstractos (obligatorios): `_es_suyo`, `_concepto`.
        * ganchos (hooks, opcionales con comportamiento por defecto):
          `_cargos` (por defecto ninguno) y `_signo_neto` (por defecto +1).
    - Concrete Classes `LiquidacionComprador` y `LiquidacionVendedor`:
      solo completan los pasos variables; nunca cambian el orden.

Ejecutar este archivo directamente corre una demo por consola:
    python "Documentacion/Semana 15/template_method.py"
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

PATRON_PERIODO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


@dataclass(frozen=True)
class Movimiento:
    comprador: str
    vendedor: str
    cantidad_kwh: float
    total: float
    fecha: str  # ISO "AAAA-MM-DD..."


# ===========================================================================
# ABSTRACT CLASS — el método plantilla fija el algoritmo
# ===========================================================================
class LiquidacionPeriodo(ABC):
    rol: str = ""

    def liquidar(self, movimientos: list[Movimiento], usuario: str, periodo: str) -> dict:
        """MÉTODO PLANTILLA: el orden de los pasos es el mismo para todos los roles."""
        self._validar_periodo(periodo)                               # 1. común
        propios = [m for m in self._del_periodo(movimientos, periodo)  # 2. común
                   if self._es_suyo(m, usuario)]                     # 3. abstracto
        bruto = self._bruto(propios)                                 # 4. común
        cargos = self._cargos(bruto)                                 # 5. gancho
        neto = round(bruto + self._signo_neto() * sum(c["valor"] for c in cargos), 2)  # 6. gancho
        return self._resumen(usuario, periodo, propios, bruto, cargos, neto)  # 7. común

    # ---- pasos comunes (no se redefinen) -----------------------------------
    @staticmethod
    def _validar_periodo(periodo: str) -> None:
        if not PATRON_PERIODO.match(periodo):
            raise ValueError("El periodo debe tener el formato AAAA-MM")

    @staticmethod
    def _del_periodo(movimientos: list[Movimiento], periodo: str) -> list[Movimiento]:
        return [m for m in movimientos if m.fecha.startswith(periodo)]

    @staticmethod
    def _bruto(propios: list[Movimiento]) -> float:
        return round(sum(m.total for m in propios), 2)

    def _resumen(self, usuario, periodo, propios, bruto, cargos, neto) -> dict:
        return {
            "usuario": usuario,
            "rol": self.rol,
            "periodo": periodo,
            "concepto": self._concepto(),
            "movimientos": len(propios),
            "energia_kwh": round(sum(m.cantidad_kwh for m in propios), 6),
            "bruto": bruto,
            "cargos": cargos,
            "neto": neto,
        }

    # ---- pasos abstractos (cada subclase DEBE darlos) ----------------------
    @abstractmethod
    def _es_suyo(self, movimiento: Movimiento, usuario: str) -> bool: ...

    @abstractmethod
    def _concepto(self) -> str: ...

    # ---- ganchos (hooks): comportamiento por defecto, redefinibles ---------
    def _cargos(self, bruto: float) -> list[dict]:
        return []

    def _signo_neto(self) -> int:
        """+1: los cargos se suman al neto (pago); -1: se restan (ingreso)."""
        return 1


# ===========================================================================
# CONCRETE CLASSES — solo completan los pasos variables
# ===========================================================================
class LiquidacionComprador(LiquidacionPeriodo):
    rol = "comprador"
    CONTRIBUCION_RED = 0.02  # 2 % por uso de la red de distribución

    def _es_suyo(self, movimiento, usuario):
        return movimiento.comprador == usuario

    def _concepto(self):
        return "Total a pagar"

    def _cargos(self, bruto):
        return [{"concepto": "Contribución por uso de red (2 %)", "valor": round(bruto * self.CONTRIBUCION_RED, 2)}]


class LiquidacionVendedor(LiquidacionPeriodo):
    rol = "vendedor"
    COMISION = 0.03  # 3 % de comisión de la plataforma
    RETENCION = 0.01  # 1 % de retención en la fuente

    def _es_suyo(self, movimiento, usuario):
        return movimiento.vendedor == usuario

    def _concepto(self):
        return "Total a recibir"

    def _cargos(self, bruto):
        return [
            {"concepto": "Comisión de la plataforma (3 %)", "valor": round(bruto * self.COMISION, 2)},
            {"concepto": "Retención en la fuente (1 %)", "valor": round(bruto * self.RETENCION, 2)},
        ]

    def _signo_neto(self):
        return -1  # al vendedor los cargos se le DESCUENTAN


LIQUIDACIONES: dict[str, type[LiquidacionPeriodo]] = {
    c.rol: c for c in (LiquidacionComprador, LiquidacionVendedor)
}


def crear_liquidacion(rol: str) -> LiquidacionPeriodo:
    try:
        return LIQUIDACIONES[rol]()
    except KeyError:
        raise ValueError(f"Rol '{rol}' no soportado. Disponibles: {', '.join(LIQUIDACIONES)}") from None


if __name__ == "__main__":
    movimientos = [
        Movimiento("marta", "ana", 5, 2200, "2026-11-03T10:00"),
        Movimiento("marta", "luis", 1, 470, "2026-11-12T19:30"),
        Movimiento("ana", "luis", 2, 900, "2026-11-20T08:15"),
        Movimiento("marta", "ana", 4, 1800, "2026-10-28T12:00"),  # otro periodo
    ]
    for rol, usuario in (("comprador", "marta"), ("vendedor", "ana")):
        liquidacion = crear_liquidacion(rol).liquidar(movimientos, usuario, "2026-11")
        print(f"\nLiquidación {rol} de {usuario} (2026-11): {liquidacion['movimientos']} movimientos, "
              f"{liquidacion['energia_kwh']} kWh")
        print(f"  Bruto: {liquidacion['bruto']}")
        for cargo in liquidacion["cargos"]:
            print(f"  {cargo['concepto']}: {cargo['valor']}")
        print(f"  {liquidacion['concepto']}: {liquidacion['neto']}")
