"""
Patrón Visitor — análisis sobre el árbol energético de la comunidad.

Problema: el árbol Comunidad → Hogar → Dispositivo (patrón Composite,
Semana 8) ya sabe calcular producción, consumo y balance. Pero aparecen
nuevas preguntas sobre ese mismo árbol: ¿cuánto CO₂ evitó cada hogar con su
producción?, ¿qué hogares están en déficit o tienen dispositivos sin
lecturas?, ¿cómo exporto todo a CSV? Agregar un método por cada pregunta a
`DispositivoHoja` y `GrupoEnergetico` haría crecer esas clases sin fin y
mezclaría con el modelo del árbol responsabilidades que no son suyas.

Solución (Visitor): cada nodo solo implementa `aceptar(visitante)`, que
llama al método del visitante que corresponde a SU clase (doble despacho):

    DispositivoHoja.aceptar(v)  → v.visitar_dispositivo(self)
    GrupoEnergetico.aceptar(v)  → v.visitar_grupo(self)

Cada análisis nuevo es una clase visitante nueva; las clases del árbol no
se vuelven a tocar:

    - VisitanteHuellaCarbono: kg de CO₂ evitados por la producción, por hogar.
    - VisitanteDiagnostico: hogares en déficit y dispositivos sin lecturas.
    - VisitanteExportarCSV: una fila por nodo, con su ruta en el árbol.

Ejecutar este archivo directamente corre una demo por consola:
    python "Documentacion/Semana 14/visitor.py"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

# Factor de emisión de referencia de la red eléctrica (kg CO₂ por kWh).
# Valor ilustrativo del orden del factor del Sistema Interconectado Nacional.
FACTOR_EMISION_KG_KWH = 0.126


# ===========================================================================
# ELEMENTS — nodos del árbol (versión reducida del Composite de la Semana 8)
# ===========================================================================
class NodoEnergetico(ABC):
    def __init__(self, nombre: str) -> None:
        self.nombre = nombre

    @abstractmethod
    def produccion_kwh(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def consumo_kwh(self) -> float:
        raise NotImplementedError

    def balance_kwh(self) -> float:
        return round(self.produccion_kwh() - self.consumo_kwh(), 2)

    @abstractmethod
    def aceptar(self, visitante: "VisitanteEnergetico") -> None:
        raise NotImplementedError


class DispositivoHoja(NodoEnergetico):
    def __init__(self, nombre: str, tipo: str, lecturas: Iterable[float] = ()) -> None:
        super().__init__(nombre)
        self.tipo = tipo
        self.lecturas = list(lecturas)

    def produccion_kwh(self) -> float:
        return round(sum((l for l in self.lecturas if l > 0), 0.0), 2)

    def consumo_kwh(self) -> float:
        return round(sum((-l for l in self.lecturas if l < 0), 0.0), 2)

    def aceptar(self, visitante: "VisitanteEnergetico") -> None:
        visitante.visitar_dispositivo(self)


class GrupoEnergetico(NodoEnergetico):
    def __init__(self, nombre: str, nivel: str = "grupo") -> None:
        super().__init__(nombre)
        self.nivel = nivel
        self.hijos: list[NodoEnergetico] = []

    def agregar(self, nodo: NodoEnergetico) -> "GrupoEnergetico":
        self.hijos.append(nodo)
        return self

    def produccion_kwh(self) -> float:
        return round(sum((h.produccion_kwh() for h in self.hijos), 0.0), 2)

    def consumo_kwh(self) -> float:
        return round(sum((h.consumo_kwh() for h in self.hijos), 0.0), 2)

    def aceptar(self, visitante: "VisitanteEnergetico") -> None:
        visitante.visitar_grupo(self)


# ===========================================================================
# VISITOR — una operación nueva sobre el árbol = una clase nueva
# ===========================================================================
class VisitanteEnergetico(ABC):
    @abstractmethod
    def visitar_dispositivo(self, dispositivo: DispositivoHoja) -> None:
        raise NotImplementedError

    @abstractmethod
    def visitar_grupo(self, grupo: GrupoEnergetico) -> None:
        raise NotImplementedError

    @abstractmethod
    def resultado(self):
        raise NotImplementedError


class VisitanteHuellaCarbono(VisitanteEnergetico):
    """kg de CO₂ que la red habría emitido para producir lo que produjo cada hogar."""

    def __init__(self, factor_kg_kwh: float = FACTOR_EMISION_KG_KWH) -> None:
        self.factor = factor_kg_kwh
        self.total_kg = 0.0
        self.por_hogar: dict[str, float] = {}
        self._hogar_actual: str | None = None

    def visitar_dispositivo(self, dispositivo: DispositivoHoja) -> None:
        kg = dispositivo.produccion_kwh() * self.factor
        self.total_kg += kg
        if self._hogar_actual is not None:
            self.por_hogar[self._hogar_actual] = round(self.por_hogar.get(self._hogar_actual, 0.0) + kg, 3)

    def visitar_grupo(self, grupo: GrupoEnergetico) -> None:
        anterior = self._hogar_actual
        if grupo.nivel == "hogar":
            self._hogar_actual = grupo.nombre
            self.por_hogar.setdefault(grupo.nombre, 0.0)
        for hijo in grupo.hijos:
            hijo.aceptar(self)
        self._hogar_actual = anterior

    def resultado(self) -> dict:
        return {"total_kg_co2": round(self.total_kg, 3), "por_hogar": self.por_hogar, "factor_kg_kwh": self.factor}


class VisitanteDiagnostico(VisitanteEnergetico):
    """Hogares en déficit (balance < 0) y dispositivos que nunca reportaron lecturas."""

    def __init__(self) -> None:
        self.hogares_en_deficit: list[dict] = []
        self.dispositivos_sin_lecturas: list[str] = []

    def visitar_dispositivo(self, dispositivo: DispositivoHoja) -> None:
        if not dispositivo.lecturas:
            self.dispositivos_sin_lecturas.append(dispositivo.nombre)

    def visitar_grupo(self, grupo: GrupoEnergetico) -> None:
        if grupo.nivel == "hogar" and grupo.balance_kwh() < 0:
            self.hogares_en_deficit.append({"hogar": grupo.nombre, "balance_kwh": grupo.balance_kwh()})
        for hijo in grupo.hijos:
            hijo.aceptar(self)

    def resultado(self) -> dict:
        return {
            "hogares_en_deficit": self.hogares_en_deficit,
            "dispositivos_sin_lecturas": self.dispositivos_sin_lecturas,
        }


class VisitanteExportarCSV(VisitanteEnergetico):
    """Una fila por nodo; la columna `ruta` conserva la posición en el árbol."""

    ENCABEZADO = "ruta;nivel;tipo;produccion_kwh;consumo_kwh;balance_kwh"

    def __init__(self) -> None:
        self.filas: list[str] = [self.ENCABEZADO]
        self._ruta: list[str] = []

    def _fila(self, nodo: NodoEnergetico, nivel: str, tipo: str) -> None:
        ruta = "/".join(self._ruta + [nodo.nombre])
        self.filas.append(
            f"{ruta};{nivel};{tipo};{nodo.produccion_kwh()};{nodo.consumo_kwh()};{nodo.balance_kwh()}"
        )

    def visitar_dispositivo(self, dispositivo: DispositivoHoja) -> None:
        self._fila(dispositivo, "dispositivo", dispositivo.tipo)

    def visitar_grupo(self, grupo: GrupoEnergetico) -> None:
        self._fila(grupo, grupo.nivel, "")
        self._ruta.append(grupo.nombre)
        for hijo in grupo.hijos:
            hijo.aceptar(self)
        self._ruta.pop()

    def resultado(self) -> str:
        return "\n".join(self.filas)


if __name__ == "__main__":
    comunidad = GrupoEnergetico("Comunidad Voltia", "comunidad")
    comunidad.agregar(
        GrupoEnergetico("Hogar de Ana", "hogar")
        .agregar(DispositivoHoja("panel-ana", "panel_solar", [3.0, 2.5]))
        .agregar(DispositivoHoja("medidor-ana", "medidor", [-1.0]))
    )
    comunidad.agregar(
        GrupoEnergetico("Hogar de Luis", "hogar")
        .agregar(DispositivoHoja("medidor-luis", "medidor", [-2.0, -1.5]))
        .agregar(DispositivoHoja("bateria-luis", "bateria"))
    )

    for visitante in (VisitanteHuellaCarbono(), VisitanteDiagnostico(), VisitanteExportarCSV()):
        comunidad.aceptar(visitante)
        print(f"--- {type(visitante).__name__} ---")
        print(visitante.resultado())
        print()
