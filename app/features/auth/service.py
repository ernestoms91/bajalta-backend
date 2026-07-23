# app/features/auth/service.py
from fastapi import HTTPException, status
from datetime import datetime, timezone
from typing import Optional
from app.core.config import settings
from app.core.dependencies import DBSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    validate_refresh_token,
    decode_token,
    verify_password,
    hash_password
)
from app.core.logging import get_logger
from app.features.auth.models import User
from app.features.auth.schemas import (
    UserCreate, 
    UserUpdate, 
    UserResponse,
    LoginResponse,
    Token,
    UserListResponse
)
from app.features.auth.repository import UsuarioRepository

logger = get_logger(__name__)


# ==========================================
# SERVICIO DE AUTENTICACIÓN
# ==========================================

class AuthService:
    """Servicio de autenticación: login, refresh, cambio de contraseña."""
    
    def __init__(self, db: DBSession):
        self.db = db
        self.repo = UsuarioRepository(db)
    
    def login(self, username: str, password: str) -> LoginResponse:
        """Autentica a un usuario y genera tokens JWT."""
        user = self.repo.get_by_username(username)  # ← Cambiar get_by_email por get_by_username
        
        if not user or not verify_password(password, user.hashed_password):
            logger.warning(f"Login fallido: {username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario o contraseña incorrectos"
            )
        
        if not user.is_active:
            logger.warning(f"Login fallido: usuario inactivo - {username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario deshabilitado. Contacte al administrador"
            )
        
        self.repo.update_last_access(user.id)
        self.db.commit()
        
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            password_version=user.password_version,
            is_admin=user.is_admin
        )
        
        refresh_token = create_refresh_token(
            user_id=user.id,
            username=user.username,
            password_version=user.password_version,
            is_admin=user.is_admin
        )
        
        logger.info(f"Login exitoso: {user.username}")
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_EXPIRES_MIN * 60,
            user=UserResponse.model_validate(user)
        )
    
    def refresh_token(self, refresh_token: str) -> Token:
        """Valida refresh_token y genera un nuevo access_token."""
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            logger.warning("Intento de refresh con token inválido")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido o expirado"
            )

        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Refresh token sin user_id")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido"
            )

        user = self.repo.get_by_id(int(user_id))
        if not user:
            logger.warning(f"Refresh token para usuario no existente: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido"
            )

        if not user.is_active:
            logger.warning(f"Refresh token usado por usuario inactivo: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )

        if not validate_refresh_token(refresh_token, user.password_version):
            logger.warning(
                f"Refresh token inválido por versión de contraseña o tipo: {user.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido o expirado"
            )

        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            password_version=user.password_version,
            is_admin=user.is_admin
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_EXPIRES_MIN * 60
        )
    
    def change_password(
        self, 
        user: User, 
        current_password: str, 
        new_password: str
    ) -> User:
        """Cambia la contraseña del usuario autenticado."""
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña actual incorrecta"
            )
        
        if verify_password(new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La nueva contraseña debe ser diferente a la actual"
            )
        
        new_hashed_password = hash_password(new_password)
        new_version = user.password_version + 1
        
        updated_user = self.repo.update_password(
            user.id, 
            new_hashed_password, 
            new_version
        )
        self.db.commit()
        self.db.refresh(updated_user)
        
        logger.info(f"Contraseña cambiada para: {user.username}")
        return updated_user


# ==========================================
# SERVICIO DE USUARIOS (CRUD ADMIN)
# ==========================================

class UserService:
    """Servicio de gestión de usuarios: CRUD, activación/desactivación."""
    
    def __init__(self, db: DBSession):
        self.db = db
        self.repo = UsuarioRepository(db)
    
    def create_user(self, admin_user: User, data: UserCreate) -> User:
        """Crea un nuevo usuario (solo admin)."""
        if self.repo.exists_by_username(data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El username '{data.username}' ya existe"
            )
        
        if self.repo.exists_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El email '{data.email}' ya existe"
            )
        
        user_data = {
            "username": data.username,
            "email": data.email,
            "hashed_password": hash_password(data.password),
            "full_name": data.full_name,
            "is_active": True,
            "is_admin": data.is_admin if hasattr(data, 'is_admin') else False,
            "password_version": 1,
            "created_at": datetime.now(timezone.utc)
        }
        
        new_user = self.repo.create(user_data)
        self.db.commit()
        self.db.refresh(new_user)
        
        logger.info(f"Admin {admin_user.username} creó usuario: {new_user.username}")
        return new_user
    
    def list_users_paginated(
        self, 
        page: int = 1, 
        size: int = 50,
        active_only: bool = False,
        is_admin: Optional[bool] = None
    ) -> UserListResponse:
        """
        Lista usuarios con paginación y filtros.
        
        Args:
            page: Número de página
            size: Elementos por página
            active_only: Solo usuarios activos
            is_admin: Filtrar por rol (True=admin, False=usuario normal)
        """
        skip = (page - 1) * size
        users, total = self.repo.get_all(
            skip=skip, 
            limit=size,
            active_only=active_only,
            is_admin=is_admin
        )
        
        pages = (total + size - 1) // size if total > 0 else 1
        
        return UserListResponse(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            per_page=size,
            pages=pages
        )
    
    def get_user(self, user_id: int) -> User:
        """Obtiene un usuario por ID."""
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        return user
    
    def update_user(
        self, 
        admin_user: User, 
        user_id: int, 
        data: UserUpdate
    ) -> User:
        """
        Actualiza un usuario (solo admin).
        
        Reglas:
        - Admin puede modificar a cualquier usuario
        - Admin NO puede deshabilitar su propia cuenta
        - Admin NO puede cambiar su propio rol de admin
        """
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # ====== RESTRICCIONES PARA AUTO-MODIFICACIÓN ======
        if admin_user.id == user_id:
            # Un admin no puede deshabilitar su propia cuenta
            if data.is_active is not None and not data.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No puedes deshabilitar tu propia cuenta"
                )
            # Un admin no puede quitarse el rol de admin
            if data.is_admin is not None and not data.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No puedes quitarte el rol de administrador"
                )
        
        # ====== PERMITIR MODIFICAR A OTRO ADMIN ======
        # Un admin puede modificar a otro admin (incluyendo deshabilitarlo)
        if user.is_admin and admin_user.id != user_id:
            logger.warning(
                f"Admin {admin_user.username} está modificando a otro admin: {user.username}"
            )
        
        # Validar username único
        if data.username and data.username != user.username:
            if self.repo.exists_by_username(data.username):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El username '{data.username}' ya está en uso"
                )
        
        # Validar email único
        if data.email and data.email != user.email:
            if self.repo.exists_by_email(data.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El email '{data.email}' ya está en uso"
                )
        
        # Preparar datos para actualizar
        update_data = data.model_dump(exclude_unset=True)
        
        # Log de cambios importantes
        if "is_admin" in update_data:
            estado = "admin" if update_data["is_admin"] else "usuario normal"
            logger.warning(
                f"Admin {admin_user.username} cambió rol de {user.username} "
                f"de {'admin' if user.is_admin else 'usuario normal'} a {estado}"
            )
        
        if "is_active" in update_data:
            estado = "habilitó" if update_data["is_active"] else "deshabilitó"
            logger.warning(
                f"Admin {admin_user.username} {estado} a {user.username} "
                f"(anterior: {'activo' if user.is_active else 'inactivo'})"
            )
        
        # Actualizar usuario
        updated_user = self.repo.update(user, update_data)
        self.db.commit()
        self.db.refresh(updated_user)
        
        logger.info(f"Admin {admin_user.username} actualizó usuario: {user.username}")
        return updated_user
    
    def disable_user(self, admin_user: User, user_id: int) -> User:
        """Deshabilita un usuario (solo admin)."""
        # Prevenir auto-deshabilitación
        if admin_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes deshabilitar tu propia cuenta"
            )
        
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El usuario {user.username} ya está deshabilitado"
            )
        
        # Permitir deshabilitar a otro admin
        if user.is_admin:
            logger.warning(
                f"ADMIN {admin_user.username} está DESHABILITANDO a otro admin: {user.username}"
            )
        
        disabled_user = self.repo.disable(user_id)
        self.db.commit()
        self.db.refresh(disabled_user)
        
        logger.info(f"Admin {admin_user.username} deshabilitó a: {user.username}")
        return disabled_user
    
    def enable_user(self, admin_user: User, user_id: int) -> User:
        """Habilita un usuario (solo admin)."""
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El usuario {user.username} ya está habilitado"
            )
        
        if user.is_admin:
            logger.warning(
                f"ADMIN {admin_user.username} está HABILITANDO a otro admin: {user.username}"
            )
        
        enabled_user = self.repo.enable(user_id)
        self.db.commit()
        self.db.refresh(enabled_user)
        
        logger.info(f"Admin {admin_user.username} habilitó a: {user.username}")
        return enabled_user
    
    def delete_user(self, admin_user: User, user_id: int) -> None:
        """Elimina un usuario físicamente (solo admin, usar con cuidado)."""
        if admin_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes eliminar tu propia cuenta"
            )
        
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        if user.is_admin:
            logger.warning(
                f"ADMIN {admin_user.username} está ELIMINANDO a otro admin: {user.username}"
            )
        
        self.repo.delete(user_id)
        self.db.commit()
        
        logger.warning(f"Admin {admin_user.username} eliminó a: {user.username}")