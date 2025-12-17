from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, List, Type  # noqa: UP035

from haystack import indexes
from haystack.exceptions import SkipDocument
from opensearchpy.exceptions import TransportError

from demo.core.models import Play, Speaker, Speech

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet

logger = logging.getLogger(__name__)


#: Flag to control SkipDocument behavior for testing
SKIP_DOCUMENT_TEST_MODE = False
#: The IDs of the documents to skip for testing.
#: This is used to test the SkipDocument exception handling in
#: _prepare_documents_for_bulk.
SKIP_DOCUMENT_IDS: set[int] = set()


class SpeechIndex(indexes.SearchIndex, indexes.Indexable):
    """Search index for Speech model."""

    # Main document field
    text = indexes.CharField(document=True, model_attr="text")

    # Existing faceted fields
    speaker_name = indexes.CharField(model_attr="speaker__name", faceted=True)
    #: The speaker ID field for faceted search
    speaker_id = indexes.IntegerField(model_attr="speaker__id")
    #: The act name field for faceted search
    act_name = indexes.CharField(model_attr="scene__act__name", faceted=True)
    #: The scene name field for faceted search
    scene_name = indexes.CharField(model_attr="scene__name", faceted=True)
    #: The play title field for faceted search
    play_title = indexes.CharField(model_attr="scene__act__play__title", faceted=True)
    #: The play ID field for faceted search
    play_id = indexes.IntegerField(model_attr="scene__act__play__id")

    # These fields are not faceted, but are used for testing different field types

    # Ngram field for partial matching
    text_ngram = indexes.NgramField(model_attr="text")
    # Edge ngram field for autocomplete-style matching
    text_edge_ngram = indexes.EdgeNgramField(model_attr="text")
    # DateTimeField for date facets and sorting
    created_date = indexes.DateTimeField(model_attr="created_date")
    # FloatField for numeric operations
    speech_length = indexes.FloatField(model_attr="speech_length")
    # BooleanField for boolean filtering
    is_soliloquy = indexes.BooleanField(model_attr="is_soliloquy")
    # Field with boost for relevance testing
    speaker_name_boosted = indexes.CharField(model_attr="speaker__name", boost=2.0)
    # Field with indexed=False for non-indexed field mapping test
    text_stored_only = indexes.CharField(model_attr="text", indexed=False)
    # Order field as integer (already existed as model field)
    order = indexes.IntegerField(model_attr="order")

    def get_model(self) -> Type[Model]:
        """Return the Speech model."""
        return Speech

    def index_queryset(self, using: str | None = None) -> QuerySet:  # noqa: ARG002
        """
        Used when the entire index for model is updated.

        Keyword Args:
            using: The alias of the database to use. (unused)

        Returns:
            QuerySet of all Speech objects.

        """
        return self.get_model().objects.all()

    def prepare_skip_test(self, obj: Speech) -> str:
        """
        Prepare method for testing SkipDocument exception.

        This method conditionally raises SkipDocument based on test mode flags.
        Used to test the SkipDocument exception handling in _prepare_documents_for_bulk.

        Args:
            obj: The Speech object being indexed.

        Returns:
            Empty string if not skipped.

        Raises:
            SkipDocument: If the object's ID is in SKIP_DOCUMENT_IDS and
                SKIP_DOCUMENT_TEST_MODE is True.

        """
        global SKIP_DOCUMENT_TEST_MODE, SKIP_DOCUMENT_IDS  # noqa: PLW0602
        if SKIP_DOCUMENT_TEST_MODE and obj.pk in SKIP_DOCUMENT_IDS:
            msg = f"Skipping Speech {obj.pk} for testing"
            raise SkipDocument(msg)
        return ""

    def reindex_play(self, play: Play) -> None:
        """
        Reindex all speeches for a particular play.

        Args:
            play: The play whose speeches we want to reindex.

        """
        qs = Speech.objects.filter(scene__act__play=play)
        backend = self.get_backend(None)
        if backend is not None:
            batch_size: int = backend.batch_size
            total: int = qs.count()
            # We need to update the index in batches because we can run into
            # backend transport errors if we try to update too many documents
            # at once.
            for start in range(0, total, batch_size):
                end = min(start + batch_size, total)
                while True:
                    try:
                        backend.update(self, qs[start:end])
                    except TransportError as e:  # noqa: PERF203
                        # Check the status_code from the exception to see if we
                        # can recover from it.
                        if (
                            hasattr(e, "status_code") and e.status_code == 429  # noqa: PLR2004
                        ):
                            # We're being rate limited, so sleep and retry.
                            time.sleep(5)
                        else:
                            # Re-raise if it's not a rate limit error
                            raise
                    else:
                        break


class SpeakerIndex(indexes.SearchIndex, indexes.Indexable):
    """Search index for Speaker model."""

    #: The main document field for the speaker name
    text = indexes.CharField(document=True, model_attr="name")
    #: The name field for faceted search
    name = indexes.CharField(model_attr="name", faceted=True)
    #: The act field for faceted search
    act = indexes.MultiValueField(faceted=True)
    #: The scene field for faceted search
    scene = indexes.MultiValueField(faceted=True)
    #: The play field for faceted search
    play = indexes.MultiValueField(faceted=True)

    def get_model(self) -> Type[Model]:
        """Return the Speaker model."""
        return Speaker

    def prepare_act(self, obj: Speaker) -> List[str]:
        """
        Prepare act names for indexing.

        Returns all act names where this speaker has speeches (across all plays).

        Args:
            obj: The Speaker object being indexed.

        Returns:
            List of unique act names.

        """
        return list(obj.speeches.values_list("scene__act__name", flat=True).distinct())

    def prepare_scene(self, obj: Speaker) -> List[str]:
        """
        Prepare scene names for indexing.

        Returns all scene names where this speaker has speeches (across all plays).

        Args:
            obj: The Speaker object being indexed.

        Returns:
            List of unique scene names.

        """
        return list(obj.speeches.values_list("scene__name", flat=True).distinct())

    def prepare_play(self, obj: Speaker) -> List[str]:
        """
        Prepare play titles for indexing.

        Returns all play titles where this speaker has speeches.

        Args:
            obj: The Speaker object being indexed.

        Returns:
            List of unique play titles.

        """
        return list(
            obj.speeches.values_list("scene__act__play__title", flat=True).distinct()
        )

    def index_queryset(self, using: str | None = None) -> QuerySet:  # noqa: ARG002
        """
        Used when the entire index for model is updated.

        Keyword Args:
            using: The alias of the database to use. (unused)

        Returns:
            QuerySet of all Speaker objects.

        """
        return self.get_model().objects.all()

    def reindex_play(self, play: Play) -> None:
        """
        Reindex all speakers who have speeches in a particular play.

        Note: Since speaker facets include all appearances across all plays,
        reindexing a play requires updating all speakers who appear in that play.

        Args:
            play: The play whose speakers we want to reindex.

        """
        qs = Speaker.objects.filter(speeches__scene__act__play=play).distinct()
        backend = self.get_backend(None)
        if backend is not None:
            batch_size: int = backend.batch_size
            total: int = qs.count()
            # We need to update the index in batches because we can run into
            # backend transport errors if we try to update too many documents
            # at once.
            for start in range(0, total, batch_size):
                end = min(start + batch_size, total)
                while True:
                    try:
                        backend.update(self, qs[start:end])
                    except TransportError as e:  # noqa: PERF203
                        # Check the status_code from the exception to see if we
                        # can recover from it.
                        if (
                            hasattr(e, "status_code") and e.status_code == 429  # noqa: PLR2004
                        ):
                            # We're being rate limited, so sleep and retry.
                            time.sleep(5)
                        else:
                            # Re-raise if it's not a rate limit error
                            raise
                    else:
                        break


class PlayIndex(indexes.SearchIndex, indexes.Indexable):
    """
    Search index for Play model.

    This index is used for testing various field types and features:
    - Simple model indexing
    - CharField with document=True (title as main search field)
    - Faceted CharField
    - IntegerField
    - DateTimeField
    - use_template=True for template-based document fields
    """

    #: Template-based document field for testing use_template
    text = indexes.CharField(document=True, use_template=True)
    #: Simple title field
    title = indexes.CharField(model_attr="title")
    #: Faceted title field for testing faceted CharField
    title_faceted = indexes.CharField(model_attr="title", faceted=True)
    #: IntegerField for testing integer mapping
    play_id = indexes.IntegerField(model_attr="id")
    #: DateTimeField for date operations
    created = indexes.DateTimeField(model_attr="created")

    def get_model(self) -> Type[Model]:
        """Return the Play model."""
        return Play

    def index_queryset(self, using: str | None = None) -> QuerySet:  # noqa: ARG002
        """
        Used when the entire index for model is updated.

        Keyword Args:
            using: The alias of the database to use. (unused)

        Returns:
            QuerySet of all Play objects.

        """
        return self.get_model().objects.all()


def reindex_all() -> None:
    """
    Reindex all plays in the database.

    This function iterates through all Play objects and calls reindex_play()
    on both SpeechIndex and SpeakerIndex for each play.

    Errors are logged but do not stop the reindexing process.

    """
    speech_index = SpeechIndex()
    speaker_index = SpeakerIndex()

    for play in Play.objects.all():
        try:
            speech_index.reindex_play(play)
            speaker_index.reindex_play(play)
        except Exception:  # noqa: PERF203
            # Log error but continue with next play
            logger.exception("Error reindexing play %s", play.title)
