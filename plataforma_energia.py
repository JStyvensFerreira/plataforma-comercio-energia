"""
Plataforma de Comercio de Energía
==================================
Implementa el requerimiento #16:
  - Compra/venta de excedentes energéticos entre usuarios
  - Sistema de subastas en tiempo real
  - Integración con dispositivos IoT domésticos
  - Predicción de producción y consumo

Patrón aplicado: SINGLETON
---------------------------
La clase `PlataformaEnergia` es el "libro mayor" central del sistema:
todas las ofertas, pujas, usuarios y lecturas IoT deben pasar por una
única instancia compartida. Si existieran varias instancias, cada una
tendría su propio libro de órdenes y el sistema sería inconsistente
(dos subastas distintas para el mismo excedente, por ejemplo).
Por eso se garantiza que, sin importar cuántas veces se instancie,
siempre se devuelve el MISMO objeto.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean
from threading import Lock
from typing import Optional
import itertools
import random


# ---------------------------------------------------------------------------
# Metaclase Singleton (reutilizable, thread-safe)
# ---------------------------------------------------------------------------
class SingletonMeta(type):
    """
    Metaclase que convierte a cualquier clase en un Singleton.
    Usamos un Lock para que sea seguro incluso si varios hilos intentan
    crear la instancia al mismo tiempo (p. ej. varias peticiones IoT
    llegando simultáneamente).
    """
    _instances: dict[type, object] = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                # Doble verificación dentro del lock (patrón clásico)
                if cls not in cls._instances:
                    instancia = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instancia
        return cls._instances[cls]


# ---------------------------------------------------------------------------
# Entidades del dominio
# ---------------------------------------------------------------------------
@dataclass
class Usuario:
    id: str
    nombre: str
    balance_kwh: float = 0.0  # excedente disponible para vender


@dataclass
class Orden:
    id: int
    usuario_id: str
    tipo: str          # "venta" | "compra"
    cantidad_kwh: float
    precio_kwh: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DispositivoIoT:
    id: str
    usuario_id: str
    tipo: str  # "panel_solar", "bateria", "medidor", etc.


# ---------------------------------------------------------------------------
# PLATAFORMA CENTRAL — SINGLETON
# ---------------------------------------------------------------------------
class PlataformaEnergia(metaclass=SingletonMeta):
    """
    Punto único de acceso al sistema de comercio de energía.
    Cualquier módulo (subastas, IoT, predicción) trabaja siempre
    sobre esta misma instancia.
    """

    def __init__(self):
        self.usuarios: dict[str, Usuario] = {}
        self.dispositivos: dict[str, DispositivoIoT] = {}
        self.ordenes_venta: list[Orden] = []
        self.ordenes_compra: list[Orden] = []
        self.historial_transacciones: list[dict] = []
        self.lecturas_iot: dict[str, list[float]] = {}  # id_dispositivo -> lecturas kWh
        self._contador_ordenes = itertools.count(1)

    # ---------- Gestión de usuarios ----------
    def registrar_usuario(self, id_: str, nombre: str) -> Usuario:
        usuario = self.usuarios.setdefault(id_, Usuario(id_, nombre))
        return usuario

    # ---------- Compra/venta de excedentes ----------
    def publicar_venta(self, usuario_id: str, cantidad_kwh: float, precio_kwh: float) -> Orden:
        orden = Orden(next(self._contador_ordenes), usuario_id, "venta", cantidad_kwh, precio_kwh)
        self.ordenes_venta.append(orden)
        return orden

    def publicar_compra(self, usuario_id: str, cantidad_kwh: float, precio_kwh: float) -> Orden:
        orden = Orden(next(self._contador_ordenes), usuario_id, "compra", cantidad_kwh, precio_kwh)
        self.ordenes_compra.append(orden)
        return orden

    # ---------- Subasta en tiempo real ----------
    def ejecutar_subasta(self) -> list[dict]:
        """
        Empareja compras y ventas: prioriza mayor precio ofrecido por
        el comprador y menor precio pedido por el vendedor (mejor precio
        primero), estilo libro de órdenes tipo bolsa de valores.
        """
        self.ordenes_venta.sort(key=lambda o: o.precio_kwh)          # vendedores más baratos primero
        self.ordenes_compra.sort(key=lambda o: -o.precio_kwh)        # compradores que más pagan primero

        transacciones = []
        for compra in list(self.ordenes_compra):
            for venta in list(self.ordenes_venta):
                if compra.precio_kwh >= venta.precio_kwh and compra.cantidad_kwh > 0 and venta.cantidad_kwh > 0:
                    cantidad = min(compra.cantidad_kwh, venta.cantidad_kwh)
                    precio_final = venta.precio_kwh  # el vendedor fija el precio de cierre
                    compra.cantidad_kwh -= cantidad
                    venta.cantidad_kwh -= cantidad

                    tx = {
                        "comprador": compra.usuario_id,
                        "vendedor": venta.usuario_id,
                        "cantidad_kwh": cantidad,
                        "precio_kwh": precio_final,
                        "total": round(cantidad * precio_final, 2),
                        "timestamp": datetime.now(),
                    }
                    transacciones.append(tx)
                    self.historial_transacciones.append(tx)

                    if compra.cantidad_kwh == 0:
                        break

        # limpiar órdenes completamente ejecutadas
        self.ordenes_venta = [o for o in self.ordenes_venta if o.cantidad_kwh > 0]
        self.ordenes_compra = [o for o in self.ordenes_compra if o.cantidad_kwh > 0]
        return transacciones

    # ---------- Integración con dispositivos IoT ----------
    def conectar_dispositivo(self, id_dispositivo: str, usuario_id: str, tipo: str) -> DispositivoIoT:
        dispositivo = DispositivoIoT(id_dispositivo, usuario_id, tipo)
        self.dispositivos[id_dispositivo] = dispositivo
        self.lecturas_iot.setdefault(id_dispositivo, [])
        return dispositivo

    def enviar_lectura_iot(self, id_dispositivo: str, valor_kwh: float) -> None:
        """Un dispositivo doméstico reporta producción/consumo a la plataforma."""
        if id_dispositivo not in self.dispositivos:
            raise ValueError(f"Dispositivo {id_dispositivo} no está registrado")
        self.lecturas_iot[id_dispositivo].append(valor_kwh)

    def simular_lecturas(self, id_dispositivo: str, n: int = 5) -> None:
        """Genera lecturas simuladas (para pruebas/demo)."""
        for _ in range(n):
            self.enviar_lectura_iot(id_dispositivo, round(random.uniform(0.5, 4.0), 2))

    # ---------- Predicción de producción y consumo ----------
    def predecir_siguiente_valor(self, id_dispositivo: str, ventana: int = 3) -> Optional[float]:
        """
        Predicción simple con media móvil sobre las últimas N lecturas.
        (Se puede sustituir por un modelo de series de tiempo más avanzado
        sin cambiar la interfaz pública del método.)
        """
        lecturas = self.lecturas_iot.get(id_dispositivo, [])
        if not lecturas:
            return None
        muestra = lecturas[-ventana:]
        return round(mean(muestra), 2)


# ---------------------------------------------------------------------------
# DEMO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Aunque se "cree" la plataforma en distintos lugares del código,
    # siempre es el mismo objeto:
    plataforma_a = PlataformaEnergia()
    plataforma_b = PlataformaEnergia()
    print("¿Misma instancia (Singleton)?:", plataforma_a is plataforma_b)

    plataforma = plataforma_a

    # Usuarios
    plataforma.registrar_usuario("u1", "Ana")
    plataforma.registrar_usuario("u2", "Luis")

    # IoT doméstico
    plataforma.conectar_dispositivo("panel-01", "u1", "panel_solar")
    plataforma.simular_lecturas("panel-01", n=5)
    print("Lecturas IoT (panel-01):", plataforma.lecturas_iot["panel-01"])
    print("Predicción próxima lectura:", plataforma.predecir_siguiente_valor("panel-01"))

    # Compra/venta de excedentes
    plataforma.publicar_venta("u1", cantidad_kwh=10, precio_kwh=0.15)
    plataforma.publicar_compra("u2", cantidad_kwh=6, precio_kwh=0.18)

    # Subasta en tiempo real
    resultado = plataforma.ejecutar_subasta()
    print("Transacciones ejecutadas en la subasta:")
    for tx in resultado:
        print(" -", tx)
