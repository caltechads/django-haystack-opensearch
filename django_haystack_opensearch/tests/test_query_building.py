import pytest
from unittest.mock import MagicMock, patch
from django_haystack_opensearch.haystack import OpenSearchSearchBackend, OpenSearchSearchQuery
from haystack.inputs import Clean, Exact, PythonData, Raw

class TestOpenSearchQueryBuilding:
    def setup_method(self):
        self.opts = {
            "URL": "http://localhost:9200",
            "INDEX_NAME": "test-index",
        }
        self.backend = OpenSearchSearchBackend("default", **self.opts)
        self.query = OpenSearchSearchQuery(using="default")
        self.query.backend = self.backend

    def _setup_mock_field(self, mock_unified_index, mock_field_class, field_name, index_fieldname, field_type="text"):
        mock_field = mock_field_class(field_type, index_fieldname=index_fieldname)
        mock_model = "mock_model"
        mock_unified_index.model_fields_map = {
            mock_model: {
                field_name: mock_field
            }
        }
        # MockUnifiedIndex doesn't have get_index_fieldname, so we add it
        mock_unified_index.get_index_fieldname = MagicMock(return_value=index_fieldname)
        # Mock get_index to return a mock index with the fields
        mock_index = MagicMock()
        # To satisfy get_facet_fieldname, we need the backend name as a key in fields
        mock_index.fields = {
            field_name: mock_field,
            index_fieldname: mock_field
        }
        mock_unified_index.get_index = MagicMock(return_value=mock_index)
        mock_unified_index.get_indexed_models = MagicMock(return_value=[mock_model])
        return mock_field

    def test_matching_all_fragment(self):
        assert self.query.matching_all_fragment() == "*:*"

    def test_build_query_fragment_content(self):
        # The 'content' field is special and doesn't get a field name prefix
        result = self.query.build_query_fragment("content", "exact", "hello world")
        assert result == '("hello world")'

    def test_build_query_fragment_exact_text(self, mock_connections, mock_unified_index, mock_field_class):
        self._setup_mock_field(mock_unified_index, mock_field_class, "name", "name_stored", "text")

        result = self.query.build_query_fragment("name", "exact", "John Doe")
        assert result == 'name_stored.keyword:("John Doe")'

    def test_build_query_fragment_in_list(self, mock_connections, mock_unified_index, mock_field_class):
        self._setup_mock_field(mock_unified_index, mock_field_class, "status", "status_stored", "text")

        result = self.query.build_query_fragment("status", "in", ["active", "pending"])
        assert result == 'status_stored.keyword:("active" OR "pending")'

    def test_build_query_fragment_range(self, mock_connections, mock_unified_index, mock_field_class):
        self._setup_mock_field(mock_unified_index, mock_field_class, "age", "age_stored", "integer")

        result = self.query.build_query_fragment("age", "range", [20, 30])
        assert result == 'age_stored:(["20" TO "30"])'

    def test_build_query_fragment_gt_gte_lt_lte(self, mock_connections, mock_unified_index, mock_field_class):
        self._setup_mock_field(mock_unified_index, mock_field_class, "price", "price", "integer")

        assert self.query.build_query_fragment("price", "gt", 100) == 'price:({"100" TO *})'
        assert self.query.build_query_fragment("price", "gte", 100) == 'price:(["100" TO *])'
        assert self.query.build_query_fragment("price", "lt", 100) == 'price:({* TO "100"})'
        assert self.query.build_query_fragment("price", "lte", 100) == 'price:([* TO "100"])'

    def test_build_query_fragment_contains_startswith_endswith(self, mock_connections, mock_unified_index, mock_field_class):
        self._setup_mock_field(mock_unified_index, mock_field_class, "title", "title", "text")

        assert self.query.build_query_fragment("title", "contains", "search") == "title:(*search*)"
        assert self.query.build_query_fragment("title", "startswith", "search") == "title:(search*)"
        assert self.query.build_query_fragment("title", "endswith", "search") == "title:(*search)"

    def test_build_query_fragment_fuzzy(self, mock_connections, mock_unified_index, mock_field_class):
        self._setup_mock_field(mock_unified_index, mock_field_class, "title", "title", "text")
        assert self.query.build_query_fragment("title", "fuzzy", "search") == "title:(search~)"

    def test_build_query_fragment_inputs(self, mock_connections, mock_unified_index, mock_field_class):
        self._setup_mock_field(mock_unified_index, mock_field_class, "text", "text", "text")

        # Raw input
        assert self.query.build_query_fragment("text", "exact", Raw("field:value")) == "text.keyword:field:value"

        # Exact input
        assert self.query.build_query_fragment("text", "exact", Exact("John Doe")) == 'text.keyword:("John Doe")'

        # Clean input
        assert self.query.build_query_fragment("text", "exact", Clean("John Doe")) == 'text.keyword:("John Doe")'

    def test_build_query_fragment_multiple_terms(self, mock_connections, mock_unified_index, mock_field_class):
        self._setup_mock_field(mock_unified_index, mock_field_class, "text", "text", "text")

        # Multiple terms should be joined by AND
        result = self.query.build_query_fragment("text", "contains", "hello world")
        assert result == "text:(*hello* AND *world*)"
