"""The shared ingestion pipeline — the one piece of orchestration logic
every agent goes through, so no source-specific subclass reimplements
retry/rate-limiting/logging/error-isolation around its own
discover/extract/normalize/validate methods.
"""

from app.ingestion.pipeline.runner import IngestionPipeline

__all__ = ["IngestionPipeline"]
