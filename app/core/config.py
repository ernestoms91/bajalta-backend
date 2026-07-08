# app/core/config.py
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from pathlib import Path
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # ==========================================
    # BASE DE DATOS
    # ==========================================
    DATABASE_URL: str = Field(
        default="sqlite:///./bajalta.db",
        env="DATABASE_URL",
        description="URL de conexión a la base de datos"
    )
    
    # ==========================================
    # SEGURIDAD Y JWT
    # ==========================================
    JWT_SECRET: str = Field(
        ...,  # Obligatorio en .env
        env="JWT_SECRET",
        min_length=32,
        description="Clave secreta para firmar tokens JWT (mínimo 32 caracteres)"
    )
    JWT_ALG: str = Field(
        default="HS256",
        env="JWT_ALG",
        description="Algoritmo para JWT"
    )
    JWT_EXPIRES_MIN: int = Field(
        default=30,
        env="JWT_EXPIRES_MIN",
        ge=1,
        description="Tiempo de expiración del token en minutos"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        env="REFRESH_TOKEN_EXPIRE_DAYS",
        ge=1,
        description="Tiempo de expiración del refresh token en días"
    )
    
    # ==========================================
    # API Y PROYECTO
    # ==========================================
    PROJECT_NAME: str = Field(
        default="Sistema de Altas y Bajas de Personal",
        env="PROJECT_NAME",
        description="Nombre del proyecto"
    )
    
    # ==========================================
    # LOGGING
    # ==========================================
    LOG_LEVEL: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # ==========================================
    # VALIDACIONES PERSONALIZADAS
    # ==========================================
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Valida que el nivel de log sea válido"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL debe ser uno de: {valid_levels}")
        return v.upper()
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Valida que la URL de BD sea soportada"""
        supported = ["sqlite", "postgresql", "mysql", "mariadb"]
        if not any(v.startswith(f"{db}://") for db in supported):
            raise ValueError(
                f"Database no soportada. Usar: {', '.join(supported)}"
            )
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# ==========================================
# INSTANCIAR CONFIGURACIÓN
# ==========================================
try:
    settings = Settings()
    logger.info(f" Configuración cargada para: {settings.PROJECT_NAME}")
    logger.info(f" Base de datos: {settings.DATABASE_URL}")
    logger.info(f" JWT expira en: {settings.JWT_EXPIRES_MIN} minutos")
    logger.info(f" Nivel de logging: {settings.LOG_LEVEL}")
    
except Exception as e:
    logging.critical(f" Error de configuración: {e}")
    raise  # Lanza la excepción para que el handler la capture