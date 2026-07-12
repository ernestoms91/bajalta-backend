# app/core/email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formataddr
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from enum import Enum
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


# ==========================================
# ESQUEMAS
# ==========================================

class EmailPriority(str, Enum):
    """Prioridades de email."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EmailAttachment(BaseModel):
    """Archivo adjunto."""
    filename: str
    content: bytes
    mime_type: Optional[str] = None


class EmailMessage(BaseModel):
    """Mensaje de email."""
    to: List[EmailStr]
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    subject: str = Field(max_length=200)
    body: str
    html_body: Optional[str] = None
    attachments: Optional[List[EmailAttachment]] = None
    priority: EmailPriority = EmailPriority.NORMAL
    reply_to: Optional[EmailStr] = None


# ==========================================
# SERVICIO DE EMAIL
# ==========================================

class EmailService:
    """Servicio para enviar emails."""
    
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM
        self.from_name = getattr(settings, "EMAIL_FROM_NAME", None)
        self.use_tls = getattr(settings, "SMTP_USE_TLS", True)
        self.use_ssl = getattr(settings, "SMTP_USE_SSL", False)
    
    def _create_connection(self):
        """Crea una conexión SMTP."""
        if self.use_ssl:
            server = smtplib.SMTP_SSL(self.host, self.port)
        else:
            server = smtplib.SMTP(self.host, self.port)
        
        if self.use_tls and not self.use_ssl:
            server.starttls()
        
        if self.username and self.password:
            server.login(self.username, self.password)
        
        return server
    
    def _build_message(self, message: EmailMessage) -> MIMEMultipart:
        """Construye el mensaje MIME."""
        msg = MIMEMultipart("alternative")
        
        # Remitente
        if self.from_name:
            msg["From"] = formataddr((self.from_name, self.from_email))
        else:
            msg["From"] = self.from_email
        
        # Destinatarios
        msg["To"] = ", ".join(message.to)
        
        if message.cc:
            msg["Cc"] = ", ".join(message.cc)
        
        if message.reply_to:
            msg["Reply-To"] = message.reply_to
        
        # Asunto
        msg["Subject"] = message.subject
        
        # Prioridad
        if message.priority:
            priorities = {"low": "5", "normal": "3", "high": "1", "urgent": "1"}
            msg["X-Priority"] = priorities.get(message.priority.value, "3")
            if message.priority in ["high", "urgent"]:
                msg["Importance"] = "High"
        
        # Cuerpo
        if message.body:
            msg.attach(MIMEText(message.body, "plain"))
        
        if message.html_body:
            msg.attach(MIMEText(message.html_body, "html"))
        
        # Adjuntos
        if message.attachments:
            for attachment in message.attachments:
                part = MIMEApplication(attachment.content, Name=attachment.filename)
                part["Content-Disposition"] = f'attachment; filename="{attachment.filename}"'
                msg.attach(part)
        
        return msg
    
    def _get_all_recipients(self, message: EmailMessage) -> List[str]:
        """Obtiene todos los destinatarios."""
        recipients = list(message.to)
        if message.cc:
            recipients.extend(message.cc)
        if message.bcc:
            recipients.extend(message.bcc)
        return recipients
    
    def send(self, message: EmailMessage) -> bool:
        """Envía un email."""
        try:
            msg = self._build_message(message)
            recipients = self._get_all_recipients(message)
            
            with self._create_connection() as server:
                server.sendmail(self.from_email, recipients, msg.as_string())
            
            logger.info(f"Email enviado: {message.subject} (to: {len(message.to)})")
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar email: {e}")
            return False


# ==========================================
# PLANTILLAS HTML
# ==========================================

class EmailTemplates:
    """Plantillas de email predefinidas."""
    
    @staticmethod
    def simple(title: str, content: str, footer: str = "Mensaje automático.") -> str:
        """Plantilla simple."""
        return f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ padding: 20px; background: #f8fafc; border: 1px solid #e2e8f0; }}
                .footer {{ padding: 10px; text-align: center; font-size: 12px; color: #94a3b8; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header"><h2>{title}</h2></div>
                <div class="content">{content}</div>
                <div class="footer">{footer}</div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def alta_empleado(nombre: str, ci: str, departamento: str) -> str:
        """Plantilla para alta de empleado."""
        return EmailTemplates.simple(
            title="🔔 Nuevo Empleado Dado de Alta",
            content=f"""
            <p>Se ha dado de alta a un nuevo empleado.</p>
            <h3>Datos:</h3>
            <ul>
                <li><strong>Nombre:</strong> {nombre}</li>
                <li><strong>CI:</strong> {ci}</li>
                <li><strong>Departamento:</strong> {departamento}</li>
            </ul>
            <p>Crear cuentas y accesos necesarios.</p>
            """
        )
    
    @staticmethod
    def baja_empleado(nombre: str, ci: str, motivo: str, urgente: bool) -> str:
        """Plantilla para baja de empleado."""
        urgencia = "⚠️ " if urgente else ""
        return EmailTemplates.simple(
            title=f"{urgencia}Baja de Empleado - {nombre}",
            content=f"""
            <p>Se ha solicitado la baja de un empleado.</p>
            <h3>Datos:</h3>
            <ul>
                <li><strong>Nombre:</strong> {nombre}</li>
                <li><strong>CI:</strong> {ci}</li>
                <li><strong>Motivo:</strong> {motivo}</li>
                <li><strong>Urgente:</strong> {"⚠️ SÍ" if urgente else "NO"}</li>
            </ul>
            <p>Desactivar todos los accesos.</p>
            """
        )
    
    @staticmethod
    def baja_completada(nombre: str) -> str:
        """Plantilla para baja completada."""
        return EmailTemplates.simple(
            title="✅ Baja Completada",
            content=f"""
            <p>La baja del empleado <strong>{nombre}</strong> ha sido completada.</p>
            <p>Todos los accesos han sido desactivados.</p>
            """
        )