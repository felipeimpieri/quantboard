FROM python:3.11-slim

# Crear directorio de trabajo
WORKDIR /app

# Instalar dependencias de sistema mínimas (por si algún paquete las necesita)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (mejor cache de Docker)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Puerto donde corre Streamlit
EXPOSE 8501

# Comando por defecto
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
