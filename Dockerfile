# Imagen base
FROM python:3.11-slim

# Evitar prompts y logs buferizados
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instalar dependencias del sistema mínimas (para pillow, tesseract opcional, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements primero para aprovechar cache
COPY requirements.txt /app/requirements.txt

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . /app

# Render asigna el puerto en la variable de entorno PORT
# No lo fijes; úsalo en el CMD.
# Exponer es opcional en Render, pero no hace daño
EXPOSE 8000

# Comando de arranque (usa el PORT que da Render)
# Ajusta 'app.main:app' si tu módulo/variable difieren.
CMD ["bash", "-lc", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
