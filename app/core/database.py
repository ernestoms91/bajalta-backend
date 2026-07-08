# app/core/database.py
from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy.exc import SQLAlchemyError  # Para manejar errores
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Engine lazy-loaded
_engine = None

def get_engine():
    """Obtener o crear el engine de forma lazy"""
    global _engine
    if _engine is None:
        try:
            _engine = create_engine(
                settings.DATABASE_URL,
                connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            logger.info("Engine de base de datos creado correctamente")
        except SQLAlchemyError as e:
            logger.error(f"Error al crear engine de BD: {e}")
            raise
    return _engine

def get_db():
    """Dependencia para obtener sesión de base de datos"""
    engine = get_engine()
    try:
        with Session(engine) as session:
            yield session
    except SQLAlchemyError as e:
        logger.error(f"Error en sesión de BD: {e}")
        raise  # Lo captura el handler de excepciones

def init_db():
    """Crear todas las tablas en la base de datos"""
    try:
        engine = get_engine()
        SQLModel.metadata.create_all(engine)
        logger.info("Tablas creadas correctamente")
    except SQLAlchemyError as e:
        logger.error(f"Error al crear tablas: {e}")
        raise