"""
Pruebas del patrón MEMENTO — `memento`.

Objetivo: verificar que la configuración del hogar (Originator) se guarda y
restaura mediante mementos inmutables; que el historial (Caretaker) permite
deshacer y rehacer sin conocer el contenido de los mementos; que un cambio
inválido no altera nada ni deja respaldo; que un cambio nuevo invalida el
rehacer; y que el historial respeta su límite de versiones.
"""

import dataclasses

import pytest

from memento import (
    ConfiguracionHogar,
    HistorialConfiguracion,
    MementoConfiguracion,
    SinVersiones,
)

INICIAL = {
    "reserva_minima_pct": 20.0,
    "precio_venta_kwh": 450.0,
    "precio_compra_max_kwh": 520.0,
    "vender_excedente": True,
}


@pytest.fixture
def config():
    return ConfiguracionHogar()


@pytest.fixture
def historial(config):
    return HistorialConfiguracion(config)


# ---------------------------------------------------------------------------
# 1. Originator y Memento
# ---------------------------------------------------------------------------
class TestMemento:
    def test_guardar_y_restaurar(self, config):
        memento = config.guardar("base")
        config.actualizar(precio_venta_kwh=999)
        config.restaurar(memento)
        assert config.to_dict() == INICIAL

    def test_el_memento_es_inmutable(self, config):
        memento = config.guardar("base")
        with pytest.raises(dataclasses.FrozenInstanceError):
            memento.etiqueta = "otra"
        with pytest.raises(TypeError):
            memento._estado["precio_venta_kwh"] = 1

    def test_cambios_posteriores_no_alteran_el_memento(self, config):
        memento = config.guardar("base")
        config.actualizar(reserva_minima_pct=80)
        config.restaurar(memento)
        assert config.reserva_minima_pct == 20.0

    def test_el_memento_solo_muestra_metadatos(self, config):
        memento = config.guardar("base")
        assert isinstance(memento, MementoConfiguracion)
        assert "450" not in repr(memento)

    def test_actualizacion_invalida_no_cambia_nada(self, config):
        with pytest.raises(ValueError):
            config.actualizar(precio_venta_kwh=500, reserva_minima_pct=150)
        assert config.to_dict() == INICIAL

    def test_campo_desconocido(self, config):
        with pytest.raises(ValueError):
            config.actualizar(color="verde")

    def test_configuracion_inicial_invalida(self):
        with pytest.raises(ValueError):
            ConfiguracionHogar(precio_compra_max_kwh=0)


# ---------------------------------------------------------------------------
# 2. Caretaker: deshacer y rehacer
# ---------------------------------------------------------------------------
class TestHistorial:
    def test_deshacer_vuelve_a_la_version_anterior(self, config, historial):
        historial.cambiar("precio", precio_venta_kwh=490)
        historial.deshacer()
        assert config.precio_venta_kwh == 450.0

    def test_deshacer_varias_veces(self, config, historial):
        historial.cambiar("precio", precio_venta_kwh=490)
        historial.cambiar("reserva", reserva_minima_pct=40)
        historial.deshacer()
        assert config.to_dict() == {**INICIAL, "precio_venta_kwh": 490}
        historial.deshacer()
        assert config.to_dict() == INICIAL

    def test_deshacer_devuelve_el_cambio_revertido(self, historial):
        historial.cambiar("reserva", reserva_minima_pct=40)
        assert historial.deshacer().etiqueta == "reserva"

    def test_rehacer_reaplica_el_cambio(self, config, historial):
        historial.cambiar("precio", precio_venta_kwh=490)
        historial.deshacer()
        historial.rehacer()
        assert config.precio_venta_kwh == 490

    def test_deshacer_y_rehacer_son_simetricos(self, config, historial):
        historial.cambiar("a", precio_venta_kwh=460)
        historial.cambiar("b", precio_venta_kwh=470)
        final = config.to_dict()
        historial.deshacer()
        historial.deshacer()
        historial.rehacer()
        historial.rehacer()
        assert config.to_dict() == final and not historial.puede_rehacer

    def test_un_cambio_nuevo_invalida_el_rehacer(self, historial):
        historial.cambiar("a", precio_venta_kwh=460)
        historial.deshacer()
        historial.cambiar("b", vender_excedente=False)
        assert not historial.puede_rehacer
        with pytest.raises(SinVersiones):
            historial.rehacer()

    def test_sin_cambios_no_se_puede_deshacer(self, historial):
        assert not historial.puede_deshacer
        with pytest.raises(SinVersiones):
            historial.deshacer()

    def test_cambio_invalido_no_deja_respaldo(self, config, historial):
        with pytest.raises(ValueError):
            historial.cambiar("error", precio_venta_kwh=-5)
        assert not historial.puede_deshacer
        assert config.to_dict() == INICIAL

    def test_versiones_solo_expone_metadatos(self, historial):
        historial.cambiar("precio", precio_venta_kwh=490)
        historial.cambiar("reserva", reserva_minima_pct=40)
        versiones = historial.versiones()
        assert [v["etiqueta"] for v in versiones] == ["precio", "reserva"]
        assert set(versiones[0]) == {"etiqueta", "creado"}

    def test_limite_descarta_las_versiones_mas_antiguas(self, config):
        historial = HistorialConfiguracion(config, limite=2)
        for precio in (460, 470, 480):
            historial.cambiar(f"precio {precio}", precio_venta_kwh=precio)
        assert [v["etiqueta"] for v in historial.versiones()] == ["precio 470", "precio 480"]
        historial.deshacer()
        historial.deshacer()
        assert config.precio_venta_kwh == 460 and not historial.puede_deshacer

    def test_limite_invalido(self, config):
        with pytest.raises(ValueError):
            HistorialConfiguracion(config, limite=0)
