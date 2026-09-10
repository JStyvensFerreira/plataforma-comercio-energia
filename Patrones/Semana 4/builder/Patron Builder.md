# Patrón Builder — Plataforma de Comercio de Energía

Implementación del patrón **Builder** (Constructor) sobre el **reporte energético**
de la plataforma: el objeto que resume, para un usuario y un período, su balance
de producción/consumo, el desglose por dispositivo IoT, el historial de
operaciones en la subasta y la predicción de la próxima lectura.

- Código del patrón (con demo y docstring explicativo): [`builder.py`](builder.py)
- Pruebas del patrón: [`test_builder.py`](test_builder.py)
- Documento de casos de prueba: [`Patrones/README.md`](../../README.md#casos-de-prueba--builder)
- Uso real en la aplicación: [`plataforma-energia-app/backend/reportes.py`](../../../plataforma-energia-app/backend/reportes.py) — consumido por [`plataforma.py`](../../../plataforma-energia-app/backend/plataforma.py) (`generar_reporte`) y expuesto en [`main.py`](../../../plataforma-energia-app/backend/main.py) (`POST /reportes/generar`)

## Por qué este patrón aquí

El reporte energético no es un objeto simple:

1. **Tiene muchas partes opcionales.** El resumen ejecutivo solo lleva balance y
   número de operaciones; el reporte completo añade el desglose por dispositivo y
   la predicción; el reporte para factura lleva el historial y el balance, pero
   no la predicción.
2. **Debe existir en varias representaciones.** El canal de notificación (patrón
   Abstract Factory) necesita un `dict` plano con unas claves concretas; el panel
   web quiere un objeto con secciones tipadas; un correo o un archivo `.txt`
   quieren una cadena ya formateada.

Sin el patrón, `PlataformaEnergia.generar_reporte()` tendría que decidir con
`if/elif` qué secciones incluir **y además** saber serializar el resultado a
`dict`, a texto o a HTML: la lógica de negocio quedaría mezclada con la de
presentación.

## Cómo funciona

- **Builder abstracto `ReporteBuilder`:** declara los **pasos** de construcción
  (`encabezado`, `balance_energetico`, `desglose_dispositivos`,
  `historial_transacciones`, `prediccion_consumo`) y un `obtener_reporte()` que
  entrega el producto terminado. Cada paso devuelve `self` para poder encadenar.
- **Builders concretos (las representaciones):**
  - `ReporteResumenBuilder` → `dict` plano (`usuario`, `produccion_kwh`,
    `consumo_kwh`, `balance_kwh`, `transacciones`) — el contrato que consume el
    `FormateadorReporte` del Abstract Factory.
  - `ReporteDetalladoBuilder` → `ReporteEnergetico`, un objeto con una
    `SeccionReporte` por paso (título, líneas legibles y datos estructurados).
  - `ReporteTextoBuilder` → `str` ya formateado.
- **Director `DirectorReportes`:** conoce las **recetas** — en qué orden y con
  qué pasos se arma un `reporte_ejecutivo`, un `reporte_completo` o un
  `reporte_para_factura`. El director llama los pasos; nunca sabe qué
  representación sale.
- **Datos de entrada `DatosReporte`:** la materia prima ya calculada por la
  plataforma. El builder solo le da forma; no consulta ni calcula nada.
- **Registro:** `crear_builder(formato)` — punto único donde se resuelve el
  builder; un formato desconocido lanza `ValueError` con la lista de formatos
  válidos.

```python
datos = DatosReporte(usuario="u1", periodo="2026-09", produccion_kwh=18.4, consumo_kwh=12.1)

# misma receta, distinta representación
DirectorReportes(crear_builder("resumen")).reporte_ejecutivo(datos)    # -> dict
DirectorReportes(crear_builder("detallado")).reporte_completo(datos)   # -> ReporteEnergetico
DirectorReportes(crear_builder("texto")).reporte_para_factura(datos)   # -> str

# uso fluido, sin Director
(crear_builder("resumen")
 .encabezado("u1", "2026-09")
 .balance_energetico(18.4, 12.1)
 .historial_transacciones(txs)
 .obtener_reporte())
```

## Qué le aporta a la plataforma

- **Separación construcción / representación / receta.** La plataforma decide
  *qué datos* van al reporte (`DatosReporte`); el Director decide *qué secciones*
  y en qué orden; el builder decide *en qué formato* sale. Cada eje cambia por
  separado.
- **Reutilización del canal de notificación.** `ReporteResumenBuilder` produce
  exactamente el `dict` que espera el `FormateadorReporte` del Abstract Factory,
  así que el reporte se puede seguir enviando por el canal del usuario sin
  código de adaptación.
- **Abierto/cerrado.** Agregar un formato (Markdown, HTML, PDF) es escribir un
  builder concreto más y registrarlo; ni el Director ni los demás builders
  cambian. La prueba `B-24` lo demuestra con un `ReporteMarkdownBuilder` definido
  dentro del test.
- **Relación con las fábricas del proyecto.** El Factory Method y el Abstract
  Factory crean un producto (o una familia) en **una** llamada; el Builder
  construye **un** objeto complejo **paso a paso**, y el mismo proceso produce
  representaciones distintas.

## Diagrama

```
   DirectorReportes  (director: conoce las recetas)
   + reporte_ejecutivo()  ─┐
   + reporte_completo()   ─┤  llaman en cierto orden a…
   + reporte_para_factura()┘
                 │
                 ▼
        ReporteBuilder  (builder abstracto: los pasos)
        + encabezado()            + historial_transacciones()
        + balance_energetico()    + prediccion_consumo()
        + desglose_dispositivos() + obtener_reporte()
                 ▲            ▲            ▲
        ┌────────┘    ┌───────┘    ┌───────┘
 ReporteResumen   ReporteDetallado  ReporteTexto     (builders concretos)
   -> dict          -> ReporteEnergetico  -> str      (una representación cada uno)
```

## Validación del patrón

```bash
python -m pytest "Patrones/Semana 4/builder" -v        # 30 casos
python validar_pruebas.py builder                      # resumen del patrón
python "Patrones/Semana 4/builder/builder.py"          # demo por consola
```
