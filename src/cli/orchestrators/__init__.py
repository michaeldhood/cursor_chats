"""
CLI orchestrators for complex workflows.

Orchestrators coordinate multiple services to implement complex operations.
They are pure Python (no Click dependencies) and can be tested independently
or called from other interfaces (web UI, scripts, etc.).
"""
# Phase 4: Ingestion orchestrator
from .ingestion import IngestionOrchestrator

__all__ = ['IngestionOrchestrator']
