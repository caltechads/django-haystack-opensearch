import pytest
from unittest.mock import MagicMock
from haystack import connections, indexes
from django_haystack_opensearch.haystack import OpenSearchSearchBackend

class MockUnifiedIndex:
    def __init__(self, fields=None):
        self.fields = fields or {}
        self.document_field = "text"

    def get_indexed_models(self):
        return [MagicMock()]

    def get_index(self, model):
        mock_index = MagicMock()
        mock_index.fields = self.fields
        return mock_index

class TestSpellingSuggestionsUnit:
    """Unit tests for spelling suggestions logic in the backend."""

    def setup_method(self):
        self.backend = OpenSearchSearchBackend(
            connection_alias="default",
            URL="http://localhost:9200",
            INDEX_NAME="test"
        )
        self.backend.include_spelling = True

    def test_add_suggest_to_kwargs_default(self):
        """Test _add_suggest_to_kwargs uses content_field by default."""
        kwargs = {}
        unified_index = MockUnifiedIndex()

        self.backend._add_suggest_to_kwargs(
            kwargs, "keng", None, "text", unified_index
        )

        assert "suggest" in kwargs
        assert kwargs["suggest"]["suggest"]["text"] == "keng"
        assert kwargs["suggest"]["suggest"]["term"]["field"] == "text"

    def test_add_suggest_to_kwargs_dedicated_field(self):
        """Test _add_suggest_to_kwargs uses _spelling field if present."""
        kwargs = {}
        unified_index = MockUnifiedIndex(fields={"_spelling": MagicMock()})

        self.backend._add_suggest_to_kwargs(
            kwargs, "keng", None, "text", unified_index
        )

        assert "suggest" in kwargs
        assert kwargs["suggest"]["suggest"]["term"]["field"] == "_spelling"

    def test_process_results_with_suggestions(self):
        """Test _process_results extracts and joins suggestions correctly."""
        raw_results = {
            "hits": {"total": {"value": 0}, "hits": []},
            "suggest": {
                "suggest": [
                    {
                        "text": "keng",
                        "offset": 0,
                        "length": 4,
                        "options": [{"text": "king", "score": 0.9, "freq": 1}]
                    },
                    {
                        "text": "prudpers",
                        "offset": 5,
                        "length": 8,
                        "options": [{"text": "prospers", "score": 0.8, "freq": 1}]
                    }
                ]
            }
        }

        # We need to mock haystack.connections because _process_results uses it
        with MagicMock() as mock_connections:
            # Mock the unified index and models
            mock_unified_index = MagicMock()
            mock_unified_index.get_indexed_models.return_value = []
            mock_unified_index.document_field = "text"

            # Setup the backend's connection alias to return our mock
            self.backend.connection_alias = "default"

            # Use a patch to avoid real Haystack connection lookups if possible,
            # or just mock the parts used.
            import haystack
            original_connections = haystack.connections
            haystack.connections = { "default": MagicMock() }
            haystack.connections["default"].get_unified_index.return_value = mock_unified_index

            try:
                results = self.backend._process_results(raw_results)
                assert results["spelling_suggestion"] == "king prospers"
            finally:
                haystack.connections = original_connections

    def test_process_results_no_options(self):
        """Test _process_results fallback when no options are returned."""
        raw_results = {
            "hits": {"total": {"value": 0}, "hits": []},
            "suggest": {
                "suggest": [
                    {
                        "text": "king",
                        "options": []
                    }
                ]
            }
        }

        import haystack
        original_connections = haystack.connections
        haystack.connections = { "default": MagicMock() }
        mock_unified_index = MagicMock()
        mock_unified_index.get_indexed_models.return_value = []
        haystack.connections["default"].get_unified_index.return_value = mock_unified_index

        try:
            results = self.backend._process_results(raw_results)
            assert results["spelling_suggestion"] == "king"
        finally:
            haystack.connections = original_connections

