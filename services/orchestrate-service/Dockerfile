FROM python:3.11-slim
WORKDIR /app
COPY job.py .
RUN pip install --no-cache-dir kafka-python requests
ENTRYPOINT ["python", "job.py"]
