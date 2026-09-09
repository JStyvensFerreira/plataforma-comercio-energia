"""
Pruebas del patrón BUILDER — `builder`.

Objetivo: verificar que un reporte energético complejo se construye PASO A PASO
mediante un builder, que el mismo proceso de construcción produce
representaciones distintas (dict, objeto, texto), que el Director encapsula las
recetas sin conocer la representación, y que agregar un formato nuevo no obliga
a tocar el código existente (principio abierto/cerrado).
"""

import pytest

from builder import (
    CLAVES_CONTRATO_NOTIFICACION,
    FORMATOS_DISPONIBLES,
    DatosReporte,
    DirectorReportes,
    ReporteBuilder,
    ReporteDetalladoBuilder,
    ReporteEnergetico,
    ReporteResumenBuilder,
    ReporteTextoBuilder,
    crear_builder,
)

# ---------------------------------------------------------------------------
# Datos de ejemplo (con la forma que produce la plataforma)
# ---------------------------------------------------------------------------
DATOS = DatosReporte(
    usuario="u1",
    periodo="2026-09",
    produccion_kwh=18.4,
    consumo_kwh=12.1,
    lecturas_por_dispositivo={
        "panel-01": [3.1, 2.8, 3.4],
        "bat-01": [1.2, -0.8, -1.4],
    },
    transacciones=[
        {"comprador": "u2", "vendedor": "u1", "cantidad_kwh": 6, "total": 0.9,
         "timestamp": "2026-09-07T10:30:00"},
        {"comprador": "u1", "vendedor": "u3", "cantidad_kwh": 2, "total": 0.3,
         "timestamp": "2026-09-08T09:00:00"},
    ],
    prediccion_por_dispositivo={"panel-01": 2.9, "bat-01": None},
)

TODOS_LOS_FORMATOS = [
    ("resumen", ReporteResumenBuilder, dict),
    ("detallado", ReporteDetalladoBuilder, ReporteEnergetico),
    ("texto", ReporteTextoBuilder, str),
]

PASOS_ESPERADOS = (
    "encabezado",
    "balance_energetico",
    "desglose_dispositivos",
    "historial_transacciones",
    "prediccion_consumo",
    "obtener_reporte",
)


class _BuilderEspia(ReporteBuilder):
    """Builder de prueba: registra el orden en que el Director llama sus pasos.

    Tras construirlo, `llamadas` ya contiene el `reiniciar` que dispara
    `ReporteBuilder.__init__`; los tests hacen `llamadas.clear()` antes de usarlo.
    """

    formato = "espia"

    def __init__(self):
        self.llamadas: list[str] = []
        super().__init__()

    def reiniciar(self):
        self.llamadas.append("reiniciar")

    def encabezado(self, usuario, periodo):
        self.llamadas.append("encabezado")
        return self

    def balance_energetico(self, produccion_kwh, consumo_kwh):
        self.llamadas.append("balance_energetico")
        return self

    def desglose_dispositivos(self, lecturas_por_dispositivo):
        self.llamadas.append("desglose_dispositivos")
        return self

    def historial_transacciones(self, transacciones):
        self.llamadas.append("historial_transacciones")
        return self

    def prediccion_consumo(self, prediccion_por_dispositivo):
        self.llamadas.append("prediccion_consumo")
        return self

    def obtener_reporte(self):
        self.llamadas.append("obtener_reporte")
        return list(self.llamadas)


# ---------------------------------------------------------------------------
# 1. La clase abstracta no se puede instanciar directamente
# ---------------------------------------------------------------------------
class TestAbstraccion:
    def test_no_se_puede_instanciar_el_builder_abstracto(self):
        with pytest.raises(TypeError):
            ReporteBuilder()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# 2. Resolución del builder concreto según el formato pedido
# ---------------------------------------------------------------------------
class TestCrearBuilder:
    @pytest.mark.parametrize("formato, clase, _tipo", TODOS_LOS_FORMATOS)
    def test_devuelve_el_builder_del_formato_correcto(self, formato, clase, _tipo):
        b = crear_builder(formato)
        assert isinstance(b, clase)
        assert b.formato == formato

    def test_registro_y_formatos_disponibles_coinciden(self):
        assert set(FORMATOS_DISPONIBLES) == {f for f, _c, _t in TODOS_LOS_FORMATOS}

    def test_formato_no_soportado_lanza_value_error_con_los_disponibles(self):
        with pytest.raises(ValueError) as exc:
            crear_builder("pdf")
        mensaje = str(exc.value)
        assert "pdf" in mensaje
        for formato in FORMATOS_DISPONIBLES:
            assert formato in mensaje


# ---------------------------------------------------------------------------
# 3. El Director ejecuta la MISMA secuencia de pasos con cualquier builder
# ---------------------------------------------------------------------------
class TestDirectorSecuenciaDePasos:
    def test_reporte_completo_llama_todos_los_pasos_en_orden(self):
        espia = _BuilderEspia()
        espia.llamadas.clear()
        DirectorReportes(espia).reporte_completo(DATOS)
        assert espia.llamadas == ["reiniciar", *PASOS_ESPERADOS]

    def test_reporte_ejecutivo_omite_desglose_y_prediccion(self):
        espia = _BuilderEspia()
        espia.llamadas.clear()
        DirectorReportes(espia).reporte_ejecutivo(DATOS)
        assert espia.llamadas == [
            "reiniciar", "encabezado", "balance_energetico",
            "historial_transacciones", "obtener_reporte",
        ]

    def test_el_director_reinicia_el_builder_al_empezar_cada_receta(self):
        espia = _BuilderEspia()
        espia.llamadas.clear()
        director = DirectorReportes(espia)
        director.reporte_completo(DATOS)
        director.reporte_ejecutivo(DATOS)
        assert espia.llamadas.count("reiniciar") == 2
        # la segunda receta arranca con un reiniciar
        assert espia.llamadas[len(PASOS_ESPERADOS) + 1] == "reiniciar"


# ---------------------------------------------------------------------------
# 4. Cada builder concreto produce SU representación
# ---------------------------------------------------------------------------
class TestRepresentaciones:
    @pytest.mark.parametrize("formato, _clase, tipo", TODOS_LOS_FORMATOS)
    def test_obtener_reporte_devuelve_el_tipo_propio_del_builder(self, formato, _clase, tipo):
        reporte = DirectorReportes(crear_builder(formato)).reporte_completo(DATOS)
        assert isinstance(reporte, tipo)

    def test_resumen_es_un_dict_plano_con_el_contrato_de_notificacion(self):
        reporte = DirectorReportes(ReporteResumenBuilder()).reporte_ejecutivo(DATOS)
        assert isinstance(reporte, dict)
        for clave in CLAVES_CONTRATO_NOTIFICACION:
            assert clave in reporte
        assert isinstance(reporte["produccion_kwh"], (int, float))
        assert isinstance(reporte["consumo_kwh"], (int, float))
        assert isinstance(reporte["balance_kwh"], (int, float))
        assert isinstance(reporte["transacciones"], int)

    def test_detallado_es_un_objeto_con_secciones_tipadas(self):
        reporte = DirectorReportes(ReporteDetalladoBuilder()).reporte_completo(DATOS)
        assert isinstance(reporte, ReporteEnergetico)
        assert reporte.usuario == "u1"
        assert reporte.generado_en  # se selló al reiniciar
        assert all(s.titulo for s in reporte.secciones)

    def test_texto_es_una_cadena_no_vacia_con_los_datos_clave(self):
        reporte = DirectorReportes(ReporteTextoBuilder()).reporte_completo(DATOS)
        assert isinstance(reporte, str)
        assert "u1" in reporte
        assert "Balance" in reporte
        assert "6.3 kWh" in reporte  # 18.4 - 12.1


# ---------------------------------------------------------------------------
# 5. Reiniciar deja el builder limpio entre reportes
# ---------------------------------------------------------------------------
class TestReiniciar:
    def test_dos_reportes_seguidos_no_se_contaminan(self):
        builder = ReporteDetalladoBuilder()
        director = DirectorReportes(builder)

        primero = director.reporte_completo(DATOS)
        otros_datos = DatosReporte(usuario="u2", periodo="2026-10")
        segundo = director.reporte_ejecutivo(otros_datos)

        assert primero.usuario == "u1" and segundo.usuario == "u2"
        assert "Desglose por dispositivo" in primero.titulos()
        assert "Desglose por dispositivo" not in segundo.titulos()

    def test_reiniciar_explicito_vacia_el_reporte_en_construccion(self):
        builder = ReporteDetalladoBuilder()
        builder.encabezado("u9", "2026-01").balance_energetico(5, 2)
        builder.reiniciar()
        assert builder.obtener_reporte().secciones == []
        assert builder.obtener_reporte().usuario == ""


# ---------------------------------------------------------------------------
# 6. Las recetas del Director cambian QUÉ se incluye, no la representación
# ---------------------------------------------------------------------------
class TestRecetasDelDirector:
    def test_reporte_completo_incluye_las_secciones_en_orden(self):
        reporte = DirectorReportes(ReporteDetalladoBuilder()).reporte_completo(DATOS)
        assert reporte.titulos() == [
            "Balance energético",
            "Desglose por dispositivo",
            "Historial de transacciones",
            "Predicción de la próxima lectura",
        ]

    def test_reporte_ejecutivo_no_incluye_desglose_ni_prediccion(self):
        reporte = DirectorReportes(ReporteDetalladoBuilder()).reporte_ejecutivo(DATOS)
        assert reporte.titulos() == [
            "Balance energético",
            "Historial de transacciones",
        ]

    def test_reporte_para_factura_lleva_historial_y_balance_sin_prediccion(self):
        reporte = DirectorReportes(ReporteDetalladoBuilder()).reporte_para_factura(DATOS)
        assert reporte.titulos() == [
            "Historial de transacciones",
            "Balance energético",
        ]

    @pytest.mark.parametrize("formato, _clase, _tipo", TODOS_LOS_FORMATOS)
    def test_una_misma_receta_sirve_para_todas_las_representaciones(self, formato, _clase, _tipo):
        reporte = DirectorReportes(crear_builder(formato)).reporte_para_factura(DATOS)
        assert reporte is not None


# ---------------------------------------------------------------------------
# 7. Contenido calculado por los pasos
# ---------------------------------------------------------------------------
class TestContenido:
    def test_el_balance_es_produccion_menos_consumo(self):
        resumen = DirectorReportes(ReporteResumenBuilder()).reporte_ejecutivo(DATOS)
        assert resumen["balance_kwh"] == round(18.4 - 12.1, 2)

        detallado = DirectorReportes(ReporteDetalladoBuilder()).reporte_completo(DATOS)
        balance = detallado.seccion("Balance energético")
        assert balance.datos["balance_kwh"] == round(18.4 - 12.1, 2)

    def test_el_resumen_cuenta_las_operaciones(self):
        resumen = DirectorReportes(ReporteResumenBuilder()).reporte_ejecutivo(DATOS)
        assert resumen["transacciones"] == len(DATOS.transacciones)

    def test_el_desglose_separa_produccion_y_consumo_por_dispositivo(self):
        detallado = DirectorReportes(ReporteDetalladoBuilder()).reporte_completo(DATOS)
        desglose = detallado.seccion("Desglose por dispositivo")
        assert desglose.datos["bat-01"]["producido_kwh"] == pytest.approx(1.2)
        assert desglose.datos["bat-01"]["consumido_kwh"] == pytest.approx(2.2)

    def test_los_datos_vacios_no_rompen_ningun_builder(self):
        vacios = DatosReporte(usuario="u0", periodo="2026-09")
        for formato in FORMATOS_DISPONIBLES:
            reporte = DirectorReportes(crear_builder(formato)).reporte_completo(vacios)
            assert reporte is not None


# ---------------------------------------------------------------------------
# 8. Uso fluido sin Director (encadenando los pasos)
# ---------------------------------------------------------------------------
class TestUsoFluido:
    def test_cada_paso_devuelve_el_builder_para_encadenar(self):
        builder = ReporteResumenBuilder()
        assert builder.encabezado("u1", "2026-09") is builder
        assert builder.balance_energetico(10, 4) is builder

    def test_encadenado_a_mano_equivale_a_la_receta_del_director(self):
        a_mano = (
            crear_builder("resumen")
            .encabezado(DATOS.usuario, DATOS.periodo)
            .balance_energetico(DATOS.produccion_kwh, DATOS.consumo_kwh)
            .historial_transacciones(DATOS.transacciones)
            .obtener_reporte()
        )
        por_director = DirectorReportes(crear_builder("resumen")).reporte_ejecutivo(DATOS)
        assert a_mano == por_director


# ---------------------------------------------------------------------------
# 9. Abierto/cerrado: un formato nuevo no toca el código existente
# ---------------------------------------------------------------------------
class TestExtensibilidad:
    def test_se_puede_agregar_un_builder_sin_modificar_los_existentes(self):
        """Un `ReporteMarkdownBuilder` nuevo implementa los mismos pasos y el
        `DirectorReportes` lo usa igual que a los demás."""

        class ReporteMarkdownBuilder(ReporteBuilder):
            formato = "markdown"

            def reiniciar(self):
                self._md: list[str] = []

            def encabezado(self, usuario, periodo):
                self._md = [f"# Reporte de {usuario}", f"_Período: {periodo}_"]
                return self

            def balance_energetico(self, produccion_kwh, consumo_kwh):
                self._md.append(f"- **Balance:** {round(produccion_kwh - consumo_kwh, 2)} kWh")
                return self

            def desglose_dispositivos(self, lecturas_por_dispositivo):
                self._md.append(f"- Dispositivos: {len(lecturas_por_dispositivo)}")
                return self

            def historial_transacciones(self, transacciones):
                self._md.append(f"- Operaciones: {len(transacciones)}")
                return self

            def prediccion_consumo(self, prediccion_por_dispositivo):
                self._md.append(f"- Predicciones: {len(prediccion_por_dispositivo)}")
                return self

            def obtener_reporte(self) -> str:
                return "\n".join(self._md)

        reporte = DirectorReportes(ReporteMarkdownBuilder()).reporte_completo(DATOS)
        assert reporte.startswith("# Reporte de u1")
        assert "**Balance:** 6.3 kWh" in reporte
