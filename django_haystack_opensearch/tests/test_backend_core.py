import datetime
import pytest
from unittest.mock import MagicMock, patch
from django.core.exceptions import ImproperlyConfigured
from haystack.exceptions import SkipDocument
from opensearchpy.exceptions import TransportError
from django_haystack_opensearch.haystack import OpenSearchSearchBackend


class TestOpenSearchBackendCore:
    def setup_method(self):
        self.opts = {
            "URL": "http://localhost:9200",
            "INDEX_NAME": "test-index",
            "KWARGS": {"some_opt": "value"},
        }
        self.backend = OpenSearchSearchBackend("default", **self.opts)

    def test_init_success(self):
        assert self.backend.connection_alias == "default"
        assert self.backend.index_name == "test-index"
        assert self.backend.setup_complete is False

    def test_init_missing_url(self):
        opts = {"INDEX_NAME": "test-index"}
        with pytest.raises(ImproperlyConfigured) as excinfo:
            OpenSearchSearchBackend("default", **opts)
        assert "You must specify a 'URL'" in str(excinfo.value)

    def test_init_missing_index_name(self):
        opts = {"URL": "http://localhost:9200"}
        with pytest.raises(ImproperlyConfigured) as excinfo:
            OpenSearchSearchBackend("default", **opts)
        assert "You must specify a 'INDEX_NAME'" in str(excinfo.value)

    def test_iso_datetime(self):
        # Test datetime object
        dt = datetime.datetime(2023, 1, 1, 12, 30, 45)
        assert self.backend._iso_datetime(dt) == "2023-01-01T12:30:45"

        # Test date object
        d = datetime.date(2023, 1, 1)
        assert self.backend._iso_datetime(d) == "2023-01-01T00:00:00"

        # Test non-datetime object
        assert self.backend._iso_datetime("not-a-date") is None

    def test_from_python_datetime(self):
        dt = datetime.datetime(2023, 1, 1, 12, 30, 45)
        assert self.backend._from_python(dt) == "2023-01-01T12:30:45"

    def test_from_python_bytes(self):
        b = b"hello"
        assert self.backend._from_python(b) == "hello"

    def test_from_python_set(self):
        s = {1, 2, 3}
        result = self.backend._from_python(s)
        assert isinstance(result, list)
        assert set(result) == s

    def test_from_python_other(self):
        assert self.backend._from_python(123) == 123
        assert self.backend._from_python("test") == "test"

    def test_to_python_datetime(self):
        # Test valid ISO datetime string
        date_str = "2023-01-01T12:30:45.000"
        result = self.backend._to_python(date_str)
        assert isinstance(result, datetime.datetime)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12
        assert result.minute == 30
        assert result.second == 45

    def test_to_python_literal_eval(self):
        # Test string representation of list
        list_str = "[1, 2, 3]"
        assert self.backend._to_python(list_str) == [1, 2, 3]

        # Test string representation of dict
        dict_str = "{'a': 1}"
        assert self.backend._to_python(dict_str) == {"a": 1}

    def test_to_python_fallback(self):
        # Test non-serializable string
        assert self.backend._to_python("plain string") == "plain string"
        # Test non-string input
        assert self.backend._to_python(123) == 123

    @patch("django_haystack_opensearch.haystack.get_identifier")
    def test_prepare_documents_for_bulk(self, mock_get_id):
        mock_get_id.return_value = "myapp.mymodel.1"
        mock_index = MagicMock()
        mock_index.full_prepare.return_value = {
            "id": "myapp.mymodel.1",
            "text": "sample text",
            "pub_date": datetime.datetime(2023, 1, 1),
        }

        iterable = [MagicMock()]

        # We need to mock self.backend._prepare_object because it's called in _prepare_documents_for_bulk
        with patch.object(
            self.backend,
            "_prepare_object",
            return_value=mock_index.full_prepare.return_value,
        ):
            docs = self.backend._prepare_documents_for_bulk("some_index", iterable)

            assert len(docs) == 1
            assert docs[0]["_id"] == "myapp.mymodel.1"
            assert docs[0]["_index"] == "test-index"
            assert docs[0]["pub_date"] == "2023-01-01T00:00:00"

    def test_prepare_documents_for_bulk_skip(self):
        iterable = [MagicMock()]
        with patch.object(self.backend, "_prepare_object", side_effect=SkipDocument):
            docs = self.backend._prepare_documents_for_bulk("some_index", iterable)
            assert len(docs) == 0

    @patch("django_haystack_opensearch.haystack.get_identifier")
    def test_prepare_documents_for_bulk_error(self, mock_get_id):
        mock_get_id.return_value = "myapp.mymodel.1"
        iterable = [MagicMock()]
        self.backend.silently_fail = False

        with patch.object(
            self.backend, "_prepare_object", side_effect=TransportError(500, "error")
        ):
            with pytest.raises(TransportError):
                self.backend._prepare_documents_for_bulk("some_index", iterable)

    @patch("django_haystack_opensearch.haystack.get_identifier")
    def test_prepare_documents_for_bulk_error_silent(self, mock_get_id):
        mock_get_id.return_value = "myapp.mymodel.1"
        iterable = [MagicMock()]
        self.backend.silently_fail = True

        with patch.object(
            self.backend, "_prepare_object", side_effect=TransportError(500, "error")
        ):
            docs = self.backend._prepare_documents_for_bulk("some_index", iterable)
            assert len(docs) == 0


