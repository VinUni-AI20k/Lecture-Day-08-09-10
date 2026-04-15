"""
Embedding provider factory for Chroma.

Priority:
1) OPENAI_EMBEDDING_MODEL -> OpenAI embeddings
2) EMBEDDING_MODEL -> local sentence-transformers
"""

from __future__ import annotations

import os
from typing import Any, Tuple


def build_embedding_function() -> Tuple[Any, str]:
    from chromadb.utils import embedding_functions

    openai_model = (os.environ.get("OPENAI_EMBEDDING_MODEL") or "").strip()
    if openai_model:
        api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required when OPENAI_EMBEDDING_MODEL is set.")
        kwargs = {
            "api_key": api_key,
            "model_name": openai_model,
        }
        api_base = (os.environ.get("OPENAI_API_BASE") or "").strip()
        if api_base:
            kwargs["api_base"] = api_base
        provider = f"openai:{openai_model}"
        return embedding_functions.OpenAIEmbeddingFunction(**kwargs), provider

    model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    provider = f"local:{model_name}"
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name), provider
