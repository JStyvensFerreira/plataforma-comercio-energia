# Documento de Pruebas — Patrones de Diseño

Pruebas automatizadas (pytest) que validan la implementación de cada patrón
de diseño aplicado en la Plataforma de Comercio de Energía.

Cada patrón vive en su propia carpeta dentro de `src/`, junto con su código y
sus pruebas:

```
src/
├── singleton/
│   ├── plataforma_energia.py   # código del patrón
│   ├── test_singleton.py       # pruebas del patrón
│   └── conftest.py             # reinicia el Singleton entre pruebas
└── factory_method/
    ├── factory_method.py       # código del patrón
    ├── test_factory_method.py  # pruebas del patrón
    └── conftest.py
```

| Patrón | Módulo bajo prueba | Archivo de pruebas |
|---|---|---|
| Singleton | [`plataforma_energia.py`](singleton/plataforma_energia.py) | [`test_singleton.py`](singleton/test_singleton.py) |
| Factory Method | [`factory_method.py`](factory_method/factory_method.py) | [`test_factory_method.py`](factory_method/test_factory_method.py) |

## Cómo ejecutar

```bash
# desde la raíz del repositorio
pip install -r requirements-dev.txt
python -m pytest
```

Opciones útiles:

```bash
python -m pytest src/singleton                     # solo un patrón
python -m pytest -k subasta                        # por palabra clave
python -m pytest -q                                # salida compacta
python -m pytest -v                                # detalle por caso (por defecto)
```

- Configuración en [`pytest.ini`](../pytest.ini).
- Cada carpeta de patrón tiene su propio `conftest.py`, que añade esa carpeta al
  `sys.path`. El de [`singleton/`](singleton/conftest.py) además **reinicia el
  Singleton** (`SingletonMeta._instances`) antes y después de cada prueba, para
  que los casos sean independientes.

## Resultado esperado

```
src\factory_method\test_factory_method.py ................               [ 47%]
src\singleton\test_singleton.py ..................                       [100%]

34 passed
```

---

## Casos de prueba — Singleton

Verifica que `PlataformaEnergia` siempre devuelve la misma instancia y opera
sobre un único estado compartido, incluso bajo concurrencia.

| # | Caso | Qué valida |
|---|---|---|
| S-01 | `test_dos_instanciaciones_devuelven_el_mismo_objeto` | `PlataformaEnergia() is PlataformaEnergia()` |
| S-02 | `test_el_id_de_memoria_no_cambia` | Misma dirección de memoria en dos llamadas |
| S-03 | `test_solo_se_registra_una_instancia_en_la_metaclase` | `SingletonMeta._instances` contiene 1 sola entrada |
| S-04 | `test_init_se_ejecuta_una_sola_vez` | Una segunda "creación" no reinicializa el estado |
| S-05 | `test_los_cambios_en_una_referencia_se_ven_en_la_otra` | Estado compartido entre referencias distintas |
| S-06 | `test_registrar_usuario_es_idempotente` | Registrar el mismo id no duplica usuarios |
| S-07 | `test_multiples_hilos_obtienen_la_misma_instancia` | 20 hilos concurrentes → 1 sola instancia (Lock + doble verificación) |
| S-08 | `test_publicar_venta_crea_orden_con_tipo_correcto` | `Orden` de tipo `"venta"` añadida al libro |
| S-09 | `test_ids_de_orden_son_incrementales_y_unicos` | Contador de órdenes 1, 2, 3… sin repetir |
| S-10 | `test_empareja_compra_y_venta_al_precio_del_vendedor` | La subasta cierra al precio pedido por el vendedor |
| S-11 | `test_orden_parcialmente_ejecutada_permanece_con_el_saldo` | El excedente no vendido queda en el libro |
| S-12 | `test_no_hay_cruce_si_el_comprador_paga_menos_que_el_vendedor` | Sin transacción si no hay solape de precios |
| S-13 | `test_la_transaccion_queda_en_el_historial` | La operación cerrada se persiste en el historial |
| S-14 | `test_conectar_dispositivo_lo_registra_y_prepara_sus_lecturas` | Alta de dispositivo IoT + buffer de lecturas |
| S-15 | `test_enviar_lectura_a_dispositivo_no_registrado_lanza_error` | `ValueError` si el dispositivo no existe |
| S-16 | `test_simular_lecturas_agrega_n_valores` | `simular_lecturas(n=5)` añade 5 lecturas |
| S-17 | `test_prediccion_es_media_movil_de_la_ventana` | `predecir_siguiente_valor` = media de la ventana |
| S-18 | `test_prediccion_sin_lecturas_devuelve_none` | Devuelve `None` cuando no hay datos |

## Casos de prueba — Factory Method

Verifica que el código cliente nunca instancia clases concretas de dispositivo:
cada fábrica concreta decide qué producto crear y agregar un tipo nuevo no
obliga a modificar el código existente.

| # | Caso | Qué valida |
|---|---|---|
| F-01 | `test_no_se_puede_instanciar_el_producto_abstracto` | `DispositivoIoT` abstracto → `TypeError` |
| F-02 | `test_no_se_puede_instanciar_el_creador_abstracto` | `DispositivoIoTFactory` abstracto → `TypeError` |
| F-03 | `test_devuelve_la_fabrica_concreta_correcta` (x3) | `obtener_factory(tipo)` retorna la fábrica esperada |
| F-04 | `test_tipo_no_soportado_lanza_value_error_con_los_disponibles` | Tipo desconocido → `ValueError` con la lista de tipos válidos |
| F-05 | `test_crear_dispositivo_devuelve_la_subclase_esperada` (x3) | El Factory Method construye el producto concreto correcto y respeta la interfaz común |
| F-06 | `test_cada_fabrica_concreta_construye_su_propio_producto` | `PanelSolarFactory`→`PanelSolar`, etc. |
| F-07 | `test_registrar_devuelve_el_producto_creado` | `registrar()` retorna el producto del Factory Method |
| F-08 | `test_registrar_emite_traza_del_factory_method` | La lógica común del creador registra la traza `[Factory Method]` |
| F-09 | `test_panel_solar_solo_produce_energia` | Lectura del panel siempre en `[0.5, 4.0]` (producción) |
| F-10 | `test_bateria_puede_cargar_o_descargar` | Lectura de la batería en `[-2.5, 2.5]` (carga/descarga) |
| F-11 | `test_medidor_solo_registra_consumo` | Lectura del medidor siempre `<= 0` (demanda) |
| F-12 | `test_to_dict_incluye_el_tipo_concreto` | La serialización expone el `tipo` del producto concreto |
