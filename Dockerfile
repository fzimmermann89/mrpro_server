# MRpro Open Recon Server
ARG CUDA_VERSION=11.8.0
ARG UBUNTU_VERSION=22.04
FROM nvidia/cuda:${CUDA_VERSION}-base-ubuntu${UBUNTU_VERSION}

RUN apt-get update && apt-get install --no-install-recommends -y \
        python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ARG TORCH_VERSION=2.5
ARG TORCH_VARIANT=cpu
RUN python3 -m pip --no-cache-dir install \
        --index-url https://download.pytorch.org/whl/${TORCH_VARIANT}\
        torch==${TORCH_VERSION}
       
    

# This will invalidate cache every time a new version of MRpro is released
ADD https://pypi.org/pypi/mrpro/json /tmp/mrpro.json
RUN python3 -m pip --no-cache-dir install \
        mrpro

WORKDIR /home
COPY *.py /home/mrpro_server/

ARG VERSION
ARG CONFIG
LABEL org.opencontainers.image.description="MRpro Open Recon"
LABEL org.opencontainers.image.url="https://github.com/PTB-MR/mrpro"
LABEL org.opencontainers.image.version=${VERSION}
LABEL org.opencontainers.image.authors="PTB"
LABEL com.siemens-healthineers.magneticresonance.OpenRecon.metadata:1.1.0=${CONFIG}

CMD ["python3", "/home/mrpro_server/server.py"]






