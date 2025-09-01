# Use Python 3.11.10 slim base
FROM python:3.11.10-slim

# Set env
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV WORKDIR=/workspace/ComfyUI

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git wget curl unzip libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create workspace
WORKDIR /workspace

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git

# Install ComfyUI Python deps
WORKDIR ${WORKDIR}
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install runpod

# -------------------------
# Install custom nodes (corrected repos)
# -------------------------
WORKDIR ${WORKDIR}/custom_nodes

RUN git clone https://github.com/kijai/comfyui-kjnodes.git \
 && git clone https://github.com/aria1th/ComfyUI-LogicUtils.git \
 && git clone https://github.com/lldacing/ComfyUI_Patches_ll.git \
 && git clone https://github.com/WASasquatch/was-node-suite-comfyui.git \
 && git clone https://github.com/kaibioinfo/ComfyUI_AdvancedRefluxControl.git \
 && git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack.git \
 && git clone https://github.com/theUpsider/ComfyUI-Logic.git \
 && git clone https://github.com/cubiq/ComfyUI_essentials.git

# Auto-install dependencies for all nodes
RUN for d in ${WORKDIR}/custom_nodes/*; do \
        if [ -f "$d/requirements.txt" ]; then pip install -r $d/requirements.txt; fi; \
        if [ -f "$d/requirements.in" ]; then pip install -r $d/requirements.in; fi; \
    done

# -------------------------
# Download Models
# -------------------------
WORKDIR ${WORKDIR}/models

# diffusion_models
RUN mkdir -p diffusion_models && \
    wget -O diffusion_models/fluxFillFP8_v10.safetensors \
    https://huggingface.co/jackzheng/flux-fill-FP8/resolve/main/fluxFillFP8_v10.safetensors

# vae
RUN mkdir -p vae && \
    wget -O vae/ae.safetensors \
    https://huggingface.co/ffxvs/vae-flux/resolve/main/ae.safetensors

# clip
RUN mkdir -p clip && \
    wget -O clip/clip_l.safetensors \
    https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors && \
    wget -O clip/t5xxl_fp16.safetensors \
    https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors

# style_models
RUN mkdir -p style_models && \
    wget -O style_models/redux.safetensors \
    https://huggingface.co/second-state/FLUX.1-Redux-dev-GGUF/resolve/c7e36ea59a409eaa553b9744b53aa350099d5d51/flux1-redux-dev.safetensors

# clip_vision
RUN mkdir -p clip_vision && \
    wget -O clip_vision/sigclip_vision_patch14_384.safetensors \
    https://huggingface.co/f5aiteam/CLIP_VISION/resolve/ab3e0511a3c17c6a601444defc83bbf017a4f3dd/sigclip_vision_patch14_384.safetensors

# -------------------------

# Copy handler script
WORKDIR ${WORKDIR}
COPY worker.py ${WORKDIR}/worker.py
COPY handler.py ${WORKDIR}/handler.py
COPY baseGraphTemplate.json /workspace/baseGraphTemplate.json

# Default command
CMD ["python", "handler.py"]
