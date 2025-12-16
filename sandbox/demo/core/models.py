from typing import ClassVar

from django.db import models


class Play(models.Model):
    """Represents a play."""

    title = models.CharField(max_length=255)

    class Meta:
        ordering: ClassVar[list[str]] = ["title"]
        verbose_name: ClassVar[str] = "play"
        verbose_name_plural: ClassVar[str] = "plays"

    def __str__(self):
        return self.title


class Act(models.Model):
    """Represents an act (including Prologue as order=0)."""

    play = models.ForeignKey(Play, on_delete=models.CASCADE, related_name="acts")
    name = models.CharField(max_length=100)
    order = models.IntegerField()

    class Meta:
        ordering: ClassVar[list[str]] = ["play", "order"]
        unique_together: ClassVar[list[list[str]]] = [["play", "order"]]
        verbose_name: ClassVar[str] = "act"
        verbose_name_plural: ClassVar[str] = "acts"

    def __str__(self):
        return f"{self.play.title} - {self.name}"


class Scene(models.Model):
    """Represents a scene within an act."""

    act = models.ForeignKey(Act, on_delete=models.CASCADE, related_name="scenes")
    name = models.CharField(max_length=100)
    order = models.IntegerField()

    class Meta:
        ordering: ClassVar[list[str]] = ["act", "order"]
        unique_together: ClassVar[list[list[str]]] = [["act", "order"]]
        verbose_name: ClassVar[str] = "scene"
        verbose_name_plural: ClassVar[str] = "scenes"

    def __str__(self):
        return f"{self.act} - {self.name}"


class Speaker(models.Model):
    """Represents a character/speaker."""

    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["name"]
        verbose_name: ClassVar[str] = "speaker"
        verbose_name_plural: ClassVar[str] = "speakers"

    def __str__(self):
        return self.name


class Speech(models.Model):
    """Represents a single speech by a speaker in a scene."""

    speaker = models.ForeignKey(
        Speaker, on_delete=models.CASCADE, related_name="speeches"
    )
    scene = models.ForeignKey(Scene, on_delete=models.CASCADE, related_name="speeches")
    text = models.TextField()
    order = models.IntegerField()

    class Meta:
        ordering: ClassVar[list[str]] = ["scene", "order"]
        verbose_name: ClassVar[str] = "speech"
        verbose_name_plural: ClassVar[str] = "speeches"

    def __str__(self):
        return f"{self.speaker.name} in {self.scene} (order {self.order})"
