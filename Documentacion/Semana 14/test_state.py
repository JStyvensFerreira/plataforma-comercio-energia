"""
Pruebas del patrón STATE — `state`.

Objetivo: verificar que la orden (Context) cambia de comportamiento según su
estado, que cada estado concreto decide sus transiciones (Abierta →
Parcial → Completada, cancelación solo mientras sea negociable), que los
estados finales rechazan cualquier operación, y que el historial de estados
queda registrado.
"""

import pytest

from state import (
    ABIERTA,
    CANCELADA,
    COMPLETADA,
    PARCIAL,
    EstadoOrden,
    Orden,
    TransicionInvalida,
)


def nueva_orden(cantidad=10):
    return Orden(1, "ana", "venta", cantidad, 450)


# ---------------------------------------------------------------------------
# 1. Transiciones válidas
# ---------------------------------------------------------------------------
class TestTransiciones:
    def test_una_orden_nueva_empieza_abierta(self):
        assert nueva_orden().estado is ABIERTA

    def test_ejecucion_parcial_pasa_a_parcial(self):
        orden = nueva_orden()
        orden.ejecutar(4)
        assert orden.estado is PARCIAL
        assert orden.cantidad_kwh == 6

    def test_ejecutar_todo_desde_abierta_pasa_a_completada(self):
        orden = nueva_orden()
        orden.ejecutar(10)
        assert orden.estado is COMPLETADA

    def test_ejecutar_el_resto_desde_parcial_pasa_a_completada(self):
        orden = nueva_orden()
        orden.ejecutar(4)
        orden.ejecutar(6)
        assert orden.estado is COMPLETADA and orden.cantidad_kwh == 0

    def test_varias_ejecuciones_parciales_siguen_en_parcial(self):
        orden = nueva_orden()
        orden.ejecutar(2)
        orden.ejecutar(3)
        assert orden.estado is PARCIAL and orden.cantidad_kwh == 5

    def test_cancelar_una_orden_abierta(self):
        orden = nueva_orden()
        orden.cancelar()
        assert orden.estado is CANCELADA

    def test_cancelar_una_orden_parcial_conserva_lo_ya_ejecutado(self):
        orden = nueva_orden()
        orden.ejecutar(4)
        orden.cancelar()
        assert orden.estado is CANCELADA
        assert orden.cantidad_inicial - orden.cantidad_kwh == 4

    def test_cantidades_decimales_no_dejan_residuos(self):
        orden = nueva_orden(0.3)
        orden.ejecutar(0.1)
        orden.ejecutar(0.2)
        assert orden.estado is COMPLETADA


# ---------------------------------------------------------------------------
# 2. Operaciones rechazadas
# ---------------------------------------------------------------------------
class TestRechazos:
    def test_una_orden_completada_no_se_puede_ejecutar(self):
        orden = nueva_orden()
        orden.ejecutar(10)
        with pytest.raises(TransicionInvalida):
            orden.ejecutar(1)

    def test_una_orden_completada_no_se_puede_cancelar(self):
        orden = nueva_orden()
        orden.ejecutar(10)
        with pytest.raises(TransicionInvalida):
            orden.cancelar()

    def test_una_orden_cancelada_no_se_puede_ejecutar(self):
        orden = nueva_orden()
        orden.cancelar()
        with pytest.raises(TransicionInvalida):
            orden.ejecutar(1)

    def test_una_orden_cancelada_no_se_puede_cancelar_otra_vez(self):
        orden = nueva_orden()
        orden.cancelar()
        with pytest.raises(TransicionInvalida):
            orden.cancelar()

    def test_no_se_puede_ejecutar_mas_de_lo_pendiente(self):
        orden = nueva_orden()
        with pytest.raises(ValueError):
            orden.ejecutar(11)
        assert orden.estado is ABIERTA and orden.cantidad_kwh == 10

    def test_no_se_puede_ejecutar_una_cantidad_no_positiva(self):
        orden = nueva_orden()
        with pytest.raises(ValueError):
            orden.ejecutar(0)


# ---------------------------------------------------------------------------
# 3. Comportamiento delegado e historial
# ---------------------------------------------------------------------------
class TestComportamiento:
    @pytest.mark.parametrize(
        "pasos, esperado",
        [([], True), ([4], True), ([10], False), (["cancelar"], False)],
    )
    def test_puede_negociar_depende_del_estado(self, pasos, esperado):
        orden = nueva_orden()
        for paso in pasos:
            orden.cancelar() if paso == "cancelar" else orden.ejecutar(paso)
        assert orden.puede_negociar() is esperado

    def test_el_historial_registra_cada_transicion(self):
        orden = nueva_orden()
        orden.ejecutar(4)
        orden.ejecutar(6)
        assert orden.historial_estados == ["abierta", "parcial", "completada"]

    def test_un_rechazo_no_agrega_entradas_al_historial(self):
        orden = nueva_orden()
        orden.cancelar()
        with pytest.raises(TransicionInvalida):
            orden.ejecutar(1)
        assert orden.historial_estados == ["abierta", "cancelada"]

    def test_los_estados_son_compartidos_entre_ordenes(self):
        a, b = nueva_orden(), Orden(2, "luis", "compra", 3, 500)
        assert a.estado is b.estado

    def test_transicion_invalida_es_un_value_error(self):
        assert issubclass(TransicionInvalida, ValueError)

    def test_no_se_puede_instanciar_el_estado_abstracto(self):
        with pytest.raises(TypeError):
            EstadoOrden()
