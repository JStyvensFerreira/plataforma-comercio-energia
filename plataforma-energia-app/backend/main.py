"""
API REST para la Plataforma de Comercio de Energía.
Expone el Singleton `PlataformaEnergia` al frontend Vue.

Ejecutar con:
    uvicorn main:app --reload --port 8000
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from plataforma import PlataformaEnergia

app = FastAPI(title="Plataforma de Comercio de Energía", version="1.0.0")

# ---------- Autenticación (JWT sobre el estado en memoria del Singleton) ----------
SECRET_KEY = os.environ.get("SECRET_KEY", "clave-secreta-dev-cambiar-en-produccion")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# auto_error=False para poder devolver un 401 con mensaje propio en vez del genérico de FastAPI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

# Permite que el frontend (Vue, servido en otro puerto/archivo) consuma la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Siempre la MISMA instancia (Singleton), sin importar cuántas veces se llame
plataforma = PlataformaEnergia()


# ---------- Esquemas de entrada ----------
class RegistroIn(BaseModel):
    id: str
    nombre: str
    password: str


class LoginIn(BaseModel):
    id: str
    password: str


class OrdenIn(BaseModel):
    cantidad_kwh: float
    precio_kwh: float


class DispositivoIn(BaseModel):
    id: str
    tipo: str


class LecturaIn(BaseModel):
    valor_kwh: float


# ---------- Autenticación ----------
def crear_token(usuario_id: str) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": usuario_id, "exp": expira}, SECRET_KEY, algorithm=ALGORITHM)


def usuario_actual(token: str | None = Depends(oauth2_scheme)) -> str:
    if not token:
        raise HTTPException(401, "No autenticado")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(401, "Token inválido o expirado")
    usuario_id = payload.get("sub")
    if usuario_id not in plataforma.usuarios:
        raise HTTPException(401, "Usuario no encontrado")
    return usuario_id


@app.post("/auth/registro")
def registro(datos: RegistroIn):
    if datos.id in plataforma.usuarios:
        raise HTTPException(400, "El usuario ya existe")
    password_hash = bcrypt.hashpw(datos.password.encode(), bcrypt.gensalt()).decode()
    usuario = plataforma.registrar_usuario(datos.id, datos.nombre, password_hash)
    return {"access_token": crear_token(usuario.id), "token_type": "bearer", "usuario": usuario.to_dict()}


@app.post("/auth/login")
def login(datos: LoginIn):
    usuario = plataforma.usuarios.get(datos.id)
    if not usuario or not usuario.password_hash or not bcrypt.checkpw(
        datos.password.encode(), usuario.password_hash.encode()
    ):
        raise HTTPException(401, "Credenciales inválidas")
    return {"access_token": crear_token(usuario.id), "token_type": "bearer", "usuario": usuario.to_dict()}


# ---------- Endpoints ----------
@app.get("/")
def raiz():
    return {"mensaje": "API de la Plataforma de Comercio de Energía activa"}


@app.get("/usuarios")
def listar_usuarios():
    return [u.to_dict() for u in plataforma.usuarios.values()]


@app.post("/ordenes/venta")
def crear_venta(o: OrdenIn, usuario_id: str = Depends(usuario_actual)):
    return plataforma.publicar_venta(usuario_id, o.cantidad_kwh, o.precio_kwh).to_dict()


@app.post("/ordenes/compra")
def crear_compra(o: OrdenIn, usuario_id: str = Depends(usuario_actual)):
    return plataforma.publicar_compra(usuario_id, o.cantidad_kwh, o.precio_kwh).to_dict()


@app.get("/ordenes")
def listar_ordenes():
    return {
        "ventas": [o.to_dict() for o in plataforma.ordenes_venta],
        "compras": [o.to_dict() for o in plataforma.ordenes_compra],
    }


@app.post("/subasta/ejecutar")
def ejecutar_subasta():
    return plataforma.ejecutar_subasta()


@app.get("/transacciones")
def listar_transacciones():
    return plataforma.historial_transacciones


@app.post("/iot/dispositivos")
def crear_dispositivo(d: DispositivoIn, usuario_id: str = Depends(usuario_actual)):
    return plataforma.conectar_dispositivo(d.id, usuario_id, d.tipo).to_dict()


@app.get("/iot/dispositivos")
def listar_dispositivos():
    return [d.to_dict() for d in plataforma.dispositivos.values()]


@app.post("/iot/dispositivos/{dispositivo_id}/lecturas")
def enviar_lectura(dispositivo_id: str, lectura: LecturaIn):
    try:
        plataforma.enviar_lectura_iot(dispositivo_id, lectura.valor_kwh)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"ok": True, "lecturas": plataforma.lecturas_iot[dispositivo_id]}


@app.post("/iot/dispositivos/{dispositivo_id}/simular")
def simular(dispositivo_id: str, n: int = 5):
    if dispositivo_id not in plataforma.dispositivos:
        raise HTTPException(404, "Dispositivo no encontrado")
    plataforma.simular_lecturas(dispositivo_id, n)
    return {"lecturas": plataforma.lecturas_iot[dispositivo_id]}


@app.get("/iot/dispositivos/{dispositivo_id}/lecturas")
def obtener_lecturas(dispositivo_id: str):
    if dispositivo_id not in plataforma.dispositivos:
        raise HTTPException(404, "Dispositivo no encontrado")
    return plataforma.lecturas_iot[dispositivo_id]


@app.get("/iot/dispositivos/{dispositivo_id}/prediccion")
def prediccion(dispositivo_id: str, ventana: int = 3):
    if dispositivo_id not in plataforma.dispositivos:
        raise HTTPException(404, "Dispositivo no encontrado")
    valor = plataforma.predecir_siguiente_valor(dispositivo_id, ventana)
    return {"prediccion_kwh": valor}


@app.get("/estado")
def estado_singleton():
    """Endpoint de comprobación: demuestra que siempre es la misma instancia."""
    return {
        "id_instancia": id(plataforma),
        "usuarios_registrados": len(plataforma.usuarios),
        "ordenes_venta_activas": len(plataforma.ordenes_venta),
        "ordenes_compra_activas": len(plataforma.ordenes_compra),
        "transacciones_totales": len(plataforma.historial_transacciones),
    }
