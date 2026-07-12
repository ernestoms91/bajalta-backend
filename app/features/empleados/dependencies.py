# app/features/empleados/dependencies.py
from typing import Annotated
from fastapi import Depends
from app.core.dependencies import DBSession
from app.features.empleados.service import EmpleadoService


# ==========================================
# DEPENDENCIAS DE SERVICIOS
# ==========================================

def get_empleado_service(session: DBSession) -> EmpleadoService:
    """Dependencia para inyectar EmpleadoService."""
    return EmpleadoService(session)


# Type Alias para servicio
EmpleadoServiceDep = Annotated[EmpleadoService, Depends(get_empleado_service)]