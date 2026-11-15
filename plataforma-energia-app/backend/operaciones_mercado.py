"""
Plataforma de Comercio de Energía — operaciones del mercado como objetos
(patrón Command). Consumido por plataforma.py (programar_operacion,
ejecutar_operaciones, deshacer_operacion).

- Receiver: `PlataformaEnergia` (publicar_venta, publicar_compra, cancelar_orden).
- Commands: `PublicarVentaComando`, `PublicarCompraComando`, `CancelarOrdenComando`.
- Invoker: `GestorOperaciones` (cola de pendientes, ejecución en lote,
  historial y deshacer del último).

Deshacer respeta el ciclo de vida de la orden (patrón State): deshacer una
publicación cancela la orden (falla si ya se completó); como una orden
cancelada no puede reabrirse, deshacer una cancelación vuelve a publicar
lo que le quedaba pendiente como una orden nueva.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class OperacionInvalida(ValueError):
    """La operación no se puede ejecutar o deshacer en el estado actual."""


def _como_operacion_invalida(funcion, *args):
    """Traduce los errores del receptor a un único tipo para el Invoker."""
    try:
        return funcion(*args)
    except (LookupError, PermissionError, ValueError) as exc:
        raise OperacionInvalida(str(exc)) from exc


# ---------------------------------------------------------------------------
# COMMAND
# ---------------------------------------------------------------------------
class ComandoMercado(ABC):
    tipo: str = ""

    @abstractmethod
    def ejecutar(self) -> dict: ...

    @abstractmethod
    def deshacer(self) -> dict: ...

    @abstractmethod
    def descripcion(self) -> str: ...

    def to_dict(self) -> dict:
        return {"tipo": self.tipo, "descripcion": self.descripcion()}


# ---------------------------------------------------------------------------
# CONCRETE COMMANDS
# ---------------------------------------------------------------------------
class _PublicarComando(ComandoMercado):
    def __init__(self, plataforma: Any, usuario_id: str, cantidad_kwh: float, precio_kwh: float) -> None:
        if cantidad_kwh <= 0 or precio_kwh <= 0:
            raise OperacionInvalida("Cantidad y precio deben ser positivos")
        self._plataforma = plataforma
        self._usuario_id = usuario_id
        self._cantidad = cantidad_kwh
        self._precio = precio_kwh
        self.orden_id: int | None = None

    def _publicar(self):
        raise NotImplementedError

    def ejecutar(self) -> dict:
        orden = self._publicar()
        self.orden_id = orden.id
        return orden.to_dict()

    def deshacer(self) -> dict:
        return _como_operacion_invalida(self._plataforma.cancelar_orden, self._usuario_id, self.orden_id).to_dict()

    def descripcion(self) -> str:
        sufijo = f" (orden #{self.orden_id})" if self.orden_id else ""
        return f"Publicar {self.tipo.split('_')[1]} de {self._cantidad} kWh a {self._precio} $/kWh{sufijo}"


class PublicarVentaComando(_PublicarComando):
    tipo = "publicar_venta"

    def _publicar(self):
        return self._plataforma.publicar_venta(self._usuario_id, self._cantidad, self._precio)


class PublicarCompraComando(_PublicarComando):
    tipo = "publicar_compra"

    def _publicar(self):
        return self._plataforma.publicar_compra(self._usuario_id, self._cantidad, self._precio)


class CancelarOrdenComando(ComandoMercado):
    tipo = "cancelar_orden"

    def __init__(self, plataforma: Any, usuario_id: str, orden_id: int) -> None:
        self._plataforma = plataforma
        self._usuario_id = usuario_id
        self.orden_id = orden_id
        self._cancelada = None
        self.orden_reabierta_id: int | None = None

    def ejecutar(self) -> dict:
        self._cancelada = _como_operacion_invalida(self._plataforma.cancelar_orden, self._usuario_id, self.orden_id)
        return self._cancelada.to_dict()

    def deshacer(self) -> dict:
        orden = self._cancelada
        publicar = self._plataforma.publicar_venta if orden.tipo == "venta" else self._plataforma.publicar_compra
        nueva = publicar(self._usuario_id, orden.cantidad_kwh, orden.precio_kwh)
        self.orden_reabierta_id = nueva.id
        return nueva.to_dict()

    def descripcion(self) -> str:
        return f"Cancelar orden #{self.orden_id}"


COMANDOS_DISPONIBLES = ("publicar_venta", "publicar_compra", "cancelar_orden")


def crear_comando(plataforma: Any, usuario_id: str, tipo: str, **datos) -> ComandoMercado:
    """Client: arma el comando con su receptor a partir de lo que pide la API."""
    try:
        if tipo == "publicar_venta":
            return PublicarVentaComando(plataforma, usuario_id, datos["cantidad_kwh"], datos["precio_kwh"])
        if tipo == "publicar_compra":
            return PublicarCompraComando(plataforma, usuario_id, datos["cantidad_kwh"], datos["precio_kwh"])
        if tipo == "cancelar_orden":
            return CancelarOrdenComando(plataforma, usuario_id, int(datos["orden_id"]))
    except (KeyError, TypeError) as exc:
        raise OperacionInvalida(f"Faltan datos para '{tipo}': {exc}") from None
    raise OperacionInvalida(f"Operación '{tipo}' no soportada. Disponibles: {', '.join(COMANDOS_DISPONIBLES)}")


# ---------------------------------------------------------------------------
# INVOKER
# ---------------------------------------------------------------------------
class GestorOperaciones:
    def __init__(self) -> None:
        self._pendientes: list[ComandoMercado] = []
        self._ejecutados: list[ComandoMercado] = []
        self.registro: list[dict] = []

    def _anotar(self, evento: str, comando: ComandoMercado, detalle: str = "") -> None:
        self.registro.append(
            {"evento": evento, "operacion": comando.descripcion(), "detalle": detalle,
             "timestamp": datetime.now().isoformat(timespec="seconds")}
        )

    def programar(self, comando: ComandoMercado) -> None:
        self._pendientes.append(comando)
        self._anotar("programado", comando)

    def descartar_pendientes(self) -> int:
        cantidad = len(self._pendientes)
        self._pendientes.clear()
        return cantidad

    def ejecutar(self, comando: ComandoMercado) -> dict:
        resultado = comando.ejecutar()
        self._ejecutados.append(comando)
        self._anotar("ejecutado", comando)
        return resultado

    def ejecutar_pendientes(self) -> dict:
        exitos, errores = [], []
        pendientes, self._pendientes = self._pendientes, []
        for comando in pendientes:
            try:
                self.ejecutar(comando)
                exitos.append(comando.descripcion())
            except OperacionInvalida as exc:
                errores.append({"operacion": comando.descripcion(), "error": str(exc)})
                self._anotar("fallido", comando, str(exc))
        return {"ejecutados": exitos, "errores": errores}

    def deshacer(self) -> ComandoMercado:
        if not self._ejecutados:
            raise OperacionInvalida("No hay operaciones para deshacer")
        comando = self._ejecutados[-1]
        comando.deshacer()  # si falla, sigue en el historial
        self._ejecutados.pop()
        self._anotar("deshecho", comando)
        return comando

    def to_dict(self) -> dict:
        return {
            "pendientes": [c.to_dict() for c in self._pendientes],
            "ejecutados": [c.to_dict() for c in self._ejecutados],
            "puede_deshacer": bool(self._ejecutados),
            "registro": list(self.registro),
        }
