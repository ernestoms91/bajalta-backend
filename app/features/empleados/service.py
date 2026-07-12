# app/features/empleados/service.py
from fastapi import HTTPException, status
from datetime import datetime, timezone
from typing import Optional, List
from io import BytesIO
from sqlmodel import select
from app.core.dependencies import DBSession
from app.core.logging import get_logger
from app.core.email import EmailService, EmailMessage, EmailTemplates
from app.core.pdf import PDFService
from app.features.empleados.models import Empleado, EstadoEmpleado
from app.features.empleados.schemas import (
    EmpleadoCreate,
    EmpleadoUpdate,
    EmpleadoResponse,
    EmpleadoListResponse,
)
from app.features.empleados.repository import EmpleadoRepository
from app.features.auth.repository import UsuarioRepository
from app.features.auth.models import User

logger = get_logger(__name__)


class EmpleadoService:
    """Servicio de gestion de empleados: CRUD, bajas, recontrataciones."""
    
    def __init__(self, db: DBSession):
        self.db = db
        self.repo = EmpleadoRepository(db)
        self.user_repo = UsuarioRepository(db)
        self.email_service = EmailService()
        self.pdf_service = PDFService()
    
    # ==========================================
    # METODOS PRIVADOS PARA NOTIFICACIONES
    # ==========================================
    
    def _get_admin_emails(self) -> List[str]:
        """Obtiene emails de administradores activos."""
        return self.user_repo.get_admin_emails()
    
    def _get_rrhh_emails(self) -> List[str]:
        """Obtiene emails de RRHH activos."""
        rrhh = self.db.exec(
            select(User).where(
                User.is_admin == False,
                User.is_active == True
            )
        ).all()
        return [user.email for user in rrhh]
    
    def _notificar_alta(self, empleado: Empleado) -> None:
        """Envía notificacion de alta a administradores."""
        admin_emails = self._get_admin_emails()
        
        if not admin_emails:
            logger.warning("No hay administradores activos para notificar")
            return
        
        html_body = EmailTemplates.alta_empleado(
            nombre=f"{empleado.nombre} {empleado.apellidos}",
            ci=empleado.ci,
            departamento=empleado.departamento
        )
        
        message = EmailMessage(
            to=admin_emails,
            subject=f"Nuevo Empleado - {empleado.nombre} {empleado.apellidos}",
            body=f"Se ha dado de alta a {empleado.nombre} {empleado.apellidos}",
            html_body=html_body
        )
        
        self.email_service.send(message)
        logger.info(f"Notificacion de alta enviada a {len(admin_emails)} administradores")
    
    def _notificar_baja_solicitada(self, empleado: Empleado, motivo: str, urgente: bool) -> None:
        """Envía notificacion de baja solicitada a administradores."""
        admin_emails = self._get_admin_emails()
        
        if not admin_emails:
            logger.warning("No hay administradores activos para notificar")
            return
        
        html_body = EmailTemplates.baja_empleado(
            nombre=f"{empleado.nombre} {empleado.apellidos}",
            ci=empleado.ci,
            motivo=motivo,
            urgente=urgente
        )
        
        urgencia_texto = "URGENTE - " if urgente else ""
        message = EmailMessage(
            to=admin_emails,
            subject=f"{urgencia_texto}Baja de Empleado - {empleado.nombre} {empleado.apellidos}",
            body=f"Se ha solicitado la baja de {empleado.nombre} {empleado.apellidos}",
            html_body=html_body
        )
        
        self.email_service.send(message)
        logger.info(f"Notificacion de baja enviada a {len(admin_emails)} administradores")
    
    def _notificar_baja_completada(self, empleado: Empleado) -> None:
        """Envía notificacion de baja completada a RRHH."""
        rrhh_emails = self._get_rrhh_emails()
        
        if not rrhh_emails:
            logger.warning("No hay usuarios RRHH para notificar")
            return
        
        html_body = EmailTemplates.baja_completada(
            nombre=f"{empleado.nombre} {empleado.apellidos}"
        )
        
        message = EmailMessage(
            to=rrhh_emails,
            subject=f"Baja Completada - {empleado.nombre} {empleado.apellidos}",
            body=f"La baja de {empleado.nombre} {empleado.apellidos} ha sido completada.",
            html_body=html_body
        )
        
        self.email_service.send(message)
        logger.info(f"Notificacion de baja completada enviada a {len(rrhh_emails)} usuarios RRHH")
    
    # ==========================================
    # CREATE
    # ==========================================
    def create_empleado(self, data: EmpleadoCreate, usuario_id: int) -> Empleado:
        """
        Crea un nuevo empleado.
        
        Args:
            data: Datos del empleado
            usuario_id: ID del usuario que realiza la accion
        
        Returns:
            Empleado creado
        """
        if self.repo.exists_by_ci(data.ci):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un empleado con CI '{data.ci}'"
            )
        
        if data.email and self.repo.exists_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un empleado con email '{data.email}'"
            )
        
        empleado_data = data.model_dump()
        empleado_data["estado"] = EstadoEmpleado.ACTIVO
        
        nuevo_empleado = self.repo.create(empleado_data)
        self.db.commit()
        self.db.refresh(nuevo_empleado)
        
        logger.info(
            f"Usuario {usuario_id} creo empleado: {nuevo_empleado.nombre} "
            f"{nuevo_empleado.apellidos} (CI: {nuevo_empleado.ci})"
        )
        
        self._notificar_alta(nuevo_empleado)
        
        return nuevo_empleado
    
    # ==========================================
    # GET
    # ==========================================
    def get_empleado(self, empleado_id: int) -> Optional[Empleado]:
        """Obtiene un empleado por su ID."""
        return self.repo.get_by_id(empleado_id)
    
    def get_empleado_by_ci(self, ci: str) -> Optional[Empleado]:
        """Obtiene un empleado por su CI."""
        return self.repo.get_by_ci(ci)
    
    # ==========================================
    # LIST
    # ==========================================
    def list_empleados(
        self,
        page: int = 1,
        size: int = 50,
        estado: Optional[str] = None,
        departamento: Optional[str] = None,
        search: Optional[str] = None
    ) -> EmpleadoListResponse:
        """
        Lista empleados con paginacion y filtros.
        """
        skip = (page - 1) * size
        empleados, total = self.repo.get_all(
            skip=skip,
            limit=size,
            estado=estado,
            departamento=departamento,
            search=search
        )
        
        pages = (total + size - 1) // size if total > 0 else 1
        
        return EmpleadoListResponse(
            items=[EmpleadoResponse.model_validate(e) for e in empleados],
            total=total,
            page=page,
            per_page=size,
            pages=pages
        )
    
    def list_activos(self, page: int = 1, size: int = 50) -> EmpleadoListResponse:
        """Lista solo empleados activos."""
        skip = (page - 1) * size
        empleados, total = self.repo.get_activos(skip, size)
        
        pages = (total + size - 1) // size if total > 0 else 1
        
        return EmpleadoListResponse(
            items=[EmpleadoResponse.model_validate(e) for e in empleados],
            total=total,
            page=page,
            per_page=size,
            pages=pages
        )
    
    def list_pendientes_baja(self, page: int = 1, size: int = 50) -> EmpleadoListResponse:
        """Lista empleados pendientes de baja."""
        skip = (page - 1) * size
        empleados, total = self.repo.get_pendientes_baja(skip, size)
        
        pages = (total + size - 1) // size if total > 0 else 1
        
        return EmpleadoListResponse(
            items=[EmpleadoResponse.model_validate(e) for e in empleados],
            total=total,
            page=page,
            per_page=size,
            pages=pages
        )
    
    # ==========================================
    # UPDATE
    # ==========================================
    def update_empleado(
        self,
        empleado_id: int,
        data: EmpleadoUpdate,
        usuario_id: int
    ) -> Empleado:
        """
        Actualiza un empleado existente.
        """
        empleado = self.repo.get_by_id(empleado_id)
        
        if not empleado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empleado no encontrado"
            )
        
        if empleado.estado == EstadoEmpleado.DADO_BAJA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede actualizar un empleado dado de baja. Use recontratacion."
            )
        
        if data.ci and data.ci != empleado.ci:
            if self.repo.exists_by_ci(data.ci):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ya existe un empleado con CI '{data.ci}'"
                )
        
        if data.email and data.email != empleado.email:
            if self.repo.exists_by_email(data.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ya existe un empleado con email '{data.email}'"
                )
        
        update_data = data.model_dump(exclude_unset=True)
        empleado_actualizado = self.repo.update(empleado, update_data)
        self.db.commit()
        self.db.refresh(empleado_actualizado)
        
        logger.info(
            f"Usuario {usuario_id} actualizo empleado: {empleado_actualizado.nombre} "
            f"{empleado_actualizado.apellidos} (ID: {empleado_actualizado.id})"
        )
        
        return empleado_actualizado
    
    # ==========================================
    # BAJA
    # ==========================================
    def solicitar_baja(
        self,
        empleado_id: int,
        motivo: str,
        urgente: bool = False,
        usuario_id: int = None
    ) -> Empleado:
        """
        Solicita la baja de un empleado.
        
        Cambia el estado a PENDIENTE_BAJA para que los informaticos
        desactiven los accesos.
        """
        empleado = self.repo.get_by_id(empleado_id)
        
        if not empleado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empleado no encontrado"
            )
        
        if empleado.estado == EstadoEmpleado.DADO_BAJA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El empleado ya esta dado de baja"
            )
        
        if empleado.estado == EstadoEmpleado.PENDIENTE_BAJA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El empleado ya tiene una solicitud de baja pendiente"
            )
        
        empleado_actualizado = self.repo.solicitar_baja(empleado_id, motivo)
        self.db.commit()
        self.db.refresh(empleado_actualizado)
        
        logger.warning(
            f"Usuario {usuario_id} solicito baja de empleado: "
            f"{empleado_actualizado.nombre} {empleado_actualizado.apellidos} (CI: {empleado_actualizado.ci}) - "
            f"Motivo: {motivo} - {'URGENTE' if urgente else 'Normal'}"
        )
        
        self._notificar_baja_solicitada(empleado_actualizado, motivo, urgente)
        
        return empleado_actualizado
    
    def completar_baja(
        self,
        empleado_id: int,
        usuario_id: int = None
    ) -> Empleado:
        """
        Completa la baja de un empleado (informaticos).
        
        Cambia el estado a DADO_BAJA y registra la fecha de baja.
        No requiere motivo, solo completa el proceso.
        """
        empleado = self.repo.get_by_id(empleado_id)
        
        if not empleado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empleado no encontrado"
            )
        
        if empleado.estado != EstadoEmpleado.PENDIENTE_BAJA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede completar la baja de un empleado con estado '{empleado.estado}'. Solo se permite para empleados en PENDIENTE_BAJA."
            )
        
        # Dar de baja (sin motivo, se usa el motivo que ya tiene)
        empleado_dado_baja = self.repo.dar_baja(empleado_id)
        self.db.commit()
        self.db.refresh(empleado_dado_baja)
        
        logger.warning(
            f"Usuario {usuario_id} completo baja de empleado: "
            f"{empleado_dado_baja.nombre} {empleado_dado_baja.apellidos} "
            f"(CI: {empleado_dado_baja.ci})"
        )
        
        self._notificar_baja_completada(empleado_dado_baja)
        
        return empleado_dado_baja
    
    # ==========================================
    # RECONTRATACION
    # ==========================================
    def reactivar_empleado(
        self,
        empleado_id: int,
        comentarios: Optional[str] = None,
        usuario_id: int = None
    ) -> Empleado:
        """
        Reactiva a un empleado dado de baja (recontratacion).
        """
        empleado = self.repo.get_by_id(empleado_id)
        
        if not empleado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empleado no encontrado"
            )
        
        if empleado.estado != EstadoEmpleado.DADO_BAJA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede reactivar un empleado con estado '{empleado.estado}'. Solo se permite reactivar empleados dados de baja."
            )
        
        empleado_reactivado = self.repo.reactivar(empleado_id)
        
        if comentarios:
            obs = f"Recontratado: {comentarios}"
            empleado_reactivado.observaciones = (
                f"{empleado_reactivado.observaciones}\n{obs}"
                if empleado_reactivado.observaciones else obs
            )
            self.db.add(empleado_reactivado)
            self.db.flush()
        
        self.db.commit()
        self.db.refresh(empleado_reactivado)
        
        logger.info(
            f"Usuario {usuario_id} reactivo empleado: "
            f"{empleado_reactivado.nombre} {empleado_reactivado.apellidos} "
            f"(CI: {empleado_reactivado.ci}) - "
            f"Recontratacion #{empleado_reactivado.veces_recontratado}"
        )
        
        self._notificar_alta(empleado_reactivado)
        
        return empleado_reactivado
    
    # ==========================================
    # LIST ALL (SIN PAGINACION) - PARA PDF
    # ==========================================

    def list_all_activos(self) -> List[Empleado]:
        """
        Obtiene todos los empleados activos (sin paginacion).
        Util para generar reportes PDF.
        """
        empleados, _ = self.repo.get_all(
            skip=0,
            limit=10000,
            estado=EstadoEmpleado.ACTIVO
        )
        return empleados

    def list_all(self) -> List[Empleado]:
        """
        Obtiene todos los empleados (sin paginacion).
        Util para generar reportes PDF.
        """
        empleados, _ = self.repo.get_all(
            skip=0,
            limit=10000
        )
        return empleados
    
    # ==========================================
    # PDF
    # ==========================================
    def generar_reporte_activos_pdf(self) -> BytesIO:
        """
        Genera un reporte PDF con todos los empleados activos.
        
        Returns:
            BytesIO: Archivo PDF en memoria
        """
        empleados = self.list_all_activos()
        return self.pdf_service.generar_reporte_empleados_activos(empleados)