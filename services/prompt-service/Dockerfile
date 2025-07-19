FROM python:3.11-slim
WORKDIR /app
COPY app/ app/

# tiniest build — gcc only for regex back-end, then removed
RUN apt-get update && apt-get install -y gcc \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
      fastapi uvicorn pydantic \
      "ibm-watsonx-ai>=0.4.0"

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080"]
