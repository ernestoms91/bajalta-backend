# Bajalta - Sistema de Altas y Bajas de Personal

Sistema de gestión de altas y bajas del personal con autenticación JWT.

## 🚀 Instalación y Configuración

### 1️⃣ Clonar el repositorio

```bash
git clone https://github.com/ernestoms91/bajalta-backend.git
cd bajalta


2️⃣ Crear y activar entorno virtual
bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

3️⃣ Instalar dependencias
bash
pip install -r requirements.txt


4️⃣ Configurar variables de entorno
Renombrar el archivo .env.example a .env en la raíz del proyecto y llenar los campos.

bash
cp .env.example .env


5️⃣ Crear usuario administrador
bash
python scripts/create_admin.py