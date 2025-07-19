# avatar-service/Dockerfile
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS base
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y git ffmpeg python3.11 python3.11-venv && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app/ app/

RUN python3.11 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip wheel && \
    /opt/venv/bin/pip install torch==2.3.0+cu124 torchvision \
      --extra-index-url https://download.pytorch.org/whl/cu124 && \
    /opt/venv/bin/pip install fastapi uvicorn[standard] opencv-python-headless \
        requests pydantic

ENV PATH="/opt/venv/bin:$PATH"
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
