from __future__ import annotations

import logging
import time
from typing import List, Type  # noqa: UP035

from opensearchpy.exceptions import TransportError

from django.db.models import Model, QuerySet
from haystack import indexes

from demo.core.models import Play, Speaker, Speech

logger = logging.getLogger(__name__)


class SpeechIndex(indexes.SearchIndex, indexes.Indexable):
    """Search index for Speech model."""

    text = indexes.CharField(document=True, model_attr="text")
    speaker_name = indexes.CharField(model_attr="speaker__name", faceted=True)
    speaker_id = indexes.IntegerField(model_attr="speaker__id")
    act_name = indexes.CharField(model_attr="scene__act__name", faceted=True)
    scene_name = indexes.CharField(model_attr="scene__name", faceted=True)
    play_title = indexes.CharField(model_attr="scene__act__play__title", faceted=True)
    play_id = indexes.IntegerField(model_attr="scene__act__play__id")

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
                    except TransportError as e:
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

    text = indexes.CharField(document=True, model_attr="name")
    name = indexes.CharField(model_attr="name", faceted=True)
    act = indexes.MultiValueField(faceted=True)
    scene = indexes.MultiValueField(faceted=True)
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
                    except TransportError as e:
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
