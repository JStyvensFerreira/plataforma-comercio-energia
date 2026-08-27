"""
Plataforma de Comercio de Energía — lógica de dominio (patrón Singleton).
Este módulo es consumido por main.py (API FastAPI).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from statistics import mean
from threading import Lock
from typing import Optional
import itertools
import random


class SingletonMeta(type):
    """Metaclase que garantiza una única instancia, segura ante concurrencia."""
    _instances: dict[type, object] = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


@dataclass
class Usuario:
    id: str
    nombre: str
    password_hash: str = ""
    balance_kwh: float = 0.0

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre, "balance_kwh": self.balance_kwh}


@dataclass
class Orden:
    id: int
    usuario_id: str
    tipo: str
    cantidad_kwh: float
    precio_kwh: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


@dataclass
class DispositivoIoT:
    id: str
    usuario_id: str
    tipo: str

    def to_dict(self):
        return asdict(self)


class PlataformaEnergia(metaclass=SingletonMeta):
    """Punto único de acceso al sistema de comercio de energía."""

    def __init__(self):
        self.usuarios: dict[str, Usuario] = {}
        self.dispositivos: dict[str, DispositivoIoT] = {}
        self.ordenes_venta: list[Orden] = []
        self.ordenes_compra: list[Orden] = []
        self.historial_transacciones: list[dict] = []
        self.lecturas_iot: dict[str, list[float]] = {}
        self._contador_ordenes = itertools.count(1)

    def registrar_usuario(self, id_: str, nombre: str, password_hash: str = "") -> Usuario:
        return self.usuarios.setdefault(id_, Usuario(id_, nombre, password_hash))

    def publicar_venta(self, usuario_id: str, cantidad_kwh: float, precio_kwh: float) -> Orden:
        orden = Orden(next(self._contador_ordenes), usuario_id, "venta", cantidad_kwh, precio_kwh)
        self.ordenes_venta.append(orden)
        return orden

    def publicar_compra(self, usuario_id: str, cantidad_kwh: float, precio_kwh: float) -> Orden:
        orden = Orden(next(self._contador_ordenes), usuario_id, "compra", cantidad_kwh, precio_kwh)
        self.ordenes_compra.append(orden)
        return orden

    def ejecutar_subasta(self) -> list[dict]:
        self.ordenes_venta.sort(key=lambda o: o.precio_kwh)
        self.ordenes_compra.sort(key=lambda o: -o.precio_kwh)

        transacciones = []
        for compra in list(self.ordenes_compra):
            for venta in list(self.ordenes_venta):
                if compra.precio_kwh >= venta.precio_kwh and compra.cantidad_kwh > 0 and venta.cantidad_kwh > 0:
                    cantidad = min(compra.cantidad_kwh, venta.cantidad_kwh)
                    precio_final = venta.precio_kwh
                    compra.cantidad_kwh -= cantidad
                    venta.cantidad_kwh -= cantidad

                    tx = {
                        "comprador": compra.usuario_id,
                        "vendedor": venta.usuario_id,
                        "cantidad_kwh": cantidad,
                        "precio_kwh": precio_final,
                        "total": round(cantidad * precio_final, 2),
                        "timestamp": datetime.now().isoformat(),
                    }
                    transacciones.append(tx)
                    self.historial_transacciones.append(tx)

                    if compra.cantidad_kwh == 0:
                        break

        self.ordenes_venta = [o for o in self.ordenes_venta if o.cantidad_kwh > 0]
        self.ordenes_compra = [o for o in self.ordenes_compra if o.cantidad_kwh > 0]
        return transacciones

    def conectar_dispositivo(self, id_dispositivo: str, usuario_id: str, tipo: str) -> DispositivoIoT:
        dispositivo = DispositivoIoT(id_dispositivo, usuario_id, tipo)
        self.dispositivos[id_dispositivo] = dispositivo
        self.lecturas_iot.setdefault(id_dispositivo, [])
        return dispositivo

    def enviar_lectura_iot(self, id_dispositivo: str, valor_kwh: float) -> None:
        if id_dispositivo not in self.dispositivos:
            raise ValueError(f"Dispositivo {id_dispositivo} no está registrado")
        self.lecturas_iot[id_dispositivo].append(valor_kwh)

    def simular_lecturas(self, id_dispositivo: str, n: int = 5) -> None:
        for _ in range(n):
            self.enviar_lectura_iot(id_dispositivo, round(random.uniform(0.5, 4.0), 2))

    def predecir_siguiente_valor(self, id_dispositivo: str, ventana: int = 3) -> Optional[float]:
        lecturas = self.lecturas_iot.get(id_dispositivo, [])
        if not lecturas:
            return None
        return round(mean(lecturas[-ventana:]), 2)
