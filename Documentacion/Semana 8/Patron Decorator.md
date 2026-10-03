# Patrón Decorator — Plataforma de Comercio de Energía

Implementación del patrón **Decorator** (Decorador) sobre el **precio final de
una transacción**: aplicar descuentos, recargos, cargos fijos y comisiones
sobre el costo base, en cualquier combinación y orden, sin crear una clase
por combinación.

- Código del patrón (con demo y docstring explicativo): [`decorator.py`](decorator.py)
- Pruebas del patrón: [`test_decorator.py`](test_decorator.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--decorator)
- Uso real en la aplicación: [`plataforma-energia-app/backend/precios.py`](../../plataforma-energia-app/backend/precios.py) — consumido por [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py) (`_calcular_costo`, `cotizar`) y expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`/precios/ajustes`, `/precios/cotizar`)

## Por qué este patrón aquí

Es el mismo problema visto en clase con el estudiante que puede tener beca,
descuento por hermanos, descuento por PP, recargos... **o una combinación de
ellos**. En la plataforma, cuando la subasta cierra una transacción, el costo
para el comprador no es solo `cantidad_kwh x precio_kwh`:

| | Ajuste | Valor | Cuándo aplica en la app |
|---|---|---|---|
| A | Descuento energía renovable | −10 % | el vendedor tiene un panel solar |
| B | Descuento comprador frecuente | −5 % | el comprador ya hizo 3 compras o más |
| C | Recargo hora pico | +15 % | la transacción cierra entre 18:00 y 20:59 |
| D | Cargo fijo por uso de la red | +$0.20 | siempre |
| E | Comisión de la plataforma | +5 % | siempre |

Con herencia habría que crear una clase por cada combinación
(`CostoRenovableFrecuente`, `CostoRenovableHoraPicoComision`...): **2⁵ = 32
clases**, y un sexto ajuste duplicaría esa cifra. ¿Cómo agregar estas
funcionalidades sin crear 2ⁿ combinaciones de clases?

## Cómo funciona

- **Component `CostoEnergia`:** interfaz común: `total()` y `desglose()`.
- **ConcreteComponent `CostoBase`:** el objeto base al que se le añaden
  capas: `cantidad_kwh x precio_kwh`, sin ajustes.
- **Decorator `AjusteCosto`:** mantiene la referencia al componente envuelto
  (`- componente: CostoEnergia`) y **delega** en él; luego añade su capa.
  `AjustePorcentual` es un decorador intermedio para los ajustes
  proporcionales.
- **ConcreteDecorators:** `DescuentoEnergiaRenovable`,
  `DescuentoCompradorFrecuente`, `RecargoHoraPico`, `CargoUsoRed`,
  `ComisionPlataforma`. Cada uno puede añadir comportamiento antes o después
  de delegar (aquí: después, sobre el subtotal acumulado).
- **Registro:** `obtener_ajuste(nombre)` y `aplicar_ajustes(costo, nombres)`:
  punto único donde se resuelven los decoradores por nombre; un nombre
  desconocido lanza `ValueError` con los disponibles, igual que
  `obtener_factory`, `obtener_canal`, `crear_builder` y `obtener_pasarela`.
- **Uso real:** al cerrar cada transacción, `PlataformaEnergia._ajustes_para()`
  decide **qué** capas le corresponden (y en qué orden: descuentos → recargos
  → cargo fijo → comisión), `_calcular_costo()` envuelve el `CostoBase` con
  ellas, y la transacción guarda `subtotal`, `ajustes` (desglose) y `total`.
  Ese `total` ya ajustado es el que cobra la pasarela de pago (**Adapter**).
  Además, `POST /precios/cotizar` y el **Cotizador** de la pestaña Mercado
  permiten elegir los ajustes y su orden a mano.

```python
costo = ComisionPlataforma(RecargoHoraPico(DescuentoEnergiaRenovable(CostoBase(10, 0.20))))
costo.total()      # 2.00 → 1.80 → 2.07 → 2.17
costo.desglose()   # una línea por capa, en el orden en que se aplicaron

aplicar_ajustes(CostoBase(10, 0.20), ["frecuente", "uso_red", "comision"]).total()  # 2.21
```

## Qué le aporta a la plataforma

- **Más flexible que la herencia:** los ajustes se apilan en tiempo de
  ejecución según el contexto de cada transacción (vendedor, historial del
  comprador, hora).
- **Evita la explosión combinatoria:** 5 clases cubren las 32 combinaciones;
  la prueba `test_cinco_clases_cubren_las_32_combinaciones` las recorre todas.
- **Abierto/cerrado:** un ajuste nuevo (p. ej. un subsidio por estrato) es un
  decorador más; ni `CostoBase` ni los demás ajustes cambian. La prueba
  `test_se_puede_agregar_un_ajuste_sin_modificar_los_existentes` lo
  demuestra con un `SubsidioEstrato` definido dentro del propio test.
- **No modifica el objeto base:** decorar un `CostoBase` no cambia su total;
  se puede reutilizar para cotizar otras combinaciones.
- **Trazabilidad:** el desglose capa por capa queda guardado en cada
  transacción y se ve en la pestaña Historial.

## Ventajas y desventajas (vistas en clase)

| Ventajas | Desventajas | Cómo se ve aquí |
|---|---|---|
| Más flexible que la herencia | Muchos objetos pequeños | Cada ajuste es un objeto que envuelve al anterior |
| Evita explosión combinatoria | Identidad del objeto | El decorado **no** es el `CostoBase` (`test_el_decorado_no_es_el_objeto_base`) |
| Abierto/cerrado | El orden importa | `uso_red → renovable` = $1.98, `renovable → uso_red` = $2.00 (`test_el_orden_de_los_ajustes_importa`) |
| Composición en cualquier orden | Complejidad de la interfaz | La interfaz se mantiene mínima: `total()` y `desglose()` |

Por eso la plataforma fija el orden en un solo lugar (`_ajustes_para`), en
lugar de dejar que cada punto del código decida cómo apilar las capas.

## Diagrama

Diagrama UML de clases: [`UML_Decorator.png`](UML_Decorator.png) (también en el documento Word).

```
                 «interface» CostoEnergia                     (Component)
                 + total() / desglose()
                              ▲
              ┌───────────────┴────────────────┐
         CostoBase                       AjusteCosto                  (Decorator)
         (ConcreteComponent)             - componente: CostoEnergia ◇──► CostoEnergia
         + total()                       + total()  → delega + su capa
                                                ▲
                                   ┌────────────┴────────────┐
                           AjustePorcentual             CargoUsoRed      (ConcreteDecorator)
                           (subtotal x %)               (+$0.20 fijo)
                                   ▲
        ┌──────────────────┬───────┴──────────┬───────────────────┐      (ConcreteDecorators)
 DescuentoEnergia   DescuentoComprador   RecargoHoraPico    ComisionPlataforma
 Renovable (-10%)   Frecuente (-5%)      (+15%)             (+5%)
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 8/test_decorator.py" -v   # 24 casos
python "Documentacion/Semana 8/decorator.py"                     # demo por consola
```
