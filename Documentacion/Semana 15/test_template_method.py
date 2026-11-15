"""
Pruebas del patrón TEMPLATE METHOD — `template_method`.

Objetivo: verificar que el método plantilla `liquidar` fija el orden de los
pasos para todos los roles; que los pasos comunes (validar y filtrar el
periodo, sumar el bruto, armar el resumen) se comparten; que cada subclase
solo completa los pasos abstractos y los ganchos; y que una subclase que no
redefine los ganchos obtiene su comportamiento por defecto.
"""

import pytest

from template_method import (
    LIQUIDACIONES,
    LiquidacionComprador,
    LiquidacionPeriodo,
    LiquidacionVendedor,
    Movimiento,
    crear_liquidacion,
)

MOVIMIENTOS = [
    Movimiento("marta", "ana", 5, 2200, "2026-11-03T10:00"),
    Movimiento("marta", "luis", 1, 470, "2026-11-12T19:30"),
    Movimiento("ana", "luis", 2, 900, "2026-11-20T08:15"),
    Movimiento("marta", "ana", 4, 1800, "2026-10-28T12:00"),  # otro periodo
]


class LiquidacionSinCargos(LiquidacionPeriodo):
    """Subclase mínima: solo los pasos abstractos, ningún gancho."""

    rol = "prueba"

    def _es_suyo(self, movimiento, usuario):
        return usuario in (movimiento.comprador, movimiento.vendedor)

    def _concepto(self):
        return "Movido en el periodo"


# ---------------------------------------------------------------------------
# 1. Liquidación del comprador
# ---------------------------------------------------------------------------
class TestComprador:
    def test_solo_cuenta_sus_compras_del_periodo(self):
        liq = LiquidacionComprador().liquidar(MOVIMIENTOS, "marta", "2026-11")
        assert liq["movimientos"] == 2
        assert liq["energia_kwh"] == 6
        assert liq["bruto"] == 2670

    def test_suma_la_contribucion_de_red(self):
        liq = LiquidacionComprador().liquidar(MOVIMIENTOS, "marta", "2026-11")
        assert liq["cargos"] == [{"concepto": "Contribución por uso de red (2 %)", "valor": 53.4}]
        assert liq["neto"] == 2723.4
        assert liq["concepto"] == "Total a pagar"

    def test_sin_compras_liquida_en_cero(self):
        liq = LiquidacionComprador().liquidar(MOVIMIENTOS, "luis", "2026-11")
        assert (liq["movimientos"], liq["bruto"], liq["neto"]) == (0, 0, 0)


# ---------------------------------------------------------------------------
# 2. Liquidación del vendedor
# ---------------------------------------------------------------------------
class TestVendedor:
    def test_solo_cuenta_sus_ventas_del_periodo(self):
        liq = LiquidacionVendedor().liquidar(MOVIMIENTOS, "luis", "2026-11")
        assert liq["movimientos"] == 2
        assert liq["bruto"] == 1370

    def test_descuenta_comision_y_retencion(self):
        liq = LiquidacionVendedor().liquidar(MOVIMIENTOS, "ana", "2026-11")
        assert [c["valor"] for c in liq["cargos"]] == [66.0, 22.0]
        assert liq["neto"] == 2112.0
        assert liq["concepto"] == "Total a recibir"

    def test_el_mismo_usuario_liquida_distinto_segun_el_rol(self):
        como_comprador = LiquidacionComprador().liquidar(MOVIMIENTOS, "ana", "2026-11")
        como_vendedor = LiquidacionVendedor().liquidar(MOVIMIENTOS, "ana", "2026-11")
        assert como_comprador["bruto"] == 900
        assert como_vendedor["bruto"] == 2200


# ---------------------------------------------------------------------------
# 3. El método plantilla y los ganchos
# ---------------------------------------------------------------------------
class TestPlantilla:
    def test_la_clase_abstracta_no_se_puede_instanciar(self):
        with pytest.raises(TypeError):
            LiquidacionPeriodo()

    def test_subclase_incompleta_no_se_puede_instanciar(self):
        class SinConcepto(LiquidacionPeriodo):
            def _es_suyo(self, movimiento, usuario):
                return True

        with pytest.raises(TypeError):
            SinConcepto()

    def test_los_ganchos_tienen_comportamiento_por_defecto(self):
        liq = LiquidacionSinCargos().liquidar(MOVIMIENTOS, "ana", "2026-11")
        assert liq["cargos"] == []
        assert liq["neto"] == liq["bruto"] == 3100

    def test_las_subclases_no_redefinen_el_metodo_plantilla(self):
        for clase in (LiquidacionComprador, LiquidacionVendedor, LiquidacionSinCargos):
            assert "liquidar" not in vars(clase)
            assert clase.liquidar is LiquidacionPeriodo.liquidar

    def test_el_orden_de_los_pasos_es_fijo(self):
        llamadas = []

        class Espia(LiquidacionVendedor):
            def _es_suyo(self, m, u):
                llamadas.append("es_suyo")
                return super()._es_suyo(m, u)

            def _cargos(self, bruto):
                llamadas.append("cargos")
                return super()._cargos(bruto)

            def _signo_neto(self):
                llamadas.append("signo_neto")
                return super()._signo_neto()

            def _concepto(self):
                llamadas.append("concepto")
                return super()._concepto()

        Espia().liquidar(MOVIMIENTOS, "ana", "2026-11")
        assert llamadas == ["es_suyo"] * 3 + ["cargos", "signo_neto", "concepto"]

    @pytest.mark.parametrize("periodo", ["2026-13", "2026/11", "nov-2026", ""])
    def test_periodo_invalido_falla_en_el_primer_paso(self, periodo):
        with pytest.raises(ValueError, match="AAAA-MM"):
            LiquidacionComprador().liquidar(MOVIMIENTOS, "marta", periodo)

    def test_otro_periodo_cambia_el_resultado(self):
        liq = LiquidacionComprador().liquidar(MOVIMIENTOS, "marta", "2026-10")
        assert liq["bruto"] == 1800

    @pytest.mark.parametrize("rol", list(LIQUIDACIONES))
    def test_crear_liquidacion_por_rol(self, rol):
        assert crear_liquidacion(rol).rol == rol

    def test_rol_desconocido_falla(self):
        with pytest.raises(ValueError, match="no soportado"):
            crear_liquidacion("operador")
