# app/features/empleados/models.py
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from typing import Optional
import enum


class EstadoEmpleado(str, enum.Enum):
    """Estados posibles de un empleado."""
    ACTIVO = "ACTIVO"
    PENDIENTE_BAJA = "PENDIENTE_BAJA"
    DADO_BAJA = "DADO_BAJA"


class Empleado(SQLModel, table=True):
    """Modelo de empleado para gestión de altas y bajas."""
    __tablename__ = "empleados"
    
    # ====== DATOS PERSONALES ======
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    nombre: str = Field(max_length=50, nullable=False)
    apellidos: str = Field(max_length=100, nullable=False)
    ci: str = Field(max_length=11, unique=True, index=True, nullable=False)
    telefono: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=100)
    
    # ====== DATOS LABORALES ======
    departamento: str = Field(max_length=50, nullable=False)
    
    # ====== FECHAS ======
    fecha_ingreso: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fecha_baja: Optional[datetime] = Field(default=None)
    
    # ====== ESTADO ======
    estado: EstadoEmpleado = Field(default=EstadoEmpleado.ACTIVO, nullable=False)
    motivo_baja: Optional[str] = Field(default=None, max_length=100)
    
    # ====== RECONTRATACIONES ======
    veces_recontratado: int = Field(default=0)
    historial_fechas: Optional[str] = Field(default=None)
    
    # ====== METADATOS ======
    observaciones: Optional[str] = Field(default=None)
    
    # ====== TIMESTAMPS ======
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))