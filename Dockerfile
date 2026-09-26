FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements-retrieval.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# The default image stays lightweight. The optional overlay enables local models.
ARG LOCAL_RETRIEVAL=0
RUN if [ "$LOCAL_RETRIEVAL" = "1" ]; then \
      pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
      pip install --no-cache-dir -r requirements-retrieval.txt; \
    fi

COPY . .

# Dentro del contenedor hay que escuchar en todas las interfaces para que el
# proxy pueda alcanzarlo; el aislamiento lo da la red de Docker, no el bind.
ENV RAG_BIND=0.0.0.0 RAG_PORT=8767 RAG_READONLY=1

EXPOSE 8767

# Usuario sin privilegios: si algún día se habilita la subida, no escribe como root.
RUN mkdir -p /app/data/models /app/data/retrieval-cache && \
    useradd -m -u 10001 ragtox && chown -R ragtox:ragtox /app
USER ragtox

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8767/health',timeout=3)"

CMD ["python", "app.py"]
