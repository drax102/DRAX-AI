"""
backend/core/app_indexer/__init__.py
"""

from backend.core.app_indexer.scanner import scan_and_rebuild_index, get_app_index

__all__ = ["scan_and_rebuild_index", "get_app_index"]
