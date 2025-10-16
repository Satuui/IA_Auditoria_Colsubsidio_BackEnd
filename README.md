# IA_Audt_Colsubsidio — Backend (Python)

Descripción
- Microservicio para auditar PDFs de dispensación (detecta firma, cédula, medicamento, fecha, cantidad) usando extracción de texto y análisis visual.
- Implementación principal en [app/services/pdf_auditor.py](app/services/pdf_auditor.py) — función pública: [`audit_pdf`](app/services/pdf_auditor.py).

Estructura relevante
- [Dockerfile](Dockerfile)
- [requirements.txt](requirements.txt)
- App: [app/main.py](app/main.py), rutas: [app/api/v1/routes.py](app/api/v1/routes.py), configuración: [app/core/config.py](app/core/config.py)
- Servicio de auditoría: [app/services/pdf_auditor.py](app/services/pdf_auditor.py) (contiene [`audit_pdf`](app/services/pdf_auditor.py), [`_has_signature_visual`](app/services/pdf_auditor.py), y constantes como `POPPLER_PATH`)
- Tests: [tests/test_basic.py](tests/test_basic.py)
- Carpetas de datos: `datasets/`, `uploads/`

Requisitos del sistema
- Python 3.11
- Dependencias Python listadas en [requirements.txt](requirements.txt)
- Herramientas nativas para OCR/convertir PDF→imagen:
  - Poppler (binarios) — requerido por pdf2image
  - Tesseract OCR — requerido por pytesseract
  - OpenCV (ya en requirements), Pillow, numpy

Instalación paso a paso (Windows)
1. Clonar repo y abrir carpeta del proyecto.
2. Crear entorno virtual:
   ```sh
   python -m venv .venv
   .venv\Scripts\activate

# 3.Instalar dependencias Python:
pip install --upgrade pip
pip install -r requirements.txt

# 4.Instalar Poppler (Windows):
Descargar Poppler para Windows (ej. release precompilado). Extrae la carpeta y coloca la ruta a los binarios. Ejemplo recomendado:
Extraer en: C:\poppler\Library\bin
Verifica que exista pdftoppm.exe en C:\poppler\Library\bin.
En app/services/pdf_auditor.py se usa la constante POPPLER_PATH — verifica que apunte a C:\poppler\Library\bin o ajusta la ruta.

# 5.Instalar Tesseract OCR (Windows):
Descargar e instalar desde el instalador oficial (por ejemplo tesseract-ocr-w64-setup.exe).
Ruta típica: C:\Program Files\Tesseract-OCR\tesseract.exe
En Windows puedes:
Añadir C:\Program Files\Tesseract-OCR al PATH (recomendado), o
Descomentar y ajustar la línea en app/services/pdf_auditor.py:

# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

6.Probar conversión y OCR manualmente (opcional)
from app.services.pdf_auditor import audit_pdf
print(audit_pdf("uploads/mi_documento.pdf"))

# Instalación paso a paso (Linux / Debian/Ubuntu)
sudo apt update
sudo apt install -y build-essential poppler-utils libpoppler-cpp-dev \
     tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng

# 2. Entorno Python
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Ajustes:
Para pdf2image en Linux no suele ser necesario setear POPPLER_PATH si pdftoppm está en PATH.
Si fue necesario, en app/services/pdf_auditor.py actualiza POPPLER_PATH o exporta

export POPPLER_PATH=/usr/bin

### Uso local (sin Docker)
# desde la raíz
1.Levantar la app (uvicorn):
python -m uvicorn app.main:app

El comando en Dockerfile usa lo mismo: python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}.
Endpoint y pruebas:
Revisa routes.py para ver rutas expuestas.
Subir PDFs a uploads y llamar al endpoint de auditoría (según la ruta implementada) o invocar audit_pdf directamente.

## Uso con Docker
docker build -t pdf-auditor:local .

## Errores comunes y soluciones
"pdf2image can't find pdftoppm": asegúrate que Poppler esté instalado y POPPLER_PATH correctamente puesto o que pdftoppm esté en PATH.
"pytesseract.TesseractNotFoundError": instalar Tesseract y/o configurar pytesseract.pytesseract.tesseract_cmd.
Errores OpenCV (import cv2): verificar que opencv-python está en requirements.txt e instalado en el entorno.
En Docker: si faltan binarios del sistema, extiende el Dockerfile para instalarlos.

# Soporte y seguimiento
Para revisar el flujo, encuentra la lógica de auditoría en pdf_auditor.py (funciones clave: _has_signature_visual, _find_firma, audit_pdf).