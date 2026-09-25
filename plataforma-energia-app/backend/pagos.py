"""
Plataforma de Comercio de Energía — pasarelas de pago externas (patrón
Adapter). Consumido por plataforma.py (cobrar_transaccion).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import itertools


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
