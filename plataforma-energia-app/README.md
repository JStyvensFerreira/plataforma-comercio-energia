# Voltia — Plataforma de Comercio de Energía (Backend + Frontend)

Implementación full-stack del proyecto #16. Usa dos patrones de diseño de forma
real:

- **Singleton** (`plataforma.py`) — estado único compartido por todas las peticiones.
- **Abstract Factory** (`notificaciones.py`) — un canal de notificación (email /
  SMS / push) es una fábrica que crea la familia completa de avisos de ese canal.
- **Builder** (`reportes.py`) — el reporte energético se construye paso a paso, y
  el mismo proceso produce distintas representaciones (dict, objeto, texto).
- **Composite** (`jerarquia.py`) — árbol Comunidad → Hogar → Dispositivo; cada
  nivel calcula producción, consumo y balance con la misma operación recursiva.
- **Decorator** (`precios.py`) — el precio final de una transacción es el costo
  base envuelto por capas de ajuste (descuentos, recargos, cargo fijo, comisión).
- **Observer** (`eventos_mercado.py`) — el mercado avisa a sus observadores
  (estadísticas del mercado, alertas de precio de cada usuario) cada vez que se
  publica, ejecuta o cancela una orden.
- **State** (`estados_orden.py`) — cada orden delega `ejecutar`/`cancelar` en su
  estado (abierta → parcial → completada, o cancelada).
- **Visitor** (`analisis_comunidad.py`) — análisis sobre el árbol del Composite
  (huella de carbono, diagnóstico, exportar CSV) sin agregarle métodos.
- **Iterator** (`recorrido_ordenes.py`) — el libro de órdenes entrega iteradores
  (por llegada, prioridad precio-tiempo, filtrado por usuario) sin exponer sus
  listas; la subasta recorre el de prioridad.
- **Mediator** (`coordinacion_hogar.py`) — la central de energía del hogar
  coordina panel solar, medidor, batería y mercado, que no se conocen entre sí.
- **Memento** (`configuracion_hogar.py`) — la configuración del hogar guarda
  instantáneas inmutables para deshacer y rehacer cambios.

## Estructura

```
plataforma-energia-app/
├── backend/
│   ├── plataforma.py       # Lógica de dominio (Singleton PlataformaEnergia)
│   ├── notificaciones.py    # Canales de notificación (Abstract Factory)
│   ├── reportes.py          # Construcción del reporte energético (Builder)
│   ├── jerarquia.py         # Árbol energético de la comunidad (Composite)
│   ├── precios.py           # Ajustes al precio de una transacción (Decorator)
│   ├── eventos_mercado.py   # Eventos del mercado y alertas de precio (Observer)
│   ├── estados_orden.py     # Ciclo de vida de una orden (State)
│   ├── analisis_comunidad.py # Análisis sobre el árbol energético (Visitor)
│   ├── recorrido_ordenes.py # Recorridos del libro de órdenes (Iterator)
│   ├── coordinacion_hogar.py # Central de energía del hogar (Mediator)
│   ├── configuracion_hogar.py # Reglas del hogar con deshacer/rehacer (Memento)
│   ├── main.py              # API FastAPI que expone los patrones
│   └── requirements.txt
└── frontend/
    └── index.html           # Dashboard en Vue 3 (sin build, vía CDN)
```

## 0. Ejecutable sin instalar nada (Windows)

En [`Ejecutables/`](../Ejecutables/) está `Voltia-windows.exe`: al abrirlo levanta
la API y abre el dashboard en el navegador (`http://127.0.0.1:8000/app/`), sin
Python ni dependencias. Se genera con `python plataforma-energia-app/ejecutable/construir.py`
(ver [`Ejecutables/README.md`](../Ejecutables/README.md)).

## 1. Levantar el backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Verifica que quedó activo entrando a: http://localhost:8000
(deberías ver `{"mensaje": "API de la Plataforma de Comercio de Energía activa"}`)

Documentación interactiva automática (Swagger): http://localhost:8000/docs

## 2. Abrir el frontend (Vue)

No necesita build ni `npm install`: es un solo archivo HTML que carga Vue 3
desde un CDN. Simplemente:

- Haz doble clic en `frontend/index.html`, o
- Sírvelo con un servidor simple: `python -m http.server 5500` dentro de `frontend/`

Al abrirlo, confirma que el campo de la API (arriba a la derecha) diga
`http://localhost:8000` y que el punto de estado esté en verde.

## 3. Flujo de prueba sugerido

1. **Login** → regístrate como `u1` / Ana eligiendo canal **push**, luego cierra sesión y regístrate como `u2` / Luis con canal **sms**
2. **Mercado** → con la sesión de Ana publica una venta (10 kWh a $0.15); cambia de sesión a Luis y publica una compra (6 kWh a $0.18)
3. Haz clic en **"Ejecutar subasta"** → se genera una transacción
4. **Notificaciones** → cada usuario ve el aviso de la operación **con el formato de su canal** (Ana un push con payload, Luis un SMS ≤ 160). Cambia tu canal y genera un reporte para verlo.
5. **IoT & Predicción** → conecta un panel solar, simula lecturas; si alguna cae fuera del rango normal del dispositivo, llega una **alerta IoT** por tu canal.
6. **Historial** → revisa las transacciones cerradas: cada una muestra el subtotal, las capas de ajuste aplicadas (Decorator) y el total cobrado
7. **Comunidad** → mira el árbol Comunidad → Hogar → Dispositivo con la producción, el consumo y el balance de cada nivel (Composite)
8. **Mercado → Cotizador** → marca ajustes en distinto orden y compara el total (Decorator)
9. **Mercado → Alerta de precio** → con Luis suscríbete con máximo $0.16; con Ana publica una venta a $0.15: a Luis le llega «Alerta de precio» en Notificaciones (Observer). Las estadísticas del mercado se actualizan solas.
10. **Mercado → Libro de órdenes** → cada orden muestra su estado; tras una subasta parcial queda `parcial`, y «Cancelar» la pasa a `cancelada` (un segundo intento responde 409). La tabla «Órdenes cerradas» muestra las transiciones (State)
11. **Comunidad → Análisis** → elige huella de carbono, diagnóstico o exportar CSV (Visitor)
12. **Mercado → Libro de órdenes → Recorrido** → cambia entre «Por llegada» y «Prioridad de subasta», y marca «Solo mis órdenes» (Iterator)
13. **IoT** → conecta un dispositivo `bateria`; luego **Mi hogar → Central de energía** → coordina un intervalo con generación 9 y consumo 2: la batería se carga y lo que no cabe se publica como venta en el libro (Mediator)
14. **Mi hogar → Reglas del hogar** → cambia el precio de venta o desactiva «Vender excedente», guarda, y usa Deshacer/Rehacer; la próxima coordinación usa la versión vigente (Memento)

## Por qué el Abstract Factory aquí

La plataforma avisa en tres momentos distintos —cierre de subasta, alerta de una
lectura IoT fuera de rango y reporte periódico— y cada usuario elige su canal
(`canal_notificacion`). En `plataforma.py`, `_servicio_notificaciones(usuario_id)`
llama a `crear_servicio(canal)` (en `notificaciones.py`): esa **fábrica abstracta**
construye la familia completa de notificadores de ese canal, todos coherentes
entre sí (el SMS nunca lleva asunto ni pasa de 160 caracteres; el push siempre
lleva `payload`). El resto del código no conoce ninguna clase concreta de
notificador, y añadir WhatsApp o Telegram sería solo una fábrica más.

Endpoints que lo exponen: `GET /notificaciones`, `GET /notificaciones/canales`,
`PUT /usuarios/me/canal`, `POST /reportes/generar`.

## Por qué el Builder aquí

El reporte energético (`POST /reportes/generar`) es un objeto con varias partes
opcionales —balance, desglose por dispositivo, historial de operaciones,
predicción— y que se necesita en varias representaciones. En `plataforma.py`,
`_recolectar_datos_reporte(usuario_id)` arma un `DatosReporte` con la materia
prima, y `DirectorReportes` (en `reportes.py`) lo construye **paso a paso** con
el builder del formato pedido:

- `formato=resumen` → `dict` plano; es justo el que consume el
  `FormateadorReporte` del Abstract Factory, así que el aviso sigue saliendo por
  el canal del usuario sin código de adaptación.
- `formato=detallado` → objeto con secciones tipadas (lo que muestra el panel).
- `formato=texto` → cadena lista para un correo o un `.txt`.

Agregar un formato (Markdown, PDF) es un builder concreto más, sin tocar el
Director ni los demás. Endpoints: `POST /reportes/generar?formato=…`,
`GET /reportes/formatos`.

## Por qué el Composite aquí

La energía de la plataforma es naturalmente jerárquica: la comunidad tiene
hogares (uno por usuario) y cada hogar tiene sus dispositivos IoT. En
`plataforma.py`, `arbol_energetico()` arma ese árbol con `GrupoEnergetico`
(composite) y `DispositivoHoja` (hoja) desde el estado del Singleton. Producción,
consumo y balance se piden igual a un panel solar que a la comunidad entera: cada
grupo delega en sus hijos. Agregar un nivel nuevo (edificio, barrio) es solo
anidar otro grupo, sin escribir código de suma por nivel.

Endpoint: `GET /comunidad/arbol` (pestaña **Comunidad**).

## Por qué el Decorator aquí

Al cerrar una transacción, el total que se cobra no es solo `cantidad x precio`:
se le aplican capas según el contexto. `_ajustes_para()` decide cuáles y en qué
orden (descuento renovable si el vendedor tiene panel solar, descuento si el
comprador es frecuente, recargo en hora pico 18:00–21:00, cargo por uso de red y
comisión), y `_calcular_costo()` envuelve el `CostoBase` con esos decoradores.
La transacción guarda `subtotal`, `ajustes` y `total`, y ese `total` es el que
cobra la pasarela (Adapter). Con 5 decoradores se cubren las 32 combinaciones
sin una clase por combinación.

Endpoints: `GET /precios/ajustes`, `POST /precios/cotizar` (Cotizador en la
pestaña **Mercado**).

## Por qué el Observer aquí

Cuando aparece una oferta de venta barata, un comprador quiere enterarse sin
refrescar el libro de órdenes, y las estadísticas del mercado deben actualizarse
con cada transacción. `PlataformaEnergia` tiene un `MercadoEventos` (Subject):
`publicar_venta`, `publicar_compra`, `ejecutar_subasta` y `cancelar_orden` solo
llaman `mercado.notificar(...)`, sin saber quién escucha. `EstadisticasMercado`
está suscrito desde el arranque, y cada usuario suscribe su propia `AlertaPrecio`,
que deja el aviso en su bandeja por su canal (Abstract Factory).

Endpoints: `GET/POST/DELETE /mercado/alertas`, `GET /mercado/estadisticas`.

## Por qué el State aquí

Una orden no se comporta igual durante toda su vida: abierta o parcial se puede
ejecutar o cancelar; completada o cancelada ya no. La clase `Orden` delega
`ejecutar`, `cancelar` y `puede_negociar` en su estado (`estados_orden.py`), y es
el estado el que decide la transición. La subasta ya no resta cantidades a mano:
llama `orden.ejecutar(cantidad)`.

Endpoints: `POST /ordenes/{id}/cancelar` (403 si no es tuya, 409 si su estado no
lo permite), `GET /ordenes/historial`.

## Por qué el Visitor aquí

Sobre el árbol del Composite aparecen análisis nuevos (CO₂ evitado por hogar,
hogares en déficit, exportar a CSV). En vez de agregarle un método por análisis a
`DispositivoHoja` y `GrupoEnergetico`, cada nodo implementa `aceptar(visitante)` y
cada análisis es un visitante en `analisis_comunidad.py`.

Endpoints: `GET /comunidad/analisis`, `GET /comunidad/analisis/{analisis}`.

## Por qué el Iterator aquí

La subasta reordenaba en sitio (`sort`) las mismas listas que leían la API y el
frontend. Ahora `LibroOrdenes` (`recorrido_ordenes.py`) envuelve esas listas y
entrega iteradores: `IteradorLlegada`, `IteradorPrioridad` (montículo
precio-tiempo, el que usa la subasta, que además se detiene apenas los precios
dejan de cruzarse) e `IteradorFiltrado` (por usuario o solo negociables).

Endpoint: `GET /ordenes?recorrido=llegada|prioridad&usuario=<id>`.

## Por qué el Mediator aquí

Para vender excedentes hay que coordinar lo que produce el panel, lo que consume
la casa, lo que cabe en la batería y el precio del mercado. En vez de que cada
componente llame a los demás, todos avisan a `CentralEnergiaHogar`
(`coordinacion_hogar.py`), que carga/descarga la batería (10 kWh por cada
dispositivo `bateria` del usuario, sin romper la reserva mínima) y publica la
venta o la compra con las mismas funciones del mercado (así la orden tiene estado
y dispara eventos). Sin kWh en la petición usa la última lectura de los paneles y
medidores del usuario.

Endpoint: `POST /hogar/coordinar`.

## Por qué el Memento aquí

Las reglas que usa la central (reserva mínima, precio de venta, precio máximo de
compra, vender o no) deciden dinero real, así que cada cambio debe poder
deshacerse. `ConfiguracionHogar` crea mementos inmutables de sí misma y
`HistorialConfiguracion` los guarda en pilas de deshacer/rehacer (máximo 10
versiones) sin abrirlos (`configuracion_hogar.py`).

Endpoints: `GET/PUT /hogar/configuracion` (400 si el cambio es inválido o vacío),
`POST /hogar/configuracion/deshacer` y `POST /hogar/configuracion/rehacer` (409 si
no hay versión).

## Autenticación

Las cuentas y contraseñas también viven en el Singleton `PlataformaEnergia` (se
pierden al reiniciar el backend, igual que el resto del estado). El flujo es:

- `POST /auth/registro` (`id`, `nombre`, `password`) → crea el usuario con la
  contraseña hasheada (`bcrypt`) y devuelve un JWT.
- `POST /auth/login` (`id`, `password`) → verifica el hash y devuelve un JWT.
- Los endpoints que pertenecen a un usuario (`/ordenes/venta`, `/ordenes/compra`,
  `/iot/dispositivos`) requieren `Authorization: Bearer <token>`; el `usuario_id`
  se toma del token, no del cuerpo de la petición, para que nadie pueda publicar
  órdenes en nombre de otro usuario.

Es una autenticación pensada para el prototipo: el secreto (`SECRET_KEY`) tiene
un valor por defecto en `main.py` y se puede sobrescribir con la variable de
entorno `SECRET_KEY`.

## Por qué el Singleton sigue siendo clave aquí

El frontend puede hacer cientos de peticiones concurrentes (varios usuarios
publicando órdenes, IoT enviando lecturas al mismo tiempo). Como
`PlataformaEnergia()` en `main.py` siempre devuelve la **misma instancia**
(gracias a `SingletonMeta` con `Lock`), todas esas peticiones leen y escriben
sobre **un solo estado consistente** — el mismo libro de órdenes, el mismo
historial, las mismas lecturas — sin importar cuántas veces FastAPI reconstruya
el objeto en cada request.
