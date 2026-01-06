import pytest
import warnings
from unittest.mock import MagicMock
import haystack
from django_haystack_opensearch.haystack import OpenSearchSearchBackend
from .conftest import MockField, MockIndex, MockUnifiedIndex


class TestSortingUnit:
    """Unit tests for sorting logic in the OpenSearch backend."""

    def setup_method(self):
        self.backend = OpenSearchSearchBackend(
            connection_alias="default", URL="http://localhost:9200", INDEX_NAME="test"
        )
        # Mock haystack.connections
        self.mock_connections = MagicMock()
        self.original_connections = haystack.connections
        haystack.connections = self.mock_connections

    def teardown_method(self):
        haystack.connections = self.original_connections

    def test_add_sort_to_kwargs_string_asc(self):
        """Test sorting with a simple string (ascending)."""
        kwargs = {}
        sort_by = ["title"]
        unified_index = MockUnifiedIndex({"model1": {"title": MockField("char")}})
        self.mock_connections["default"].get_unified_index.return_value = unified_index

        self.backend._add_sort_to_kwargs(kwargs, sort_by, None)

        assert kwargs["sort"] == [{"title.keyword": {"order": "asc"}}]

    def test_add_sort_to_kwargs_string_desc(self):
        """Test sorting with a string prefixed with '-' (descending)."""
        kwargs = {}
        sort_by = ["-title"]
        unified_index = MockUnifiedIndex({"model1": {"title": MockField("char")}})
        self.mock_connections["default"].get_unified_index.return_value = unified_index

        self.backend._add_sort_to_kwargs(kwargs, sort_by, None)

        assert kwargs["sort"] == [{"title.keyword": {"order": "desc"}}]

    def test_add_sort_to_kwargs_tuple(self):
        """Test sorting with a tuple (field, direction)."""
        kwargs = {}
        sort_by = [("title", "desc")]
        unified_index = MockUnifiedIndex({"model1": {"title": MockField("char")}})
        self.mock_connections["default"].get_unified_index.return_value = unified_index

        self.backend._add_sort_to_kwargs(kwargs, sort_by, None)

        assert kwargs["sort"] == [{"title.keyword": {"order": "desc"}}]

    def test_add_sort_to_kwargs_text_field(self):
        """Test that text fields automatically use .keyword suffix."""
        kwargs = {}
        sort_by = ["content"]
        unified_index = MockUnifiedIndex({"model1": {"content": MockField("text")}})
        self.mock_connections["default"].get_unified_index.return_value = unified_index

        self.backend._add_sort_to_kwargs(kwargs, sort_by, None)

        assert kwargs["sort"] == [{"content.keyword": {"order": "asc"}}]

    def test_add_sort_to_kwargs_faceted_field(self):
        """Test that faceted fields automatically use .keyword suffix if text."""
        kwargs = {}
        sort_by = ["category"]
        unified_index = MockUnifiedIndex(
            {"model1": {"category": MockField("char", faceted=True)}}
        )
        self.mock_connections["default"].get_unified_index.return_value = unified_index

        self.backend._add_sort_to_kwargs(kwargs, sort_by, None)

        assert kwargs["sort"] == [{"category.keyword": {"order": "asc"}}]

    def test_add_sort_to_kwargs_geo_distance(self):
        """Test geo-distance sorting."""
        kwargs = {}
        sort_by = ["distance"]
        distance_point = {"field": "location", "point": MagicMock(coords=(1.0, 2.0))}
        unified_index = MockUnifiedIndex({})
        self.mock_connections["default"].get_unified_index.return_value = unified_index

        self.backend._add_sort_to_kwargs(kwargs, sort_by, distance_point)

        assert kwargs["sort"] == [
            {"_geo_distance": {"location": [1.0, 2.0], "order": "asc", "unit": "km"}}
        ]

    def test_add_sort_to_kwargs_multiple_fields(self):
        """Test sorting with multiple fields of different types."""
        kwargs = {}
        sort_by = ["-priority", "title"]
        unified_index = MockUnifiedIndex(
            {"model1": {"priority": MockField("integer"), "title": MockField("text")}}
        )
        self.mock_connections["default"].get_unified_index.return_value = unified_index

        self.backend._add_sort_to_kwargs(kwargs, sort_by, None)

        assert kwargs["sort"] == [
            {"priority": {"order": "desc"}},
            {"title.keyword": {"order": "asc"}},
        ]
