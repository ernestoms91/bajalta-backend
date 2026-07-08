# main.py
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging, get_logger
from app.features.auth.endpoints import auth_router, user_router

# ==========================================
# CONFIGURAR LOGGING AL INICIO
# ==========================================
setup_logging()
logger = get_logger(__name__)


# ==========================================
# LIFESPAN (startup / shutdown)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(">>> Iniciando servidor...")
    logger.info(f"Proyecto: {settings.PROJECT_NAME}")
    logger.info(f"Base de datos: {settings.DATABASE_URL}")

    # Inicializar base de datos (crear tablas)
    init_db()
    logger.info("Base de datos inicializada correctamente")

    yield  # La aplicación se ejecuta aquí

    # Shutdown
    logger.info("<<< Cerrando servidor...")


# ==========================================
# CREAR APLICACIÓN FASTAPI
# ==========================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Sistema para gestionar altas y bajas de personal",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True
    }
)


# ==========================================
# PAGINACIÓN (para listados grandes)
# ==========================================
add_pagination(app)


# ==========================================
# CORS (permitir peticiones del frontend)
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# REGISTRAR MANEJADORES DE ERRORES
# ==========================================
register_exception_handlers(app)


# ==========================================
# REGISTRAR ROUTERS DE FEATURES
# ==========================================
app.include_router(auth_router)
app.include_router(user_router)
# app.include_router(empleados_router, prefix="/api/v1/empleados", tags=["Empleados"])
# app.include_router(solicitudes_router, prefix="/api/v1/solicitudes", tags=["Solicitudes"])
# app.include_router(usuarios_router, prefix="/api/v1/usuarios", tags=["Usuarios"])


# ==========================================
# RUTAS BÁSICAS
# ==========================================

@app.get("/", tags=["Root"])
def root():
    return {
        "message": f"Bienvenido a {settings.PROJECT_NAME}",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs"
    }

# ==========================================
# LOG DE CONFIRMACIÓN
# ==========================================
logger.info(f"API {settings.PROJECT_NAME} configurada correctamente")
logger.info(f"Nivel de logging: {settings.LOG_LEVEL}")
logger.info(f"Documentación: http://localhost:8000/docs")
