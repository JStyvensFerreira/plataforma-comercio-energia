"""
Plataforma de Comercio de Energía
==================================
Implementa el requerimiento #16:
  - Compra/venta de excedentes energéticos entre usuarios
  - Sistema de subastas en tiempo real
  - Integración con dispositivos IoT domésticos
  - Predicción de producción y consumo

Patrón aplicado: ADAPTER (Adaptador)
-------------------------------------
Las transacciones que cierra la subasta (Singleton) calculan un `total` en
dinero, pero la plataforma nunca lo cobra de verdad: falta conectar una
pasarela de pagos externa (PayU, Stripe...) para cobrarle al comprador.

El problema es que cada pasarela expone su propio SDK, con nombres de
método y formatos de request/response incompatibles entre sí:
  - Stripe: create_charge(amount_cents, currency, metadata) -> StripeCharge
  - PayU:   generar_transaccion(monto, moneda, referencia) -> dict con
            claves propias y sus propios códigos de estado

Si la plataforma llamara directamente a esos SDKs, terminaría con
condicionales repartidos por todo el código decidiendo "si es Stripe hago
esto, si es PayU hago esto otro", y cambiar de pasarela (o soportar varias)
obligaría a tocar la lógica de negocio en cada punto donde se cobra.

Con ADAPTER, la plataforma programa contra una única interfaz propia
(`PasarelaPago`) y cada SDK externo (el "Adaptee") se envuelve en un
Adapter (`AdaptadorStripe`, `AdaptadorPayU`) que traduce esa llamada
uniforme a la forma particular que cada SDK espera. La plataforma nunca
conoce Stripe ni PayU directamente.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import itertools


# ---------------------------------------------------------------------------
# TARGET — interfaz que la plataforma ya espera
# ---------------------------------------------------------------------------
@dataclass
class ResultadoPago:
    """Objeto de valor uniforme que devuelve cualquier pasarela adaptada."""

    exitoso: bool
    id_transaccion_externa: str
    pasarela: str
    monto: float
    mensaje: str = ""


class PasarelaPago(ABC):
    """Target: interfaz uniforme que PlataformaEnergia consume."""

    @abstractmethod
    def procesar_pago(self, usuario_id: str, monto: float, concepto: str) -> ResultadoPago:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# ADAPTEES — SDKs externos simulados, con interfaces incompatibles entre sí
# ---------------------------------------------------------------------------
@dataclass
class StripeCharge:
    id: str
    status: str
    amount: int
    currency: str


class StripeAPI:
    """Simulación del SDK real de Stripe: trabaja en centavos y en inglés."""

    _contador = itertools.count(1)

    def create_charge(self, amount_cents: int, currency: str, metadata: dict) -> StripeCharge:
        return StripeCharge(
            id=f"ch_{next(self._contador):06d}",
            status="succeeded",
            amount=amount_cents,
            currency=currency,
        )

    def is_charge_successful(self, charge: StripeCharge) -> bool:
        return charge.status == "succeeded"


class PayUAPI:
    """
    Simulación del SDK real de PayU: trabaja en pesos y en español, y
    reporta el resultado con sus propias claves y códigos de estado.
    """

    _contador = itertools.count(1)

    def generar_transaccion(self, monto: float, moneda: str, referencia: str) -> dict:
        return {
            "ordenId": f"PAYU-{next(self._contador):06d}",
            "estado": "APPROVED",
            "valor": monto,
            "moneda": moneda,
            "referencia": referencia,
        }

    def consultar_estado(self, orden_id: str) -> str:
        return "APPROVED"


# ---------------------------------------------------------------------------
# ADAPTERS — traducen cada Adaptee a la interfaz PasarelaPago
# ---------------------------------------------------------------------------
class AdaptadorStripe(PasarelaPago):
    """Adapta StripeAPI (centavos, inglés) a la interfaz PasarelaPago."""

    nombre = "stripe"

    def __init__(self, api: Optional[StripeAPI] = None) -> None:
        self._api = api or StripeAPI()

    def procesar_pago(self, usuario_id: str, monto: float, concepto: str) -> ResultadoPago:
        centavos = round(monto * 100)
        charge = self._api.create_charge(
            amount_cents=centavos,
            currency="usd",
            metadata={"usuario_id": usuario_id, "concepto": concepto},
        )
        exitoso = self._api.is_charge_successful(charge)
        return ResultadoPago(
            exitoso=exitoso,
            id_transaccion_externa=charge.id,
            pasarela=self.nombre,
            monto=monto,
            mensaje="Pago procesado" if exitoso else "Pago rechazado",
        )


class AdaptadorPayU(PasarelaPago):
    """Adapta PayUAPI (pesos, español, dict con claves propias) a PasarelaPago."""

    nombre = "payu"

    def __init__(self, api: Optional[PayUAPI] = None) -> None:
        self._api = api or PayUAPI()

    def procesar_pago(self, usuario_id: str, monto: float, concepto: str) -> ResultadoPago:
        respuesta = self._api.generar_transaccion(monto=monto, moneda="COP", referencia=concepto)
        exitoso = respuesta["estado"] == "APPROVED"
        return ResultadoPago(
            exitoso=exitoso,
            id_transaccion_externa=respuesta["ordenId"],
            pasarela=self.nombre,
            monto=monto,
            mensaje="Pago procesado" if exitoso else "Pago rechazado",
        )


# ---------------------------------------------------------------------------
# Registro de pasarelas disponibles
# ---------------------------------------------------------------------------
_PASARELAS: dict[str, type[PasarelaPago]] = {
    "stripe": AdaptadorStripe,
    "payu": AdaptadorPayU,
}

PASARELAS_DISPONIBLES = tuple(_PASARELAS)


def obtener_pasarela(nombre: str) -> PasarelaPago:
    """
    Punto único donde se resuelve qué adaptador concreto usar según el
    nombre de la pasarela. Una pasarela desconocida lanza `ValueError` con
    las disponibles.
    """
    try:
        return _PASARELAS[nombre]()
    except KeyError:
        disponibles = ", ".join(_PASARELAS)
        raise ValueError(f"Pasarela de pago '{nombre}' no soportada. Disponibles: {disponibles}")


# ---------------------------------------------------------------------------
# DEMO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("La plataforma programa contra PasarelaPago, sin conocer Stripe ni PayU:\n")
    for nombre in PASARELAS_DISPONIBLES:
        pasarela = obtener_pasarela(nombre)
        resultado = pasarela.procesar_pago("u1", 12.50, "Venta de excedente energético")
        print(f"[{nombre}] {resultado}")

    print("\nPasarela no soportada:")
    try:
        obtener_pasarela("mercadopago")
    except ValueError as e:
        print(" ", e)
