"""Download BGE-large-zh embedding model to local models/ directory.

This script downloads the BAAI/bge-large-zh model from HuggingFace
and saves it to models/BAAI/bge-large-zh/ for offline usage.
"""

import os
import sys

# 默认走国内镜像站，加速 HuggingFace 模型下载（可用环境变量覆盖）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

MODEL_NAME = "BAAI/bge-large-zh"
TARGET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "BAAI", "bge-large-zh")

def download_model():
    os.makedirs(TARGET_DIR, exist_ok=True)

    print(f"Downloading {MODEL_NAME} to {TARGET_DIR}...")
    print("This may take a few minutes (model is ~1.3 GB)...")

    try:
        from sentence_transformers import SentenceTransformer

        print("Loading model via SentenceTransformer (this downloads to local cache first)...")
        model = SentenceTransformer(MODEL_NAME)
        print(f"Model loaded. Dimension: {model.get_sentence_embedding_dimension()}")

        # Save to local directory
        print(f"Saving model to {TARGET_DIR}...")
        model.save(TARGET_DIR)
        print(f"Model saved successfully to {TARGET_DIR}")

        # Verify
        print("Verifying saved model...")
        model2 = SentenceTransformer(TARGET_DIR)
        test_vec = model2.encode("测试文本", normalize_embeddings=True)
        print(f"Verification OK. Vector dimension: {len(test_vec)}")

        # List files
        total_size = 0
        for root, dirs, files in os.walk(TARGET_DIR):
            for f in files:
                fp = os.path.join(root, f)
                total_size += os.path.getsize(fp)
        print(f"Total size: {total_size / (1024**3):.2f} GB")
        print("DONE!")

    except ImportError as e:
        print(f"ERROR: Missing package: {e}")
        print("Install with: pip install sentence-transformers")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    download_model()
