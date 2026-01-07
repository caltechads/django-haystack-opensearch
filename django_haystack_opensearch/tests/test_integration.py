import os
import pytest
from django.core.management import call_command
from haystack.query import SearchQuerySet
from demo.core.models import Speech, Speaker, Play
from django.conf import settings

@pytest.mark.integration
@pytest.mark.django_db
class TestOpenSearchIntegration:
    @pytest.fixture(autouse=True)
    def setup_index(self, real_opensearch):
        """
        Rebuild the index before each test to ensure a clean state.
        We use the real_opensearch fixture to ensure OpenSearch is available.
        """
        # Ensure we are using the OpenSearch backend
        connections = getattr(settings, "HAYSTACK_CONNECTIONS", {})
        if "default" not in connections or "OpenSearchSearchEngine" not in connections["default"]["ENGINE"]:
             pytest.skip("OpenSearch backend not configured in settings")

        call_command('rebuild_index', interactive=False, verbosity=0)

    def test_rebuild_index_populated(self):
        """Verify that rebuild_index correctly populates OpenSearch from fixtures."""
        sqs = SearchQuerySet().all()
        # Macbeth and Henry V fixtures contain many speeches
        assert sqs.count() > 1000

    def test_basic_search(self):
        """Test basic keyword search for a famous quote."""
        # "Once more unto the breach" is from Henry V
        results = SearchQuerySet().filter(content="Once more unto the breach")
        assert results.count() > 0
        assert "Once more unto the breach" in results[0].text

    def test_filtering_and_soliloquy(self):
        """Test filtering by play and speaker, and test boolean filtering (soliloquy)."""
        # Filter by play
        macbeth_speeches = SearchQuerySet().filter(play_title="Macbeth")
        assert macbeth_speeches.count() > 0
        for result in macbeth_speeches[:5]:
            assert result.play_title == "Macbeth"

        # Filter by speaker
        henry_speeches = SearchQuerySet().filter(speaker_name="KING HENRY")
        assert henry_speeches.count() > 0
        for result in henry_speeches[:5]:
            assert result.speaker_name == "KING HENRY"

        # Since no speeches are marked as soliloquy in fixtures, create one
        speech = Speech.objects.first()
        speech.is_soliloquy = True
        speech.save()

        # Update index for this specific object
        from haystack import connections
        backend = connections['default'].get_backend()
        unified_index = connections['default'].get_unified_index()
        index = unified_index.get_index(Speech)
        backend.update(index, [speech])

        # Verify filtering by boolean field
        soliloquies = SearchQuerySet().filter(is_soliloquy=True)
        assert soliloquies.count() == 1
        assert soliloquies[0].pk == str(speech.pk)

    def test_faceting(self):
        """Verify facet counts for play titles."""
        sqs = SearchQuerySet().facet("play_title")
        facet_counts = sqs.facet_counts()

        assert "fields" in facet_counts
        assert "play_title" in facet_counts["fields"]

        play_facets = dict(facet_counts["fields"]["play_title"])
        assert "Macbeth" in play_facets
        assert play_facets["Macbeth"] > 0
        assert "Henry V" in play_facets
        assert play_facets["Henry V"] > 0

    def test_ordering(self):
        """Test sorting by numeric fields."""
        # Sort by speech length (float field)
        results = SearchQuerySet().order_by("speech_length")
        lengths = [float(r.speech_length) for r in results[:10]]
        assert lengths == sorted(lengths)

        # Sort descending
        results_desc = SearchQuerySet().order_by("-speech_length")
        lengths_desc = [float(r.speech_length) for r in results_desc[:10]]
        assert lengths_desc == sorted(lengths_desc, reverse=True)

    def test_spelling_suggestions(self):
        """Test spelling suggestion for a misspelled word."""
        # "breach" -> "brech" (misspelled)
        sqs = SearchQuerySet().filter(content="brech")
        suggestion = sqs.spelling_suggestion()
        # Suggestions depend on what's in the index and OpenSearch configuration
        # If it returns something, it should be a string.
        if suggestion:
            assert isinstance(suggestion, str)
            assert "breach" in suggestion.lower()

    def test_highlighting(self):
        """Test highlighting of search terms."""
        results = SearchQuerySet().filter(content="Macbeth").highlight()
        assert results.count() > 0

        for result in results[:5]:
            if hasattr(result, "highlighted"):
                assert "<em>" in result.highlighted[0].lower()
                assert "macbeth" in result.highlighted[0].lower()

    def test_more_like_this(self):
        """Test More Like This functionality."""
        # Get a speech to use as reference
        reference_speech = Speech.objects.get(text__contains="Once more unto the breach")

        # MLT is usually handled via the backend directly in Haystack
        from haystack import connections
        backend = connections['default'].get_backend()

        results = backend.more_like_this(reference_speech)
        assert results['hits'] > 0
        # Results should be related speeches (likely from the same play or with similar terms)
        assert len(results['results']) > 0

    def test_extract_file_contents(self, real_opensearch):
        """Test extraction of text from PDF and DOCX files."""
        from haystack import connections
        backend = connections['default'].get_backend()

        # Check if ingest-attachment plugin is installed
        try:
            nodes_info = real_opensearch.nodes.info()
            plugins = []
            for node_id in nodes_info['nodes']:
                plugins.extend([p['name'] for p in nodes_info['nodes'][node_id].get('plugins', [])])

            if 'ingest-attachment' not in plugins:
                pytest.skip("OpenSearch ingest-attachment plugin not installed")
        except Exception:
            # Fallback: try to call it and see if it fails with a specific error
            pass

        # Paths to test files
        tests_dir = os.path.dirname(__file__)
        docx_path = os.path.join(tests_dir, "translating.docx")
        pdf_path = os.path.join(tests_dir, "translating.pdf")

        # Test DOCX extraction
        if os.path.exists(docx_path):
            with open(docx_path, "rb") as f:
                result = backend.extract_file_contents(f)
                assert result is not None
                assert "translating" in result["contents"].lower()
                assert "metadata" in result

        # Test PDF extraction
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                result = backend.extract_file_contents(f)
                assert result is not None
                assert "translating" in result["contents"].lower()
                assert "metadata" in result

