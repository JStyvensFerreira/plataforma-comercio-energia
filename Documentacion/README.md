# Documento de Pruebas — Patrones de Diseño

Pruebas automatizadas (pytest) que validan la implementación de cada patrón
de diseño aplicado en la Plataforma de Comercio de Energía.

Los patrones están organizados por semana dentro de `Documentacion/`; los archivos
de cada patrón (explicación, código, pruebas y `conftest.py`) viven directamente en
la carpeta de su semana:

```
Documentacion/
├── Semana 2/                        # Singleton
│   ├── Patron Singleton.md
│   ├── UML_Singleton.png            # diagrama UML de clases
│   ├── plataforma_energia.py
│   ├── test_singleton.py
│   └── conftest.py                  # reinicia el Singleton entre pruebas
├── Semana 3/                        # Factory Method
│   ├── Patron Factory Method.md
│   ├── UML_FactoryMethod.png
│   ├── factory_method.py
│   ├── test_factory_method.py
│   └── conftest.py
├── Semana 4/                        # Abstract Factory
│   ├── Patron Abstract Factory.md
│   ├── UML_AbstractFactory.png
│   ├── abstract_factory.py
│   ├── test_abstract_factory.py
│   └── conftest.py
├── Semana 5/                        # Builder
│   ├── Patron Builder.md
│   ├── UML_Builder.png
│   ├── builder.py
│   ├── test_builder.py
│   └── conftest.py
└── Semana 6/                        # Prototype
    ├── Patron Prototype.md
    ├── prototype.py
    ├── test_prototype.py
    └── conftest.py
```

Cada carpeta incluye además el **diagrama UML de clases** del patrón (generado a
partir del código real), embebido también en el documento Word (Figuras 16-19)
junto con una sección de evaluación de si el patrón se justifica para el proyecto.

| Patrón | Semana | Explicación | Módulo bajo prueba | Archivo de pruebas | Diagrama UML |
|---|---|---|---|---|---|
| Singleton | 2 | [`Patron Singleton.md`](Semana%202/Patron%20Singleton.md) | [`plataforma_energia.py`](Semana%202/plataforma_energia.py) | [`test_singleton.py`](Semana%202/test_singleton.py) | [`UML_Singleton.png`](Semana%202/UML_Singleton.png) |
| Factory Method | 3 | [`Patron Factory Method.md`](Semana%203/Patron%20Factory%20Method.md) | [`factory_method.py`](Semana%203/factory_method.py) | [`test_factory_method.py`](Semana%203/test_factory_method.py) | [`UML_FactoryMethod.png`](Semana%203/UML_FactoryMethod.png) |
| Abstract Factory | 4 | [`Patron Abstract Factory.md`](Semana%204/Patron%20Abstract%20Factory.md) | [`abstract_factory.py`](Semana%204/abstract_factory.py) | [`test_abstract_factory.py`](Semana%204/test_abstract_factory.py) | [`UML_AbstractFactory.png`](Semana%204/UML_AbstractFactory.png) |
| Builder | 5 | [`Patron Builder.md`](Semana%205/Patron%20Builder.md) | [`builder.py`](Semana%205/builder.py) | [`test_builder.py`](Semana%205/test_builder.py) | [`UML_Builder.png`](Semana%205/UML_Builder.png) |
| Prototype | 6 | [`Patron Prototype.md`](Semana%206/Patron%20Prototype.md) | [`prototype.py`](Semana%206/prototype.py) | [`test_prototype.py`](Semana%206/test_prototype.py) | — |

## Cómo ejecutar

```bash
# desde la raíz del repositorio
pip install -r requirements-dev.txt
python -m pytest
```

Opciones útiles:

```bash
python -m pytest "Documentacion/Semana 3"           # solo una semana
python -m pytest -k subasta                         # por palabra clave
python -m pytest -q                                 # salida compacta
python -m pytest -v                                 # detalle por caso (por defecto)
```

- Configuración en [`pytest.ini`](../pytest.ini).
- Cada carpeta de semana tiene su propio `conftest.py`, que añade esa carpeta al
  `sys.path`. El de [`Semana 2/`](Semana%202/conftest.py) además **reinicia el
  Singleton** (`SingletonMeta._instances`) antes y después de cada prueba, para
  que los casos sean independientes.

## Resultado esperado

```
Documentacion\Semana 2\test_singleton.py ..................              [ 15%]
Documentacion\Semana 3\test_factory_method.py ................           [ 29%]
Documentacion\Semana 4\test_abstract_factory.py ........................ [ 50%]
Documentacion\Semana 5\test_builder.py ..............................    [ 79%]
Documentacion\Semana 6\test_prototype.py ........................        [100%]

115 passed
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

## Casos de prueba — Abstract Factory

Verifica que el código cliente (`ServicioNotificaciones`) nunca instancia
notificadores concretos: cada fábrica de canal crea la **familia completa** de
notificadores de ese canal (transacción + alerta IoT + reporte), todos coherentes
entre sí, y agregar un canal nuevo no obliga a modificar el código existente.

| # | Caso | Qué valida |
|---|---|---|
| A-01 | `test_no_se_puede_instanciar_la_fabrica_abstracta` | `CanalNotificacionFactory` abstracta → `TypeError` |
| A-02 | `test_no_se_pueden_instanciar_los_productos_abstractos` (x3) | Los tres productos abstractos → `TypeError` |
| A-03 | `test_devuelve_la_fabrica_de_canal_correcta` (x3) | `obtener_canal(nombre)` retorna la fábrica esperada y su `canal` coincide |
| A-04 | `test_canal_no_soportado_lanza_value_error_con_los_disponibles` | Canal desconocido → `ValueError` con la lista de canales válidos |
| A-05 | `test_crea_los_tres_miembros_de_la_familia` (x3) | Cada fábrica construye los tres notificadores con la interfaz común |
| A-06 | `test_los_notificadores_no_son_las_clases_abstractas` (x3) | Los productos devueltos son subclases concretas, no las ABC |
| A-07 | `test_todos_los_mensajes_salen_por_el_mismo_canal` (x3) | Los tres mensajes de un servicio llevan el mismo `canal` |
| A-08 | `test_no_se_pueden_mezclar_canales_en_una_misma_familia` | Un servicio nunca emite un mensaje de un canal ajeno |
| A-09 | `test_email_siempre_lleva_asunto_y_cuerpo_largo` | Toda la familia email lleva asunto y firma, sin `datos` |
| A-10 | `test_sms_no_lleva_asunto_y_respeta_el_limite_de_160` | Toda la familia SMS: sin asunto y `len(cuerpo) <= 160` |
| A-11 | `test_push_lleva_titulo_cuerpo_cortos_y_payload_estructurado` | Toda la familia push: título/cuerpo cortos + `datos["evento"]` |
| A-12 | `test_sms_recorta_los_textos_muy_largos` | El recorte del canal SMS se aplica aunque el texto sea enorme |
| A-13 | `test_construye_la_familia_una_sola_vez` | `ServicioNotificaciones` reutiliza los notificadores entre llamadas |
| A-14 | `test_transaccion_distingue_comprador_de_vendedor` | El notificador redacta según el `rol` del destinatario |
| A-15 | `test_alerta_iot_incluye_el_dispositivo_y_los_valores` | El payload de la alerta lleva `dispositivo_id`, `lectura`, `umbral` |
| A-16 | `test_reporte_expone_el_balance_en_el_payload` | El payload del reporte lleva `balance_kwh` y `transacciones` |
| A-17 | `test_se_puede_agregar_un_canal_sin_modificar_los_existentes` | Un `CanalWebhook` nuevo funciona con `ServicioNotificaciones` sin tocar nada (abierto/cerrado) |

## Casos de prueba — Builder

Verifica que el reporte energético se construye **paso a paso** mediante un
builder, que el mismo proceso de construcción produce **representaciones
distintas** (`dict`, objeto con secciones, `str`), que el `DirectorReportes`
encapsula las recetas sin conocer la representación, y que agregar un formato
nuevo no obliga a modificar el código existente.

| # | Caso | Qué valida |
|---|---|---|
| B-01 | `test_no_se_puede_instanciar_el_builder_abstracto` | `ReporteBuilder` abstracto → `TypeError` |
| B-02 | `test_devuelve_el_builder_del_formato_correcto` (x3) | `crear_builder(formato)` retorna el builder esperado y su `formato` coincide |
| B-03 | `test_registro_y_formatos_disponibles_coinciden` | `FORMATOS_DISPONIBLES` refleja el registro de builders |
| B-04 | `test_formato_no_soportado_lanza_value_error_con_los_disponibles` | Formato desconocido → `ValueError` con la lista de formatos válidos |
| B-05 | `test_reporte_completo_llama_todos_los_pasos_en_orden` | El Director llama `reiniciar` + los 6 pasos en el orden de la receta |
| B-06 | `test_reporte_ejecutivo_omite_desglose_y_prediccion` | La receta ejecutiva no invoca `desglose_dispositivos` ni `prediccion_consumo` |
| B-07 | `test_el_director_reinicia_el_builder_al_empezar_cada_receta` | Cada receta arranca con `reiniciar()`; dos recetas seguidas → 2 `reiniciar` |
| B-08 | `test_obtener_reporte_devuelve_el_tipo_propio_del_builder` (x3) | `resumen`→`dict`, `detallado`→`ReporteEnergetico`, `texto`→`str` |
| B-09 | `test_resumen_es_un_dict_plano_con_el_contrato_de_notificacion` | El `dict` del resumen expone `CLAVES_CONTRATO_NOTIFICACION` con tipos numéricos |
| B-10 | `test_detallado_es_un_objeto_con_secciones_tipadas` | `ReporteEnergetico` con secciones tituladas y sello `generado_en` |
| B-11 | `test_texto_es_una_cadena_no_vacia_con_los_datos_clave` | El `str` incluye el usuario y el balance calculado |
| B-12 | `test_dos_reportes_seguidos_no_se_contaminan` | `reiniciar` aísla dos reportes consecutivos del mismo builder |
| B-13 | `test_reiniciar_explicito_vacia_el_reporte_en_construccion` | `reiniciar()` deja el builder sin secciones ni encabezado |
| B-14 | `test_reporte_completo_incluye_las_secciones_en_orden` | Orden: Balance → Desglose → Historial → Predicción |
| B-15 | `test_reporte_ejecutivo_no_incluye_desglose_ni_prediccion` | Ejecutivo = Balance + Historial únicamente |
| B-16 | `test_reporte_para_factura_lleva_historial_y_balance_sin_prediccion` | Factura = Historial + Balance |
| B-17 | `test_una_misma_receta_sirve_para_todas_las_representaciones` (x3) | `reporte_para_factura` funciona con los tres builders |
| B-18 | `test_el_balance_es_produccion_menos_consumo` | `balance_kwh == produccion - consumo` en el resumen y en la sección detallada |
| B-19 | `test_el_resumen_cuenta_las_operaciones` | `transacciones` = número de filas del historial |
| B-20 | `test_el_desglose_separa_produccion_y_consumo_por_dispositivo` | El desglose separa kWh producidos y consumidos por dispositivo |
| B-21 | `test_los_datos_vacios_no_rompen_ningun_builder` | Un `DatosReporte` vacío se construye en los tres formatos sin error |
| B-22 | `test_cada_paso_devuelve_el_builder_para_encadenar` | Cada paso devuelve `self` (interfaz fluida) |
| B-23 | `test_encadenado_a_mano_equivale_a_la_receta_del_director` | Encadenar los pasos a mano == `DirectorReportes.reporte_ejecutivo` |
| B-24 | `test_se_puede_agregar_un_builder_sin_modificar_los_existentes` | Un `ReporteMarkdownBuilder` nuevo funciona con el `DirectorReportes` sin tocar nada (abierto/cerrado) |

## Casos de prueba — Prototype

Verifica que clonar un dispositivo IoT ya calibrado preserva su configuración
(tipo, umbrales, notas) mediante copia PROFUNDA (sin compartir estado mutable con
el original ni entre clones), que se pueden ajustar campos puntuales al clonar, y
que el `RegistroPlantillas` resuelve plantillas por nombre con el mismo contrato
que las demás fábricas del proyecto.

| # | Caso | Qué valida |
|---|---|---|
| P-01 | `test_dispositivo_implementa_la_interfaz_prototipo` | `DispositivoIoT` implementa `PrototipoDispositivo` |
| P-02 | `test_el_clon_es_un_objeto_distinto_del_original` | `clonar()` devuelve una instancia nueva, no la misma referencia |
| P-03 | `test_el_clon_tiene_el_id_nuevo` / `test_el_original_conserva_su_id` | El `id` cambia en el clon y no se altera en el original |
| P-04 | `test_sin_nuevo_usuario_el_clon_hereda_el_usuario_del_original` / `test_con_nuevo_usuario_el_clon_queda_a_nombre_de_ese_usuario` | `usuario_id` es opcional al clonar |
| P-05 | `test_el_clon_conserva_el_tipo` | El tipo de dispositivo se preserva |
| P-06 | `test_el_clon_conserva_los_umbrales_calibrados` | `umbral_min`/`umbral_max` calibrados se preservan |
| P-07 | `test_el_clon_conserva_las_notas_de_calibracion` | Las notas de calibración se preservan |
| P-08 | `test_las_notas_del_clon_no_son_el_mismo_objeto_lista` | La lista de notas del clon es un objeto distinto (copia profunda) |
| P-09 | `test_modificar_las_notas_del_clon_no_afecta_al_original` | Cambios en el clon no se filtran al original |
| P-10 | `test_dos_clones_del_mismo_original_no_comparten_las_notas` | Dos clones del mismo original no comparten la lista de notas |
| P-11 | `test_modificar_un_umbral_del_clon_no_afecta_al_original` | Los campos escalares también son independientes tras clonar |
| P-12 | `test_se_puede_ajustar_un_umbral_al_clonar` / `test_el_override_no_afecta_al_original` | `clonar(**cambios)` sobreescribe campos puntuales sin tocar el original |
| P-13 | `test_los_campos_no_sobrescritos_mantienen_el_valor_clonado` | Un override parcial no borra el resto de la configuración clonada |
| P-14 | `test_override_de_un_campo_inexistente_lanza_value_error` | Un campo inválido en `**cambios` lanza `ValueError` |
| P-15 | `test_plantilla_registrada_aparece_en_las_disponibles` | `RegistroPlantillas.plantillas_disponibles` refleja lo registrado |
| P-16 | `test_crear_desde_plantilla_devuelve_un_clon_configurado` | `crear_desde_plantilla` clona con la configuración de la plantilla |
| P-17 | `test_crear_desde_plantilla_admite_overrides` | `crear_desde_plantilla` acepta `**cambios` igual que `clonar()` |
| P-18 | `test_plantilla_inexistente_lanza_value_error_con_las_disponibles` | Plantilla desconocida → `ValueError` con las disponibles |
| P-19 | `test_registrar_una_plantilla_guarda_una_copia_no_la_referencia` | Modificar el original tras registrarlo no altera la plantilla guardada |
| P-20 | `test_dos_plantillas_distintas_producen_clones_independientes` | Dos plantillas registradas producen clones del tipo correcto cada una |
