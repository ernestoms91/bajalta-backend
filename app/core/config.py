# app/core/config.py
from pydantic import Field, field_validator, EmailStr
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
    # EMAIL (SMTP)
    # ==========================================
    SMTP_HOST: str = Field(
        default="smtp.gmail.com",
        env="SMTP_HOST",
        description="Servidor SMTP"
    )
    SMTP_PORT: int = Field(
        default=587,
        env="SMTP_PORT",
        ge=1,
        le=65535,
        description="Puerto SMTP"
    )
    SMTP_USER: str = Field(
        ...,  # Obligatorio en .env
        env="SMTP_USER",
        description="Usuario SMTP"
    )
    SMTP_PASSWORD: str = Field(
        ...,  # Obligatorio en .env
        env="SMTP_PASSWORD",
        min_length=1,
        description="Contraseña SMTP"
    )
    EMAIL_FROM: EmailStr = Field(
        ...,  # Obligatorio en .env
        env="EMAIL_FROM",
        description="Email del remitente"
    )
    EMAIL_FROM_NAME: str = Field(
        default="Bajalta",
        env="EMAIL_FROM_NAME",
        max_length=100,
        description="Nombre del remitente"
    )
    SMTP_USE_TLS: bool = Field(
        default=True,
        env="SMTP_USE_TLS",
        description="Usar TLS"
    )
    SMTP_USE_SSL: bool = Field(
        default=False,
        env="SMTP_USE_SSL",
        description="Usar SSL"
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
    
    @field_validator("SMTP_PORT")
    @classmethod
    def validate_smtp_port(cls, v: int) -> int:
        """Valida que el puerto SMTP sea válido"""
        valid_ports = [25, 465, 587, 2525]
        if v not in valid_ports:
            raise ValueError(
                f"Puerto SMTP no válido. Usar: {', '.join(map(str, valid_ports))}"
            )
        return v
    
    @field_validator("SMTP_USE_TLS", "SMTP_USE_SSL")
    @classmethod
    def validate_tls_ssl(cls, v: bool, info) -> bool:
        """Valida que no se usen TLS y SSL simultáneamente"""
        if info.field_name == "SMTP_USE_TLS":
            return v
        # Si es SMTP_USE_SSL, verificar que no esté activo junto con TLS
        if v and info.data.get("SMTP_USE_TLS", False):
            raise ValueError("No se puede usar TLS y SSL simultáneamente")
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
    logger.info(f" Email: {settings.EMAIL_FROM} ({settings.EMAIL_FROM_NAME})")
    logger.info(f" SMTP: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
    
except Exception as e:
    logging.critical(f" Error de configuración: {e}")
    raise  # Lanza la excepción para que el handler la capture