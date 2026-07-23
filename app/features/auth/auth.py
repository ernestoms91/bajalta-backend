# app/features/auth/auth.py
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from app.features.auth.dependencies import CurrentUser, AuthServiceDep
from app.features.auth.schemas import (
    LoginResponse,
    Token,
    RefreshTokenRequest,
    UserChangePassword,
    UserResponse
)
from features.shared.schemas import CommonResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/login",
    response_model=CommonResponse[LoginResponse],
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión"
)
def login(
    auth_service: AuthServiceDep,
    form_data: OAuth2PasswordRequestForm = Depends()
) -> CommonResponse[LoginResponse]:
    """
    Autentica un usuario y devuelve access_token y refresh_token.
    
    - **username**: Email del usuario
    - **password**: Contraseña
    """
    result = auth_service.login(form_data.username, form_data.password)
    return CommonResponse.success(
        message="Login exitoso",
        data=result
    )


@router.post(
    "/refresh",
    response_model=CommonResponse[Token],
    status_code=status.HTTP_200_OK,
    summary="Refrescar token de acceso"
)
def refresh_access_token(
    auth_service: AuthServiceDep,
    request: RefreshTokenRequest
) -> CommonResponse[Token]:
    """
    Genera un nuevo access_token usando un refresh_token válido.
    """
    result = auth_service.refresh_token(request.refresh_token)
    return CommonResponse.success(
        message="Token refrescado exitosamente",
        data=result
    )


@router.post(
    "/change-password",
    response_model=CommonResponse,
    status_code=status.HTTP_200_OK,
    summary="Cambiar contraseña"
)
def change_password(
    current_user: CurrentUser,
    auth_service: AuthServiceDep,
    request: UserChangePassword
) -> CommonResponse:
    """
    Cambia la contraseña del usuario autenticado.
    
    - **current_password**: Contraseña actual
    - **new_password**: Nueva contraseña
    """
    auth_service.change_password(
        current_user,
        request.current_password,
        request.new_password
    )
    return CommonResponse.success(
        message="Contraseña cambiada exitosamente"
    )


@router.get(
    "/me",
    response_model=CommonResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Obtener perfil del usuario actual"
)
def get_current_user_profile(
    current_user: CurrentUser
) -> CommonResponse[UserResponse]:
    """
    Retorna la información del usuario autenticado.
    """
    return CommonResponse.success(
        message="Perfil obtenido exitosamente",
        data=UserResponse.model_validate(current_user)
    )