"""
Plataforma de Comercio de Energía
==================================
Implementa el requerimiento #16:
  - Compra/venta de excedentes energéticos entre usuarios
  - Sistema de subastas en tiempo real
  - Integración con dispositivos IoT domésticos
  - Predicción de producción y consumo

Patrón aplicado: COMPOSITE (Compuesto)
---------------------------------------
La energía de la plataforma se organiza de forma naturalmente jerárquica:
una comunidad energética (microrred) contiene edificios y casas, un edificio
contiene apartamentos, y cada hogar contiene sus dispositivos IoT (paneles
solares, baterías, medidores), que son los que realmente producen o
consumen energía.

La pregunta es la misma que la del SGA (Facultad → Programa → Curso →
Estudiante): ¿cómo calcular la producción, el consumo o el balance de una
comunidad entera sin escribir código distinto en cada nivel? Sin el patrón,
habría un método para sumar los dispositivos de un hogar, otro para sumar
los hogares de un edificio, otro para sumar los edificios de la comunidad...
y cada nivel nuevo (p. ej. "barrio") obligaría a escribir otro más.

Con COMPOSITE, todos los nodos del árbol comparten la interfaz
`NodoEnergetico`:
  - `DispositivoHoja` (Leaf): objeto individual, sin hijos; calcula su
    producción/consumo a partir de sus propias lecturas.
  - `GrupoEnergetico` (Composite): contiene hijos (`NodoEnergetico`) y
    DELEGA la operación en ellos, sumando los resultados.

El cliente llama `nodo.balance_kwh()` sin saber si `nodo` es un panel solar
o una comunidad entera: la recursión la resuelve la propia estructura.

Se implementa la variante "transparente" vista en clase: `agregar`,
`eliminar` y `obtener_hijo` están declarados en la interfaz común; una hoja
los rechaza con `TypeError`. Además se controla una de las desventajas del
patrón (riesgo de ciclos): un grupo no puede contenerse a sí mismo ni a uno
de sus ancestros.
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


# ---------------------------------------------------------------------------
# DEMO
# ---------------------------------------------------------------------------
def _imprimir(nodo: NodoEnergetico, sangria: int = 0) -> None:
    """Cliente: recorre el árbol sin distinguir hojas de grupos."""
    etiqueta = nodo.tipo if isinstance(nodo, DispositivoHoja) else nodo.nivel
    print(
        f"{'   ' * sangria}- {nodo.nombre} [{etiqueta}] "
        f"prod={nodo.produccion_kwh()} cons={nodo.consumo_kwh()} balance={nodo.balance_kwh()}"
    )
    if nodo.es_compuesto():
        for hijo in nodo.hijos:
            _imprimir(hijo, sangria + 1)


if __name__ == "__main__":
    comunidad = GrupoEnergetico("Microrred La Floresta", "comunidad")

    edificio = GrupoEnergetico("Edificio Los Pinos", "edificio")
    apto_101 = GrupoEnergetico("Apto 101 (Ana)", "hogar")
    apto_101.agregar(DispositivoHoja("panel-01", "panel_solar", [2.5, 3.0, 2.8]))
    apto_101.agregar(DispositivoHoja("bateria-01", "bateria", [1.0, -0.5]))
    apto_102 = GrupoEnergetico("Apto 102 (Luis)", "hogar")
    apto_102.agregar(DispositivoHoja("medidor-02", "medidor", [-1.2, -2.0, -1.5]))
    edificio.agregar(apto_101)
    edificio.agregar(apto_102)

    casa = GrupoEnergetico("Casa 7 (Marta)", "hogar")
    casa.agregar(DispositivoHoja("panel-07", "panel_solar", [1.5, 1.8]))

    comunidad.agregar(edificio)
    comunidad.agregar(casa)  # una casa cuelga directo de la comunidad: profundidad variable

    print("Árbol energético (el cliente usa la misma interfaz en cada nivel):\n")
    _imprimir(comunidad)
    print(f"\nBalance total de la comunidad: {comunidad.balance_kwh()} kWh")
    print(f"Promedio por dispositivo:     {comunidad.promedio_balance_por_dispositivo()} kWh")

    print("\nIntento de ciclo (agregar la comunidad dentro del edificio):")
    try:
        edificio.agregar(comunidad)
    except ValueError as e:
        print(" ", e)

    print("\nUna hoja no admite hijos:")
    try:
        apto_101.obtener_hijo(0).agregar(casa)
    except TypeError as e:
        print(" ", e)
