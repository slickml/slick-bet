"""
File-based cache for Livescore API responses.

Enables fast backtesting and hyperparameter optimization by storing
API responses locally and reusing them instead of hitting the API.

Usage:
    # First run: fetch and cache (e.g. 12 weeks backtest)
    client = LivescoreClient(cache_dir="data/api_cache")
    # ... run backtest ...

    # Later runs: use cache only (no API calls)
    client = LivescoreClient(cache_dir="data/api_cache", cache_only=True)
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _serialize_params(params: dict[str, Any] | None) -> str:
    """Convert request params to a stable JSON string for cache keys."""
    if not params:
        return "{}"
    out: dict[str, Any] = {}
    for k, v in sorted(params.items()):
        if isinstance(v, datetime):
            out[k] = v.strftime("%Y-%m-%d")
        else:
            out[k] = v
    return json.dumps(out, sort_keys=True)


def cache_key(endpoint: str, params: dict[str, Any] | None) -> str:
    """Produce a short, filesystem-safe cache key from endpoint and params."""
    raw = f"{endpoint}|{_serialize_params(params)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class ApiCache:
    """
    File-based cache for API response bodies (JSON).

    Each request is stored as a single JSON file keyed by endpoint + params.
    """

    def __init__(self, cache_dir: str | Path) -> None:
        """
        Parameters
        ----------
        cache_dir : str or Path
            Directory to store cache files (created if missing).
        """
        self.root = Path(cache_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def get(self, endpoint: str, params: dict[str, Any] | None) -> dict | None:
        """
        Load cached response if present.

        Returns
        -------
        dict or None
            Cached JSON body or None if miss.
        """
        key = cache_key(endpoint, params)
        path = self.root / f"{key}.json"
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def set(
        self, endpoint: str, params: dict[str, Any] | None, data: dict
    ) -> None:
        """Store response in cache."""
        key = cache_key(endpoint, params)
        path = self.root / f"{key}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError:
            pass

    def clear(self) -> None:
        """Remove all cached files in the cache directory."""
        for f in self.root.glob("*.json"):
            try:
                f.unlink()
            except OSError:
                pass
