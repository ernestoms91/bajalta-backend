# app/features/auth/dependencies.py
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import select
from app.core.dependencies import DBSession
from app.features.auth.models import User
from app.core.security import decode_token, validate_token_and_password_version
from app.features.auth.service import AuthService, UserService


# ==========================================
# DEPENDENCIAS DE SERVICIOS
# ==========================================

def get_auth_service(session: DBSession) -> AuthService:
    """Dependencia para inyectar AuthService."""
    return AuthService(session)

def get_user_service(session: DBSession) -> UserService:
    """Dependencia para inyectar UserService."""
    return UserService(session)

# Type Aliases para servicios
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


# ==========================================
# DEPENDENCIAS DE AUTENTICACIÓN
# ==========================================

security = HTTPBearer(auto_error=False)
Credentials = Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]


async def get_current_user(
    credentials: Credentials,
    session: DBSession,
) -> Optional[User]:
    """
    Obtiene el usuario actual a partir del token JWT.
    Retorna None si no está autenticado.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    statement = select(User).where(User.id == int(user_id))
    user = session.exec(statement).first()
    
    if not user:
        return None
    
    if not validate_token_and_password_version(token, user.password_version):
        return None
    
    return user


async def get_current_active_user(
    current_user: Annotated[Optional[User], Depends(get_current_user)]
) -> User:
    """
    Obtiene el usuario actual y verifica que esté activo.
    Lanza HTTPException si no está autenticado o inactivo.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    return current_user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    Verifica que el usuario sea administrador.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren privilegios de administrador"
        )
    
    return current_user


# ==========================================
# TYPE ALIASES
# ==========================================

# Usuario autenticado y activo (obligatorio)
CurrentUser = Annotated[User, Depends(get_current_active_user)]

# Usuario con rol ADMIN
CurrentAdmin = Annotated[User, Depends(get_current_admin_user)]

# Usuario opcional (puede ser None)
OptionalUser = Annotated[Optional[User], Depends(get_current_user)]