#!/bin/sh
set -e

# 首次启动：本地 embedding 模型缺失时自动下载（走 hf-mirror 镜像站）
# 用 config.json 作为「模型已完整落地」的判定标记（sentence-transformers 保存时必然存在）
MODEL_DIR="/app/models/BAAI/bge-large-zh"
if [ ! -f "$MODEL_DIR/config.json" ]; then
  echo "[entrypoint] Embedding model missing, downloading (~1.3GB) ..."
  python scripts/download_embedding_model.py \
    || echo "[entrypoint] download failed, RAG unavailable (app will still start)"
else
  echo "[entrypoint] Embedding model found, skip download"
fi

exec python main.py
