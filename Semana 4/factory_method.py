"""
Plataforma de Comercio de Energía
==================================
Implementa el requerimiento #16:
  - Compra/venta de excedentes energéticos entre usuarios
  - Sistema de subastas en tiempo real
  - Integración con dispositivos IoT domésticos
  - Predicción de producción y consumo

Patrón aplicado: FACTORY METHOD
--------------------------------
La plataforma debe integrar distintos tipos de dispositivos IoT domésticos
(paneles solares, baterías inteligentes, medidores, etc.). Cada tipo de
dispositivo produce sus lecturas de forma diferente: un panel solar genera
energía (nunca la consume), una batería puede cargar o descargar, y un
medidor simplemente registra el consumo del hogar.

Si el código que registra dispositivos tuviera que decidir con `if/elif`
qué clase instanciar y cómo simular sus lecturas, cada vez que se agregue
un nuevo tipo de dispositivo (ej. un cargador de vehículo eléctrico) habría
que modificar esa lógica central, violando el principio abierto/cerrado.

Con FACTORY METHOD, cada tipo de dispositivo tiene su propia fábrica
(`DispositivoIoTFactory`) que sabe cómo crear su producto (`DispositivoIoT`)
y cómo generar una lectura realista para ese tipo. La plataforma solo
conoce la interfaz común `DispositivoIoT` / `DispositivoIoTFactory`, nunca
las clases concretas. Agregar un nuevo tipo de dispositivo se reduce a
crear una nueva subclase de producto + una nueva subclase de fábrica,
sin tocar el código existente.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
import random


# ---------------------------------------------------------------------------
# PRODUCTO — interfaz común de los dispositivos IoT
# ---------------------------------------------------------------------------
@dataclass
class DispositivoIoT(ABC):
    """Producto abstracto: todo dispositivo IoT conectado a la plataforma."""
    id: str
    usuario_id: str

    @property
    @abstractmethod
    def tipo(self) -> str:
        """Nombre del tipo de dispositivo (ej. 'panel_solar')."""
        raise NotImplementedError

    @abstractmethod
    def generar_lectura(self) -> float:
        """
        Cada tipo de dispositivo sabe cómo simular su propia lectura
        (kWh producidos, cargados/descargados o consumidos).
        """
        raise NotImplementedError

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tipo"] = self.tipo
        return d


# ---------------------------------------------------------------------------
# PRODUCTOS CONCRETOS
# ---------------------------------------------------------------------------
@dataclass
class PanelSolar(DispositivoIoT):
    """Genera energía; la lectura siempre es positiva (producción)."""

    @property
    def tipo(self) -> str:
        return "panel_solar"

    def generar_lectura(self) -> float:
        return round(random.uniform(0.5, 4.0), 2)


@dataclass
class BateriaInteligente(DispositivoIoT):
    """Puede cargar (+) o descargar (-) energía almacenada."""

    @property
    def tipo(self) -> str:
        return "bateria"

    def generar_lectura(self) -> float:
        return round(random.uniform(-2.5, 2.5), 2)


@dataclass
class MedidorInteligente(DispositivoIoT):
    """Registra el consumo del hogar; la lectura siempre es negativa (demanda)."""

    @property
    def tipo(self) -> str:
        return "medidor"

    def generar_lectura(self) -> float:
        return round(-random.uniform(0.3, 3.0), 2)


# ---------------------------------------------------------------------------
# CREADOR — declara el Factory Method
# ---------------------------------------------------------------------------
class DispositivoIoTFactory(ABC):
    """
    Creador abstracto. Define el método de fábrica `crear_dispositivo`,
    que las subclases concretas implementan para decidir qué clase de
    producto (`DispositivoIoT`) instanciar.
    """

    @abstractmethod
    def crear_dispositivo(self, id_dispositivo: str, usuario_id: str) -> DispositivoIoT:
        """Factory Method: cada subclase decide qué producto concreto crear."""
        raise NotImplementedError

    def registrar(self, id_dispositivo: str, usuario_id: str) -> DispositivoIoT:
        """
        Lógica común a todas las fábricas (logging, validaciones futuras, etc.)
        que reutiliza el producto devuelto por el Factory Method, sin conocer
        su clase concreta.
        """
        dispositivo = self.crear_dispositivo(id_dispositivo, usuario_id)
        print(f"[Factory Method] Dispositivo creado -> tipo={dispositivo.tipo} id={dispositivo.id}")
        return dispositivo


# ---------------------------------------------------------------------------
# CREADORES CONCRETOS
# ---------------------------------------------------------------------------
class PanelSolarFactory(DispositivoIoTFactory):
    def crear_dispositivo(self, id_dispositivo: str, usuario_id: str) -> DispositivoIoT:
        return PanelSolar(id_dispositivo, usuario_id)


class BateriaFactory(DispositivoIoTFactory):
    def crear_dispositivo(self, id_dispositivo: str, usuario_id: str) -> DispositivoIoT:
        return BateriaInteligente(id_dispositivo, usuario_id)


class MedidorFactory(DispositivoIoTFactory):
    def crear_dispositivo(self, id_dispositivo: str, usuario_id: str) -> DispositivoIoT:
        return MedidorInteligente(id_dispositivo, usuario_id)


# ---------------------------------------------------------------------------
# Registro de fábricas disponibles
# ---------------------------------------------------------------------------
_FACTORIES: dict[str, DispositivoIoTFactory] = {
    "panel_solar": PanelSolarFactory(),
    "bateria": BateriaFactory(),
    "medidor": MedidorFactory(),
}


def obtener_factory(tipo: str) -> DispositivoIoTFactory:
    """
    Punto único donde se resuelve qué fábrica concreta usar según el tipo
    solicitado. Agregar un nuevo tipo de dispositivo solo requiere registrar
    su fábrica aquí, sin modificar el resto de la plataforma.
    """
    try:
        return _FACTORIES[tipo]
    except KeyError:
        disponibles = ", ".join(_FACTORIES)
        raise ValueError(f"Tipo de dispositivo '{tipo}' no soportado. Disponibles: {disponibles}")


def crear_dispositivo(tipo: str, id_dispositivo: str, usuario_id: str) -> DispositivoIoT:
    """Función de conveniencia usada por la plataforma para registrar dispositivos."""
    factory = obtener_factory(tipo)
    return factory.registrar(id_dispositivo, usuario_id)


# ---------------------------------------------------------------------------
# DEMO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # La plataforma nunca instancia PanelSolar/BateriaInteligente/MedidorInteligente
    # directamente: solo pide un dispositivo por tipo y el Factory Method decide
    # qué clase concreta construir.
    dispositivos = [
        crear_dispositivo("panel_solar", "panel-01", "u1"),
        crear_dispositivo("bateria", "bat-01", "u1"),
        crear_dispositivo("medidor", "medidor-01", "u2"),
    ]

    print("\nDispositivos registrados:")
    for d in dispositivos:
        print(" -", d.to_dict())

    print("\nLecturas simuladas (cada tipo genera la suya):")
    for d in dispositivos:
        print(f" - {d.tipo} ({d.id}): {d.generar_lectura()} kWh")

    # Ejemplo de tipo no soportado
    try:
        crear_dispositivo("cargador_ev", "ev-01", "u1")
    except ValueError as e:
        print("\nError esperado al pedir un tipo no registrado:", e)
