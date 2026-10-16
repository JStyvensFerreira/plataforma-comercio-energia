"""
Pruebas del patrón PROXY — `proxy`.

Objetivo: verificar que `ReporteProxy` protege el acceso al reporte de otro
usuario, que sirve una copia cacheada en vez de reconstruir el reporte
dentro del tiempo de vida configurado, que el objeto real se invoca cuando
corresponde (no siempre, no nunca), y que cada intento queda auditado.
"""

import pytest

from proxy import GeneradorReportes, GeneradorReportesReal, ReporteProxy


# ---------------------------------------------------------------------------
# 1. Protection Proxy
# ---------------------------------------------------------------------------
class TestProteccionDeAcceso:
    def test_el_dueno_puede_pedir_su_propio_reporte(self):
        proxy = ReporteProxy(real=GeneradorReportesReal())
        reporte = proxy.generar("ana", "ana", "resumen")
        assert reporte["usuario"] == "ana"

    def test_otro_usuario_no_puede_pedir_un_reporte_ajeno(self):
        proxy = ReporteProxy(real=GeneradorReportesReal())
        with pytest.raises(PermissionError):
            proxy.generar("luis", "ana", "resumen")

    def test_el_intento_denegado_no_llega_al_objeto_real(self):
        real = GeneradorReportesReal()
        proxy = ReporteProxy(real=real)
        with pytest.raises(PermissionError):
            proxy.generar("luis", "ana", "resumen")
        assert real.construcciones == 0


# ---------------------------------------------------------------------------
# 2. Caching Proxy
# ---------------------------------------------------------------------------
class TestCacheDeReportes:
    def test_la_segunda_solicitud_identica_no_reconstruye_el_reporte(self):
        real = GeneradorReportesReal()
        proxy = ReporteProxy(real=real)
        proxy.generar("ana", "ana", "resumen")
        proxy.generar("ana", "ana", "resumen")
        assert real.construcciones == 1

    def test_formatos_distintos_no_comparten_cache(self):
        real = GeneradorReportesReal()
        proxy = ReporteProxy(real=real)
        proxy.generar("ana", "ana", "resumen")
        proxy.generar("ana", "ana", "detallado")
        assert real.construcciones == 2

    def test_usuarios_distintos_no_comparten_cache(self):
        real = GeneradorReportesReal()
        proxy = ReporteProxy(real=real)
        proxy.generar("ana", "ana", "resumen")
        proxy.generar("luis", "luis", "resumen")
        assert real.construcciones == 2

    def test_cache_vencida_reconstruye_el_reporte(self):
        real = GeneradorReportesReal()
        proxy = ReporteProxy(real=real, ttl_segundos=0.0)
        proxy.generar("ana", "ana", "resumen")
        proxy.generar("ana", "ana", "resumen")
        assert real.construcciones == 2


# ---------------------------------------------------------------------------
# 3. Logging Proxy (auditoría)
# ---------------------------------------------------------------------------
class TestAuditoria:
    def test_cada_solicitud_queda_registrada(self):
        proxy = ReporteProxy(real=GeneradorReportesReal())
        proxy.generar("ana", "ana", "resumen")
        assert len(proxy.auditoria) == 1
        assert proxy.auditoria[0]["resultado"] == "generado"

    def test_la_denegacion_tambien_queda_registrada(self):
        proxy = ReporteProxy(real=GeneradorReportesReal())
        with pytest.raises(PermissionError):
            proxy.generar("luis", "ana", "resumen")
        assert proxy.auditoria[-1]["resultado"] == "denegado"

    def test_el_acierto_de_cache_queda_registrado_distinto_de_generado(self):
        proxy = ReporteProxy(real=GeneradorReportesReal())
        proxy.generar("ana", "ana", "resumen")
        proxy.generar("ana", "ana", "resumen")
        assert [e["resultado"] for e in proxy.auditoria] == ["generado", "cache"]


# ---------------------------------------------------------------------------
# 4. El proxy respeta la interfaz del Subject
# ---------------------------------------------------------------------------
class TestInterfazComun:
    def test_el_proxy_y_el_objeto_real_implementan_el_mismo_subject(self):
        assert isinstance(ReporteProxy(real=GeneradorReportesReal()), GeneradorReportes)
        assert isinstance(GeneradorReportesReal(), GeneradorReportes)

    def test_no_se_puede_instanciar_el_subject_abstracto(self):
        with pytest.raises(TypeError):
            GeneradorReportes()
