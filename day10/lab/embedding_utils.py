"""Shared embedding function — OpenAI-compatible API via ShopAIKey."""

from __future__ import annotations

import os

from chromadb import Documents, EmbeddingFunction, Embeddings
from openai import OpenAI


class OpenAICompatibleEmbeddingFunction(EmbeddingFunction):
    """ChromaDB-compatible wrapper around any OpenAI-compatible embedding endpoint."""

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self._model = model_name or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self._client = OpenAI(
            api_key=api_key or os.getenv("SHOPAIKEY_API_KEY"),
            base_url=base_url or os.getenv("SHOPAIKEY_BASE_URL", "https://api.shopaikey.com/v1"),
            default_headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            },
        )

    def __call__(self, input: Documents) -> Embeddings:
        resp = self._client.embeddings.create(input=input, model=self._model)
        return [item.embedding for item in resp.data]


def get_embedding_function(model_name: str | None = None) -> OpenAICompatibleEmbeddingFunction:
    return OpenAICompatibleEmbeddingFunction(model_name=model_name)
