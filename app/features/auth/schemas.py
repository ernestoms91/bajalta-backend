# app/features/auth/schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional
import re


# ==========================================
# ESQUEMAS DE AUTENTICACIÓN
# ==========================================

class LoginRequest(BaseModel):
    """Datos para iniciar sesion."""
    username: str = Field(..., description="Nombre de usuario")
    password: str = Field(..., min_length=6, description="Contraseña")


class Token(BaseModel):
    """Respuesta base con tokens JWT."""
    access_token: str = Field(..., description="Token de acceso (corta duracion)")
    refresh_token: str = Field(..., description="Token de refresco (larga duracion)")
    token_type: str = Field(default="bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Segundos hasta expiracion del access_token")


class LoginResponse(Token):
    """Respuesta completa de login (tokens + usuario)."""
    user: "UserResponse" = Field(..., description="Datos del usuario autenticado")


class RefreshTokenRequest(BaseModel):
    """Solicitud para renovar el access token."""
    refresh_token: str = Field(..., description="Refresh token valido")


class LogoutRequest(BaseModel):
    """Solicitud para cerrar sesion."""
    refresh_token: str = Field(..., description="Refresh token a invalidar")


# ==========================================
# ESQUEMAS DE USUARIO (CRUD)
# ==========================================

class UserBase(BaseModel):
    """Base de usuario (sin campos sensibles)."""
    email: EmailStr = Field(..., description="Email unico")
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        description="Nombre de usuario unico"
    )
    full_name: Optional[str] = Field(
        None, 
        max_length=100,
        description="Nombre completo del usuario"
    )
    is_admin: bool = Field(
        default=False,
        description="Si el usuario es administrador"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Valida que el username solo contenga caracteres permitidos."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username solo puede contener letras, numeros, guiones y guiones bajos")
        return v


class UserCreate(UserBase):
    """Creacion de nuevo usuario (incluye contrasena)."""
    password: str = Field(
        ..., 
        min_length=8,  # ← Cambiado de 6 a 8
        max_length=100,
        description="Contrasena del usuario (minimo 8 caracteres)"
    )
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Valida que la contrasena sea segura:
        - Minimo 8 caracteres
        - Al menos una mayuscula
        - Al menos una minuscula
        - Al menos un numero
        - Al menos un caracter especial
        """
        if len(v) < 8:
            raise ValueError("La contrasena debe tener al menos 8 caracteres")
        
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contrasena debe tener al menos una mayuscula")
        
        if not re.search(r"[a-z]", v):
            raise ValueError("La contrasena debe tener al menos una minuscula")
        
        if not re.search(r"\d", v):
            raise ValueError("La contrasena debe tener al menos un numero")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("La contrasena debe tener al menos un caracter especial (!@#$%^&*(),.?\":{}|<>)")
        
        return v


class UserUpdate(BaseModel):
    """Actualizacion de datos de usuario."""
    email: Optional[EmailStr] = Field(None, description="Nuevo email")
    username: Optional[str] = Field(
        None, 
        min_length=3, 
        max_length=50,
        description="Nuevo nombre de usuario"
    )
    full_name: Optional[str] = Field(
        None, 
        max_length=100,
        description="Nuevo nombre completo"
    )
    is_admin: Optional[bool] = Field(None, description="Hacer administrador o no")
    is_active: Optional[bool] = Field(None, description="Activar/desactivar usuario")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Valida el username si se proporciona."""
        if v is not None:
            if not v.replace("_", "").replace("-", "").isalnum():
                raise ValueError("Username solo puede contener letras, numeros, guiones y guiones bajos")
        return v


class UserChangePassword(BaseModel):
    """Cambio de contrasena del usuario autenticado."""
    current_password: str = Field(
        ..., 
        min_length=8,
        description="Contrasena actual"
    )
    new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=100,
        description="Nueva contrasena (minimo 8 caracteres)"
    )
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """
        Valida que la nueva contrasena sea segura.
        """
        if len(v) < 8:
            raise ValueError("La nueva contrasena debe tener al menos 8 caracteres")
        
        if not re.search(r"[A-Z]", v):
            raise ValueError("La nueva contrasena debe tener al menos una mayuscula")
        
        if not re.search(r"[a-z]", v):
            raise ValueError("La nueva contrasena debe tener al menos una minuscula")
        
        if not re.search(r"\d", v):
            raise ValueError("La nueva contrasena debe tener al menos un numero")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("La nueva contrasena debe tener al menos un caracter especial (!@#$%^&*(),.?\":{}|<>)")
        
        return v


class UserResetPassword(BaseModel):
    """Resetear contrasena de un usuario (solo admin)."""
    new_password: str = Field(
        ..., 
        min_length=8, 
        max_length=100,
        description="Nueva contrasena temporal (minimo 8 caracteres)"
    )
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Valida que la contrasena sea segura."""
        if len(v) < 8:
            raise ValueError("La contrasena debe tener al menos 8 caracteres")
        
        if not re.search(r"[A-Z]", v):
            raise ValueError("La contrasena debe tener al menos una mayuscula")
        
        if not re.search(r"[a-z]", v):
            raise ValueError("La contrasena debe tener al menos una minuscula")
        
        if not re.search(r"\d", v):
            raise ValueError("La contrasena debe tener al menos un numero")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("La contrasena debe tener al menos un caracter especial (!@#$%^&*(),.?\":{}|<>)")
        
        return v


# ==========================================
# ESQUEMAS DE RESPUESTA
# ==========================================

class UserResponse(UserBase):
    """Respuesta de usuario (sin contrasena)."""
    id: int = Field(..., description="ID del usuario")
    is_active: bool = Field(..., description="Si el usuario esta activo")
    created_at: datetime = Field(..., description="Fecha de creacion")
    updated_at: datetime = Field(..., description="Fecha de ultima actualizacion")
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Respuesta para listado paginado de usuarios."""
    items: list[UserResponse]
    total: int = Field(..., description="Total de usuarios")
    page: int = Field(..., description="Pagina actual")
    per_page: int = Field(..., description="Elementos por pagina")
    pages: int = Field(..., description="Total de paginas")


# ==========================================
# ESQUEMAS DE MI PERFIL
# ==========================================

class UserProfileUpdate(BaseModel):
    """Actualizacion del propio perfil del usuario."""
    full_name: Optional[str] = Field(None, max_length=100, description="Nuevo nombre completo")
    email: Optional[EmailStr] = Field(None, description="Nuevo email")


class UserProfileResponse(UserResponse):
    """Respuesta del perfil del usuario autenticado."""
    pass


# ==========================================
# EVITAR REFERENCIAS CIRCULARES
# ==========================================
LoginResponse.model_rebuild()