# Patrón Template Method — Plataforma de Comercio de Energía

Implementación del patrón **Template Method** sobre la **liquidación del
periodo**: al cerrar el mes, comprador y vendedor se liquidan con el mismo
algoritmo (validar el periodo, tomar sus transacciones, sumar, aplicar
cargos, calcular el neto y armar el resumen); cada rol solo completa los
pasos que le son propios.

- Código del patrón (con demo y docstring explicativo): [`template_method.py`](template_method.py)
- Pruebas del patrón: [`test_template_method.py`](test_template_method.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--template-method)
- Uso real en la aplicación: [`plataforma-energia-app/backend/liquidaciones.py`](../../plataforma-energia-app/backend/liquidaciones.py) — usado por `liquidar_periodo` en [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py), expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`GET /liquidacion?rol=&periodo=`)

## Por qué este patrón aquí

Las dos liquidaciones comparten casi todo el algoritmo y difieren en
detalles: qué transacciones le corresponden a cada uno, qué importe cuenta,
qué cargos se le aplican y si esos cargos se suman (el comprador paga más)
o se descuentan (el vendedor recibe menos). Si cada liquidación repitiera
el algoritmo completo, una corrección en un paso común (cómo se filtra el
periodo, cómo se redondea) habría que hacerla en cada copia, y nada
garantizaría que los pasos se ejecuten en el mismo orden.

## Cómo funciona

- **Abstract Class `LiquidacionPeriodo`:** `liquidar(transacciones, usuario, periodo)`
  es el **método plantilla**; ninguna subclase lo redefine.

| Paso | Tipo | Quién lo da |
|---|---|---|
| 1. `_validar_periodo` (AAAA-MM) | común | clase abstracta |
| 2. `_del_periodo` | común | clase abstracta |
| 3. `_es_suyo` / `_es_suya` | **abstracto** | cada rol |
| 4. `_bruto` | común (en la app usa el paso abstracto `_importe`) | clase abstracta |
| 5. `_cargos` | **gancho** (por defecto, ninguno) | cada rol, si quiere |
| 6. `_signo_neto` | **gancho** (por defecto, +1) | el vendedor lo cambia a −1 |
| 7. `_resumen` (usa el paso abstracto `_concepto`) | común | clase abstracta |

- **Concrete Classes:**
  - `LiquidacionComprador`: sus compras; suma una contribución del 2 %;
    concepto «Total a pagar».
  - `LiquidacionVendedor`: sus ventas; descuenta comisión de la plataforma
    (3 %) y retención en la fuente (1 %); concepto «Total a recibir».
- **Uso real:** en la app el comprador liquida el `total` que pagó (ya con
  los ajustes del Decorator) y el vendedor el `subtotal`, que es el valor de
  su energía; por eso `_importe` es un paso abstracto más. La API responde
  **400** a un rol o periodo inválido. En el frontend: pestaña
  «Operaciones», tarjeta «Liquidación del periodo».

```python
liquidacion = LiquidacionVendedor().liquidar(movimientos, "ana", "2026-11")
liquidacion["bruto"], liquidacion["neto"]   # 2200, 2112.0
```

## Qué le aporta a la plataforma

- **Un solo algoritmo:** el orden de los pasos está en un único lugar; las
  subclases no pueden alterarlo.
- **Sin duplicación:** filtrar el periodo, sumar y armar el resumen se
  escriben una vez.
- **Extensión controlada:** un rol nuevo (por ejemplo, la comunidad como
  intermediaria) es una subclase con dos o tres métodos.
- **Ganchos:** una subclase que no necesita cargos simplemente no redefine
  `_cargos`.
- **Desventaja:** la herencia ata a las subclases al esqueleto; si un rol
  necesitara un orden distinto, Template Method ya no sirve y convendría
  Strategy.

## Diagrama

```
                  LiquidacionPeriodo (Abstract Class)
                  + liquidar(transacciones, usuario, periodo)   ← método plantilla
                  # _validar_periodo, _del_periodo, _bruto, _resumen   (comunes)
                  # _es_suyo(), _concepto()                           (abstractos)
                  # _cargos() → []   ·   _signo_neto() → +1           (ganchos)
                                 ▲
               ┌─────────────────┴──────────────────┐
     LiquidacionComprador                   LiquidacionVendedor
     _es_suyo: tx.comprador == usuario      _es_suyo: tx.vendedor == usuario
     _cargos: contribución 2 %              _cargos: comisión 3 % + retención 1 %
     _concepto: "Total a pagar"             _signo_neto: −1 · "Total a recibir"
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 15/test_template_method.py" -v   # 19 casos
python "Documentacion/Semana 15/template_method.py"                     # demo por consola
```
