"""
tests/conftest.py
-----------------
Pytest configuration and environment initialization.

Sets critical environment variables before any tests or imports run:
- Prevents OpenMP / PyTorch / FAISS multi-threading runtime collision on macOS ARM64.
- Disables tokenizers fork parallelism to prevent EXC_BAD_ACCESS / SIGSEGV crashes.
"""

import os

# Prevent OpenMP and threading collision between PyTorch, HuggingFace Tokenizers, and FAISS
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

