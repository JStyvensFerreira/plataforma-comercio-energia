"""
Pruebas del patrón DECORATOR — `decorator`.

Objetivo: verificar que cada ajuste de precio envuelve a otro `CostoEnergia`
compartiendo su interfaz, que delega en el componente y añade su propia capa,
que los ajustes se apilan en tiempo de ejecución en cualquier combinación sin
modificar el objeto base, que el orden de aplicación importa, y que el
registro resuelve los ajustes por nombre con el mismo contrato que las demás
fábricas del proyecto.
"""

from itertools import combinations

import pytest

from decorator import (
    AJUSTES_DISPONIBLES,
    AjusteCosto,
    CargoUsoRed,
    ComisionPlataforma,
    CostoBase,
    CostoEnergia,
    DescuentoCompradorFrecuente,
    DescuentoEnergiaRenovable,
    RecargoHoraPico,
    aplicar_ajustes,
    obtener_ajuste,
)


@pytest.fixture
def base():
    return CostoBase(cantidad_kwh=10, precio_kwh=0.20)  # total = 2.00


# ---------------------------------------------------------------------------
# 1. Interfaz común (Component)
# ---------------------------------------------------------------------------
class TestInterfazComun:
    def test_no_se_puede_instanciar_el_componente_abstracto(self):
        with pytest.raises(TypeError):
            CostoEnergia()

    def test_base_y_decoradores_implementan_costo_energia(self, base):
        assert isinstance(base, CostoEnergia)
        assert isinstance(ComisionPlataforma(base), CostoEnergia)

    def test_el_decorador_base_solo_delega(self, base):
        assert AjusteCosto(base).total() == base.total()


# ---------------------------------------------------------------------------
# 2. Concrete Component
# ---------------------------------------------------------------------------
class TestCostoBase:
    def test_total_es_cantidad_por_precio(self, base):
        assert base.total() == 2.0

    def test_desglose_tiene_una_sola_linea(self, base):
        assert len(base.desglose()) == 1
        assert base.desglose()[0]["acumulado"] == 2.0


# ---------------------------------------------------------------------------
# 3. Concrete Decorators: cada uno añade su capa
# ---------------------------------------------------------------------------
class TestDecoradoresConcretos:
    @pytest.mark.parametrize(
        "decorador, esperado",
        [
            (DescuentoEnergiaRenovable, 1.80),
            (DescuentoCompradorFrecuente, 1.90),
            (RecargoHoraPico, 2.30),
            (CargoUsoRed, 2.20),
            (ComisionPlataforma, 2.10),
        ],
    )
    def test_cada_ajuste_modifica_el_total(self, base, decorador, esperado):
        assert decorador(base).total() == esperado

    def test_cada_ajuste_agrega_una_linea_al_desglose(self, base):
        lineas = ComisionPlataforma(base).desglose()
        assert len(lineas) == 2
        assert "Comisión" in lineas[-1]["concepto"]


# ---------------------------------------------------------------------------
# 4. Composición dinámica
# ---------------------------------------------------------------------------
class TestComposicion:
    def test_los_ajustes_se_apilan(self, base):
        costo = ComisionPlataforma(RecargoHoraPico(DescuentoEnergiaRenovable(base)))
        # 2.00 → 1.80 → 2.07 → 2.17
        assert costo.total() == 2.17

    def test_el_desglose_sigue_el_orden_de_envoltura(self, base):
        costo = ComisionPlataforma(RecargoHoraPico(base))
        conceptos = [l["concepto"] for l in costo.desglose()]
        assert "Recargo" in conceptos[1] and "Comisión" in conceptos[2]

    def test_el_ultimo_acumulado_coincide_con_el_total(self, base):
        costo = CargoUsoRed(DescuentoCompradorFrecuente(base))
        assert costo.desglose()[-1]["acumulado"] == costo.total()

    def test_decorar_no_modifica_el_objeto_base(self, base):
        ComisionPlataforma(RecargoHoraPico(base))
        assert base.total() == 2.0

    def test_el_mismo_ajuste_se_puede_aplicar_dos_veces(self, base):
        assert CargoUsoRed(CargoUsoRed(base)).total() == 2.40

    def test_el_decorado_no_es_el_objeto_base(self, base):
        # desventaja vista en clase: la identidad del objeto cambia
        decorado = ComisionPlataforma(base)
        assert decorado is not base
        assert not isinstance(decorado, CostoBase)
        assert decorado.componente is base

    def test_el_orden_de_los_ajustes_importa(self, base):
        assert aplicar_ajustes(base, ["uso_red", "renovable"]).total() == 1.98
        assert aplicar_ajustes(base, ["renovable", "uso_red"]).total() == 2.00

    def test_cinco_clases_cubren_las_32_combinaciones(self, base):
        # con herencia serían 2^5 = 32 clases; aquí bastan las 5 decoradoras
        costos = [
            aplicar_ajustes(base, combo)
            for n in range(len(AJUSTES_DISPONIBLES) + 1)
            for combo in combinations(AJUSTES_DISPONIBLES, n)
        ]
        assert len(costos) == 32
        assert all(c.total() > 0 for c in costos)
        assert len({c.total() for c in costos}) > 20  # combinaciones realmente distintas


# ---------------------------------------------------------------------------
# 5. Registro de ajustes
# ---------------------------------------------------------------------------
class TestRegistro:
    def test_devuelve_la_clase_decoradora_por_nombre(self):
        assert obtener_ajuste("comision") is ComisionPlataforma
        assert obtener_ajuste("uso_red") is CargoUsoRed

    def test_ajuste_no_soportado_lanza_value_error_con_los_disponibles(self):
        with pytest.raises(ValueError, match="comision"):
            obtener_ajuste("cupon")

    def test_ajustes_disponibles_coincide_con_el_registro(self):
        assert set(AJUSTES_DISPONIBLES) == {"renovable", "frecuente", "hora_pico", "uso_red", "comision"}

    def test_sin_ajustes_devuelve_el_mismo_costo_base(self, base):
        assert aplicar_ajustes(base, []) is base

    def test_se_puede_agregar_un_ajuste_sin_modificar_los_existentes(self, base):
        class SubsidioEstrato(AjusteCosto):
            etiqueta = "Subsidio estrato 1 (-$0.50)"

            def _valor_ajuste(self, subtotal):
                return -0.50

        assert ComisionPlataforma(SubsidioEstrato(base)).total() == 1.58
