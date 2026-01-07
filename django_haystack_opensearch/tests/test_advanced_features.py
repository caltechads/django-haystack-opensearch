import pytest
from unittest.mock import MagicMock, patch
from django_haystack_opensearch.haystack import OpenSearchSearchBackend


@pytest.fixture
def backend(mock_connections, mock_opensearch):
    backend = OpenSearchSearchBackend(connection_alias="default", URL="http://localhost:9200", INDEX_NAME="test_index")
    backend.conn = mock_opensearch
    backend.setup_complete = True
    return backend


def test_build_search_query_dwithin(backend):
    # Mock dwithin dict
    mock_point = MagicMock()
    mock_point.coords = (1.23, 4.56)  # lng, lat

    mock_distance = MagicMock()
    mock_distance.km = 10.5

    dwithin = {
        "field": "location",
        "point": mock_point,
        "distance": mock_distance,
    }

    query = backend._build_search_query_dwithin(dwithin)

    assert query == {
        "geo_distance": {
            "distance": "10.500000km",
            "location": {"lat": 4.56, "lon": 1.23},
        }
    }


def test_build_search_query_within(backend):
    # Mock within dict
    mock_point_1 = MagicMock()
    mock_point_2 = MagicMock()

    within = {
        "field": "location",
        "point_1": mock_point_1,
        "point_2": mock_point_2,
    }

    # Patch generate_bounding_box to return fixed coordinates
    # south, west, north, east
    with patch("django_haystack_opensearch.haystack.generate_bounding_box") as mock_gen_box:
        mock_gen_box.return_value = ((30.0, 10.0), (40.0, 20.0))

        query = backend._build_search_query_within(within)

        mock_gen_box.assert_called_once_with(mock_point_1, mock_point_2)

        assert query == {
            "geo_bounding_box": {
                "location": {
                    "top_left": {"lat": 40.0, "lon": 10.0},
                    "bottom_right": {"lat": 30.0, "lon": 20.0},
                }
            }
        }


def test_build_mlt_query_base(backend):
    query = backend._build_mlt_query(
        field_name="text",
        doc_id="myapp.mymodel.1",
        additional_query_string=None,
        model_choices=[],
    )

    assert query == {
        "query": {
            "more_like_this": {
                "fields": ["text"],
                "like": [
                    {
                        "_index": "test_index",
                        "_id": "myapp.mymodel.1",
                    }
                ],
            }
        }
    }


def test_build_mlt_query_with_additional_query(backend):
    query = backend._build_mlt_query(
        field_name="text",
        doc_id="myapp.mymodel.1",
        additional_query_string="category:news",
        model_choices=[],
    )

    assert query == {
        "query": {
            "bool": {
                "must": {
                    "more_like_this": {
                        "fields": ["text"],
                        "like": [{"_index": "test_index", "_id": "myapp.mymodel.1"}],
                    }
                },
                "filter": {
                    "bool": {
                        "must": [{"query_string": {"query": "category:news"}}]
                    }
                },
            }
        }
    }


def test_build_mlt_query_with_model_choices(backend):
    query = backend._build_mlt_query(
        field_name="text",
        doc_id="myapp.mymodel.1",
        additional_query_string=None,
        model_choices=["myapp.model1", "myapp.model2"],
    )

    assert query == {
        "query": {
            "bool": {
                "must": {
                    "more_like_this": {
                        "fields": ["text"],
                        "like": [{"_index": "test_index", "_id": "myapp.mymodel.1"}],
                    }
                },
                "filter": {
                    "bool": {
                        "must": [{"terms": {"django_ct": ["myapp.model1", "myapp.model2"]}}]
                    }
                },
            }
        }
    }


def test_more_like_this_execution(backend, mock_connections, mock_unified_index):
    # Setup mocks
    mock_instance = MagicMock()
    mock_instance._meta.concrete_model = MagicMock()

    mock_index = MagicMock()
    mock_index.get_content_field.return_value = "text"

    # We need to ensure connections in haystack.py is also mocked
    with patch("django_haystack_opensearch.haystack.connections", mock_connections):
        with patch.object(mock_unified_index, "get_index", return_value=mock_index):
            with patch("django_haystack_opensearch.haystack.get_identifier") as mock_get_id:
                mock_get_id.return_value = "myapp.mymodel.1"
                backend.conn.search.return_value = {"hits": {"total": {"value": 0}, "hits": []}}

                backend.more_like_this(
                    model_instance=mock_instance,
                    additional_query_string="test",
                    start_offset=10,
                    end_offset=25,
                )

        # Verify search call
        backend.conn.search.assert_called_once()
        call_kwargs = backend.conn.search.call_args.kwargs

        assert call_kwargs["from_"] == 10
        assert call_kwargs["size"] == 15
        assert call_kwargs["index"] == "test_index"
        assert "_source" in call_kwargs

        # Verify MLT query structure in body
        body = call_kwargs["body"]
        assert "more_like_this" in body["query"]["bool"]["must"]
        assert body["query"]["bool"]["filter"]["bool"]["must"][0] == {"query_string": {"query": "test"}}


def test_more_like_this_with_models(backend, mock_connections, mock_unified_index):
    mock_instance = MagicMock()
    mock_instance._meta.concrete_model = MagicMock()

    mock_index = MagicMock()
    mock_index.get_content_field.return_value = "text"

    mock_model = MagicMock()

    with patch("django_haystack_opensearch.haystack.connections", mock_connections):
        with patch.object(mock_unified_index, "get_index", return_value=mock_index):
            with patch("django_haystack_opensearch.haystack.get_identifier") as mock_get_id:
                with patch("django_haystack_opensearch.haystack.get_model_ct") as mock_get_ct:
                    mock_get_id.return_value = "myapp.mymodel.1"
                    mock_get_ct.return_value = "myapp.mockmodel"
                    backend.conn.search.return_value = {"hits": {"total": {"value": 0}, "hits": []}}

                    backend.more_like_this(
                        model_instance=mock_instance,
                        models=[mock_model],
                    )

                    body = backend.conn.search.call_args.kwargs["body"]
                    # Verify model filter is present
                    assert body["query"]["bool"]["filter"]["bool"]["must"][0] == {"terms": {"django_ct": ["myapp.mockmodel"]}}


def test_more_like_this_transport_error(backend, mock_connections, mock_unified_index):
    mock_instance = MagicMock()
    mock_instance._meta.concrete_model = MagicMock()

    mock_index = MagicMock()
    mock_index.get_content_field.return_value = "text"

    from opensearchpy.exceptions import TransportError

    with patch("django_haystack_opensearch.haystack.connections", mock_connections):
        with patch.object(mock_unified_index, "get_index", return_value=mock_index):
            with patch("django_haystack_opensearch.haystack.get_identifier") as mock_get_id:
                mock_get_id.return_value = "myapp.mymodel.1"
                backend.conn.search.side_effect = TransportError(500, "Error")
                backend.silently_fail = True

                results = backend.more_like_this(model_instance=mock_instance)

                assert results == {"results": [], "hits": 0, "facets": {"fields": {}, "dates": {}, "queries": {}}, "spelling_suggestion": None}


def test_more_like_this_transport_error_no_silent_fail(backend, mock_connections, mock_unified_index):
    mock_instance = MagicMock()
    mock_instance._meta.concrete_model = MagicMock()

    mock_index = MagicMock()
    mock_index.get_content_field.return_value = "text"

    from opensearchpy.exceptions import TransportError

    with patch("django_haystack_opensearch.haystack.connections", mock_connections):
        with patch.object(mock_unified_index, "get_index", return_value=mock_index):
            with patch("django_haystack_opensearch.haystack.get_identifier") as mock_get_id:
                mock_get_id.return_value = "myapp.mymodel.1"
                backend.conn.search.side_effect = TransportError(500, "Error")
                backend.silently_fail = False

                with pytest.raises(TransportError):
                    backend.more_like_this(model_instance=mock_instance)


def test_more_like_this_no_registered_models(backend, mock_connections, mock_unified_index):
    mock_instance = MagicMock()
    mock_instance._meta.concrete_model = MagicMock()

    mock_index = MagicMock()
    mock_index.get_content_field.return_value = "text"

    with patch("django_haystack_opensearch.haystack.connections", mock_connections):
        with patch.object(mock_unified_index, "get_index", return_value=mock_index):
            with patch("django_haystack_opensearch.haystack.get_identifier") as mock_get_id:
                mock_get_id.return_value = "myapp.mymodel.1"
                backend.conn.search.return_value = {"hits": {"total": {"value": 0}, "hits": []}}

                backend.more_like_this(
                    model_instance=mock_instance,
                    limit_to_registered_models=False,
                )

                body = backend.conn.search.call_args.kwargs["body"]
                # Verify no model filter is present (it should just be the mlt query, not wrapped in bool if no filters)
                assert "more_like_this" in body["query"]
                assert "bool" not in body["query"]


def test_more_like_this_triggers_setup(backend, mock_connections, mock_unified_index):
    backend.setup_complete = False

    mock_instance = MagicMock()
    mock_instance._meta.concrete_model = MagicMock()

    mock_index = MagicMock()
    mock_index.get_content_field.return_value = "text"

    with patch("django_haystack_opensearch.haystack.connections", mock_connections):
        with patch.object(mock_unified_index, "get_index", return_value=mock_index):
            with patch.object(backend, "setup") as mock_setup:
                with patch("django_haystack_opensearch.haystack.get_identifier") as mock_get_id:
                    mock_get_id.return_value = "myapp.mymodel.1"
                    backend.conn.search.return_value = {"hits": {"total": {"value": 0}, "hits": []}}

                    backend.more_like_this(model_instance=mock_instance)

                    mock_setup.assert_called_once()

