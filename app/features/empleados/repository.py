# app/features/empleados/repository.py
from sqlmodel import Session, select
from typing import Optional, List, Tuple
from sqlalchemy import func
from datetime import datetime, timezone
from app.features.empleados.models import Empleado, EstadoEmpleado
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmpleadoRepository:
    """Repositorio para operaciones CRUD de empleados."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==========================================
    # GET BY FIELD
    # ==========================================
    def get_by_id(self, empleado_id: int) -> Optional[Empleado]:
        """Obtiene un empleado por su ID."""
        return self.db.get(Empleado, empleado_id)
    
    def get_by_ci(self, ci: str) -> Optional[Empleado]:
        """Obtiene un empleado por su CI."""
        return self.db.exec(
            select(Empleado).where(Empleado.ci == ci)
        ).first()
    
    def get_by_email(self, email: str) -> Optional[Empleado]:
        """Obtiene un empleado por su email."""
        return self.db.exec(
            select(Empleado).where(Empleado.email == email)
        ).first()
    
    # ==========================================
    # LIST EMPLEADOS (CON PAGINACIÓN Y FILTROS)
    # ==========================================
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        estado: Optional[str] = None,
        departamento: Optional[str] = None,
        search: Optional[str] = None
    ) -> Tuple[List[Empleado], int]:
        """
        Obtiene lista paginada de empleados con filtros.
        
        Args:
            skip: Número de registros a saltar
            limit: Límite de registros
            estado: Filtrar por estado (ACTIVO, PENDIENTE_BAJA, DADO_BAJA)
            departamento: Filtrar por departamento
            search: Buscar por nombre, apellidos o CI
        
        Returns:
            Tuple con (lista de empleados, total)
        """
        query = select(Empleado)
        
        # Filtros
        if estado:
            query = query.where(Empleado.estado == estado)
        
        if departamento:
            query = query.where(Empleado.departamento == departamento)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                (Empleado.nombre.like(search_term)) |
                (Empleado.apellidos.like(search_term)) |
                (Empleado.ci.like(search_term))
            )
        
        # Contar total
        total = self.db.exec(select(func.count()).select_from(query.subquery())).one()
        
        # Paginación
        empleados = self.db.exec(
            query.offset(skip).limit(limit).order_by(Empleado.id)
        ).all()
        
        return empleados, total
    
    def get_activos(self, skip: int = 0, limit: int = 100) -> Tuple[List[Empleado], int]:
        """Obtiene solo empleados activos."""
        return self.get_all(skip=skip, limit=limit, estado=EstadoEmpleado.ACTIVO)
    
    def get_pendientes_baja(self, skip: int = 0, limit: int = 100) -> Tuple[List[Empleado], int]:
        """Obtiene empleados pendientes de baja."""
        return self.get_all(skip=skip, limit=limit, estado=EstadoEmpleado.PENDIENTE_BAJA)
    
    def get_dados_baja(self, skip: int = 0, limit: int = 100) -> Tuple[List[Empleado], int]:
        """Obtiene empleados dados de baja."""
        return self.get_all(skip=skip, limit=limit, estado=EstadoEmpleado.DADO_BAJA)
    
    def get_by_departamento(self, departamento: str, skip: int = 0, limit: int = 100) -> Tuple[List[Empleado], int]:
        """Obtiene empleados por departamento."""
        return self.get_all(skip=skip, limit=limit, departamento=departamento)
    
    # ==========================================
    # CREATE
    # ==========================================
    def create(self, empleado_data: dict) -> Empleado:
        """Crea un nuevo empleado."""
        empleado = Empleado(**empleado_data)
        self.db.add(empleado)
        self.db.flush()
        return empleado
    
    # ==========================================
    # UPDATE
    # ==========================================
    def update(self, empleado: Empleado, update_data: dict) -> Empleado:
        """Actualiza un empleado existente."""
        for key, value in update_data.items():
            if hasattr(empleado, key) and value is not None:
                setattr(empleado, key, value)
        empleado.updated_at = datetime.now(timezone.utc)
        self.db.add(empleado)
        self.db.flush()
        self.db.refresh(empleado)
        return empleado
    
    # ==========================================
    # BAJA Y RECONTRATACIÓN
    # ==========================================
    def solicitar_baja(self, empleado_id: int, motivo: str) -> Optional[Empleado]:
        """
        Cambia el estado de un empleado a PENDIENTE_BAJA.
        """
        empleado = self.get_by_id(empleado_id)
        if empleado:
            empleado.estado = EstadoEmpleado.PENDIENTE_BAJA
            empleado.motivo_baja = motivo
            empleado.updated_at = datetime.now(timezone.utc)
            self.db.add(empleado)
            self.db.flush()
            self.db.refresh(empleado)
        return empleado

    def dar_baja(self, empleado_id: int) -> Optional[Empleado]:
        """
        Marca un empleado como dado de baja.
        Actualiza el historial de fechas.
        """
        empleado = self.get_by_id(empleado_id)
        if empleado:
            # Cambiar estado
            empleado.estado = EstadoEmpleado.DADO_BAJA
            empleado.fecha_baja = datetime.now(timezone.utc)
            empleado.updated_at = datetime.now(timezone.utc)
            
            año_actual = datetime.now(timezone.utc).year
            if empleado.historial_fechas:
                # Si el historial termina en "-", lo completamos con el año actual
                if empleado.historial_fechas.endswith("-"):
                    empleado.historial_fechas += str(año_actual)
                else:
                    empleado.historial_fechas += f"-{año_actual}"
            else:
                # Si no hay historial, empezamos uno
                empleado.historial_fechas = f"{año_actual}-{año_actual}"
            
            self.db.add(empleado)
            self.db.flush()
            self.db.refresh(empleado)
        return empleado
    
    def reactivar(self, empleado_id: int) -> Optional[Empleado]:
        """Reactivar a un empleado dado de baja."""
        empleado = self.get_by_id(empleado_id)
        if empleado:
            empleado.estado = EstadoEmpleado.ACTIVO
            empleado.fecha_baja = None
            empleado.motivo_baja = None
            empleado.veces_recontratado += 1
            
            # Actualizar historial
            año_actual = datetime.now(timezone.utc).year
            if empleado.historial_fechas:
                empleado.historial_fechas += f", {año_actual}-"
            else:
                empleado.historial_fechas = f"{año_actual}-"
            
            empleado.updated_at = datetime.now(timezone.utc)
            self.db.add(empleado)
            self.db.flush()
            self.db.refresh(empleado)
        return empleado
    
    # ==========================================
    # EXISTENCE CHECKS
    # ==========================================
    def exists_by_ci(self, ci: str) -> bool:
        """Verifica si existe un empleado con ese CI."""
        return self.get_by_ci(ci) is not None
    
    def exists_by_email(self, email: str) -> bool:
        """Verifica si existe un empleado con ese email."""
        return self.get_by_email(email) is not None
    
    # ==========================================
    # COUNTS
    # ==========================================
    def count_all(self) -> int:
        """Cuenta todos los empleados."""
        return self.db.exec(select(func.count()).select_from(Empleado)).one()
    
    def count_activos(self) -> int:
        """Cuenta solo empleados activos."""
        return self.db.exec(
            select(func.count()).select_from(Empleado)
            .where(Empleado.estado == EstadoEmpleado.ACTIVO)
        ).one()
    
    def count_pendientes_baja(self) -> int:
        """Cuenta empleados pendientes de baja."""
        return self.db.exec(
            select(func.count()).select_from(Empleado)
            .where(Empleado.estado == EstadoEmpleado.PENDIENTE_BAJA)
        ).one()
    
    def count_dados_baja(self) -> int:
        """Cuenta empleados dados de baja."""
        return self.db.exec(
            select(func.count()).select_from(Empleado)
            .where(Empleado.estado == EstadoEmpleado.DADO_BAJA)
        ).one()
    
    def count_by_departamento(self, departamento: str) -> int:
        """Cuenta empleados por departamento."""
        return self.db.exec(
            select(func.count()).select_from(Empleado)
            .where(Empleado.departamento == departamento)
        ).one()