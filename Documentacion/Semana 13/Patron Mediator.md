# Patrón Mediator — Plataforma de Comercio de Energía

Implementación del patrón **Mediator** en la **central de energía del
hogar**: el panel solar, el medidor, la batería y el punto de conexión con
el mercado no se conocen entre sí; solo avisan a `CentralEnergiaHogar`, que
decide si cargar o descargar la batería y si vender o comprar energía.

- Código del patrón (con demo y docstring explicativo): [`mediator.py`](mediator.py)
- Pruebas del patrón: [`test_mediator.py`](test_mediator.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--mediator)
- Uso real en la aplicación: [`plataforma-energia-app/backend/coordinacion_hogar.py`](../../plataforma-energia-app/backend/coordinacion_hogar.py) — usado por `coordinar_hogar` en [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py), expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`POST /hogar/coordinar`)

## Por qué este patrón aquí

El requerimiento #16 habla de hogares que **venden sus excedentes**. Para
decidir cuánto vender hay que coordinar varios dispositivos: lo que produce
el panel, lo que consume la casa, cuánto cabe o queda en la batería y a qué
precio publicar en el mercado. Si cada componente llamara directamente a
los demás (el panel a la batería, la batería al mercado, el medidor a la
batería y al mercado), se formaría una red de referencias cruzadas: cambiar
la regla «primero la batería, después el mercado» obligaría a tocar varias
clases, y la batería no podría reutilizarse sin arrastrar al panel y al
mercado.

## Cómo funciona

- **Mediator `MediadorEnergia`:** interfaz con un único método
  `notificar(emisor, evento, valor)`.
- **Colleagues (`Componente`):** cada uno guarda solo la referencia a su
  mediador.
  - `PanelSolar.reportar_generacion(kwh)` → avisa `"generacion"`.
  - `Medidor.reportar_consumo(kwh)` → avisa `"consumo"`.
  - `Bateria.cargar(kwh)` / `descargar(kwh, reserva)` → los invoca la central.
  - `PuntoMercado.vender(kwh, precio)` / `comprar(kwh, precio)` → los invoca la central.
- **ConcreteMediator `CentralEnergiaHogar`:** espera la lectura del panel y
  la del medidor del intervalo (en cualquier orden) y aplica la regla:

| Situación | Decisión de la central |
|---|---|
| excedente > 0 | carga la batería hasta su capacidad; lo que no quepa se **vende** al precio configurado (o se vierte a la red si el hogar no vende) |
| excedente < 0 | descarga la batería **sin bajar de la reserva mínima**; lo que falte se **compra** al precio máximo configurado |
| excedente = 0 | no mueve energía |

  Cada decisión queda en `registro`, para que el usuario vea por qué se
  publicó una orden.
- **Uso real:** `POST /hogar/coordinar` arma la central con los
  componentes del usuario. Si no se envían los kWh, usa la última lectura de
  sus paneles solares y medidores. La batería tiene 10 kWh por cada
  dispositivo `bateria` conectado y conserva su carga entre intervalos. El
  `PuntoMercado` recibe `publicar_venta`/`publicar_compra` de la plataforma,
  así las órdenes que decide la central entran al mismo libro, con su
  estado (State) y sus eventos (Observer). Las reglas que lee son la
  configuración del hogar versionada con **Memento**. En el frontend:
  pestaña «Mi hogar», tarjeta «Central de energía del hogar».

```python
central = CentralEnergiaHogar(panel, medidor, Bateria("bateria", 10, 6), mercado)
panel.reportar_generacion(9)
medidor.reportar_consumo(2)   # carga 4 kWh (llena) y vende 3 kWh
```

## Qué le aporta a la plataforma

- **Bajo acoplamiento:** ningún componente referencia a otro; se pueden
  probar y reutilizar por separado.
- **Reglas en un solo lugar:** cambiar la estrategia (por ejemplo, vender
  antes de cargar cuando el precio es alto) solo toca la central.
- **Integración con el mercado sin duplicar lógica:** la central publica
  órdenes reales con las mismas funciones que usa el usuario.
- **Trazabilidad:** el registro explica cada decisión.
- **Desventaja:** la central concentra mucha lógica y puede crecer hasta
  volverse un «objeto dios»; se mitiga manteniendo las reglas en métodos
  pequeños (`_repartir_excedente`, `_cubrir_deficit`).

## Diagrama

```
   «abstract» MediadorEnergia ◀──────────── mediador ─── Componente
   + notificar(emisor, evento, valor)                    - nombre
              ▲                                          ▲   ▲   ▲   ▲
              │                       ┌──────────────────┘   │   │   └───────────────┐
     CentralEnergiaHogar          PanelSolar             Medidor  Bateria         PuntoMercado
     - panel, medidor,            + reportar_generacion  + reportar_consumo        + vender(kwh, $)
       bateria, mercado ─────────────────────────────────────▶ + cargar(kwh)       + comprar(kwh, $)
     - reglas: ReglasHogar                                     + descargar(kwh, reserva)
     - registro
     - _balancear / _repartir_excedente / _cubrir_deficit

   PanelSolar ──"generacion"──▶ Central ──cargar/descargar──▶ Bateria
   Medidor    ──"consumo"────▶ Central ──vender/comprar────▶ PuntoMercado
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 13/test_mediator.py" -v   # 22 casos
python "Documentacion/Semana 13/mediator.py"                     # demo por consola
```
