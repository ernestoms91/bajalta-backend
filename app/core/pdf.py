# app/core/pdf.py
from fpdf import FPDF
from datetime import datetime
from io import BytesIO
from typing import List
from app.features.empleados.models import Empleado


class PDFService:
    """Servicio para generar PDFs con fpdf2."""
    
    def generar_reporte_empleados_activos(self, empleados: List[Empleado]) -> BytesIO:
        """
        Genera un reporte PDF de empleados activos.
        
        Args:
            empleados: Lista de empleados activos
        
        Returns:
            BytesIO: Archivo PDF en memoria
        """
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(left=10, top=10, right=10)
        pdf.add_page()
        
        # ========== TITULO ==========
        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(37, 99, 235)
        pdf.cell(0, 10, "Reporte de Empleados Activos", ln=True, align="C")
        
        # ========== FECHA ==========
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
        pdf.ln(10)
        
        # ========== ESTADISTICAS ==========
        total = len(empleados)
        
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, f"Total de empleados activos: {total}", ln=True, align="C")
        pdf.ln(8)
        
        # ========== TABLA DE EMPLEADOS ==========
        col_widths = [20, 65, 40, 55]
        headers = ["ID", "Nombre", "CI", "Departamento"]
        row_height = 8
        
        # Función para dibujar la cabecera de la tabla
        def draw_table_header():
            pdf.set_font("helvetica", "B", 9)
            pdf.set_fill_color(37, 99, 235)
            pdf.set_text_color(255, 255, 255)
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], row_height, header, border=1, align="C", fill=True)
            pdf.ln()
        
        # Dibujar cabecera inicial
        draw_table_header()
        
        # ========== DATOS ==========
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(0, 0, 0)
        
        for idx, empleado in enumerate(empleados):
            # Verificar si cabe en la página
            if pdf.get_y() + row_height + 10 > pdf.page_break_trigger:
                pdf.add_page()
                draw_table_header()
            
            # Alternar colores de fila
            if idx % 2 == 0:
                pdf.set_fill_color(248, 250, 252)
            else:
                pdf.set_fill_color(255, 255, 255)
            
            # ID
            pdf.cell(col_widths[0], row_height, str(empleado.id), border=1, align="C", fill=True)
            
            # Nombre
            pdf.cell(col_widths[1], row_height, f"{empleado.nombre} {empleado.apellidos}", border=1, align="C", fill=True)
            
            # CI
            pdf.cell(col_widths[2], row_height, empleado.ci, border=1, align="C", fill=True)
            
            # Departamento
            pdf.cell(col_widths[3], row_height, empleado.departamento, border=1, align="C", fill=True, ln=True)
        
        # ========== PIE DE PAGINA ==========
        # Solo añadir pie si hay contenido
        pdf.set_y(-20)
        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, f"Reporte generado automaticamente - Pagina {pdf.page_no()}", align="C")
        
        # ========== GENERAR PDF ==========
        pdf_bytes = bytes(pdf.output(dest='S'))
        buffer = BytesIO(pdf_bytes)
        buffer.seek(0)
        
        return buffer