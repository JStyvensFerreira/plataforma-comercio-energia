# Cómo ejecutar el proyecto — Guía paso a paso (para quien nunca lo ha visto)

Esta guía asume que **no tienes nada instalado todavía** y que acabas de
descargar (o clonar) este repositorio en tu computador. Está pensada para
Windows, que es donde se desarrolló el proyecto; al final hay una nota para
Mac/Linux.

No necesitas saber programar para seguir estos pasos: solo copiar y pegar
los comandos, en orden, en una terminal.

---

## 0. Lo que vas a necesitar

- **Python 3.10 o superior.** Es el único requisito real. Todo lo demás
  (`pip`, `pytest`, `fastapi`, etc.) se instala con comandos que están más
  abajo.
- Una terminal. En Windows puede ser **PowerShell**, la que ya viene
  instalada (búscala como "PowerShell" en el menú de inicio) o la terminal
  integrada de VS Code (menú **Terminal → New Terminal**).

### ¿Ya tengo Python instalado?

Abre una terminal y escribe:

```powershell
python --version
```

- Si responde algo como `Python 3.11.5` → ya tienes Python, pasa al punto 1.
- Si da error ("no se reconoce como un comando...") → instala Python desde
  <https://www.python.org/downloads/>. **Importante:** durante la
  instalación, marca la casilla que dice **"Add python.exe to PATH"** antes
  de darle a "Install Now". Luego cierra y vuelve a abrir la terminal, y
  repite `python --version` para confirmar.

---

## 1. Descargar el proyecto

Si ya tienes la carpeta del proyecto en tu equipo (por ejemplo porque te la
compartieron o la descargaste como ZIP y la descomprimiste), salta al
punto 2.

Si vas a **clonarlo desde GitHub** y tienes Git instalado:

```powershell
git clone <URL-del-repositorio>
```

Esto crea una carpeta nueva con el nombre del repositorio. Entra a ella.

---

## 2. Abrir una terminal DENTRO de la carpeta del proyecto

Esto es importante: todos los comandos de esta guía asumen que la terminal
está parada exactamente en la carpeta raíz del proyecto (la que contiene los
archivos `README.md`, `pytest.ini`, y las carpetas `Documentacion/` y
`plataforma-energia-app/`).

Formas fáciles de lograrlo en Windows:

- Abre la carpeta del proyecto en el Explorador de Windows, haz clic en la
  barra de direcciones (arriba), escribe `powershell` y presiona Enter.
- O, si usas VS Code: abre la carpeta del proyecto con **Archivo → Abrir
  carpeta**, y luego abre la terminal integrada con **Terminal → New
  Terminal**.

Para confirmar que estás en el lugar correcto, escribe:

```powershell
dir
```

y deberías ver, entre otras cosas, `README.md`, `pytest.ini`,
`Documentacion` y `plataforma-energia-app`.

---

## 3. Instalar las dependencias para correr las pruebas

Este proyecto trae 5 patrones de diseño con sus propias pruebas
automatizadas (pytest). Para poder ejecutarlas:

```powershell
pip install -r requirements-dev.txt
```

Esto instala únicamente `pytest`. Si el comando `pip` no se reconoce, prueba
con `python -m pip install -r requirements-dev.txt`.

---

## 4. Ejecutar las pruebas unitarias

Con las dependencias instaladas, corre:

```powershell
python -m pytest -q
```

Deberías ver algo como esto al final:

```
Documentacion\Semana 2\test_singleton.py ..................              [ 15%]
Documentacion\Semana 3\test_factory_method.py ................           [ 29%]
Documentacion\Semana 4\test_abstract_factory.py ........................ [ 50%]
Documentacion\Semana 5\test_builder.py ..............................    [ 79%]
Documentacion\Semana 6\test_prototype.py ........................        [100%]

115 passed in 0.4s
```

**Si ves `115 passed` sin ningún `failed`, las pruebas de los 5 patrones de
diseño están validadas correctamente.** Esto es justamente la
"validación de las pruebas dispuestas en el informe" que pide el parcial.

Si quieres ver el detalle de cada prueba, una por una, corre simplemente
`python -m pytest` (sin `-q`) — el proyecto ya está configurado para mostrar
ese detalle por defecto.

---

## 5. Levantar el backend (la API del proyecto)

El backend es el programa que corre por detrás y expone los 5 patrones ya
integrados entre sí (no solo como demos sueltas).

**5.1.** Entra a la carpeta del backend:

```powershell
cd plataforma-energia-app/backend
```

**5.2.** Instala sus dependencias (solo la primera vez):

```powershell
pip install -r requirements.txt
```

Esto puede tardar uno o dos minutos, es normal.

**5.3.** Levanta el servidor:

```powershell
uvicorn main:app --reload --port 8000
```

Si todo sale bien, verás varias líneas terminando en algo como:

```
INFO:     Application startup complete.
```

**Deja esta terminal abierta** — mientras la cierres o presiones `Ctrl+C`,
el servidor sigue corriendo. No vuelvas a escribir nada en esta terminal;
para los siguientes pasos vas a usar el navegador (o abrir una terminal
nueva si quieres seguir usando comandos).

**5.4. Confirmar que quedó activo:** abre tu navegador (Chrome, Edge, el que
tengas) y entra a:

```
http://localhost:8000
```

Deberías ver un texto así:

```json
{"mensaje": "API de la Plataforma de Comercio de Energía activa"}
```

También puedes entrar a `http://localhost:8000/docs` para ver, de forma
interactiva, **todos** los endpoints de la API (documentación automática
generada por FastAPI).

---

## 6. Abrir el frontend (la interfaz visual)

El frontend es una sola página web que se conecta al backend que dejaste
corriendo en el paso anterior.

Ve a la carpeta `plataforma-energia-app/frontend/` en el Explorador de
Windows y haz **doble clic** en `index.html`. Se abrirá en tu navegador
predeterminado.

Confirma que:

- El punto de estado (arriba a la derecha, junto al campo que dice
  `http://localhost:8000`) esté en **verde**. Si está en rojo, revisa que el
  backend del paso 5 siga corriendo.

---

## 7. Probar la plataforma (flujo guiado)

Con el backend corriendo y el frontend abierto, prueba este flujo — así ves
los 5 patrones funcionando en conjunto:

1. **Regístrate** (pantalla de inicio, pestaña "Regístrate"): id `u1`,
   nombre `Ana`, la contraseña que quieras.
2. Pestaña **Mercado**: publica una venta (10 kWh a $0.15). Cierra sesión y
   regístrate como un segundo usuario (id `u2`, nombre `Luis`) para publicar
   una compra (6 kWh a $0.18), y dale clic a **"Ejecutar subasta"** — verás
   una transacción cerrada (usa el patrón **Singleton**, que mantiene un
   único estado compartido de la plataforma).
3. Pestaña **IoT & Predicción**: conecta un dispositivo (tipo "Panel
   solar") — se crea usando el patrón **Factory Method**. Luego, en la
   tarjeta "Clonar dispositivo calibrado", clónalo con un id nuevo — eso usa
   el patrón **Prototype**.
4. Pestaña **Notificaciones**: cambia tu canal (Email/SMS/Push) y genera un
   reporte — usan **Abstract Factory** (canales) y **Builder** (reporte paso
   a paso), respectivamente.

Si todo eso funciona sin errores en pantalla, el proyecto está corriendo
correctamente de punta a punta.

---

## 8. Cómo detener todo

- En la terminal donde corre el backend (paso 5.3), presiona `Ctrl+C`.
- Simplemente cierra la pestaña del navegador con el frontend.

---

## Solución de problemas comunes

**"python no se reconoce como un comando..."**
Python no está instalado o no se agregó al PATH. Reinstálalo marcando
"Add python.exe to PATH" (ver punto 0).

**"pip no se reconoce como un comando..."**
Usa `python -m pip install ...` en vez de `pip install ...`.

**El backend dice `[Errno 10048] ... address already in use` (puerto ocupado)**
Ya hay algo corriendo en el puerto 8000. Ciérralo (`Ctrl+C` en esa terminal)
o levanta este backend en otro puerto: `uvicorn main:app --reload --port 8001`
(y cambia el campo de la API en el frontend a `http://localhost:8001`).

**El punto de estado del frontend está en rojo**
El backend no está corriendo, o corre en un puerto distinto al que aparece
en el campo de texto junto al punto. Revisa el paso 5.

**Alguna prueba falla (`failed` en vez de `passed`)**
Asegúrate de estar corriendo `python -m pytest` desde la **raíz** del
repositorio (no desde `plataforma-energia-app/`), y de haber hecho
`pip install -r requirements-dev.txt` primero.

---

## Nota para Mac / Linux

Los comandos son los mismos, cambiando `python` por `python3` si tu sistema
lo requiere, y usando una terminal normal (Terminal.app en Mac, o la que uses
en Linux) en vez de PowerShell. El resto de la guía aplica igual.
