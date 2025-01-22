# MRpro Open Recon Server
ARG CUDA_VERSION=11.8.0
ARG UBUNTU_VERSION=22.04
FROM nvidia/cuda:${CUDA_VERSION}-base-ubuntu${UBUNTU_VERSION}

# Python
RUN apt-get update && apt-get install --no-install-recommends -y \
        python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Torch
ARG TORCH_VERSION=2.5
ARG TORCH_VARIANT=cpu
RUN python3 -m pip --no-cache-dir install \
        --index-url https://download.pytorch.org/whl/${TORCH_VARIANT}\
        torch==${TORCH_VERSION}
       
# MRpro    
ARG MRPRO_VERSION=0.250107
RUN python3 -m pip --no-cache-dir install \
        mrpro==${MRPRO_VERSION}

# MRpro Server
WORKDIR /home
COPY *.py /home/mrpro_server/
CMD ["python3", "/home/mrpro_server/server.py"]

# Metadata
ARG VERSION
ARG CONFIG
LABEL maintainer="PTB"
LABEL org.opencontainers.image.ref.name="mrpro_openrecon"
LABEL org.opencontainers.image.description="MRpro Open Recon"
LABEL org.opencontainers.image.url="https://github.com/PTB-MR/mrpro"
LABEL org.opencontainers.image.authors="PTB"
LABEL org.opencontainers.image.version=${VERSION}
LABEL com.siemens-healthineers.magneticresonance.openrecon.metadata:1.1.0=${CONFIG}







