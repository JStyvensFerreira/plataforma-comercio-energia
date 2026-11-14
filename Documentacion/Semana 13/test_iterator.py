"""
Pruebas del patrón ITERATOR — `iterator`.

Objetivo: verificar que el libro de órdenes (Aggregate) entrega recorridos
intercambiables sin exponer sus listas internas: por llegada, por prioridad
precio-tiempo (ventas baratas primero, compras caras primero, empate por
llegada) y filtrado; que todos cumplen la misma interfaz y el protocolo de
Python; que se pueden reiniciar; y que trabajan sobre una instantánea.
"""

import pytest

from iterator import (
    COMPRA,
    VENTA,
    IteradorFiltrado,
    IteradorLlegada,
    IteradorOrdenes,
    IteradorPrioridad,
    LibroOrdenes,
    Orden,
)


@pytest.fixture
def libro():
    libro = LibroOrdenes()
    for orden in (
        Orden(1, "ana", VENTA, 5, 480),
        Orden(2, "luis", COMPRA, 3, 500),
        Orden(3, "marta", VENTA, 2, 450),
        Orden(4, "ana", COMPRA, 4, 520),
        Orden(5, "pedro", VENTA, 6, 450),
        Orden(6, "luis", VENTA, 1, 470, negociable=False),
        Orden(7, "pedro", COMPRA, 2, 520),
    ):
        libro.agregar(orden)
    return libro


def ids(iterador):
    return [o.id for o in iterador]


# ---------------------------------------------------------------------------
# 1. Recorridos
# ---------------------------------------------------------------------------
class TestRecorridos:
    def test_por_llegada_respeta_el_orden_de_publicacion(self, libro):
        assert ids(libro.crear_iterador("llegada")) == [1, 2, 3, 4, 5, 6, 7]

    def test_por_llegada_de_un_solo_tipo(self, libro):
        assert ids(libro.crear_iterador("llegada", VENTA)) == [1, 3, 5, 6]

    def test_ventas_por_prioridad_mas_baratas_primero(self, libro):
        precios = [o.precio_kwh for o in libro.crear_iterador("prioridad", VENTA)]
        assert precios == sorted(precios)

    def test_compras_por_prioridad_mas_caras_primero(self, libro):
        precios = [o.precio_kwh for o in libro.crear_iterador("prioridad", COMPRA)]
        assert precios == sorted(precios, reverse=True)

    def test_a_igual_precio_gana_la_que_llego_antes(self, libro):
        assert ids(libro.crear_iterador("prioridad", VENTA))[:2] == [3, 5]
        assert ids(libro.crear_iterador("prioridad", COMPRA))[:2] == [4, 7]

    def test_la_coleccion_es_iterable_directamente(self, libro):
        assert ids(libro) == [1, 2, 3, 4, 5, 6, 7]

    def test_libro_vacio_no_entrega_nada(self):
        it = LibroOrdenes().crear_iterador("prioridad", VENTA)
        assert not it.tiene_siguiente() and list(it) == []


# ---------------------------------------------------------------------------
# 2. Filtrado (iterador que envuelve a otro)
# ---------------------------------------------------------------------------
class TestFiltrado:
    def test_ordenes_de_un_usuario(self, libro):
        assert ids(libro.ordenes_de("ana")) == [1, 4]

    def test_usuario_sin_ordenes(self, libro):
        assert ids(libro.ordenes_de("nadie")) == []

    def test_negociables_omite_las_cerradas_y_conserva_la_prioridad(self, libro):
        assert ids(libro.negociables(VENTA)) == [3, 5, 1]

    def test_el_filtro_envuelve_cualquier_iterador(self, libro):
        base = libro.crear_iterador("prioridad", COMPRA)
        caras = IteradorFiltrado(base, lambda o: o.precio_kwh > 510)
        assert ids(caras) == [4, 7]

    def test_tiene_siguiente_no_consume_elementos(self, libro):
        it = libro.ordenes_de("ana")
        assert it.tiene_siguiente() and it.tiene_siguiente()
        assert it.siguiente().id == 1


# ---------------------------------------------------------------------------
# 3. Interfaz común, reinicio e instantánea
# ---------------------------------------------------------------------------
class TestInterfaz:
    @pytest.mark.parametrize(
        "crear",
        [
            lambda l: l.crear_iterador("llegada"),
            lambda l: l.crear_iterador("prioridad", VENTA),
            lambda l: l.ordenes_de("ana"),
        ],
    )
    def test_todos_cumplen_la_interfaz_comun(self, libro, crear):
        it = crear(libro)
        assert isinstance(it, IteradorOrdenes)
        assert iter(it) is it

    def test_tipos_concretos_segun_el_recorrido(self, libro):
        assert isinstance(libro.crear_iterador("llegada"), IteradorLlegada)
        assert isinstance(libro.crear_iterador("prioridad", VENTA), IteradorPrioridad)

    def test_siguiente_al_final_lanza_stop_iteration(self, libro):
        it = libro.ordenes_de("marta")
        it.siguiente()
        with pytest.raises(StopIteration):
            it.siguiente()

    @pytest.mark.parametrize("recorrido,tipo", [("llegada", None), ("prioridad", VENTA)])
    def test_reiniciar_vuelve_al_principio(self, libro, recorrido, tipo):
        it = libro.crear_iterador(recorrido, tipo)
        primera = ids(it)
        it.reiniciar()
        assert ids(it) == primera

    def test_reiniciar_un_filtrado(self, libro):
        it = libro.ordenes_de("ana")
        list(it)
        it.reiniciar()
        assert ids(it) == [1, 4]

    def test_dos_iteradores_son_independientes(self, libro):
        a, b = libro.crear_iterador(), libro.crear_iterador()
        a.siguiente()
        a.siguiente()
        assert b.siguiente().id == 1

    def test_publicar_durante_el_recorrido_no_altera_la_instantanea(self, libro):
        it = libro.crear_iterador("prioridad", VENTA)
        it.siguiente()
        libro.agregar(Orden(8, "sofia", VENTA, 1, 100))
        assert 8 not in ids(it)
        assert libro.crear_iterador("prioridad", VENTA).siguiente().id == 8

    def test_recorrer_no_modifica_el_libro(self, libro):
        list(libro.crear_iterador("prioridad", COMPRA))
        assert ids(libro.crear_iterador("llegada", COMPRA)) == [2, 4, 7]


# ---------------------------------------------------------------------------
# 4. Errores
# ---------------------------------------------------------------------------
class TestErrores:
    def test_recorrido_desconocido(self, libro):
        with pytest.raises(ValueError):
            libro.crear_iterador("aleatorio")

    def test_prioridad_exige_tipo(self, libro):
        with pytest.raises(ValueError):
            libro.crear_iterador("prioridad")

    def test_tipo_de_orden_desconocido(self, libro):
        with pytest.raises(ValueError):
            libro.agregar(Orden(9, "ana", "trueque", 1, 1))
