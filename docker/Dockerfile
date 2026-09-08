# 훈련 전용 격리 컨테이너. 호스트에는 NVIDIA 드라이버 + Docker + nvidia-container-toolkit 만 있으면 된다.
# 베이스 CUDA 12.1: 호스트 드라이버 535(CUDA 12.2) 와 호환. NGC 최신(12.9)은 GeForce+535 에서 안 뜬다.
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

ARG UID=1001
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN useradd -m -u ${UID} -s /bin/bash agent \
 && apt-get update && apt-get install -y --no-install-recommends git tmux curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# 검출기 트랙 스택 + 서체 스왑 재렌더용 chromium. VLM 트랙(ms-swift)은 필요해지면 추가.
RUN pip install --no-cache-dir ultralytics huggingface_hub playwright \
 && playwright install --with-deps chromium && chmod -R a+rX /ms-playwright

USER agent
WORKDIR /work
ENV PATH=/home/agent/.local/bin:$PATH \
    HF_HOME=/home/agent/.cache/huggingface

# Claude Code 네이티브 설치 (Node 불필요)
RUN curl -fsSL https://claude.ai/install.sh | bash

CMD ["sleep", "infinity"]
