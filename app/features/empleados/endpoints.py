# app/features/empleados/endpoints.py
from datetime import datetime

from fastapi import APIRouter, Response, status, Query, Path
from typing import Optional
from app.core.dependencies import DBSession
from app.features.auth.dependencies import CurrentUser, CurrentAdmin
from app.features.empleados.dependencies import EmpleadoServiceDep
from app.features.empleados.schemas import (
    EmpleadoCreate,
    EmpleadoUpdate,
    EmpleadoResponse,
    EmpleadoListResponse,
    EmpleadoBajaRequest,
    EmpleadoRecontratar,
)
from app.features.shared.schemas import CommonResponse


empleados_router = APIRouter(prefix="/empleados", tags=["Empleados"])


# ==========================================
# ENDPOINTS DE EMPLEADOS (RRHH Y ADMIN)
# ==========================================

@empleados_router.post(
    "/",
    response_model=CommonResponse[EmpleadoResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo empleado"
)
def create_empleado(
    current_user: CurrentUser,
    service: EmpleadoServiceDep,
    data: EmpleadoCreate
) -> CommonResponse[EmpleadoResponse]:
    """
    Crea un nuevo empleado en el sistema.
    
    - **nombre**: Nombre del empleado
    - **apellidos**: Apellidos del empleado
    - **ci**: Carnet de identidad (11 digitos exactos)
    - **telefono**: Numero de telefono (opcional)
    - **email**: Email personal (opcional)
    - **departamento**: Departamento al que pertenece
    - **observaciones**: Observaciones adicionales (opcional)
    """
    nuevo_empleado = service.create_empleado(data, current_user.id)
    return CommonResponse.success(
        message=f"Empleado {nuevo_empleado.nombre} {nuevo_empleado.apellidos} creado exitosamente",
        data=EmpleadoResponse.model_validate(nuevo_empleado)
    )


@empleados_router.get(
    "/",
    response_model=CommonResponse[EmpleadoListResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar empleados"
)
def list_empleados(
    current_user: CurrentUser,
    service: EmpleadoServiceDep,
    page: int = Query(1, ge=1, description="Numero de pagina"),
    size: int = Query(50, ge=1, le=100, description="Elementos por pagina"),
    estado: Optional[str] = Query(None, description="Filtrar por estado (ACTIVO, PENDIENTE_BAJA, DADO_BAJA)"),
    departamento: Optional[str] = Query(None, description="Filtrar por departamento"),
    search: Optional[str] = Query(None, description="Buscar por nombre, apellidos o CI")
) -> CommonResponse[EmpleadoListResponse]:
    """
    Lista empleados con paginacion y filtros.
    """
    result = service.list_empleados(
        page=page,
        size=size,
        estado=estado,
        departamento=departamento,
        search=search
    )
    return CommonResponse.success(
        message="Empleados obtenidos exitosamente",
        data=result
    )


@empleados_router.get(
    "/activos",
    response_model=CommonResponse[EmpleadoListResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar empleados activos"
)
def list_empleados_activos(
    current_user: CurrentUser,
    service: EmpleadoServiceDep,
    page: int = Query(1, ge=1, description="Numero de pagina"),
    size: int = Query(50, ge=1, le=100, description="Elementos por pagina")
) -> CommonResponse[EmpleadoListResponse]:
    """
    Lista solo empleados activos.
    """
    result = service.list_activos(page=page, size=size)
    return CommonResponse.success(
        message="Empleados activos obtenidos exitosamente",
        data=result
    )


@empleados_router.get(
    "/pendientes-baja",
    response_model=CommonResponse[EmpleadoListResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar empleados pendientes de baja"
)
def list_empleados_pendientes_baja(
    current_user: CurrentAdmin,
    service: EmpleadoServiceDep,
    page: int = Query(1, ge=1, description="Numero de pagina"),
    size: int = Query(50, ge=1, le=100, description="Elementos por pagina")
) -> CommonResponse[EmpleadoListResponse]:
    """
    Lista empleados pendientes de baja (solo ADMIN).
    """
    result = service.list_pendientes_baja(page=page, size=size)
    return CommonResponse.success(
        message="Empleados pendientes de baja obtenidos exitosamente",
        data=result
    )


@empleados_router.get(
    "/{empleado_id}",
    response_model=CommonResponse[EmpleadoResponse],
    status_code=status.HTTP_200_OK,
    summary="Obtener empleado por ID"
)
def get_empleado(
    current_user: CurrentUser,
    service: EmpleadoServiceDep,
    empleado_id: int = Path(..., ge=1, description="ID del empleado")
) -> CommonResponse[EmpleadoResponse]:
    """
    Obtiene un empleado especifico por su ID.
    """
    empleado = service.get_empleado(empleado_id)
    if not empleado:
        return CommonResponse.fail(
            message=f"Empleado con ID {empleado_id} no encontrado",
            data=None
        )
    return CommonResponse.success(
        message="Empleado obtenido exitosamente",
        data=EmpleadoResponse.model_validate(empleado)
    )


@empleados_router.get(
    "/ci/{ci}",
    response_model=CommonResponse[EmpleadoResponse],
    status_code=status.HTTP_200_OK,
    summary="Obtener empleado por CI"
)
def get_empleado_by_ci(
    current_user: CurrentUser,
    service: EmpleadoServiceDep,
    ci: str = Path(..., min_length=11, max_length=11, description="Carnet de identidad (11 digitos)")
) -> CommonResponse[EmpleadoResponse]:
    """
    Obtiene un empleado especifico por su CI.
    """
    empleado = service.get_empleado_by_ci(ci)
    if not empleado:
        return CommonResponse.fail(
            message=f"Empleado con CI {ci} no encontrado",
            data=None
        )
    return CommonResponse.success(
        message="Empleado obtenido exitosamente",
        data=EmpleadoResponse.model_validate(empleado)
    )


@empleados_router.put(
    "/{empleado_id}",
    response_model=CommonResponse[EmpleadoResponse],
    status_code=status.HTTP_200_OK,
    summary="Actualizar empleado"
)
def update_empleado(
    current_user: CurrentUser,
    service: EmpleadoServiceDep,
    empleado_id: int = Path(..., ge=1, description="ID del empleado"),
    data: EmpleadoUpdate = None
) -> CommonResponse[EmpleadoResponse]:
    """
    Actualiza los datos de un empleado.
    
    - **nombre**: Nuevo nombre (opcional)
    - **apellidos**: Nuevos apellidos (opcional)
    - **telefono**: Nuevo telefono (opcional)
    - **email**: Nuevo email (opcional)
    - **departamento**: Nuevo departamento (opcional)
    - **observaciones**: Nuevas observaciones (opcional)
    """
    empleado_actualizado = service.update_empleado(empleado_id, data, current_user.id)
    return CommonResponse.success(
        message=f"Empleado {empleado_actualizado.nombre} {empleado_actualizado.apellidos} actualizado exitosamente",
        data=EmpleadoResponse.model_validate(empleado_actualizado)
    )


@empleados_router.put(
    "/{empleado_id}/baja",
    response_model=CommonResponse[EmpleadoResponse],
    status_code=status.HTTP_200_OK,
    summary="Solicitar baja de empleado"
)
def solicitar_baja_empleado(
    current_user: CurrentUser,
    service: EmpleadoServiceDep,
    empleado_id: int = Path(..., ge=1, description="ID del empleado"),
    data: EmpleadoBajaRequest = None
) -> CommonResponse[EmpleadoResponse]:
    """
    Solicita la baja de un empleado.
    
    Cambia el estado a PENDIENTE_BAJA y notifica a los administradores.
    
    - **motivo**: Motivo de la baja
    - **urgente**: Si la baja es urgente (True/False)
    """
    if not data:
        data = EmpleadoBajaRequest(motivo="No especificado")
    
    empleado = service.solicitar_baja(
        empleado_id=empleado_id,
        motivo=data.motivo,
        urgente=data.urgente,
        usuario_id=current_user.id
    )
    return CommonResponse.success(
        message=f"Baja solicitada para {empleado.nombre} {empleado.apellidos}",
        data=EmpleadoResponse.model_validate(empleado)
    )


@empleados_router.put(
    "/{empleado_id}/completar-baja",
    response_model=CommonResponse[EmpleadoResponse],
    status_code=status.HTTP_200_OK,
    summary="Completar baja de empleado (ADMIN)"
)
def completar_baja_empleado(
    current_user: CurrentAdmin,
    service: EmpleadoServiceDep,
    empleado_id: int = Path(..., ge=1, description="ID del empleado")
) -> CommonResponse[EmpleadoResponse]:
    """
    Completa la baja de un empleado (solo ADMIN).
    
    Cambia el estado a DADO_BAJA y notifica a RRHH.
    Solo se puede completar bajas de empleados en estado PENDIENTE_BAJA.
    El motivo ya se registro al solicitar la baja.
    """
    empleado = service.completar_baja(
        empleado_id=empleado_id,
        usuario_id=current_user.id
    )
    return CommonResponse.success(
        message=f"Baja completada para {empleado.nombre} {empleado.apellidos}",
        data=EmpleadoResponse.model_validate(empleado)
    )


@empleados_router.post(
    "/{empleado_id}/reactivar",
    response_model=CommonResponse[EmpleadoResponse],
    status_code=status.HTTP_200_OK,
    summary="Recontratar empleado"
)
def reactivar_empleado(
    current_user: CurrentUser,
    service: EmpleadoServiceDep,
    empleado_id: int = Path(..., ge=1, description="ID del empleado"),
    data: EmpleadoRecontratar = None
) -> CommonResponse[EmpleadoResponse]:
    """
    Reactiva a un empleado dado de baja (recontratacion).
    
    Solo se puede reactivar empleados en estado DADO_BAJA.
    Incrementa el contador de recontrataciones.
    """
    if not data:
        data = EmpleadoRecontratar()
    
    empleado = service.reactivar_empleado(
        empleado_id=empleado_id,
        comentarios=data.comentarios,
        usuario_id=current_user.id
    )
    return CommonResponse.success(
        message=f"Empleado {empleado.nombre} {empleado.apellidos} reactivado exitosamente. Recontratacion #{empleado.veces_recontratado}",
        data=EmpleadoResponse.model_validate(empleado)
    ) 

@empleados_router.get(
    "/reporte/activos/pdf",
    summary="Generar reporte PDF de empleados activos"
)
def generar_reporte_activos_pdf(
    current_user: CurrentAdmin,
    service: EmpleadoServiceDep
) -> Response:
    """
    Genera un reporte PDF con todos los empleados activos.
    Solo accesible para administradores.
    """
    pdf_buffer = service.generar_reporte_activos_pdf()
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=reporte_activos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        }
    )