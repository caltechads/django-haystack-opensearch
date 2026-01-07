from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from opensearchpy import OpenSearch
from opensearchpy.exceptions import ConnectionError as OpenSearchConnectionError


class MockField:
    def __init__(
        self,
        field_type,
        faceted=False,
        index_fieldname=None,
        boost=1.0,
        document=False,
        indexed=True,
    ):
        self.field_type = field_type
        self.faceted = faceted
        self.index_fieldname = index_fieldname or "field"
        self.boost = boost
        self.document = document
        self.indexed = indexed

    def convert(self, value):
        return value


class MockIndex:
    def __init__(self, fields, document_field="text"):
        self.fields = fields
        self.document_field = document_field

    def get_content_field(self):
        return self.document_field

    def full_prepare(self, obj):
        return obj


class MockUnifiedIndex:
    def __init__(self, model_fields_map=None, document_field="text"):
        self.model_fields_map = model_fields_map or {}
        self.document_field = document_field

    def get_indexed_models(self):
        return list(self.model_fields_map.keys())

    def get_index(self, model):
        return MockIndex(self.model_fields_map.get(model, {}), self.document_field)

    def all_searchfields(self):
        all_fields = {}
        for fields in self.model_fields_map.values():
            all_fields.update(fields)
        return all_fields


@pytest.fixture
def mock_opensearch():
    mock = MagicMock()
    mock.indices = MagicMock()
    return mock


@pytest.fixture
def mock_unified_index():
    return MockUnifiedIndex()


@pytest.fixture
def mock_field_class():
    return MockField


@pytest.fixture
def mock_connections(mock_unified_index):
    mock = MagicMock()
    mock.__getitem__.return_value.get_unified_index.return_value = mock_unified_index
    with patch("haystack.connections", mock):
        yield mock


@pytest.fixture(scope="session")
def opensearch_url():
    """
    Get the OpenSearch URL from Django settings or default to localhost.
    """
    default_url = "http://localhost:9200"
    try:
        # Check if Django settings are configured
        if not settings.configured:
            return default_url
        connections = getattr(settings, "HAYSTACK_CONNECTIONS", {})
        url = connections.get("default", {}).get("URL", default_url)
    except Exception:  # noqa: BLE001
        return default_url
    else:
        return url


@pytest.fixture(scope="session")
def real_opensearch(opensearch_url):
    """
    Return an OpenSearch client if the backend is reachable, otherwise skip.
    """
    client = OpenSearch(hosts=[opensearch_url], timeout=2)
    try:
        if client.ping():
            return client
    except OpenSearchConnectionError:
        pass

    pytest.skip(f"OpenSearch at {opensearch_url} is not reachable")
