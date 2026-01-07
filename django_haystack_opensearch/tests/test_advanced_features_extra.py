import pytest
import base64
import io
from unittest.mock import MagicMock, patch
from django_haystack_opensearch.haystack import OpenSearchSearchBackend

@pytest.fixture
def backend(mock_connections, mock_opensearch):
    backend = OpenSearchSearchBackend(connection_alias="default", URL="http://localhost:9200", INDEX_NAME="test_index")
    backend.conn = mock_opensearch
    backend.setup_complete = True
    return backend

def test_extract_file_contents_success(backend):
    # Mock file-like object
    file_content = b"fake binary content"
    file_obj = io.BytesIO(file_content)

    # Mock OpenSearch response for ingest simulate
    mock_response = {
        "docs": [
            {
                "doc": {
                    "_source": {
                        "attachment": {
                            "content": "extracted text content",
                            "metadata": {"title": "Test Doc"}
                        }
                    }
                }
            }
        ]
    }
    backend.conn.ingest.simulate.return_value = mock_response

    result = backend.extract_file_contents(file_obj)

    assert result == {
        "contents": "extracted text content",
        "metadata": {"title": "Test Doc"}
    }

    # Verify the call
    backend.conn.ingest.simulate.assert_called_once()
    call_args = backend.conn.ingest.simulate.call_args
    body = call_args.kwargs["body"]

    assert body["docs"][0]["_source"]["data"] == base64.b64encode(file_content).decode("utf-8")
    assert body["pipeline"]["processors"][0]["attachment"]["field"] == "data"

def test_extract_file_contents_failure_silent(backend):
    file_obj = io.BytesIO(b"content")
    backend.conn.ingest.simulate.side_effect = Exception("OpenSearch error")
    backend.silently_fail = True

    result = backend.extract_file_contents(file_obj)

    assert result is None

def test_extract_file_contents_failure_no_silent(backend):
    file_obj = io.BytesIO(b"content")
    backend.conn.ingest.simulate.side_effect = Exception("OpenSearch error")
    backend.silently_fail = False

    with pytest.raises(Exception, match="OpenSearch error"):
        backend.extract_file_contents(file_obj)

def test_search_logging(backend, mock_connections):
    # Mock settings.DEBUG
    with patch("django.conf.settings.DEBUG", True):
        # We need to mock haystack.connections because BaseSearchBackend's @log_query uses it
        mock_conn = MagicMock()
        mock_conn.queries = []
        mock_connections.__getitem__.return_value = mock_conn

        # Mock search execution to avoid errors
        backend.conn.search.return_value = {"hits": {"total": {"value": 0}, "hits": []}}

        backend.search("test query")

        assert len(mock_conn.queries) == 1
        query_entry = mock_conn.queries[0]
        assert query_entry["query_string"] == "test query"
        assert "time" in query_entry

