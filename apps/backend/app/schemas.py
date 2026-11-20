from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    name: str
    nombres: str
    apellidos: str
    email: str
    store: str
    activo: bool
    creadoEn: str
    revocadoEn: str | None = None


class TokenOut(BaseModel):
    token: str
    profile: ProfileOut


class SignupIn(BaseModel):
    nombres: str = Field(min_length=1, max_length=80)
    apellidos: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=200)
    store: str = Field(min_length=1, max_length=120)


class LoginIn(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordIn(BaseModel):
    currentPassword: str = Field(min_length=1, max_length=200)
    newPassword: str = Field(min_length=8, max_length=200)


class EmployeeCreateIn(BaseModel):
    nombres: str = Field(min_length=1, max_length=80)
    apellidos: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=200)


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=60)
    icon: str = Field(default="📦", max_length=8)
    stock: float = Field(gt=0)
    unit: str = Field(default="unid.", max_length=20)
    price: float = Field(ge=0)
    expires: str | None = None


class ProductPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, min_length=1, max_length=60)
    icon: str | None = Field(default=None, max_length=8)
    stock: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=20)
    price: float | None = Field(default=None, ge=0)
    expires: str | None = None


class ProductOut(BaseModel):
    id: str
    name: str
    category: str
    icon: str
    stock: float
    unit: str
    price: float
    expires: str | None
    creadoPor: str
    bloqueado: bool
    bloqueadoPor: str | None
    activo: bool


class MovementItemIn(BaseModel):
    productoId: str
    loteId: str | None = None
    cantidad: float = Field(gt=0)
    importeUnitario: float | None = Field(default=None, ge=0)
    codigoLote: str | None = None
    fechaVencimiento: str | None = None
    costoUnitario: float | None = Field(default=None, ge=0)


class MovementIn(BaseModel):
    tipo: Literal["entrada", "salida"]
    motivo: str = Field(min_length=1, max_length=160)
    items: list[MovementItemIn] = Field(min_length=1)


class MovementOut(BaseModel):
    id: str
    fechaHora: str
    tipo: str
    motivo: str
    total: float | None
    responsableId: str
    responsableNombre: str
    productoId: str | None
    stockAnterior: float | None
    stockNuevo: float | None
    diferencia: float | None
    detalles: list[dict]
