# Patrón Prototype — Plataforma de Comercio de Energía

Implementación del patrón **Prototype** (Prototipo) sobre el **alta de dispositivos IoT**
de la plataforma: clonar un dispositivo ya calibrado en vez de crearlo desde cero.

- Código del patrón (con demo y docstring explicativo): [`prototype.py`](prototype.py)
- Pruebas del patrón: [`test_prototype.py`](test_prototype.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--prototype)
- Uso real en la aplicación: [`plataforma-energia-app/backend/plataforma.py`](../../plataforma-energia-app/backend/plataforma.py) (`clonar_dispositivo`) — expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`POST /iot/dispositivos/{id}/clonar`)

## Por qué este patrón aquí

El patrón **Factory Method** (Semana 3) da de alta un dispositivo IoT **desde cero**,
con los umbrales por defecto de su tipo (`UMBRALES_IOT`: panel solar, batería,
medidor). Eso alcanza para el caso general, pero no para el caso real más común
en una instalación:

- Un instalador **calibra en campo** un panel solar (ajusta `umbral_min`/`umbral_max`
  según la orientación del techo, una sombra parcial, etc.) y luego necesita dar de
  alta **varios paneles idénticos más** en la misma instalación, con exactamente esos
  umbrales ya ajustados — no los de fábrica.
- Sin Prototype, la única forma de repetir ese ajuste es que el operador vuelva a
  escribir los mismos números a mano en cada alta nueva, con el riesgo de
  transcribirlos mal o de que la fábrica termine acumulando parámetros de
  configuración que no le corresponden (deja de ser una fábrica "por tipo").

Con **PROTOTYPE**, el dispositivo ya calibrado se **clona**: el nuevo objeto nace
con el mismo estado (tipo, umbrales) sin que el cliente conozca su clase concreta
ni tenga que re-especificar cada campo, y solo cambia lo que identifica al
dispositivo nuevo (`id`, y opcionalmente el usuario o un umbral puntual).

## Cómo funciona

- **Interfaz `PrototipoDispositivo`:** declara el método abstracto `clonar()`. El
  cliente nunca llama al constructor de la clase concreta: siempre clona un objeto
  existente.
- **Producto `DispositivoIoT`:** implementa `clonar()` con **copia profunda**
  (`copy.deepcopy`) — no superficial. La demo educativa (`prototype.py`) incluye
  `notas_calibracion`, una lista mutable, precisamente para evidenciar el motivo:
  con una copia superficial, dos "clones" terminarían compartiendo la misma lista
  por referencia y una nota agregada a uno aparecería en el otro. `clonar()` acepta
  además `**cambios` para ajustar campos puntuales (p. ej. un `umbral_max` distinto)
  sin perder el resto de la configuración clonada.
- **`RegistroPlantillas` (prototype registry):** guarda dispositivos ya calibrados
  con un nombre de catálogo (`registrar_plantilla`) y los clona bajo demanda
  (`crear_desde_plantilla`) — el mismo rol que `obtener_factory` (Factory Method),
  `obtener_canal` (Abstract Factory) o `crear_builder` (Builder): un punto único
  donde se resuelve "a partir de cuál" y un `ValueError` con las opciones
  disponibles ante un nombre desconocido. Registra una **copia** del prototipo
  recibido, para que cambios posteriores al objeto original del llamador no
  contaminen la plantilla ya guardada.
- **Uso real:** `PlataformaEnergia.clonar_dispositivo()` aplica la misma idea sobre
  el dispositivo real de la app — deep-copy del original, nueva identidad, umbrales
  opcionalmente ajustables — expuesto como `POST /iot/dispositivos/{id}/clonar`.

```python
maestro = DispositivoIoT("panel-maestro", "u1", "panel_solar", umbral_min=0.0, umbral_max=2.8,
                          notas_calibracion=["Sombra parcial 14:00-16:00"])

registro = RegistroPlantillas()
registro.registrar_plantilla("panel_con_sombra", maestro)

panel_2 = registro.crear_desde_plantilla("panel_con_sombra", "panel-02")   # mismos umbrales
panel_3 = registro.crear_desde_plantilla("panel_con_sombra", "panel-03", umbral_max=3.5)  # override puntual

panel_2.notas_calibracion.append("nota exclusiva")   # no aparece en panel_3 ni en maestro
```

## Qué le aporta a la plataforma

- **No repetir configuración fina:** un ajuste de calibración hecho una vez se
  reutiliza en todas las altas siguientes, sin volver a escribir números a mano.
- **Desacopla "cómo se creó" de "a partir de qué":** el cliente clona sin conocer
  la clase concreta del original, igual que las fábricas del proyecto crean sin
  que el cliente conozca la clase concreta del producto.
- **Copia profunda por contrato:** el propio patrón obliga a decidir explícitamente
  la semántica de copia (superficial vs. profunda) para el estado mutable del
  objeto — evita un bug sutil (dos "copias" que en realidad comparten listas) que
  sería fácil pasar por alto si cada módulo clonara "a mano" con `copy.copy` o una
  asignación directa.
- **Relación con las demás fábricas del proyecto:** Factory Method y Abstract
  Factory crean objetos **desde una descripción estática** (un tipo, un canal);
  Prototype crea objetos **a partir de una instancia ya configurada en tiempo de
  ejecución**, incluyendo ajustes que nadie escribió en el código. Son
  complementarios, no compiten: la fábrica sigue siendo el punto de entrada para
  el primer dispositivo de un tipo; Prototype entra cuando ya existe uno calibrado
  y hay que repetirlo.

## Validación del patrón — ¿es viable en este proyecto?

**Sí, es viable y está integrado en la app real** (no se quedó solo como demo
educativa):

- Encaja sobre una entidad que **ya existía** (`DispositivoIoT`) sin tocar el
  Factory Method de la Semana 3 ni el resto de la plataforma — es un método
  adicional (`clonar_dispositivo`) más un endpoint nuevo, sin romper nada existente
  (los tests de Singleton/Factory Method/Abstract Factory/Builder siguen pasando).
- Resuelve un caso de uso real y frecuente en el dominio (instalaciones con varios
  dispositivos idénticos), no uno forzado para justificar el patrón.
- El costo de implementarlo fue bajo: `copy.deepcopy` + reasignar identidad: no
  necesitó infraestructura nueva ni cambiar el modelo de datos existente.
- Riesgo controlado: se probó explícitamente que la copia es profunda (las pruebas
  `test_las_notas_del_clon_no_son_el_mismo_objeto_lista` y
  `test_dos_clones_del_mismo_original_no_comparten_las_notas`), que es el error
  más común al implementar Prototype a mano.

Dónde **no** se justificaría forzar Prototype en esta plataforma: `Orden` y
`Usuario` no se benefician igual, porque su variabilidad está en campos que
cambian en *cada* instancia (usuario, cantidad, precio) más que en configuración
repetida; ahí basta con el constructor normal.

## Diagrama

```
        PrototipoDispositivo  (interfaz)
        + clonar(nuevo_id, nuevo_usuario_id, **cambios)
                 ▲
                 │ implementa
          DispositivoIoT  (producto concreto, clonable)
          - id, usuario_id, tipo
          - umbral_min, umbral_max
          - notas_calibracion  (estado mutable → exige copy.deepcopy)
                 ▲
                 │ guarda copias con nombre / clona bajo demanda
        RegistroPlantillas  (prototype registry)
        + registrar_plantilla(nombre, prototipo)
        + crear_desde_plantilla(nombre, nuevo_id, ...)  -> DispositivoIoT
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 6/test_prototype.py" -v   # 24 casos
python "Documentacion/Semana 6/prototype.py"                     # demo por consola
```
