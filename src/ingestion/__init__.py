"""Ingestion package exports."""

from ingestion.document_manager import CollectionStats, DeleteResult, DocumentDetail, DocumentInfo, DocumentManager
from ingestion.pipeline import IngestionPipeline, IngestionResult

__all__ = [
    "CollectionStats",
    "DeleteResult",
    "DocumentDetail",
    "DocumentInfo",
    "DocumentManager",
    "IngestionPipeline",
    "IngestionResult",
]
