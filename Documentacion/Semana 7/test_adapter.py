"""
Pruebas del patrón ADAPTER — `adapter`.

Objetivo: verificar que la plataforma puede cobrar con distintas pasarelas
externas de interfaz incompatible (Stripe, PayU) programando solo contra
`PasarelaPago`, que cada adaptador traduce correctamente la llamada al SDK
concreto y su respuesta al contrato uniforme `ResultadoPago`, y que el
registro de pasarelas resuelve por nombre con el mismo contrato que las
demás fábricas del proyecto.
"""

import pytest

from adapter import (
    AdaptadorPayU,
    AdaptadorStripe,
    PASARELAS_DISPONIBLES,
    PasarelaPago,
    PayUAPI,
    ResultadoPago,
    StripeAPI,
    obtener_pasarela,
)


# ---------------------------------------------------------------------------
# Dobles de prueba: espían qué le llega exactamente al SDK simulado
# ---------------------------------------------------------------------------
class _StripeEspia(StripeAPI):
    def __init__(self):
        self.ultimo_amount_cents = None

    def create_charge(self, amount_cents, currency, metadata):
        self.ultimo_amount_cents = amount_cents
        return super().create_charge(amount_cents, currency, metadata)


class _PayUEspia(PayUAPI):
    def __init__(self, estado="APPROVED"):
        self.ultimo_monto = None
        self._estado = estado

    def generar_transaccion(self, monto, moneda, referencia):
        self.ultimo_monto = monto
        return {
            "ordenId": "PAYU-TEST",
            "estado": self._estado,
            "valor": monto,
            "moneda": moneda,
            "referencia": referencia,
        }


# ---------------------------------------------------------------------------
# 1. Interfaz uniforme (Target)
# ---------------------------------------------------------------------------
class TestInterfazUniforme:
    def test_adaptador_stripe_implementa_pasarela_pago(self):
        assert isinstance(AdaptadorStripe(), PasarelaPago)

    def test_adaptador_payu_implementa_pasarela_pago(self):
        assert isinstance(AdaptadorPayU(), PasarelaPago)

    def test_no_se_puede_instanciar_la_interfaz_abstracta(self):
        with pytest.raises(TypeError):
            PasarelaPago()

    def test_ambos_adaptadores_devuelven_resultadopago(self):
        r1 = AdaptadorStripe().procesar_pago("u1", 10.0, "venta")
        r2 = AdaptadorPayU().procesar_pago("u1", 10.0, "venta")
        assert isinstance(r1, ResultadoPago)
        assert isinstance(r2, ResultadoPago)


# ---------------------------------------------------------------------------
# 2. AdaptadorStripe traduce correctamente hacia/desde StripeAPI
# ---------------------------------------------------------------------------
class TestAdaptadorStripe:
    def test_convierte_el_monto_a_centavos_para_el_sdk(self):
        espia = _StripeEspia()
        AdaptadorStripe(espia).procesar_pago("u1", 12.5, "venta")
        assert espia.ultimo_amount_cents == 1250

    def test_marca_exitoso_cuando_el_sdk_confirma_el_cargo(self):
        resultado = AdaptadorStripe(StripeAPI()).procesar_pago("u1", 10.0, "venta")
        assert resultado.exitoso is True

    def test_expone_el_id_de_transaccion_del_sdk(self):
        resultado = AdaptadorStripe(StripeAPI()).procesar_pago("u1", 10.0, "venta")
        assert resultado.id_transaccion_externa.startswith("ch_")

    def test_identifica_la_pasarela_como_stripe(self):
        resultado = AdaptadorStripe(StripeAPI()).procesar_pago("u1", 10.0, "venta")
        assert resultado.pasarela == "stripe"


# ---------------------------------------------------------------------------
# 3. AdaptadorPayU traduce correctamente hacia/desde PayUAPI
# ---------------------------------------------------------------------------
class TestAdaptadorPayU:
    def test_envia_el_monto_en_pesos_sin_convertir(self):
        espia = _PayUEspia()
        AdaptadorPayU(espia).procesar_pago("u1", 45000.0, "venta")
        assert espia.ultimo_monto == 45000.0

    def test_marca_exitoso_cuando_el_sdk_aprueba(self):
        resultado = AdaptadorPayU(PayUAPI()).procesar_pago("u1", 10.0, "venta")
        assert resultado.exitoso is True

    def test_expone_el_id_de_orden_del_sdk(self):
        resultado = AdaptadorPayU(PayUAPI()).procesar_pago("u1", 10.0, "venta")
        assert resultado.id_transaccion_externa.startswith("PAYU-")

    def test_identifica_la_pasarela_como_payu(self):
        resultado = AdaptadorPayU(PayUAPI()).procesar_pago("u1", 10.0, "venta")
        assert resultado.pasarela == "payu"

    def test_marca_no_exitoso_si_el_sdk_rechaza(self):
        espia = _PayUEspia(estado="REJECTED")
        resultado = AdaptadorPayU(espia).procesar_pago("u1", 10.0, "venta")
        assert resultado.exitoso is False


# ---------------------------------------------------------------------------
# 4. Registro de pasarelas
# ---------------------------------------------------------------------------
class TestRegistroDePasarelas:
    def test_devuelve_el_adaptador_correcto_por_nombre(self):
        assert isinstance(obtener_pasarela("stripe"), AdaptadorStripe)
        assert isinstance(obtener_pasarela("payu"), AdaptadorPayU)

    def test_pasarela_no_soportada_lanza_value_error_con_las_disponibles(self):
        with pytest.raises(ValueError, match="stripe"):
            obtener_pasarela("mercadopago")

    def test_pasarelas_disponibles_coincide_con_el_registro(self):
        assert set(PASARELAS_DISPONIBLES) == {"stripe", "payu"}

    def test_se_puede_agregar_una_pasarela_sin_modificar_las_existentes(self):
        class AdaptadorFalso(PasarelaPago):
            nombre = "falso"

            def procesar_pago(self, usuario_id, monto, concepto):
                return ResultadoPago(True, "FAKE-1", self.nombre, monto)

        resultado = AdaptadorFalso().procesar_pago("u1", 5.0, "venta")
        assert resultado.exitoso is True
        assert resultado.pasarela == "falso"
