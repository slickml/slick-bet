"""Tests for the file-based API cache."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from assertpy import assert_that

from slickbet.cache import ApiCache, _serialize_params, cache_key


class TestSerializeParams:
    """Tests for _serialize_params."""

    def test_none_params(self) -> None:
        assert_that(_serialize_params(None)).is_equal_to("{}")

    def test_empty_params(self) -> None:
        assert_that(_serialize_params({})).is_equal_to("{}")

    def test_datetime_params(self) -> None:
        result = _serialize_params({"date": datetime(2025, 3, 15), "page": 1})
        assert_that(result).contains("2025-03-15")
        assert_that(result).contains('"page": 1')

    def test_sorted_keys(self) -> None:
        a = _serialize_params({"z": 1, "a": 2})
        b = _serialize_params({"a": 2, "z": 1})
        assert_that(a).is_equal_to(b)


class TestCacheKey:
    """Tests for cache_key."""

    def test_deterministic(self) -> None:
        k1 = cache_key("fixtures/matches.json", {"date": "2025-01-01"})
        k2 = cache_key("fixtures/matches.json", {"date": "2025-01-01"})
        assert_that(k1).is_equal_to(k2)

    def test_different_endpoints(self) -> None:
        k1 = cache_key("a.json", {"x": 1})
        k2 = cache_key("b.json", {"x": 1})
        assert_that(k1).is_not_equal_to(k2)

    def test_length(self) -> None:
        key = cache_key("endpoint", None)
        assert_that(len(key)).is_equal_to(32)


class TestApiCache:
    """Tests for ApiCache class."""

    def test_set_and_get(self, tmp_cache_dir: Path) -> None:
        cache = ApiCache(tmp_cache_dir)
        data = {"success": True, "data": {"fixtures": []}}
        cache.set("fixtures/matches.json", {"date": "2025-01-01"}, data)
        loaded = cache.get("fixtures/matches.json", {"date": "2025-01-01"})
        assert_that(loaded).is_equal_to(data)

    def test_get_miss(self, tmp_cache_dir: Path) -> None:
        cache = ApiCache(tmp_cache_dir)
        assert_that(cache.get("missing.json", None)).is_none()

    def test_clear(self, tmp_cache_dir: Path) -> None:
        cache = ApiCache(tmp_cache_dir)
        cache.set("a.json", {"p": 1}, {"ok": True})
        cache.set("b.json", {"p": 2}, {"ok": True})
        cache.clear()
        assert_that(list(tmp_cache_dir.glob("*.json"))).is_empty()

    def test_corrupt_json(self, tmp_cache_dir: Path) -> None:
        cache = ApiCache(tmp_cache_dir)
        key = cache_key("bad.json", {"x": 1})
        bad_file = tmp_cache_dir / f"{key}.json"
        bad_file.write_text("{not valid json", encoding="utf-8")
        assert_that(cache.get("bad.json", {"x": 1})).is_none()

    def test_get_oserror(self, tmp_cache_dir: Path) -> None:
        cache = ApiCache(tmp_cache_dir)
        key = cache_key("err.json", None)
        path = tmp_cache_dir / f"{key}.json"
        path.write_text('{"ok": true}', encoding="utf-8")
        with patch("builtins.open", side_effect=OSError("read fail")):
            assert_that(cache.get("err.json", None)).is_none()

    def test_set_oserror(self, tmp_cache_dir: Path) -> None:
        cache = ApiCache(tmp_cache_dir)
        with patch("builtins.open", side_effect=OSError("write fail")):
            cache.set("fail.json", None, {"data": 1})  # should not raise

    def test_clear_oserror(self, tmp_cache_dir: Path) -> None:
        cache = ApiCache(tmp_cache_dir)
        cache.set("a.json", None, {"ok": True})
        with patch.object(Path, "unlink", side_effect=OSError("unlink fail")):
            cache.clear()  # should not raise

    def test_creates_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested" / "cache"
        cache = ApiCache(nested)
        assert_that(nested.exists()).is_true()
        assert_that(cache.root).is_equal_to(nested)
