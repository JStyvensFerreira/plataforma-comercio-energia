# Voltia — Plataforma de Comercio de Energía (Backend + Frontend)

Implementación full-stack del proyecto #16, sobre la base del patrón **Singleton**
ya usado en `plataforma_energia.py`.

## Estructura

```
plataforma-energia-app/
├── backend/
│   ├── plataforma.py     # Lógica de dominio (Singleton PlataformaEnergia)
│   ├── main.py            # API FastAPI que expone el Singleton
│   └── requirements.txt
└── frontend/
    └── index.html         # Dashboard en Vue 3 (sin build, vía CDN)
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

1. **Login** → regístrate como `u1` / Ana con una contraseña, luego cierra sesión y regístrate como `u2` / Luis
2. **Mercado** → con la sesión de Ana publica una venta (10 kWh a $0.15); cambia de sesión a Luis y publica una compra (6 kWh a $0.18)
3. Haz clic en **"Ejecutar subasta"** → se genera una transacción
4. **IoT & Predicción** → conecta un panel solar (queda ligado al usuario con sesión activa), simula lecturas y pide la predicción
5. **Historial** → revisa las transacciones cerradas

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
