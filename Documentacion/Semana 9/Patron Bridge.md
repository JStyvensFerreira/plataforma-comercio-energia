# Patrón Bridge — Plataforma de Comercio de Energía

Implementación del patrón **Bridge** (Puente) sobre la **sincronización de
lecturas de dispositivos IoT**: separar *cómo se sincroniza* (¿reintenta
ante fallas o no?) de *por dónde llega el dato* (¿simulado, HTTP, MQTT?),
dos cosas que varían de forma independiente.

- Código del patrón (con demo y docstring explicativo): [`bridge.py`](bridge.py)
- Pruebas del patrón: [`test_bridge.py`](test_bridge.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--bridge)
- Uso real en la aplicación: [`plataforma-energia-app/backend/sincronizacion.py`](../../plataforma-energia-app/backend/sincronizacion.py) — consumido por [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py) (`sincronizar_dispositivo`) y expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`/iot/protocolos`, `/iot/dispositivos/{id}/sincronizar`)

## Por qué este patrón aquí

Factory Method (Semana 3) resuelve **qué tipo** de dispositivo crear; pero
ya creado, falta decidir **por dónde llega** cada lectura nueva. En una
instalación real eso varía según el fabricante: unos dispositivos exponen
una API HTTP propia, otros publican por MQTT, y en desarrollo/demo basta
con simular valores. Además, independientemente del protocolo, a veces
conviene **reintentar** ante una falla de comunicación (una lectura crítica)
y a veces no (una lectura de rutina).

Son **dos cosas que varían por separado**. Si se modelara con herencia (una
subclase por combinación), agregar un protocolo nuevo o una forma de
sincronizar nueva multiplicaría las clases: `SincronizadorSimpleHTTP`,
`SincronizadorConReintentosHTTP`, `SincronizadorSimpleMQTT`,
`SincronizadorConReintentosMQTT`...

## Cómo funciona

- **Implementor `ProtocoloLectura`:** declara `leer(dispositivo, ultima_lectura)`.
  Cada protocolo concreto sabe CÓMO obtener el valor y puede fallar con
  `ConnectionError`.
- **ConcreteImplementor `ProtocoloSimulado` / `ProtocoloHTTP` / `ProtocoloMQTT`:**
  en la app real, `ProtocoloHTTP` simula la API del fabricante devolviendo un
  valor dentro de los umbrales ya calibrados del dispositivo; `ProtocoloMQTT`
  simula un valor retenido por el broker, con una variación pequeña sobre la
  última lectura.
- **Abstraction `SincronizadorDispositivo`:** el cliente programa contra
  esta clase. **Guarda una referencia** al Implementor (no hereda de él) y le
  delega la lectura — por eso es un *puente*, no una jerarquía de herencia.
- **RefinedAbstraction `SincronizadorConReintentos`:** extiende la
  Abstraction con reintentos ante `ConnectionError`. Ese comportamiento es
  el mismo sin importar cuál protocolo esté detrás.
- **Registro:** `obtener_protocolo(nombre)` resuelve el protocolo concreto
  en un punto único, con el mismo contrato (`ValueError` + disponibles) que
  las demás fábricas del proyecto.
- **Uso real:** `PlataformaEnergia.sincronizar_dispositivo(id, protocolo, con_reintentos)`
  arma la Abstraction correspondiente y registra la lectura igual que
  `enviar_lectura_iot` (umbrales, alertas). La pestaña **IoT & Predicción**
  deja elegir el protocolo y si se desean reintentos.

```python
SincronizadorDispositivo(ProtocoloHTTP()).sincronizar(dispositivo)
SincronizadorConReintentos(ProtocoloMQTT(), intentos=3).sincronizar(dispositivo)
```

## Qué le aporta a la plataforma

- **Dos jerarquías, cada una crece sola:** un protocolo nuevo (Zigbee) no
  toca `SincronizadorConReintentos`; una forma de sincronizar nueva (p. ej.
  con *circuit breaker*) no toca ningún protocolo.
- **Composición en tiempo de ejecución:** cualquier combinación se arma
  pasando el protocolo por el constructor, sin clases nuevas.
- **Abierto/cerrado:** la prueba
  `test_se_puede_agregar_un_protocolo_sin_modificar_los_existentes` lo
  demuestra con un `ProtocoloFalso` definido dentro del propio test.
- **Diferencia con Adapter (Semana 7):** Adapter traduce una interfaz
  **externa ya existente** e incompatible hacia la que el cliente espera —
  un solo eje, una sola traducción. Bridge separa **dos jerarquías que la
  plataforma diseña a la vez** para que varíen independientemente — por eso
  aquí sí tiene sentido una segunda clase (`SincronizadorConReintentos`) que
  combina con cualquier protocolo.

## Diagrama

```
      SincronizadorDispositivo              (Abstraction)
      - protocolo: ProtocoloLectura  ◇──────────┐
      + sincronizar(id)                          │
                 ▲                                ▼
                 │                     «interface» ProtocoloLectura   (Implementor)
      SincronizadorConReintentos       + leer(id) : float
      (RefinedAbstraction)                        ▲
      + sincronizar(id)  → reintenta   ┌──────────┼──────────┐
                                 ProtocoloSimulado ProtocoloHTTP ProtocoloMQTT
                                                        (ConcreteImplementor)
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 9/test_bridge.py" -v   # 18 casos
python "Documentacion/Semana 9/bridge.py"                     # demo por consola
```
