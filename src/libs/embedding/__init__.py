"""Embedding abstractions and provider clients."""

from libs.embedding.azure_embedding import AzureEmbedding
from libs.embedding.base_embedding import BaseEmbedding
from libs.embedding.embedding_factory import EmbeddingFactory
from libs.embedding.ollama_embedding import OllamaEmbedding
from libs.embedding.openai_embedding import OpenAIEmbedding

__all__ = [
    "BaseEmbedding",
    "EmbeddingFactory",
    "OpenAIEmbedding",
    "AzureEmbedding",
    "OllamaEmbedding",
]
