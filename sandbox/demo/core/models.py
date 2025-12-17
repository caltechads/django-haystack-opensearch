from typing import ClassVar

from django.db import models
from django.utils import timezone


class Play(models.Model):
    """Represents a play."""

    title = models.CharField(max_length=255, help_text="The title of the play.")
    created = models.DateTimeField(
        default=timezone.now, help_text="The date and time the play was created."
    )

    class Meta:
        ordering: ClassVar[list[str]] = ["title"]
        verbose_name: ClassVar[str] = "play"
        verbose_name_plural: ClassVar[str] = "plays"

    def __str__(self) -> str:
        return self.title


class Act(models.Model):
    """Represents an act (including Prologue as order=0)."""

    play = models.ForeignKey(
        Play,
        on_delete=models.CASCADE,
        related_name="acts",
        help_text="The play this act belongs to.",
    )
    name = models.CharField(max_length=100, help_text="The name of the act.")
    order = models.IntegerField(help_text="The order of the act within the play.")

    class Meta:
        ordering: ClassVar[list[str]] = ["play", "order"]
        unique_together: ClassVar[list[list[str]]] = [["play", "order"]]
        verbose_name: ClassVar[str] = "act"
        verbose_name_plural: ClassVar[str] = "acts"

    def __str__(self) -> str:
        return f"{self.play.title} - {self.name}"


class Scene(models.Model):
    """Represents a scene within an act."""

    play = models.ForeignKey(
        Play,
        on_delete=models.CASCADE,
        null=True,
        related_name="scenes",
        help_text="The play this scene belongs to.",
    )
    act = models.ForeignKey(
        Act,
        on_delete=models.CASCADE,
        related_name="scenes",
        help_text="The act this scene belongs to.",
    )
    name = models.CharField(max_length=100, help_text="The name of the scene.")
    order = models.IntegerField(help_text="The order of the scene within the act.")

    class Meta:
        ordering: ClassVar[list[str]] = ["act", "order"]
        unique_together: ClassVar[list[list[str]]] = [["play", "act", "order"]]
        verbose_name: ClassVar[str] = "scene"
        verbose_name_plural: ClassVar[str] = "scenes"

    def __str__(self) -> str:
        return f"{self.play} - {self.act.name} - {self.name}"

    def save(self, *args, **kwargs):
        """
        Set the play to the act's play.

        We need to set the play on this model so we can use it in the unique
        together constraint.  In Django, unique_together constraints cannot
        reference FKs of FKs  ``play`` is an FK of ``act``, but we want our
        constraint to enforce that play, act, and order are unique together,
        so we need to set the play on this model before saving.

        """
        self.play = self.act.play
        super().save(*args, **kwargs)


class Speaker(models.Model):
    """Represents a character/speaker."""

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="The name of the speaker.",
    )

    class Meta:
        ordering: ClassVar[list[str]] = ["name"]
        verbose_name: ClassVar[str] = "speaker"
        verbose_name_plural: ClassVar[str] = "speakers"

    def __str__(self) -> str:
        return self.name


class Speech(models.Model):
    """Represents a single speech by a speaker in a scene."""

    speaker = models.ForeignKey(
        Speaker,
        on_delete=models.CASCADE,
        related_name="speeches",
        help_text="The speaker who gave the speech.",
    )
    scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="speeches",
        help_text="The scene where the speech took place.",
    )
    text = models.TextField(help_text="The text of the speech.")
    order = models.IntegerField(help_text="The order of the speech within the scene.")
    created_date = models.DateTimeField(
        default=timezone.now,
        help_text="The date and time the speech was created.",
    )
    is_soliloquy = models.BooleanField(
        default=False,
        help_text="Whether the speech is a soliloquy.",
    )

    class Meta:
        ordering: ClassVar[list[str]] = ["scene", "order"]
        verbose_name: ClassVar[str] = "speech"
        verbose_name_plural: ClassVar[str] = "speeches"

    def __str__(self):
        return f"{self.speaker.name} in {self.scene} (order {self.order})"

    @property
    def speech_length(self) -> float:
        """Return the length of the speech text as a float."""
        return float(len(self.text))
