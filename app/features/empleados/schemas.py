# app/features/empleados/schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional
from .models import EstadoEmpleado


# ==========================================
# ESQUEMAS DE EMPLEADO (CRUD)
# ==========================================

class EmpleadoBase(BaseModel):
    """Base de empleado."""
    nombre: str = Field(max_length=50, description="Nombre del empleado")
    apellidos: str = Field(max_length=100, description="Apellidos del empleado")
    ci: str = Field(max_length=11, min_length=11, description="Carnet de identidad (11 dígitos exactos)")
    telefono: Optional[str] = Field(default=None, max_length=20, description="Número de teléfono")
    email: Optional[EmailStr] = Field(default=None, description="Email personal")
    departamento: str = Field(max_length=50, description="Departamento")
    observaciones: Optional[str] = Field(default=None, description="Observaciones")

    @field_validator("ci")
    @classmethod
    def validate_ci(cls, v: str) -> str:
        """Valida que el CI tenga exactamente 11 dígitos numéricos."""
        v = v.strip()
        if not v.isdigit():
            raise ValueError("El CI debe contener solo números")
        if len(v) != 11:
            raise ValueError("El CI debe tener exactamente 11 dígitos")
        return v

    @field_validator("telefono")
    @classmethod
    def validate_telefono(cls, v: Optional[str]) -> Optional[str]:
        """Valida que el teléfono tenga formato correcto."""
        if v:
            v = v.strip()
            if not v.isdigit():
                raise ValueError("El teléfono debe contener solo números")
            if len(v) < 7 or len(v) > 20:
                raise ValueError("El teléfono debe tener entre 7 y 20 dígitos")
        return v


class EmpleadoCreate(EmpleadoBase):
    """Creación de nuevo empleado."""
    pass


class EmpleadoUpdate(BaseModel):
    """Actualización de datos de empleado."""
    nombre: Optional[str] = Field(default=None, max_length=50)
    apellidos: Optional[str] = Field(default=None, max_length=100)
    telefono: Optional[str] = Field(default=None, max_length=20)
    email: Optional[EmailStr] = Field(default=None)
    departamento: Optional[str] = Field(default=None, max_length=50)
    observaciones: Optional[str] = Field(default=None)
    
    @field_validator("telefono")
    @classmethod
    def validate_telefono(cls, v: Optional[str]) -> Optional[str]:
        """Valida que el teléfono tenga formato correcto."""
        if v:
            v = v.strip()
            if not v.isdigit():
                raise ValueError("El teléfono debe contener solo números")
            if len(v) < 7 or len(v) > 20:
                raise ValueError("El teléfono debe tener entre 7 y 20 dígitos")
        return v


class EmpleadoBajaRequest(BaseModel):
    """Solicitud de baja de empleado."""
    motivo: str = Field(max_length=100, description="Motivo de la baja")
    urgente: bool = Field(default=False, description="Si la baja es urgente")


class EmpleadoRecontratar(BaseModel):
    """Solicitud de recontratación."""
    comentarios: Optional[str] = Field(default=None, description="Comentarios sobre la recontratación")


# ==========================================
# ESQUEMAS DE RESPUESTA
# ==========================================

class EmpleadoResponse(EmpleadoBase):
    """Respuesta de empleado."""
    id: int
    estado: EstadoEmpleado
    fecha_ingreso: datetime
    fecha_baja: Optional[datetime]
    motivo_baja: Optional[str]
    veces_recontratado: int
    historial_fechas: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class EmpleadoListResponse(BaseModel):
    """Respuesta para listado paginado de empleados."""
    items: list[EmpleadoResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ==========================================
# ESQUEMAS PARA ESTADÍSTICAS
# ==========================================

class EmpleadoStatsResponse(BaseModel):
    """Estadísticas de empleados."""
    total: int
    activos: int
    pendientes_baja: int
    dados_baja: int
    recontratados: int