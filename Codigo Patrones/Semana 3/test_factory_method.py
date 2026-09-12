"""
Pruebas del patrón FACTORY METHOD — `factory_method`.

Objetivo: verificar que la plataforma nunca instancia clases concretas de
dispositivo. Cada fábrica concreta decide qué producto crear, y agregar un
tipo nuevo no obliga a tocar el código existente (principio abierto/cerrado).
"""

import pytest

from factory_method import (
    BateriaFactory,
    BateriaInteligente,
    DispositivoIoT,
    DispositivoIoTFactory,
    MedidorFactory,
    MedidorInteligente,
    PanelSolar,
    PanelSolarFactory,
    crear_dispositivo,
    obtener_factory,
)


# ---------------------------------------------------------------------------
# 1. Las clases abstractas no se pueden instanciar directamente
# ---------------------------------------------------------------------------
class TestAbstracciones:
    def test_no_se_puede_instanciar_el_producto_abstracto(self):
        with pytest.raises(TypeError):
            DispositivoIoT("x", "u1")  # type: ignore[abstract]

    def test_no_se_puede_instanciar_el_creador_abstracto(self):
        with pytest.raises(TypeError):
            DispositivoIoTFactory()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# 2. Resolución de la fábrica según el tipo solicitado
# ---------------------------------------------------------------------------
class TestObtenerFactory:
    @pytest.mark.parametrize(
        "tipo, clase_fabrica",
        [
            ("panel_solar", PanelSolarFactory),
            ("bateria", BateriaFactory),
            ("medidor", MedidorFactory),
        ],
    )
    def test_devuelve_la_fabrica_concreta_correcta(self, tipo, clase_fabrica):
        assert isinstance(obtener_factory(tipo), clase_fabrica)

    def test_tipo_no_soportado_lanza_value_error_con_los_disponibles(self):
        with pytest.raises(ValueError) as exc:
            obtener_factory("cargador_ev")
        mensaje = str(exc.value)
        assert "cargador_ev" in mensaje
        assert "panel_solar" in mensaje and "bateria" in mensaje and "medidor" in mensaje


# ---------------------------------------------------------------------------
# 3. El Factory Method crea el producto concreto adecuado
# ---------------------------------------------------------------------------
class TestFactoryMethodCreaProducto:
    @pytest.mark.parametrize(
        "tipo, clase_producto, nombre_tipo",
        [
            ("panel_solar", PanelSolar, "panel_solar"),
            ("bateria", BateriaInteligente, "bateria"),
            ("medidor", MedidorInteligente, "medidor"),
        ],
    )
    def test_crear_dispositivo_devuelve_la_subclase_esperada(
        self, tipo, clase_producto, nombre_tipo
    ):
        d = crear_dispositivo(tipo, f"{tipo}-01", "u1")
        assert isinstance(d, clase_producto)
        assert isinstance(d, DispositivoIoT)  # respeta la interfaz común
        assert d.tipo == nombre_tipo
        assert d.id == f"{tipo}-01"
        assert d.usuario_id == "u1"

    def test_cada_fabrica_concreta_construye_su_propio_producto(self):
        assert isinstance(
            PanelSolarFactory().crear_dispositivo("p", "u"), PanelSolar
        )
        assert isinstance(
            BateriaFactory().crear_dispositivo("b", "u"), BateriaInteligente
        )
        assert isinstance(
            MedidorFactory().crear_dispositivo("m", "u"), MedidorInteligente
        )


# ---------------------------------------------------------------------------
# 4. `registrar()` — lógica común del creador que reutiliza el producto
# ---------------------------------------------------------------------------
class TestRegistrar:
    def test_registrar_devuelve_el_producto_creado(self):
        d = PanelSolarFactory().registrar("panel-9", "u1")
        assert isinstance(d, PanelSolar)

    def test_registrar_emite_traza_del_factory_method(self, capsys):
        PanelSolarFactory().registrar("panel-9", "u1")
        salida = capsys.readouterr().out
        assert "[Factory Method]" in salida
        assert "panel_solar" in salida


# ---------------------------------------------------------------------------
# 5. Cada producto genera su lectura según su naturaleza
# ---------------------------------------------------------------------------
class TestGenerarLectura:
    def test_panel_solar_solo_produce_energia(self):
        panel = PanelSolar("p", "u")
        for _ in range(50):
            assert 0.5 <= panel.generar_lectura() <= 4.0

    def test_bateria_puede_cargar_o_descargar(self):
        bateria = BateriaInteligente("b", "u")
        for _ in range(50):
            assert -2.5 <= bateria.generar_lectura() <= 2.5

    def test_medidor_solo_registra_consumo(self):
        medidor = MedidorInteligente("m", "u")
        for _ in range(50):
            assert -3.0 <= medidor.generar_lectura() <= 0.0


# ---------------------------------------------------------------------------
# 6. Serialización
# ---------------------------------------------------------------------------
class TestToDict:
    def test_to_dict_incluye_el_tipo_concreto(self):
        d = crear_dispositivo("bateria", "bat-01", "u1")
        assert d.to_dict() == {"id": "bat-01", "usuario_id": "u1", "tipo": "bateria"}
