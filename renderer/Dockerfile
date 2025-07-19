# Using an NVIDIA CUDA base image is the standard for GPU workloads on Kubernetes.
# It includes the necessary libraries to interface with the GPU drivers on the host node.
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

WORKDIR /app

COPY render.py .

# Install Python and the boto3 library for IBM COS communication.
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    pip3 install boto3 && \
    rm -rf /var/lib/apt/lists/*

# Set the entrypoint to run the Python rendering script.
ENTRYPOINT ["python3", "render.py"]
