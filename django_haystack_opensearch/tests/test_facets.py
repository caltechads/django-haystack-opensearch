import pytest
from unittest.mock import MagicMock
import haystack
from django_haystack_opensearch.haystack import OpenSearchSearchBackend
from .conftest import MockField, MockIndex, MockUnifiedIndex


class TestFacetsUnit:
    """Unit tests for faceting logic in the OpenSearch backend."""

    def setup_method(self):
        self.backend = OpenSearchSearchBackend(
            connection_alias="default", URL="http://localhost:9200", INDEX_NAME="test"
        )
        self.mock_connections = MagicMock()
        self.original_connections = haystack.connections
        haystack.connections = self.mock_connections

    def teardown_method(self):
        haystack.connections = self.original_connections

    def test_add_facets_to_kwargs_correct_method_call(self):
        """Test that _add_facets_to_kwargs calls self.get_facet_fieldname."""
        kwargs = {}
        facets = {"category": {}}

        # We want to verify that self.get_facet_fieldname is called
        self.backend.get_facet_fieldname = MagicMock(return_value="category.keyword")

        self.backend._add_facets_to_kwargs(kwargs, facets)

        assert "aggs" in kwargs
        assert "category" in kwargs["aggs"]
        assert kwargs["aggs"]["category"]["terms"]["field"] == "category.keyword"
        self.backend.get_facet_fieldname.assert_called_once_with("category")

    def test_get_facet_fieldname_text(self):
        """Test that get_facet_fieldname returns .keyword for text fields."""
        unified_index = MockUnifiedIndex({"model1": {"title": MockField("text")}})
        self.mock_connections["default"].get_unified_index.return_value = unified_index

        assert self.backend.get_facet_fieldname("title") == "title.keyword"

    def test_get_facet_fieldname_char(self):
        """Test that get_facet_fieldname returns .keyword for char fields."""
        unified_index = MockUnifiedIndex({"model1": {"title": MockField("char")}})
        self.mock_connections["default"].get_unified_index.return_value = unified_index

        assert self.backend.get_facet_fieldname("title") == "title.keyword"

    def test_get_facet_fieldname_integer(self):
        """Test that get_facet_fieldname returns base name for integer fields."""
        unified_index = MockUnifiedIndex({"model1": {"count": MockField("integer")}})
        self.mock_connections["default"].get_unified_index.return_value = unified_index

        assert self.backend.get_facet_fieldname("count") == "count"

    def test_process_facets_terms(self):
        """Test that _process_facets correctly parses terms aggregations."""
        raw_results = {
            "aggregations": {
                "category": {
                    "meta": {"_type": "terms"},
                    "buckets": [
                        {"key": "fiction", "doc_count": 10},
                        {"key": "history", "doc_count": 5},
                    ],
                }
            }
        }
        facets = self.backend._process_facets(raw_results)
        assert "fields" in facets
        assert facets["fields"]["category"] == [("fiction", 10), ("history", 5)]

    def test_build_schema_faceted_field(self):
        """Test that build_schema keeps faceted fields as text."""
        fields = {"category": MockField("char", faceted=True)}
        # In build_schema, field_class.index_fieldname is used
        fields["category"].index_fieldname = "category"
        fields["category"].boost = 1.0
        fields["category"].document = False
        fields["category"].indexed = True

        content_field, mapping = self.backend.build_schema(fields)

        assert mapping["category"]["type"] == "text"
        assert "analyzer" in mapping["category"]

    def test_add_keyword_and_exact_subfields(self):
        """Test that _add_keyword_and_exact_subfields adds .keyword subfield and removes _exact."""
        props = {
            "category": {"type": "text", "analyzer": "snowball"},
            "count": {"type": "long"},
        }
        mock_unified_index = MagicMock()

        new_props = self.backend._add_keyword_and_exact_subfields(
            props, mock_unified_index
        )

        assert "category" in new_props
        assert new_props["category"]["type"] == "text"
        assert "fields" in new_props["category"]
        assert "keyword" in new_props["category"]["fields"]
        assert new_props["category"]["fields"]["keyword"]["type"] == "keyword"

        assert "category_exact" not in new_props
        assert "count" in new_props
        assert new_props["count"]["type"] == "long"
        assert "fields" not in new_props["count"]

    def test_build_search_kwargs_narrow_queries(self):
        """Test that build_search_kwargs resolves narrow_queries correctly."""
        query_string = "test"
        narrow_queries = {'category_exact:"fiction"'}

        # Mock unified index and fields
        unified_index = MockUnifiedIndex(
            {"model1": {"category": MockField("char", faceted=True)}}
        )
        self.mock_connections["default"].get_unified_index.return_value = unified_index

        # We need to mock build_models_list since it's called in build_search_kwargs
        self.backend.build_models_list = MagicMock(return_value=[])

        # Mock index.document_field
        unified_index.document_field = "text"

        kwargs = self.backend.build_search_kwargs(
            query_string, narrow_queries=narrow_queries
        )

        # Check that post_filter contains the correctly resolved field name
        # In build_search_kwargs, it adds to filters, then calls _apply_filters_to_query
        # which adds to kwargs['query']['bool']['filter']
        assert "query" in kwargs
        assert "bool" in kwargs["query"]
        assert "filter" in kwargs["query"]["bool"]

        # The filter should be a term query for category.keyword
        found = False
        filters = kwargs["query"]["bool"]["filter"]
        if isinstance(filters, dict) and "term" in filters:
            if "category.keyword" in filters["term"]:
                found = True
        elif isinstance(filters, list):
            for f in filters:
                if "term" in f and "category.keyword" in f["term"]:
                    found = True
        elif (
            isinstance(filters, dict)
            and "bool" in filters
            and "must" in filters["bool"]
        ):
            for f in filters["bool"]["must"]:
                if "term" in f and "category.keyword" in f["term"]:
                    found = True

        assert found, (
            f"Could not find category.keyword filter in {kwargs['query']['bool']['filter']}"
        )
