FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BLENDER_ROOT=/workspace

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY static ./static
RUN mkdir -p /workspace/data /workspace/renders

EXPOSE 8778
HEALTHCHECK --interval=20s --timeout=3s --start-period=8s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8778/api/health', timeout=2)"
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8778", "--proxy-headers"]
