FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt requirements-optimizer.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-optimizer.txt

# Copiar código fonte
COPY src/ ./src/

# Expor porta
EXPOSE 8000

# Comando para iniciar a aplicação
CMD ["uvicorn", "src.prompt_optimizer.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

