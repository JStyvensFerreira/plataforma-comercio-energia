"""
Patrón Command — operaciones del mercado programadas, ejecutadas en lote y reversibles.

Problema: un prosumidor quiere preparar varias operaciones del mercado
(publicar una venta para la tarde, una compra para la noche, retirar una
orden vieja), revisarlas y ejecutarlas todas juntas; y si se equivocó,
deshacer la última operación ejecutada. Si la interfaz llamara directamente
a los métodos del mercado, no habría forma de guardar una operación para
después, de llevar un registro de lo que se hizo ni de revertirlo: cada
botón tendría que saber cómo deshacer cada acción.

Solución (Command):

    - Receiver `Mercado`: sabe publicar, cancelar y reabrir órdenes. No sabe
      nada de colas ni de deshacer.
    - Command `ComandoMercado`: interfaz `ejecutar()` / `deshacer()` /
      `descripcion()`.
    - Concrete Commands `PublicarVentaComando`, `PublicarCompraComando` y
      `CancelarOrdenComando`: guardan el receptor y los datos de la
      solicitud, y lo que necesitan para revertirla (el id de la orden
      creada o la orden cancelada).
    - Invoker `GestorOperaciones`: cola de comandos pendientes, ejecución en
      lote, historial de ejecutados y `deshacer()` del último. Nunca llama
      al mercado directamente.
    - Client: arma los comandos con su receptor y se los entrega al gestor.

Ejecutar este archivo directamente corre una demo por consola:
    python "Documentacion/Semana 15/command.py"
"""

from __future__ import annotations

import itertools
from abc import ABC, abstractmethod
from dataclasses import dataclass


class OperacionInvalida(ValueError):
    """La operación no se puede ejecutar o deshacer en el estado actual."""


@dataclass
class Orden:
    id: int
    usuario: str
    tipo: str
    cantidad_kwh: float
    precio_kwh: float
    activa: bool = True


# ===========================================================================
# RECEIVER — la lógica real del mercado
# ===========================================================================
class Mercado:
    def __init__(self) -> None:
        self.ordenes: dict[int, Orden] = {}
        self._ids = itertools.count(1)

    def publicar(self, usuario: str, tipo: str, cantidad_kwh: float, precio_kwh: float) -> Orden:
        if cantidad_kwh <= 0 or precio_kwh <= 0:
            raise OperacionInvalida("Cantidad y precio deben ser positivos")
        orden = Orden(next(self._ids), usuario, tipo, cantidad_kwh, precio_kwh)
        self.ordenes[orden.id] = orden
        return orden

    def cancelar(self, usuario: str, orden_id: int) -> Orden:
        orden = self.ordenes.get(orden_id)
        if orden is None:
            raise OperacionInvalida(f"La orden {orden_id} no existe")
        if orden.usuario != usuario:
            raise OperacionInvalida(f"La orden {orden_id} no es de {usuario}")
        if not orden.activa:
            raise OperacionInvalida(f"La orden {orden_id} ya no está activa")
        orden.activa = False
        return orden

    def reabrir(self, orden_id: int) -> Orden:
        orden = self.ordenes[orden_id]
        orden.activa = True
        return orden

    def activas(self) -> list[Orden]:
        return [o for o in self.ordenes.values() if o.activa]


# ===========================================================================
# COMMAND — una solicitud convertida en objeto
# ===========================================================================
class ComandoMercado(ABC):
    @abstractmethod
    def ejecutar(self) -> None: ...

    @abstractmethod
    def deshacer(self) -> None: ...

    @abstractmethod
    def descripcion(self) -> str: ...


# ===========================================================================
# CONCRETE COMMANDS — guardan receptor, datos y cómo revertirse
# ===========================================================================
class _PublicarComando(ComandoMercado):
    tipo = ""

    def __init__(self, mercado: Mercado, usuario: str, cantidad_kwh: float, precio_kwh: float) -> None:
        self._mercado = mercado
        self._usuario = usuario
        self._cantidad = cantidad_kwh
        self._precio = precio_kwh
        self.orden_id: int | None = None

    def ejecutar(self) -> None:
        self.orden_id = self._mercado.publicar(self._usuario, self.tipo, self._cantidad, self._precio).id

    def deshacer(self) -> None:
        self._mercado.cancelar(self._usuario, self.orden_id)  # retira la orden publicada

    def descripcion(self) -> str:
        return f"Publicar {self.tipo} de {self._cantidad} kWh a {self._precio}"


class PublicarVentaComando(_PublicarComando):
    tipo = "venta"


class PublicarCompraComando(_PublicarComando):
    tipo = "compra"


class CancelarOrdenComando(ComandoMercado):
    def __init__(self, mercado: Mercado, usuario: str, orden_id: int) -> None:
        self._mercado = mercado
        self._usuario = usuario
        self.orden_id = orden_id

    def ejecutar(self) -> None:
        self._mercado.cancelar(self._usuario, self.orden_id)

    def deshacer(self) -> None:
        self._mercado.reabrir(self.orden_id)  # la orden vuelve al mercado

    def descripcion(self) -> str:
        return f"Cancelar orden #{self.orden_id}"


# ===========================================================================
# INVOKER — cola, ejecución en lote, historial y deshacer
# ===========================================================================
class GestorOperaciones:
    def __init__(self) -> None:
        self._pendientes: list[ComandoMercado] = []
        self._ejecutados: list[ComandoMercado] = []
        self.registro: list[str] = []

    def programar(self, comando: ComandoMercado) -> None:
        self._pendientes.append(comando)

    def descartar_pendientes(self) -> int:
        cantidad = len(self._pendientes)
        self._pendientes.clear()
        return cantidad

    def ejecutar(self, comando: ComandoMercado) -> None:
        """Ejecuta de inmediato; solo pasa al historial si tuvo éxito."""
        comando.ejecutar()
        self._ejecutados.append(comando)
        self.registro.append(f"ejecutado: {comando.descripcion()}")

    def ejecutar_pendientes(self) -> dict:
        """Ejecuta la cola en orden. Un comando que falla se informa y no detiene a los demás."""
        exitos, errores = [], []
        pendientes, self._pendientes = self._pendientes, []
        for comando in pendientes:
            try:
                self.ejecutar(comando)
                exitos.append(comando.descripcion())
            except OperacionInvalida as exc:
                errores.append({"operacion": comando.descripcion(), "error": str(exc)})
                self.registro.append(f"fallido: {comando.descripcion()} ({exc})")
        return {"ejecutados": exitos, "errores": errores}

    def deshacer(self) -> ComandoMercado:
        if not self._ejecutados:
            raise OperacionInvalida("No hay operaciones para deshacer")
        comando = self._ejecutados[-1]
        comando.deshacer()  # si falla, el comando sigue en el historial
        self._ejecutados.pop()
        self.registro.append(f"deshecho: {comando.descripcion()}")
        return comando

    def pendientes(self) -> list[str]:
        return [c.descripcion() for c in self._pendientes]

    def ejecutados(self) -> list[str]:
        return [c.descripcion() for c in self._ejecutados]


if __name__ == "__main__":
    mercado = Mercado()
    gestor = GestorOperaciones()
    vieja = mercado.publicar("ana", "venta", 2, 500)

    gestor.programar(PublicarVentaComando(mercado, "ana", 5, 440))
    gestor.programar(PublicarCompraComando(mercado, "ana", 3, 380))
    gestor.programar(CancelarOrdenComando(mercado, "ana", vieja.id))
    gestor.programar(CancelarOrdenComando(mercado, "ana", 99))
    print(f"Pendientes: {gestor.pendientes()}")

    resultado = gestor.ejecutar_pendientes()
    print(f"Ejecutados: {resultado['ejecutados']}")
    print(f"Errores:    {resultado['errores']}")
    print(f"Órdenes activas: {[(o.id, o.tipo, o.precio_kwh) for o in mercado.activas()]}")

    print(f"\nDeshacer: {gestor.deshacer().descripcion()}")
    print(f"Deshacer: {gestor.deshacer().descripcion()}")
    print(f"Órdenes activas: {[(o.id, o.tipo, o.precio_kwh) for o in mercado.activas()]}")
    print("\nRegistro:")
    for linea in gestor.registro:
        print(f"  {linea}")
