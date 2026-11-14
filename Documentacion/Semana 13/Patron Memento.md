# Patrón Memento — Plataforma de Comercio de Energía

Implementación del patrón **Memento** sobre la **configuración energética
del hogar** (reserva mínima de batería, precio de venta del excedente,
precio máximo de compra y si vende o no): antes de cada cambio se guarda
una instantánea inmutable de la versión actual, y el usuario puede deshacer
y rehacer.

- Código del patrón (con demo y docstring explicativo): [`memento.py`](memento.py)
- Pruebas del patrón: [`test_memento.py`](test_memento.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--memento)
- Uso real en la aplicación: [`plataforma-energia-app/backend/configuracion_hogar.py`](../../plataforma-energia-app/backend/configuracion_hogar.py) — usado por `configuracion_hogar`, `cambiar_configuracion_hogar`, `deshacer_configuracion_hogar` y `rehacer_configuracion_hogar` en [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py), expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`GET`/`PUT /hogar/configuracion`, `POST /hogar/configuracion/deshacer`, `POST /hogar/configuracion/rehacer`)

## Por qué este patrón aquí

Las reglas del hogar deciden dinero real: con ellas la central de energía
(Mediator) publica ventas y compras en el mercado. Un error al editarlas
(vender demasiado barato, dejar la reserva en 0 %) debe poder revertirse.
Si otro objeto copiara los atributos de la configuración para respaldarla,
conocería su estructura interna (cada campo nuevo obligaría a cambiar el
respaldo) y nada impediría modificar una copia guardada.

## Cómo funciona

- **Originator `ConfiguracionHogar`:** el único que sabe crear su
  instantánea (`guardar(etiqueta)`) y volver a ella (`restaurar(memento)`).
  `actualizar(**cambios)` valida el resultado y, si es inválido, se
  restaura a sí mismo con un memento interno: un cambio inválido no deja
  la configuración a medias.
- **Memento `MementoConfiguracion`:** `dataclass(frozen=True)`; el estado
  viaja en `_estado`, un `MappingProxyType` de solo lectura que solo lee el
  Originator. Hacia afuera expone solo `etiqueta` y `creado`.
- **Caretaker `HistorialConfiguracion`:**

| Operación | Qué hace |
|---|---|
| `cambiar(etiqueta, **cambios)` | guarda un memento de la versión actual y aplica el cambio; si el cambio es inválido no deja respaldo. Vacía la pila de rehacer |
| `deshacer()` | guarda la versión actual en «rehacer» y restaura el último memento (`SinVersiones` si no hay) |
| `rehacer()` | operación simétrica |
| `versiones()` | lista solo metadatos (etiqueta y fecha), nunca el estado |
| `limite` | conserva como máximo N versiones; descarta las más antiguas |

- **Uso real:** cada usuario tiene su configuración y su historial. La
  API responde **400** a un cambio inválido o vacío y **409** cuando no hay
  nada que deshacer/rehacer. La central de energía (Mediator) lee esta
  configuración en cada intervalo, así que deshacer un cambio cambia de
  inmediato su próxima decisión. En el frontend: pestaña «Mi hogar»,
  tarjeta «Reglas del hogar», con botones Deshacer/Rehacer y la lista de
  versiones guardadas.

```python
config = ConfiguracionHogar()
historial = HistorialConfiguracion(config)
historial.cambiar("subir precio", precio_venta_kwh=490)
historial.deshacer()   # vuelve a 450
historial.rehacer()    # otra vez 490
```

## Qué le aporta a la plataforma

- **Deshacer seguro:** un error de configuración se revierte sin
  reconstruir los valores a mano.
- **Encapsulamiento:** el historial no conoce los campos de la
  configuración; agregar uno nuevo solo toca la lista `CAMPOS` del
  Originator.
- **Instantáneas confiables:** los mementos son inmutables; nadie puede
  alterar una versión guardada.
- **Memoria acotada:** el límite de versiones evita que el historial
  crezca sin control.
- **Desventaja:** cada memento copia todo el estado; para una
  configuración de cuatro campos es despreciable, pero en objetos grandes
  convendría guardar solo diferencias.

## Diagrama

```
   ConfiguracionHogar (Originator)         MementoConfiguracion (Memento, inmutable)
   - reserva_minima_pct                    + etiqueta
   - precio_venta_kwh          crea ──────▶ + creado
   - precio_compra_max_kwh                 - _estado (solo lo lee el Originator)
   - vender_excedente                                ▲
   + guardar(etiqueta) → Memento                     │ guarda (sin abrir)
   + restaurar(memento)                              │
   + actualizar(**cambios)             HistorialConfiguracion (Caretaker)
              ▲                        - _deshacer: [Memento]
              └──────── _configuracion - _rehacer:  [Memento]
                                       + cambiar / deshacer / rehacer / versiones
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 13/test_memento.py" -v   # 18 casos
python "Documentacion/Semana 13/memento.py"                     # demo por consola
```
