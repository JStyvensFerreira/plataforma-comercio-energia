"""
Patrón Observer — eventos del mercado de energía y alertas de precio.

Problema: cada vez que se publica una orden o se cierra una transacción en
el mercado, varias partes del sistema necesitan enterarse: un comprador que
espera energía barata quiere un aviso cuando aparezca una oferta por debajo
de su precio máximo, las estadísticas del mercado (precio promedio, volumen)
deben actualizarse, y la auditoría debe dejar registro. Si la plataforma
llamara a cada interesado a mano desde `publicar_venta` o `ejecutar_subasta`,
cada interesado nuevo obligaría a modificar esos métodos, y la lógica del
mercado quedaría acoplada a quién escucha.

Solución (Observer): `MercadoEnergia` (Subject) mantiene una lista de
observadores que implementan la interfaz `ObservadorMercado` y les avisa con
un `EventoMercado` cada vez que algo ocurre. El mercado no conoce las clases
concretas de sus observadores, y se pueden suscribir/desuscribir en tiempo
de ejecución:

    - AlertaPrecio: avisa a UN usuario cuando se publica una venta (de otro
      usuario) a un precio <= su precio máximo.
    - EstadisticasMercado: acumula volumen y precio promedio de las
      transacciones ejecutadas.
    - RegistroAuditoria: guarda todos los eventos tal cual llegan.

Si un observador falla, el mercado registra el error y sigue notificando al
resto: un observador defectuoso no puede tumbar la subasta.

Ejecutar este archivo directamente corre una demo por consola:
    python "Documentacion/Semana 14/observer.py"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

ORDEN_PUBLICADA = "orden_publicada"
TRANSACCION_EJECUTADA = "transaccion_ejecutada"


@dataclass(frozen=True)
class EventoMercado:
    tipo: str
    datos: dict


# ===========================================================================
# OBSERVER — interfaz que implementa cualquier interesado en el mercado
# ===========================================================================
class ObservadorMercado(ABC):
    @abstractmethod
    def actualizar(self, evento: EventoMercado) -> None:
        raise NotImplementedError


# ===========================================================================
# SUBJECT — el mercado mantiene y avisa a sus observadores
# ===========================================================================
class MercadoEnergia:
    def __init__(self) -> None:
        self._observadores: list[ObservadorMercado] = []
        self.errores: list[str] = []

    @property
    def observadores(self) -> tuple[ObservadorMercado, ...]:
        return tuple(self._observadores)

    def suscribir(self, observador: ObservadorMercado) -> None:
        if observador not in self._observadores:
            self._observadores.append(observador)

    def desuscribir(self, observador: ObservadorMercado) -> None:
        if observador in self._observadores:
            self._observadores.remove(observador)

    def notificar(self, evento: EventoMercado) -> None:
        # Se itera sobre una copia: un observador puede desuscribirse a sí
        # mismo (o a otro) mientras recibe el evento.
        for observador in list(self._observadores):
            try:
                observador.actualizar(evento)
            except Exception as exc:  # un observador defectuoso no frena al resto
                self.errores.append(f"{type(observador).__name__}: {exc}")

    # --- operaciones del mercado que generan eventos ---
    def publicar_venta(self, vendedor: str, cantidad_kwh: float, precio_kwh: float) -> dict:
        orden = {"tipo": "venta", "usuario": vendedor, "cantidad_kwh": cantidad_kwh, "precio_kwh": precio_kwh}
        self.notificar(EventoMercado(ORDEN_PUBLICADA, orden))
        return orden

    def publicar_compra(self, comprador: str, cantidad_kwh: float, precio_kwh: float) -> dict:
        orden = {"tipo": "compra", "usuario": comprador, "cantidad_kwh": cantidad_kwh, "precio_kwh": precio_kwh}
        self.notificar(EventoMercado(ORDEN_PUBLICADA, orden))
        return orden

    def registrar_transaccion(self, comprador: str, vendedor: str, cantidad_kwh: float, precio_kwh: float) -> dict:
        tx = {"comprador": comprador, "vendedor": vendedor, "cantidad_kwh": cantidad_kwh, "precio_kwh": precio_kwh}
        self.notificar(EventoMercado(TRANSACCION_EJECUTADA, tx))
        return tx


# ===========================================================================
# CONCRETE OBSERVERS
# ===========================================================================
@dataclass(eq=False)
class AlertaPrecio(ObservadorMercado):
    """Avisa a `usuario_id` cuando aparece una venta ajena a <= `precio_max`."""

    usuario_id: str
    precio_max: float
    avisos: list[str] = field(default_factory=list)

    def actualizar(self, evento: EventoMercado) -> None:
        orden = evento.datos
        if (
            evento.tipo == ORDEN_PUBLICADA
            and orden["tipo"] == "venta"
            and orden["usuario"] != self.usuario_id
            and orden["precio_kwh"] <= self.precio_max
        ):
            self.avisos.append(
                f"{orden['usuario']} vende {orden['cantidad_kwh']} kWh a "
                f"{orden['precio_kwh']} $/kWh (tu máximo: {self.precio_max})"
            )


@dataclass(eq=False)
class EstadisticasMercado(ObservadorMercado):
    transacciones: int = 0
    volumen_kwh: float = 0.0
    monto_total: float = 0.0

    def actualizar(self, evento: EventoMercado) -> None:
        if evento.tipo != TRANSACCION_EJECUTADA:
            return
        self.transacciones += 1
        self.volumen_kwh += evento.datos["cantidad_kwh"]
        self.monto_total += evento.datos["cantidad_kwh"] * evento.datos["precio_kwh"]

    @property
    def precio_promedio(self) -> float:
        """Precio promedio ponderado por volumen (no promedio simple de precios)."""
        if self.volumen_kwh == 0:
            return 0.0
        return round(self.monto_total / self.volumen_kwh, 2)


@dataclass(eq=False)
class RegistroAuditoria(ObservadorMercado):
    eventos: list[EventoMercado] = field(default_factory=list)

    def actualizar(self, evento: EventoMercado) -> None:
        self.eventos.append(evento)


if __name__ == "__main__":
    mercado = MercadoEnergia()
    alerta_luis = AlertaPrecio("luis", precio_max=500)
    estadisticas = EstadisticasMercado()
    auditoria = RegistroAuditoria()
    for obs in (alerta_luis, estadisticas, auditoria):
        mercado.suscribir(obs)

    print("1) Ana publica 5 kWh a 450 $/kWh (por debajo del máximo de Luis).")
    mercado.publicar_venta("ana", 5, 450)
    print(f"   Avisos de Luis: {alerta_luis.avisos}")

    print("2) Marta publica 3 kWh a 650 $/kWh (por encima: Luis no recibe aviso).")
    mercado.publicar_venta("marta", 3, 650)
    print(f"   Avisos de Luis: {len(alerta_luis.avisos)}")

    print("3) Se cierran dos transacciones: las estadísticas se actualizan solas.")
    mercado.registrar_transaccion("luis", "ana", 5, 450)
    mercado.registrar_transaccion("pedro", "marta", 3, 650)
    print(f"   Volumen: {estadisticas.volumen_kwh} kWh | precio promedio: {estadisticas.precio_promedio} $/kWh")

    print("4) Luis se desuscribe y Ana publica otra oferta barata.")
    mercado.desuscribir(alerta_luis)
    mercado.publicar_venta("ana", 2, 400)
    print(f"   Avisos de Luis: {len(alerta_luis.avisos)} (no debió subir)")

    print(f"\nEventos auditados: {len(auditoria.eventos)}")
