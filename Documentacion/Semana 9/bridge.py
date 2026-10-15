"""
Plataforma de Comercio de Energía
==================================
Implementa el requerimiento #16:
  - Compra/venta de excedentes energéticos entre usuarios
  - Sistema de subastas en tiempo real
  - Integración con dispositivos IoT domésticos
  - Predicción de producción y consumo

Patrón aplicado: BRIDGE (Puente)
---------------------------------
La plataforma necesita sincronizar lecturas de dispositivos IoT, pero el
MEDIO de comunicación varía según el fabricante o la instalación: algunos
dispositivos exponen una API HTTP propia, otros publican por MQTT, y en
demo/desarrollo se simulan lecturas aleatorias. Independiente del protocolo,
a veces conviene reintentar ante una falla de comunicación y a veces no.

Hay DOS cosas que varían de forma independiente:
  1. CÓMO se sincroniza (¿reintenta ante fallas, o falla directo?)
  2. POR DÓNDE llega el dato (¿simulado, HTTP, MQTT?)

Si se modelara con herencia (una subclase por combinación), agregar un
protocolo nuevo o una forma de sincronizar nueva multiplicaría las clases:
`SincronizadorSimpleHTTP`, `SincronizadorConReintentosHTTP`,
`SincronizadorSimpleMQTT`, `SincronizadorConReintentosMQTT`...

Con BRIDGE, las dos jerarquías se separan y una (la Abstraction) GUARDA UNA
REFERENCIA a la otra (el Implementor), en vez de heredar de ella:

  - Implementor `ProtocoloLectura`: declara `leer(dispositivo_id)`. Cada
    protocolo concreto (`ProtocoloSimulado`, `ProtocoloHTTP`, `ProtocoloMQTT`)
    sabe CÓMO obtener el valor, y puede fallar con `ConnectionError`.
  - Abstraction `SincronizadorDispositivo`: el cliente programa contra esta
    interfaz; delega la lectura en el protocolo que reciba por constructor.
  - RefinedAbstraction `SincronizadorConReintentos`: extiende la abstracción
    con reintentos — ese comportamiento es el mismo sin importar cuál
    protocolo esté detrás.

Cualquier combinación se arma por composición, en tiempo de ejecución, sin
clases nuevas:

    SincronizadorConReintentos(ProtocoloMQTT(), intentos=3)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


# ---------------------------------------------------------------------------
# IMPLEMENTOR — la jerarquía de "cómo se obtiene el dato"
# ---------------------------------------------------------------------------
class ProtocoloLectura(ABC):
    """Implementor: declara la operación que cada protocolo concreto implementa."""

    nombre: str = ""

    @abstractmethod
    def leer(self, dispositivo_id: str) -> float:
        """Devuelve la lectura en kWh, o lanza ConnectionError si falla."""
        raise NotImplementedError


class ProtocoloSimulado(ProtocoloLectura):
    """ConcreteImplementor: valores fijos predefinidos (útil para demo/pruebas)."""

    nombre = "simulado"

    def __init__(self, valores: Optional[dict[str, float]] = None) -> None:
        self._valores = valores or {}

    def leer(self, dispositivo_id: str) -> float:
        return self._valores.get(dispositivo_id, 1.0)


class ProtocoloHTTP(ProtocoloLectura):
    """ConcreteImplementor: simula leer la API propia del fabricante del dispositivo."""

    nombre = "http"

    def __init__(self, valores: Optional[dict[str, float]] = None) -> None:
        self._valores = valores or {}

    def leer(self, dispositivo_id: str) -> float:
        if dispositivo_id not in self._valores:
            raise ConnectionError(f"El fabricante no respondió para '{dispositivo_id}' (HTTP)")
        return self._valores[dispositivo_id]


class ProtocoloMQTT(ProtocoloLectura):
    """ConcreteImplementor: simula un valor publicado por un broker MQTT."""

    nombre = "mqtt"

    def __init__(self, valores: Optional[dict[str, float]] = None) -> None:
        self._valores = valores or {}

    def leer(self, dispositivo_id: str) -> float:
        if dispositivo_id not in self._valores:
            raise ConnectionError(f"Sin mensaje reciente en el tópico de '{dispositivo_id}' (MQTT)")
        return self._valores[dispositivo_id]


# ---------------------------------------------------------------------------
# ABSTRACTION — la jerarquía de "cómo se sincroniza"
# ---------------------------------------------------------------------------
class SincronizadorDispositivo:
    """
    Abstraction: el cliente programa contra esta clase. Mantiene una
    referencia al Implementor (`protocolo`) y le delega la lectura: no sabe
    ni le importa si es HTTP, MQTT o simulado.
    """

    def __init__(self, protocolo: ProtocoloLectura) -> None:
        self._protocolo = protocolo

    @property
    def protocolo(self) -> ProtocoloLectura:
        return self._protocolo

    def sincronizar(self, dispositivo_id: str) -> float:
        return self._protocolo.leer(dispositivo_id)


class SincronizadorConReintentos(SincronizadorDispositivo):
    """
    RefinedAbstraction: extiende la Abstraction con reintentos ante una
    falla de comunicación. Este comportamiento es independiente del
    protocolo: funciona igual con `ProtocoloHTTP` que con `ProtocoloMQTT`.
    """

    def __init__(self, protocolo: ProtocoloLectura, intentos: int = 3) -> None:
        super().__init__(protocolo)
        self.intentos = intentos
        self.intentos_usados = 0

    def sincronizar(self, dispositivo_id: str) -> float:
        self.intentos_usados = 0
        error: Optional[ConnectionError] = None
        for _ in range(self.intentos):
            self.intentos_usados += 1
            try:
                return self._protocolo.leer(dispositivo_id)
            except ConnectionError as e:
                error = e
        raise error  # se agotaron los intentos


# ---------------------------------------------------------------------------
# Registro de protocolos disponibles
# ---------------------------------------------------------------------------
_PROTOCOLOS: dict[str, type[ProtocoloLectura]] = {
    "simulado": ProtocoloSimulado,
    "http": ProtocoloHTTP,
    "mqtt": ProtocoloMQTT,
}

PROTOCOLOS_DISPONIBLES = tuple(_PROTOCOLOS)


def obtener_protocolo(nombre: str, valores: Optional[dict[str, float]] = None) -> ProtocoloLectura:
    """
    Punto único donde se resuelve el protocolo concreto por nombre. Un
    nombre desconocido lanza `ValueError` con los disponibles, igual que
    las demás fábricas/registros del proyecto.
    """
    try:
        return _PROTOCOLOS[nombre](valores)
    except KeyError:
        disponibles = ", ".join(_PROTOCOLOS)
        raise ValueError(f"Protocolo de lectura '{nombre}' no soportado. Disponibles: {disponibles}")


# ---------------------------------------------------------------------------
# DEMO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    http = ProtocoloHTTP({"panel-01": 2.8})
    mqtt = ProtocoloMQTT({"bateria-01": -0.5})

    print("Mismo cliente (SincronizadorDispositivo), distinto protocolo por detrás:\n")
    for protocolo, id_ in ((http, "panel-01"), (mqtt, "bateria-01")):
        sinc = SincronizadorDispositivo(protocolo)
        print(f"[{protocolo.nombre}] {id_} -> {sinc.sincronizar(id_)} kWh")

    print("\nSin reintentos, una falla de comunicación se propaga:")
    sinc = SincronizadorDispositivo(ProtocoloHTTP({}))
    try:
        sinc.sincronizar("panel-02")
    except ConnectionError as e:
        print(" ", e)

    print("\nCon SincronizadorConReintentos (RefinedAbstraction), mismo protocolo, más resiliente:")

    class _ProtocoloInestable(ProtocoloLectura):
        """Solo para la demo: falla las primeras veces y luego responde."""

        nombre = "inestable"

        def __init__(self, fallas_antes_de_responder: int, valor: float) -> None:
            self._restantes = fallas_antes_de_responder
            self._valor = valor

        def leer(self, dispositivo_id: str) -> float:
            if self._restantes > 0:
                self._restantes -= 1
                raise ConnectionError("Timeout del broker")
            return self._valor

    confiable = SincronizadorConReintentos(_ProtocoloInestable(2, 3.4), intentos=3)
    valor = confiable.sincronizar("medidor-03")
    print(f"  Lectura obtenida tras {confiable.intentos_usados} intento(s): {valor} kWh")

    print("\nRegistro por nombre:")
    sinc2 = SincronizadorDispositivo(obtener_protocolo("simulado", {"panel-09": 2.1}))
    print(f"  [simulado] panel-09 -> {sinc2.sincronizar('panel-09')} kWh")

    print("\nProtocolo no soportado:")
    try:
        obtener_protocolo("zigbee")
    except ValueError as e:
        print(" ", e)
