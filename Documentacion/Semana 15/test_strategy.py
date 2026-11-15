"""
Pruebas del patrón STRATEGY — `strategy`.

Objetivo: verificar que cada regla de precio de cierre está encapsulada en
su propia estrategia; que el motor de subasta (Context) delega el precio en
la estrategia configurada sin conocer cuál es; que la estrategia se puede
cambiar en tiempo de ejecución; y que el emparejamiento (qué órdenes se
cruzan y cuántos kWh) no depende de la estrategia elegida.
"""

import pytest

from strategy import (
    ESTRATEGIAS,
    EstrategiaPrecio,
    MotorSubasta,
    Orden,
    PrecioComprador,
    PrecioPuntoMedio,
    PrecioVendedor,
    crear_estrategia,
)


def libro():
    return [
        Orden("ana", "venta", 5, 440),
        Orden("luis", "venta", 3, 470),
        Orden("marta", "compra", 6, 500),
    ]


COMPRA = Orden("marta", "compra", 1, 500)
VENTA = Orden("ana", "venta", 1, 440)


# ---------------------------------------------------------------------------
# 1. Estrategias concretas
# ---------------------------------------------------------------------------
class TestEstrategias:
    def test_precio_vendedor_cobra_lo_que_pide_la_venta(self):
        assert PrecioVendedor().precio_cierre(COMPRA, VENTA) == 440

    def test_precio_comprador_cobra_lo_que_ofrece_la_compra(self):
        assert PrecioComprador().precio_cierre(COMPRA, VENTA) == 500

    def test_punto_medio_reparte_la_diferencia(self):
        assert PrecioPuntoMedio().precio_cierre(COMPRA, VENTA) == 470

    def test_punto_medio_redondea_a_dos_decimales(self):
        compra = Orden("m", "compra", 1, 0.211)
        venta = Orden("a", "venta", 1, 0.14)
        assert PrecioPuntoMedio().precio_cierre(compra, venta) == 0.18

    @pytest.mark.parametrize("estrategia", [PrecioVendedor(), PrecioComprador(), PrecioPuntoMedio()])
    def test_el_precio_queda_entre_venta_y_compra(self, estrategia):
        assert VENTA.precio_kwh <= estrategia.precio_cierre(COMPRA, VENTA) <= COMPRA.precio_kwh

    @pytest.mark.parametrize("nombre", list(ESTRATEGIAS))
    def test_todas_cumplen_la_interfaz_y_tienen_descripcion(self, nombre):
        estrategia = crear_estrategia(nombre)
        assert isinstance(estrategia, EstrategiaPrecio)
        assert estrategia.nombre == nombre and estrategia.descripcion

    def test_la_interfaz_no_se_puede_instanciar(self):
        with pytest.raises(TypeError):
            EstrategiaPrecio()

    def test_estrategia_desconocida_falla(self):
        with pytest.raises(ValueError, match="no soportada"):
            crear_estrategia("subasta_holandesa")


# ---------------------------------------------------------------------------
# 2. Context: el motor de subasta delega el precio
# ---------------------------------------------------------------------------
class TestMotorSubasta:
    def test_usa_la_estrategia_inyectada(self):
        txs = MotorSubasta(PrecioComprador()).ejecutar(libro())
        assert {tx.precio_kwh for tx in txs} == {500}
        assert {tx.estrategia for tx in txs} == {"comprador"}

    def test_cambiar_la_estrategia_en_caliente(self):
        motor = MotorSubasta(PrecioVendedor())
        antes = [tx.precio_kwh for tx in motor.ejecutar(libro())]
        motor.estrategia = PrecioPuntoMedio()
        despues = [tx.precio_kwh for tx in motor.ejecutar(libro())]
        assert antes == [440, 470]
        assert despues == [470, 485]

    def test_rechaza_algo_que_no_es_estrategia(self):
        with pytest.raises(TypeError):
            MotorSubasta(lambda c, v: 1)

    def test_el_emparejamiento_no_depende_de_la_estrategia(self):
        cruces = {
            nombre: [(tx.vendedor, tx.comprador, tx.cantidad_kwh) for tx in MotorSubasta(crear_estrategia(nombre)).ejecutar(libro())]
            for nombre in ESTRATEGIAS
        }
        assert len({tuple(c) for c in cruces.values()}) == 1
        assert cruces["vendedor"] == [("ana", "marta", 5), ("luis", "marta", 1)]

    def test_la_venta_mas_barata_se_cruza_primero(self):
        txs = MotorSubasta(PrecioVendedor()).ejecutar(libro())
        assert txs[0].vendedor == "ana"

    def test_no_cruza_si_la_venta_es_mas_cara(self):
        ordenes = [Orden("ana", "venta", 5, 600), Orden("marta", "compra", 5, 500)]
        assert MotorSubasta(PrecioVendedor()).ejecutar(ordenes) == []

    def test_descuenta_las_cantidades_ejecutadas(self):
        ordenes = libro()
        MotorSubasta(PrecioVendedor()).ejecutar(ordenes)
        assert [o.cantidad_kwh for o in ordenes] == [0, 2, 0]

    def test_total_de_la_transaccion(self):
        tx = MotorSubasta(PrecioPuntoMedio()).ejecutar(libro())[0]
        assert tx.total == 5 * 470

    @pytest.mark.parametrize("tipo, cantidad, precio", [("trueque", 1, 1), ("venta", 0, 1), ("compra", 1, -5)])
    def test_orden_invalida(self, tipo, cantidad, precio):
        with pytest.raises(ValueError):
            Orden("x", tipo, cantidad, precio)
