import pytest
from unittest.mock import MagicMock, patch
from opensearchpy.exceptions import NotFoundError, TransportError
from django_haystack_opensearch.haystack import OpenSearchSearchBackend
class TestOpenSearchIndexManagement:
    def setup_method(self):
        self.opts = {
            "URL": "http://localhost:9200",
            "INDEX_NAME": "test-index",
        }
        self.backend = OpenSearchSearchBackend("default", **self.opts)
        self.backend.conn = MagicMock()

    def test_add_keyword_and_exact_subfields(self, mock_unified_index):
        props = {
            "text_field": {"type": "text"},
            "date_field": {"type": "date"},
        }
        new_props = self.backend._add_keyword_and_exact_subfields(props, mock_unified_index)

        assert new_props["text_field"]["type"] == "text"
        assert "keyword" in new_props["text_field"]["fields"]
        assert new_props["text_field"]["fields"]["keyword"]["type"] == "keyword"
        assert new_props["date_field"]["type"] == "date"
        assert "fields" not in new_props["date_field"]

    def test_build_schema(self, mock_field_class):
        fields = {
            "text": mock_field_class("text", document=True, index_fieldname="text"),
            "pub_date": mock_field_class("date", index_fieldname="pub_date"),
            "boosted": mock_field_class("text", index_fieldname="boosted", boost=2.0),
            "non_indexed": mock_field_class("text", index_fieldname="non_indexed", indexed=False),
        }
        content_field_name, mapping = self.backend.build_schema(fields)

        assert content_field_name == "text"
        assert mapping["text"]["type"] == "text"
        assert mapping["pub_date"]["type"] == "date"
        assert mapping["boosted"]["boost"] == 2.0
        assert mapping["non_indexed"]["type"] == "keyword"
        assert "analyzer" not in mapping["non_indexed"]

    def test_setup_new_index(self, mock_connections, mock_unified_index):
        # Mock indices.get_mapping to raise NotFoundError (index doesn't exist)
        self.backend.conn.indices.get_mapping.side_effect = NotFoundError(404, "Not Found")

        # Mock build_schema to return something simple
        with patch.object(self.backend, "build_schema", return_value=("text", {"text": {"type": "text"}})):
            self.backend.setup()

            # Verify index creation and mapping update
            self.backend.conn.indices.create.assert_called_once_with(
                index="test-index", body=self.backend.DEFAULT_SETTINGS, ignore=[400]
            )
            self.backend.conn.indices.put_mapping.assert_called_once()
            assert self.backend.setup_complete is True

    def test_setup_existing_index_no_change(self, mock_connections, mock_unified_index):
        # Mock indices.get_mapping to return current mapping
        # Note: _add_keyword_and_exact_subfields will add the keyword subfield
        current_mapping = {"properties": {"text": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}}}}
        self.backend.conn.indices.get_mapping.return_value = {"test-index": {"mappings": current_mapping}}

        with patch.object(self.backend, "build_schema", return_value=("text", {"text": {"type": "text"}})):
            self.backend.setup()

            # Verify indices.create and put_mapping NOT called because mapping matches
            self.backend.conn.indices.create.assert_not_called()
            self.backend.conn.indices.put_mapping.assert_not_called()
            assert self.backend.setup_complete is True

    def test_clear_all_models(self):
        self.backend.setup_complete = True
        self.backend._clear_all_models()

        self.backend.conn.indices.delete.assert_called_with(index="test-index", ignore=[404])
        assert self.backend.setup_complete is False
        assert self.backend.existing_mapping == {}
        assert self.backend.content_field_name is None

    @patch("django_haystack_opensearch.haystack.scan")
    @patch("django_haystack_opensearch.haystack.bulk")
    @patch("django_haystack_opensearch.haystack.get_model_ct")
    def test_clear_specific_models(self, mock_get_model_ct, mock_bulk, mock_scan):
        mock_get_model_ct.return_value = "myapp.mymodel"
        mock_scan.return_value = [{"_id": "1"}, {"_id": "2"}]

        models = [MagicMock()]
        self.backend._clear_specific_models(models)

        mock_scan.assert_called_once()
        mock_bulk.assert_called_once()
        self.backend.conn.indices.refresh.assert_called_with(index="test-index")

    def test_clear_delegation(self):
        with patch.object(self.backend, "_clear_all_models") as mock_clear_all:
            self.backend.clear(models=None)
            mock_clear_all.assert_called_once()

        with patch.object(self.backend, "_clear_specific_models") as mock_clear_spec:
            self.backend.clear(models=["model1", "model2"])
            mock_clear_spec.assert_called_once_with(["model1", "model2"])

