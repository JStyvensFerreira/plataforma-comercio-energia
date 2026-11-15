"""
Pruebas del patrón COMMAND — `command`.

Objetivo: verificar que cada operación del mercado es un objeto con
`ejecutar` y `deshacer`; que el gestor (Invoker) puede programarlas en una
cola, ejecutarlas en lote, llevar un historial y deshacer la última, sin
llamar nunca al mercado directamente; y que un comando que falla no entra
al historial ni detiene al resto del lote.
"""

import pytest

from command import (
    CancelarOrdenComando,
    ComandoMercado,
    GestorOperaciones,
    Mercado,
    OperacionInvalida,
    PublicarCompraComando,
    PublicarVentaComando,
)


@pytest.fixture
def mercado():
    return Mercado()


@pytest.fixture
def gestor():
    return GestorOperaciones()


# ---------------------------------------------------------------------------
# 1. Comandos concretos
# ---------------------------------------------------------------------------
class TestComandos:
    def test_crear_el_comando_no_ejecuta_nada(self, mercado):
        PublicarVentaComando(mercado, "ana", 5, 440)
        assert mercado.ordenes == {}

    def test_publicar_venta_y_deshacer(self, mercado):
        comando = PublicarVentaComando(mercado, "ana", 5, 440)
        comando.ejecutar()
        orden = mercado.ordenes[comando.orden_id]
        assert (orden.tipo, orden.cantidad_kwh, orden.activa) == ("venta", 5, True)
        comando.deshacer()
        assert mercado.activas() == []

    def test_publicar_compra(self, mercado):
        comando = PublicarCompraComando(mercado, "ana", 3, 380)
        comando.ejecutar()
        assert mercado.ordenes[comando.orden_id].tipo == "compra"

    def test_cancelar_y_deshacer_reabre_la_orden(self, mercado):
        orden = mercado.publicar("ana", "venta", 2, 500)
        comando = CancelarOrdenComando(mercado, "ana", orden.id)
        comando.ejecutar()
        assert not orden.activa
        comando.deshacer()
        assert orden.activa

    def test_descripcion_legible(self, mercado):
        assert PublicarVentaComando(mercado, "ana", 5, 440).descripcion() == "Publicar venta de 5 kWh a 440"
        assert CancelarOrdenComando(mercado, "ana", 7).descripcion() == "Cancelar orden #7"

    def test_la_interfaz_no_se_puede_instanciar(self):
        with pytest.raises(TypeError):
            ComandoMercado()

    @pytest.mark.parametrize("usuario, orden_id, mensaje", [("ana", 99, "no existe"), ("luis", 1, "no es de")])
    def test_cancelar_invalido(self, mercado, usuario, orden_id, mensaje):
        mercado.publicar("ana", "venta", 2, 500)
        with pytest.raises(OperacionInvalida, match=mensaje):
            CancelarOrdenComando(mercado, usuario, orden_id).ejecutar()


# ---------------------------------------------------------------------------
# 2. Invoker: cola, lote, historial y deshacer
# ---------------------------------------------------------------------------
class TestGestor:
    def test_programar_no_ejecuta(self, mercado, gestor):
        gestor.programar(PublicarVentaComando(mercado, "ana", 5, 440))
        assert gestor.pendientes() == ["Publicar venta de 5 kWh a 440"]
        assert mercado.ordenes == {}

    def test_ejecutar_pendientes_en_orden(self, mercado, gestor):
        gestor.programar(PublicarVentaComando(mercado, "ana", 5, 440))
        gestor.programar(PublicarCompraComando(mercado, "ana", 3, 380))
        resultado = gestor.ejecutar_pendientes()
        assert resultado["ejecutados"] == ["Publicar venta de 5 kWh a 440", "Publicar compra de 3 kWh a 380"]
        assert [o.tipo for o in mercado.activas()] == ["venta", "compra"]
        assert gestor.pendientes() == []

    def test_un_fallo_no_detiene_el_lote_ni_entra_al_historial(self, mercado, gestor):
        gestor.programar(CancelarOrdenComando(mercado, "ana", 99))
        gestor.programar(PublicarVentaComando(mercado, "ana", 5, 440))
        resultado = gestor.ejecutar_pendientes()
        assert resultado["errores"] == [{"operacion": "Cancelar orden #99", "error": "La orden 99 no existe"}]
        assert gestor.ejecutados() == ["Publicar venta de 5 kWh a 440"]

    def test_deshacer_revierte_en_orden_inverso(self, mercado, gestor):
        vieja = mercado.publicar("ana", "venta", 2, 500)
        gestor.ejecutar(PublicarVentaComando(mercado, "ana", 5, 440))
        gestor.ejecutar(CancelarOrdenComando(mercado, "ana", vieja.id))
        assert gestor.deshacer().descripcion() == f"Cancelar orden #{vieja.id}"
        assert vieja.activa
        assert gestor.deshacer().descripcion() == "Publicar venta de 5 kWh a 440"
        assert mercado.activas() == [vieja]

    def test_deshacer_sin_historial_falla(self, gestor):
        with pytest.raises(OperacionInvalida, match="No hay operaciones"):
            gestor.deshacer()

    def test_si_deshacer_falla_el_comando_sigue_en_el_historial(self, mercado, gestor):
        comando = PublicarVentaComando(mercado, "ana", 5, 440)
        gestor.ejecutar(comando)
        mercado.cancelar("ana", comando.orden_id)  # alguien la retiró por otra vía
        with pytest.raises(OperacionInvalida):
            gestor.deshacer()
        assert gestor.ejecutados() == ["Publicar venta de 5 kWh a 440"]

    def test_descartar_pendientes(self, mercado, gestor):
        gestor.programar(PublicarVentaComando(mercado, "ana", 5, 440))
        assert gestor.descartar_pendientes() == 1
        assert gestor.ejecutar_pendientes() == {"ejecutados": [], "errores": []}

    def test_el_registro_guarda_todo_lo_que_paso(self, mercado, gestor):
        gestor.programar(PublicarVentaComando(mercado, "ana", 5, 440))
        gestor.programar(PublicarVentaComando(mercado, "ana", 0, 440))
        gestor.ejecutar_pendientes()
        gestor.deshacer()
        assert [linea.split(":")[0] for linea in gestor.registro] == ["ejecutado", "fallido", "deshecho"]

    def test_el_gestor_funciona_con_cualquier_comando(self, gestor):
        class ComandoEco(ComandoMercado):
            def __init__(self):
                self.estado = "nuevo"

            def ejecutar(self):
                self.estado = "hecho"

            def deshacer(self):
                self.estado = "revertido"

            def descripcion(self):
                return "eco"

        comando = ComandoEco()
        gestor.ejecutar(comando)
        gestor.deshacer()
        assert comando.estado == "revertido"
