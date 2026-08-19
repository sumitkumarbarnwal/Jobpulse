"""
Tests for schema validation in source adapters.
"""
from __future__ import annotations

import pytest

from app.sources.arbeitnow import ArbeitnowAdapter
from app.sources.base import SourceSchemaError


class TestSchemaValidation:
    def test_rejects_missing_data_key(self):
        adapter = ArbeitnowAdapter()
        with pytest.raises(SourceSchemaError, match="data"):
            adapter._parse_response(_MockResponse({"unexpected": "format"}))

    def test_rejects_non_list_data(self):
        adapter = ArbeitnowAdapter()
        with pytest.raises(SourceSchemaError, match="list"):
            adapter._parse_response(_MockResponse({"data": "not a list"}))

    def test_rejects_invalid_json(self):
        adapter = ArbeitnowAdapter()
        with pytest.raises(SourceSchemaError, match="JSON"):
            adapter._parse_response(_BadJsonResponse())

    def test_accepts_empty_data_list(self):
        adapter = ArbeitnowAdapter()
        result = adapter._parse_response(_MockResponse({"data": [], "links": {}}))
        assert result == []

    def test_accepts_valid_response(self, arbeitnow_200_response):
        adapter = ArbeitnowAdapter()
        result = adapter._parse_response(_MockResponse(arbeitnow_200_response))
        assert len(result) == 2


class _MockResponse:
    """Minimal mock of httpx.Response for testing _parse_response."""

    def __init__(self, data: dict):
        self._data = data

    def json(self):
        return self._data


class _BadJsonResponse:
    def json(self):
        import json
        raise json.JSONDecodeError("bad json", "", 0)
