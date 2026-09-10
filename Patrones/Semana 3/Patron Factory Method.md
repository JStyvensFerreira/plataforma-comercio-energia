# Patrón Factory Method — Plataforma de Comercio de Energía

Implementación del patrón **Factory Method** (Método de Fábrica) sobre la
**integración de dispositivos IoT domésticos** de la plataforma: paneles solares,
baterías inteligentes y medidores.

- Código del patrón (con demo y docstring explicativo): [`factory_method.py`](factory_method.py)
- Pruebas del patrón: [`test_factory_method.py`](test_factory_method.py)
- Documento de casos de prueba: [`Patrones/README.md`](../README.md#casos-de-prueba--factory-method)
- Escenario en la aplicación: la conexión de dispositivos IoT en [`plataforma-energia-app/backend/plataforma.py`](../../plataforma-energia-app/backend/plataforma.py) (`conectar_dispositivo`, `UMBRALES_IOT`) y el selector de **tipo** del panel *IoT & Predicción* del frontend. La decisión "según el tipo, crear el dispositivo adecuado y simular su lectura" es justo lo que el Factory Method encapsula.

## Por qué este patrón aquí

La plataforma debe integrar distintos **tipos** de dispositivos IoT y cada uno se
comporta de forma diferente al generar sus lecturas:

- Un **panel solar** solo produce energía → su lectura siempre es positiva.
- Una **batería** puede cargar o descargar → su lectura puede ser positiva o negativa.
- Un **medidor** solo registra consumo → su lectura siempre es negativa.

Sin el patrón, el código que da de alta un dispositivo tendría que decidir con
`if/elif` qué clase instanciar y cómo simular sus lecturas:

```python
if tipo == "panel_solar":
    lectura = random.uniform(0.5, 4.0)
elif tipo == "bateria":
    lectura = random.uniform(-2.5, 2.5)
elif tipo == "medidor":
    lectura = -random.uniform(0.3, 3.0)
```

Cada vez que se agrega un tipo nuevo (por ejemplo, un cargador de vehículo
eléctrico) habría que modificar esa lógica central, violando el principio
abierto/cerrado.

## Cómo funciona

- **Producto abstracto `DispositivoIoT`:** define la interfaz común
  (`generar_lectura()`, propiedad `tipo`, `to_dict()`) que todo dispositivo debe
  cumplir.
- **Productos concretos:** `PanelSolar`, `BateriaInteligente` y
  `MedidorInteligente` implementan esa interfaz, cada uno con su propio rango de
  lectura.
- **Creador abstracto `DispositivoIoTFactory`:** declara el **factory method**
  `crear_dispositivo(id, usuario_id)` y un método común `registrar(...)` que
  reutiliza el producto devuelto por el factory method sin conocer su clase
  concreta (deja una traza `[Factory Method]`).
- **Creadores concretos:** `PanelSolarFactory`, `BateriaFactory` y
  `MedidorFactory` — cada uno sabe instanciar **su** producto.
- **Registro:** `obtener_factory(tipo)` / `crear_dispositivo(tipo, id, usuario_id)`
  — punto único donde se resuelve qué fábrica usar según el `tipo`; un tipo
  desconocido lanza `ValueError` con la lista de tipos válidos.

```python
d = crear_dispositivo("bateria", "bat-01", "u1")   # el cliente solo conoce el string
d.generar_lectura()        # -> valor en [-2.5, 2.5], propio de una batería
crear_dispositivo("cargador_ev", "ev-01", "u1")     # -> ValueError con los tipos válidos
```

## Qué le aporta a la plataforma

- **El cliente nunca instancia clases concretas:** el código que registra
  dispositivos (o el endpoint de FastAPI) solo pasa un `tipo`; el factory method
  decide qué producto construir.
- **Extensible sin tocar lo existente:** sumar un cargador de vehículo eléctrico
  es agregar `CargadorEV` + `CargadorEVFactory` y registrarla; el resto no cambia.
- **Lecturas y predicción realistas por tipo:** al delegar `generar_lectura()` en
  el producto, la simulación y la predicción salen coherentes con cada dispositivo
  automáticamente.
- **Relación con el Abstract Factory del proyecto:** el Factory Method crea **un**
  producto (`DispositivoIoT`); el Abstract Factory crea una **familia** de
  productos relacionados que deben usarse juntos (los tres notificadores de un
  canal).

## Diagrama

```
        DispositivoIoTFactory  (creador abstracto)
        + crear_dispositivo(id, usuario_id)   ← factory method
        + registrar(id, usuario_id)           ← lógica común
                 ▲              ▲              ▲
        ┌────────┘       ┌──────┘       ┌──────┘
 PanelSolarFactory   BateriaFactory   MedidorFactory   (creadores concretos)
        │                  │                │
     PanelSolar     BateriaInteligente  MedidorInteligente   (productos concretos)
        └──────────────────┴────────────────┘
                    DispositivoIoT  (producto abstracto: interfaz común)
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Patrones/Semana 3/test_factory_method.py" -v   # 16 casos
python validar_pruebas.py factory                                # resumen del patrón
python "Patrones/Semana 3/factory_method.py"                    # demo por consola
```
