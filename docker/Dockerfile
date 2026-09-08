# 훈련 전용 격리 컨테이너. 호스트에는 NVIDIA 드라이버 + Docker + nvidia-container-toolkit 만 있으면 된다.
FROM nvcr.io/nvidia/pytorch:25.06-py3

ARG UID=1001
RUN useradd -m -u ${UID} -s /bin/bash agent \
 && apt-get update && apt-get install -y --no-install-recommends git tmux \
 && rm -rf /var/lib/apt/lists/*

# 학습 스택. CUDA/cuDNN/torch/flash-attn 은 베이스 이미지에 이미 맞춰져 있다.
RUN pip install --no-cache-dir ms-swift qwen-vl-utils

USER agent
WORKDIR /work
ENV PATH=/home/agent/.local/bin:$PATH \
    HF_HOME=/home/agent/.cache/huggingface

# Claude Code 네이티브 설치 (Node 불필요)
RUN curl -fsSL https://claude.ai/install.sh | bash

CMD ["sleep", "infinity"]
