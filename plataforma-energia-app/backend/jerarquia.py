"""
Plataforma de Comercio de Energía — árbol energético de la comunidad (patrón
Composite). Consumido por plataforma.py (arbol_energetico).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable


# ---------------------------------------------------------------------------
# COMPONENT — interfaz común para hojas y grupos
# ---------------------------------------------------------------------------
class NodoEnergetico(ABC):
    """Component: cualquier nodo del árbol energético (hoja o grupo)."""

    def __init__(self, nombre: str) -> None:
        self.nombre = nombre

    # --- operaciones que se resuelven recursivamente ---
    @abstractmethod
    def produccion_kwh(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def consumo_kwh(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def cantidad_dispositivos(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict:
        raise NotImplementedError

    # --- operaciones definidas UNA sola vez para todos los niveles ---
    def balance_kwh(self) -> float:
        """Excedente (positivo) o déficit (negativo) del nodo."""
        return round(self.produccion_kwh() - self.consumo_kwh(), 2)

    def promedio_balance_por_dispositivo(self) -> float:
        """
        Balance promedio por dispositivo del nodo. Se calcula con los totales
        del subárbol (suma / cantidad), no promediando promedios de los hijos,
        así un hogar con un solo dispositivo no pesa lo mismo que un edificio
        con veinte.
        """
        cantidad = self.cantidad_dispositivos()
        if cantidad == 0:
            return 0.0
        return round(self.balance_kwh() / cantidad, 2)

    # --- gestión de hijos (variante transparente) ---
    def es_compuesto(self) -> bool:
        return False

    def agregar(self, nodo: "NodoEnergetico") -> None:
        raise TypeError(f"'{self.nombre}' es una hoja: no puede tener hijos")

    def eliminar(self, nodo: "NodoEnergetico") -> None:
        raise TypeError(f"'{self.nombre}' es una hoja: no tiene hijos que eliminar")

    def obtener_hijo(self, indice: int) -> "NodoEnergetico":
        raise TypeError(f"'{self.nombre}' es una hoja: no tiene hijos")

    def contiene(self, nodo: "NodoEnergetico") -> bool:
        """True si `nodo` es este mismo nodo o está en su subárbol."""
        return nodo is self


# ---------------------------------------------------------------------------
# LEAF — dispositivo IoT individual
# ---------------------------------------------------------------------------
class DispositivoHoja(NodoEnergetico):
    """
    Leaf: un dispositivo IoT. Las lecturas positivas son producción y las
    negativas consumo (la misma convención que usa el resto de la plataforma).
    """

    def __init__(self, nombre: str, tipo: str, lecturas: Iterable[float] = ()) -> None:
        super().__init__(nombre)
        self.tipo = tipo
        self.lecturas = list(lecturas)

    def produccion_kwh(self) -> float:
        return round(sum((l for l in self.lecturas if l > 0), 0.0), 2)

    def consumo_kwh(self) -> float:
        return round(sum((-l for l in self.lecturas if l < 0), 0.0), 2)

    def cantidad_dispositivos(self) -> int:
        return 1

    def to_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "nivel": "dispositivo",
            "tipo": self.tipo,
            "produccion_kwh": self.produccion_kwh(),
            "consumo_kwh": self.consumo_kwh(),
            "balance_kwh": self.balance_kwh(),
            "dispositivos": 1,
            "hijos": [],
        }


# ---------------------------------------------------------------------------
# COMPOSITE — grupo de nodos (hogar, edificio, comunidad...)
# ---------------------------------------------------------------------------
class GrupoEnergetico(NodoEnergetico):
    """
    Composite: contiene hijos y delega en ellos cada operación. El `nivel` es
    solo una etiqueta ("hogar", "edificio", "comunidad"...): el comportamiento
    es el mismo en todos los niveles, por eso no hace falta una clase por nivel.
    """

    def __init__(self, nombre: str, nivel: str = "grupo") -> None:
        super().__init__(nombre)
        self.nivel = nivel
        self._hijos: list[NodoEnergetico] = []

    # --- gestión de hijos ---
    def es_compuesto(self) -> bool:
        return True

    def agregar(self, nodo: NodoEnergetico) -> None:
        if nodo.contiene(self):
            raise ValueError(
                f"No se puede agregar '{nodo.nombre}' a '{self.nombre}': se formaría un ciclo"
            )
        if any(hijo is nodo for hijo in self._hijos):
            raise ValueError(f"'{nodo.nombre}' ya pertenece a '{self.nombre}'")
        self._hijos.append(nodo)

    def eliminar(self, nodo: NodoEnergetico) -> None:
        for i, hijo in enumerate(self._hijos):
            if hijo is nodo:
                del self._hijos[i]
                return
        raise ValueError(f"'{nodo.nombre}' no pertenece a '{self.nombre}'")

    def obtener_hijo(self, indice: int) -> NodoEnergetico:
        return self._hijos[indice]

    @property
    def hijos(self) -> tuple[NodoEnergetico, ...]:
        return tuple(self._hijos)

    def contiene(self, nodo: NodoEnergetico) -> bool:
        return nodo is self or any(hijo.contiene(nodo) for hijo in self._hijos)

    # --- operaciones: delegan en los hijos ---
    def produccion_kwh(self) -> float:
        return round(sum((hijo.produccion_kwh() for hijo in self._hijos), 0.0), 2)

    def consumo_kwh(self) -> float:
        return round(sum((hijo.consumo_kwh() for hijo in self._hijos), 0.0), 2)

    def cantidad_dispositivos(self) -> int:
        return sum(hijo.cantidad_dispositivos() for hijo in self._hijos)

    def to_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "nivel": self.nivel,
            "tipo": None,
            "produccion_kwh": self.produccion_kwh(),
            "consumo_kwh": self.consumo_kwh(),
            "balance_kwh": self.balance_kwh(),
            "dispositivos": self.cantidad_dispositivos(),
            "hijos": [hijo.to_dict() for hijo in self._hijos],
        }
