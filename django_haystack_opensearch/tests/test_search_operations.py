import pytest
import datetime
from unittest.mock import MagicMock, patch
from haystack.models import SearchResult
from django_haystack_opensearch.haystack import OpenSearchSearchBackend
from .conftest import MockField, MockIndex, MockUnifiedIndex

class TestSearchOperationsUnit:
    """Unit tests for search operations logic in the OpenSearch backend."""

    def setup_method(self):
        self.backend = OpenSearchSearchBackend(
            connection_alias="default", URL="http://localhost:9200", INDEX_NAME="test"
        )
        # Mock connections to return our mock unified index
        self.mock_unified_index = MockUnifiedIndex()
        self.mock_unified_index.document_field = "text"

        # Explicitly mock the methods if they are not already MagicMocks
        self.mock_unified_index.get_indexed_models = MagicMock(return_value=[])
        self.mock_unified_index.get_index = MagicMock()

        self.mock_connections = MagicMock()
        self.mock_connections["default"].get_unified_index.return_value = self.mock_unified_index

        self.patcher = patch("haystack.connections", self.mock_connections)
        self.patcher.start()

        # Mock the OpenSearch client's search method
        self.backend.conn.search = MagicMock()

    def teardown_method(self):
        self.patcher.stop()

    def test_build_search_params_pagination(self):
        """Test _build_search_params sets from and size correctly."""
        kwargs = {}
        # start=0, end=10 -> from=0, size=10
        self.backend._build_search_params(kwargs, 0, 10)
        assert kwargs["from"] == 0
        assert kwargs["size"] == 10

        kwargs = {}
        # start=20, end=50 -> from=20, size=30
        self.backend._build_search_params(kwargs, 20, 50)
        assert kwargs["from"] == 20
        assert kwargs["size"] == 30

    def test_add_highlight_to_kwargs(self):
        """Test _add_highlight_to_kwargs adds highlight config."""
        kwargs = {}
        self.backend._add_highlight_to_kwargs(kwargs, True, "text")
        assert "highlight" in kwargs
        assert kwargs["highlight"]["fields"]["text"] == {}

        # With dict config
        kwargs = {}
        self.backend._add_highlight_to_kwargs(kwargs, {"pre_tags": ["<b>"]}, "text")
        assert "highlight" in kwargs
        assert kwargs["highlight"]["pre_tags"] == ["<b>"]
        assert kwargs["highlight"]["fields"]["text"] == {}

    def test_process_hits(self):
        """Test _process_hits extracts total value."""
        raw_results = {"hits": {"total": {"value": 42}}}
        assert self.backend._process_hits(raw_results) == 42

        assert self.backend._process_hits({}) == 0

    def test_process_results_basic(self, mock_field_class):
        """Test processing basic hits into SearchResult objects."""
        # Setup mock model and index
        mock_model = MagicMock()
        mock_model._meta.concrete_model = mock_model

        # Mock haystack_get_model
        with patch("django_haystack_opensearch.haystack.haystack_get_model", return_value=mock_model):
            # Define fields for the mock index
            fields = {
                "text": mock_field_class("text", document=True, index_fieldname="text"),
                "title": mock_field_class("char", index_fieldname="title")
            }
            self.mock_unified_index.model_fields_map = {mock_model: fields}
            self.mock_unified_index.get_indexed_models.return_value = [mock_model]

            raw_results = {
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_score": 1.5,
                            "_source": {
                                "django_ct": "app.model",
                                "django_id": "1",
                                "text": "sample content",
                                "title": "Sample Title"
                            }
                        }
                    ]
                }
            }

            results = self.backend._process_results(raw_results)

            assert results["hits"] == 1
            assert len(results["results"]) == 1
            res = results["results"][0]
            assert isinstance(res, SearchResult)
            assert res.app_label == "app"
            assert res.model_name == "model"
            assert res.pk == "1"
            assert res.score == 1.5
            assert res.text == "sample content"
            assert res.title == "Sample Title"

    def test_process_results_highlighting(self, mock_field_class):
        """Test that highlighting data is processed correctly."""
        mock_model = MagicMock()
        with patch("django_haystack_opensearch.haystack.haystack_get_model", return_value=mock_model):
            self.mock_unified_index.model_fields_map = {
                mock_model: {"text": mock_field_class("text", document=True, index_fieldname="text")}
            }
            self.mock_unified_index.get_indexed_models.return_value = [mock_model]

            raw_results = {
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_score": 1.0,
                            "_source": {
                                "django_ct": "app.model",
                                "django_id": "1",
                                "text": "original text"
                            },
                            "highlight": {
                                "text": ["<em>highlighted</em> text"]
                            }
                        }
                    ]
                }
            }

            results = self.backend._process_results(raw_results)
            res = results["results"][0]
            # SearchResult additional fields are stored in the object
            assert res.highlighted == ["<em>highlighted</em> text"]

    def test_process_results_spelling_suggestions(self):
        """Test spelling suggestion extraction during result processing."""
        self.backend.include_spelling = True
        raw_results = {
            "hits": {"total": {"value": 0}, "hits": []},
            "suggest": {
                "suggest": [
                    {
                        "text": "keng",
                        "options": [{"text": "king"}]
                    }
                ]
            }
        }

        # We need model mocks to avoid errors in _process_results loop, even if hits is 0
        self.mock_unified_index.get_indexed_models.return_value = []

        results = self.backend._process_results(raw_results)
        assert results["spelling_suggestion"] == "king"

    def test_search_empty_query(self):
        """Test search returns empty results for empty query string."""
        results = self.backend.search("")
        assert results["results"] == []
        assert results["hits"] == 0

    def test_search_orchestration(self):
        """Test the search method orchestration (calls to build, execute, process)."""
        self.backend.setup_complete = True

        with patch.object(self.backend, "build_search_kwargs", return_value={"query": "..."}) as mock_build, \
             patch.object(self.backend, "_build_search_params", side_effect=lambda k, s, e: k) as mock_params, \
             patch.object(self.backend, "_execute_search", return_value={"raw": "data"}) as mock_exec, \
             patch.object(self.backend, "_process_results", return_value={"results": [], "hits": 0}) as mock_process:

            self.backend.search("test query", start_offset=10, end_offset=20, highlight=True)

            mock_build.assert_called_once()
            mock_params.assert_called_once_with({"query": "..."}, 10, 20)
            mock_exec.assert_called_once()
            mock_process.assert_called_once()

    def test_execute_search_success(self):
        """Test _execute_search calls conn.search correctly."""
        self.backend.conn.search.return_value = {"hits": {"total": {"value": 1}}}
        search_kwargs = {"query": {"match_all": {}}}

        results = self.backend._execute_search(search_kwargs)

        self.backend.conn.search.assert_called_once_with(
            body=search_kwargs,
            index="test",
            _source=True
        )
        assert results["hits"]["total"]["value"] == 1

    def test_execute_search_exception(self):
        """Test _execute_search handles TransportError when silently_fail is True."""
        from opensearchpy.exceptions import TransportError
        self.backend.conn.search.side_effect = TransportError(500, "error")
        self.backend.silently_fail = True

        results = self.backend._execute_search({})
        assert results == {}

        self.backend.silently_fail = False
        with pytest.raises(TransportError):
            self.backend._execute_search({})

    def test_process_results_with_field_conversion(self, mock_field_class):
        """Test that index-specific field conversion is used during result processing."""
        mock_model = MagicMock()
        mock_model._meta.concrete_model = mock_model

        # Create a mock field with a custom converter
        mock_date_field = mock_field_class("date", index_fieldname="pub_date")
        mock_date_field.convert = MagicMock(return_value=datetime.date(2023, 1, 1))

        with patch("django_haystack_opensearch.haystack.haystack_get_model", return_value=mock_model):
            self.mock_unified_index.model_fields_map = {
                mock_model: {
                    "text": mock_field_class("text", document=True, index_fieldname="text"),
                    "pub_date": mock_date_field
                }
            }
            self.mock_unified_index.get_indexed_models.return_value = [mock_model]

            # Need to mock get_index for the model to return our mock index with converters
            mock_index = MockIndex(self.mock_unified_index.model_fields_map[mock_model])
            self.mock_unified_index.get_index.return_value = mock_index

            raw_results = {
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_score": 1.0,
                            "_source": {
                                "django_ct": "app.model",
                                "django_id": "1",
                                "text": "content",
                                "pub_date": "2023-01-01"
                            }
                        }
                    ]
                }
            }

            results = self.backend._process_results(raw_results)
            res = results["results"][0]
            assert res.pub_date == datetime.date(2023, 1, 1)
            mock_date_field.convert.assert_called_once_with("2023-01-01")

