# app/features/auth/repository.py
from sqlmodel import Session, select
from typing import Optional, List, Tuple
from sqlalchemy import func
from datetime import datetime, timezone
from app.features.auth.models import User
from app.core.logging import get_logger

logger = get_logger(__name__)


class UsuarioRepository:
    """Repositorio para operaciones CRUD de usuarios."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============================================
    # GET BY FIELD
    # ============================================
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Obtiene un usuario por su ID."""
        return self.db.get(User, user_id)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Obtiene un usuario por su nombre de usuario."""
        return self.db.exec(
            select(User).where(User.username == username)
        ).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Obtiene un usuario por su email."""
        return self.db.exec(
            select(User).where(User.email == email)
        ).first()
    
    # ============================================
    # LIST USERS (CON PAGINACIÓN Y FILTROS)
    # ============================================
    def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        active_only: bool = False,
        is_admin: Optional[bool] = None  # ← Cambio: is_admin en lugar de rol
    ) -> Tuple[List[User], int]:
        """
        Obtiene lista paginada de usuarios.
        
        Args:
            skip: Número de registros a saltar
            limit: Límite de registros
            active_only: Solo usuarios activos
            is_admin: Filtrar por rol (True=admin, False=usuario normal, None=todos)
        
        Returns:
            Tuple con (lista de usuarios, total)
        """
        # Construir query base
        query = select(User)
        
        # Aplicar filtros
        if active_only:
            query = query.where(User.is_active == True)
        
        if is_admin is not None:  # ← Cambio: filtrar por is_admin
            query = query.where(User.is_admin == is_admin)
        
        # Contar total
        total = self.db.exec(select(func.count()).select_from(query.subquery())).one()
        
        # Aplicar paginación
        users = self.db.exec(
            query.offset(skip).limit(limit).order_by(User.id)
        ).all()
        
        return users, total
    
    def get_active_users(self, skip: int = 0, limit: int = 100) -> Tuple[List[User], int]:
        """Obtiene solo usuarios activos."""
        return self.get_all(skip=skip, limit=limit, active_only=True)
    
    def get_admins(self, skip: int = 0, limit: int = 100) -> Tuple[List[User], int]:
        """Obtiene solo usuarios administradores."""
        return self.get_all(skip=skip, limit=limit, is_admin=True)
    
    def get_non_admins(self, skip: int = 0, limit: int = 100) -> Tuple[List[User], int]:
        """Obtiene solo usuarios no administradores."""
        return self.get_all(skip=skip, limit=limit, is_admin=False)
    
    # ============================================
    # CREATE
    # ============================================
    def create(self, user_data: dict) -> User:
        """Crea un nuevo usuario."""
        user = User(**user_data)
        self.db.add(user)
        self.db.flush()  # Obtiene el ID sin commit
        return user
    
    # ============================================
    # UPDATE
    # ============================================
    def update(self, user: User, update_data: dict) -> User:
        """
        Actualiza un usuario existente.
        
        Args:
            user: Objeto User a actualizar
            update_data: Diccionario con los campos a actualizar
        """
        for key, value in update_data.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        
        user.updated_at = datetime.now(timezone.utc)
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user
    
    def update_password(
        self, 
        user_id: int, 
        new_hashed_password: str, 
        new_version: int
    ) -> Optional[User]:
        """Actualiza la contraseña de un usuario."""
        user = self.get_by_id(user_id)
        if user:
            user.hashed_password = new_hashed_password
            user.password_version = new_version
            user.updated_at = datetime.now(timezone.utc)
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        return user
    
    def update_last_access(self, user_id: int) -> Optional[User]:
        """Actualiza la fecha de último acceso."""
        user = self.get_by_id(user_id)
        if user:
            user.updated_at = datetime.now(timezone.utc)  # ← Cambio: updated_at en lugar de ultimo_acceso
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        return user
    
    # ============================================
    # DISABLE / ENABLE
    # ============================================
    def disable(self, user_id: int) -> Optional[User]:
        """Desactiva un usuario."""
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            user.updated_at = datetime.now(timezone.utc)
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        return user
    
    def enable(self, user_id: int) -> Optional[User]:
        """Activa un usuario."""
        user = self.get_by_id(user_id)
        if user:
            user.is_active = True
            user.updated_at = datetime.now(timezone.utc)
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        return user
    
    # ============================================
    # DELETE (OPCIONAL - USAR CON CUIDADO)
    # ============================================
    def delete(self, user_id: int) -> bool:
        """
        Elimina un usuario (hard delete).
        
        Nota: Recomiendo usar disable() en lugar de delete()
        para mantener el historial.
        """
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.flush()
            return True
        return False
    
    # ============================================
    # EXISTENCE CHECKS
    # ============================================
    def exists_by_username(self, username: str) -> bool:
        """Verifica si existe un usuario con ese username."""
        return self.get_by_username(username) is not None
    
    def exists_by_email(self, email: str) -> bool:
        """Verifica si existe un usuario con ese email."""
        return self.get_by_email(email) is not None
    
    # ============================================
    # COUNTS
    # ============================================
    def count_all(self) -> int:
        """Cuenta todos los usuarios."""
        return self.db.exec(select(func.count()).select_from(User)).one()
    
    def count_active(self) -> int:
        """Cuenta solo usuarios activos."""
        return self.db.exec(
            select(func.count()).select_from(User).where(User.is_active == True)
        ).one()
    
    def count_admins(self) -> int:
        """Cuenta usuarios administradores."""
        return self.db.exec(
            select(func.count()).select_from(User).where(User.is_admin == True)
        ).one()
    
    def count_non_admins(self) -> int:
        """Cuenta usuarios no administradores."""
        return self.db.exec(
            select(func.count()).select_from(User).where(User.is_admin == False)
        ).one()