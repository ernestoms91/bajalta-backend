# app/features/auth/endpoints.py
from fastapi import APIRouter, status, Query, Path
from app.features.auth.dependencies import AuthServiceDep, UserServiceDep, CurrentUser, CurrentAdmin
from app.features.auth.schemas import (
    LoginResponse,
    Token,
    LoginRequest,
    RefreshTokenRequest,
    UserChangePassword,
    UserResponse,
    UserListResponse,
    UserCreate,
    UserUpdate
)
from app.features.shared.schemas import CommonResponse

# ==========================================
# ROUTER DE AUTENTICACION
# ==========================================

auth_router = APIRouter(prefix="/auth", tags=["Autenticacion"])


@auth_router.post("/login", response_model=CommonResponse[LoginResponse])
def login(
    auth_service: AuthServiceDep,
    request: LoginRequest
) -> CommonResponse[LoginResponse]:
    """Iniciar sesion."""
    result = auth_service.login(request.username, request.password)
    return CommonResponse.success(message="Login exitoso", data=result)


@auth_router.post("/refresh", response_model=CommonResponse[Token])
def refresh_access_token(
    auth_service: AuthServiceDep,
    request: RefreshTokenRequest
) -> CommonResponse[Token]:
    """Refrescar token de acceso."""
    result = auth_service.refresh_token(request.refresh_token)
    return CommonResponse.success(message="Token refrescado", data=result)


@auth_router.post("/change-password", response_model=CommonResponse)
def change_password(
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
    request: UserChangePassword
) -> CommonResponse:
    """Cambiar contrasena."""
    auth_service.change_password(current_user, request.current_password, request.new_password)
    return CommonResponse.success(message="Contrasena cambiada exitosamente")


@auth_router.get("/me", response_model=CommonResponse[UserResponse])
def get_current_user_profile(
    current_user: CurrentUser
) -> CommonResponse[UserResponse]:
    """Obtener perfil del usuario actual."""
    return CommonResponse.success(
        message="Perfil obtenido",
        data=UserResponse.model_validate(current_user)
    )


# ==========================================
# ROUTER DE USUARIOS (ADMIN)
# ==========================================

user_router = APIRouter(prefix="/users", tags=["Usuarios"])


@user_router.post("/", response_model=CommonResponse[UserResponse], status_code=201)
def create_user(
    current_admin: CurrentAdmin,
    user_service: UserServiceDep,
    request: UserCreate
) -> CommonResponse[UserResponse]:
    """Crear usuario (solo admin)."""
    new_user = user_service.create_user(current_admin, request)
    return CommonResponse.success(
        message="Usuario creado",
        data=UserResponse.model_validate(new_user)
    )


@user_router.get("/", response_model=CommonResponse[UserListResponse])
def list_users(
    current_admin: CurrentAdmin,
    user_service: UserServiceDep,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    active_only: bool = Query(False),
    is_admin: bool = Query(None, description="Filtrar por administrador (true/false)")
) -> CommonResponse[UserListResponse]:
    """Listar usuarios (solo admin)."""
    result = user_service.list_users_paginated(
        page=page, 
        size=size, 
        active_only=active_only, 
        is_admin=is_admin
    )
    return CommonResponse.success(message="Usuarios obtenidos", data=result)


@user_router.put("/{user_id}", response_model=CommonResponse[UserResponse])
def update_user(
    current_admin: CurrentAdmin,
    user_service: UserServiceDep,
    request: UserUpdate,
    user_id: int = Path(..., ge=1)
) -> CommonResponse[UserResponse]:
    """Actualizar usuario (solo admin)."""
    updated_user = user_service.update_user(current_admin, user_id, request)
    return CommonResponse.success(
        message="Usuario actualizado",
        data=UserResponse.model_validate(updated_user)
    )


@user_router.delete("/{user_id}", response_model=CommonResponse[UserResponse])
def disable_user(
    current_admin: CurrentAdmin,
    user_service: UserServiceDep,
    user_id: int = Path(..., ge=1)
) -> CommonResponse[UserResponse]:
    """Deshabilitar usuario (solo admin)."""
    user = user_service.disable_user(current_admin, user_id)
    return CommonResponse.success(
        message="Usuario deshabilitado",
        data=UserResponse.model_validate(user)
    )


@user_router.put("/{user_id}/enable", response_model=CommonResponse[UserResponse])
def enable_user(
    current_admin: CurrentAdmin,
    user_service: UserServiceDep,
    user_id: int = Path(..., ge=1)
) -> CommonResponse[UserResponse]:
    """Habilitar usuario (solo admin)."""
    user = user_service.enable_user(current_admin, user_id)
    return CommonResponse.success(
        message="Usuario habilitado",
        data=UserResponse.model_validate(user)
    )


# ==========================================
# EXPORTAR ROUTERS
# ==========================================
__all__ = ["auth_router", "user_router"]