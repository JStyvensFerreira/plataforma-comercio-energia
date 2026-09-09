# Voltia — Plataforma de Comercio de Energía (Backend + Frontend)

Implementación full-stack del proyecto #16. Usa dos patrones de diseño de forma
real:

- **Singleton** (`plataforma.py`) — estado único compartido por todas las peticiones.
- **Abstract Factory** (`notificaciones.py`) — un canal de notificación (email /
  SMS / push) es una fábrica que crea la familia completa de avisos de ese canal.
- **Builder** (`reportes.py`) — el reporte energético se construye paso a paso, y
  el mismo proceso produce distintas representaciones (dict, objeto, texto).

## Estructura

```
plataforma-energia-app/
├── backend/
│   ├── plataforma.py       # Lógica de dominio (Singleton PlataformaEnergia)
│   ├── notificaciones.py    # Canales de notificación (Abstract Factory)
│   ├── reportes.py          # Construcción del reporte energético (Builder)
│   ├── main.py              # API FastAPI que expone los patrones
│   └── requirements.txt
└── frontend/
    └── index.html           # Dashboard en Vue 3 (sin build, vía CDN)
```

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
6. **Historial** → revisa las transacciones cerradas

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
