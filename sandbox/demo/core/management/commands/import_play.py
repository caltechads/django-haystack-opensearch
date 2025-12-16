from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from demo.core.models import Act, Play, Scene, Speaker, Speech
from django.core.management.base import BaseCommand, CommandError

if TYPE_CHECKING:
    from argparse import ArgumentParser


@dataclass
class SpeechData:
    """Represents a single speech in a scene."""

    #: The name of the speaker.
    speaker: str
    #: The text of the speech.
    text: str
    #: The order number of the speech in the scene.
    order: int


@dataclass
class SceneData:
    """Represents a scene within an act."""

    #: The name of the scene.
    name: str
    #: The order of the scene.
    order: int
    #: The speeches in the scene.
    speeches: list[SpeechData] = field(default_factory=list)


@dataclass
class ActData:
    """Represents an act within a play."""

    name: str
    order: int
    scenes: list[SceneData] = field(default_factory=list)


@dataclass
class PlayData:
    """Represents the complete play data."""

    #: The title of the play.
    title: str
    #: The acts in the play.
    acts: list[ActData] = field(default_factory=list)


@dataclass
class ParserState:
    """Maintains the current parsing state."""

    #: The current act.
    current_act: ActData | None = None
    #: The current scene.
    current_scene: SceneData | None = None
    #: The current speaker.
    current_speaker: str | None = None
    #: The current speech lines.
    current_speech_lines: list[str] = field(default_factory=list)
    #: The current act order number in the play.
    act_order: int = 0
    #: The current scene order number in its act.
    scene_order: int = 0
    #: The current speech order number in its scene.
    speech_order: int = 0

    @classmethod
    def create_initial(cls) -> ParserState:
        """
        Create initial parser state.

        Returns:
            New ParserState instance with default values.

        """
        return cls()

    def reset_for_new_act(self, name: str, order: int) -> None:
        """
        Reset state when starting a new act.

        Args:
            name: Name of the new act.
            order: Order number of the new act.

        """
        self.current_act = ActData(name=name, order=order)
        self.current_scene = None
        self.current_speaker = None
        self.current_speech_lines = []
        self.act_order = order
        self.scene_order = 0
        self.speech_order = 0

    def reset_for_new_scene(self, name: str, order: int) -> None:
        """
        Reset state when starting a new scene.

        Args:
            name: Name of the new scene.
            order: Order number of the new scene.

        """
        self.current_scene = SceneData(name=name, order=order)
        self.current_speaker = None
        self.current_speech_lines = []
        self.scene_order = order
        self.speech_order = 0


@dataclass
class HandleResult:
    """Result from major handler methods (prologue, act, scene)."""

    #: The current parser state.
    state: ParserState
    #: The number of lines to skip. This is used to skip lines that are not part
    #: of the play.
    lines_to_skip: int


@dataclass
class SpeechStateResult:
    """Lightweight result for speech-related operations."""

    #: The current speaker.
    current_speaker: str | None
    #: The current speech lines.
    current_speech_lines: list[str]
    #: The current speech order number in its scene.
    speech_order: int


@dataclass
class SceneStateResult:
    """Lightweight result for scene creation operations."""

    #: The current scene.
    current_scene: SceneData | None
    #: The current scene order number in its act.
    scene_order: int
    #: The current speech order number in its scene.
    speech_order: int


class Command(BaseCommand):
    """Import a play text file in the standard format."""

    help = "Import a play text file in the standard format"

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("file_path", type=str, help="Path to the play text file")
        parser.add_argument(
            "--title",
            type=str,
            help="Title of the play (if not provided, extracted from filename)",
        )
        parser.add_argument(
            "--output-fixture",
            type=str,
            help=(
                "Output fixture file path (if provided, generates fixture instead of "
                "saving to database)"
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse without saving to database",
        )

    def handle(self, *args, **options):  # noqa: ARG002
        file_path = Path(options["file_path"])
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise CommandError(msg)

        title = options.get("title")
        if not title:
            # Extract title from filename
            title = file_path.stem.replace("-", " ").replace("_", " ").title()

        output_fixture = options.get("output_fixture")
        dry_run = options.get("dry_run", False)

        self.stdout.write(f"Parsing play: {title}")
        self.stdout.write(f"Reading from: {file_path}")

        # Parse the file
        play_data = self.parse_play_file(file_path, title)

        if output_fixture:
            self.generate_fixture(play_data, output_fixture)
            self.stdout.write(
                self.style.SUCCESS(f"Fixture generated: {output_fixture}")
            )
        elif not dry_run:
            self.save_to_database(play_data)
            self.stdout.write(self.style.SUCCESS("Play imported successfully"))
        else:
            self.stdout.write("Dry run - no data saved")

    def parse_play_file(self, file_path: Path, title: str) -> PlayData:
        """
        Parse the play text file and return structured data.

        Args:
            file_path: Path to the play text file.
            title: Title of the play.

        Returns:
            PlayData containing parsed play data with title and acts.

        """
        with file_path.open(encoding="utf-8") as f:
            lines = f.readlines()

        play_data = PlayData(title=title)
        state = ParserState.create_initial()
        i = 0

        while i < len(lines):
            line = lines[i].rstrip("\n")
            next_line = lines[i + 1].rstrip("\n") if i + 1 < len(lines) else ""

            # Check for PROLOGUE
            if self._is_prologue_marker(line, next_line):
                result = self._handle_prologue(play_data, state)
                i += result.lines_to_skip
                continue

            # Check for ACT N
            act_match = self._is_act_marker(line, next_line)
            if act_match:
                result = self._handle_act(play_data, state, act_match)
                i += result.lines_to_skip
                continue

            # Check for Scene N
            scene_match = self._is_scene_marker(line, next_line)
            if scene_match:
                result = self._handle_scene(state, scene_match)
                i += result.lines_to_skip
                continue

            # Skip stage directions (lines in [])
            if self._is_stage_direction(line):
                i += 1
                continue

            # Skip empty lines (but they might separate speakers)
            if not line.strip():
                speech_result = self._handle_empty_line(
                    lines,
                    i,
                    state.current_scene,
                    state.current_speaker,
                    state.current_speech_lines,
                    state.speech_order,
                )
                state.current_speaker = speech_result.current_speaker
                state.current_speech_lines = speech_result.current_speech_lines
                state.speech_order = speech_result.speech_order
                i += 1
                continue

            # Ensure we have a scene if we're about to process speeches
            # Some acts (like Prologue or Act 2) don't have explicit Scene markers
            if state.current_act is not None and state.current_scene is None:
                scene_result = self._ensure_scene_exists(
                    state.scene_order, state.speech_order
                )
                state.current_scene = scene_result.current_scene
                state.scene_order = scene_result.scene_order
                state.speech_order = scene_result.speech_order

            # Check if line is a speaker (ALL CAPS, possibly with speech text)
            if self._is_speaker_line(line):
                speech_result = self._handle_speaker_line(
                    line,
                    state.current_scene,
                    state.current_speaker,
                    state.current_speech_lines,
                    state.speech_order,
                )
                state.current_speaker = speech_result.current_speaker
                state.current_speech_lines = speech_result.current_speech_lines
                state.speech_order = speech_result.speech_order
            # Regular text line - part of current speech
            elif state.current_speaker and state.current_scene:
                state.current_speech_lines.append(line)

            i += 1

        # Save final speech, scene, and act
        self._finalize_play_data(play_data, state)

        return play_data

    def _is_underline_line(self, line: str) -> bool:
        """
        Check if line is an underline marker (all '=' characters).

        Args:
            line: Line to check.

        Returns:
            True if line is an underline, False otherwise.

        """
        return line and all(c == "=" for c in line)

    def _is_prologue_marker(self, line: str, next_line: str) -> bool:
        """
        Check if line is a PROLOGUE marker.

        Args:
            line: Current line to check.
            next_line: Next line (should be underline).

        Returns:
            True if line is PROLOGUE marker, False otherwise.

        """
        return line == "PROLOGUE" and self._is_underline_line(next_line)

    def _is_act_marker(self, line: str, next_line: str) -> re.Match[str] | None:
        """
        Check if line is an ACT marker.

        Args:
            line: Current line to check.
            next_line: Next line (should be underline).

        Returns:
            Match object if line is ACT marker, None otherwise.

        """
        act_match = re.match(r"^ACT (\d+)$", line)
        if act_match and self._is_underline_line(next_line):
            return act_match
        return None

    def _is_scene_marker(self, line: str, next_line: str) -> re.Match[str] | None:
        """
        Check if line is a Scene marker.

        Args:
            line: Current line to check.
            next_line: Next line (should be underline).

        Returns:
            Match object if line is Scene marker, None otherwise.

        """
        scene_match = re.match(r"^Scene (\d+)$", line)
        if scene_match and self._is_underline_line(next_line):
            return scene_match
        return None

    def _is_stage_direction(self, line):
        """
        Check if line is a stage direction (enclosed in brackets).

        Args:
            line: Line to check.

        Returns:
            True if line is stage direction, False otherwise.

        """
        stripped = line.strip()
        return stripped.startswith("[") and stripped.endswith("]")

    def _is_speaker_line(self, line: str) -> bool:
        """
        Check if line is a speaker name (ALL CAPS, not a marker or stage direction).

        Args:
            line: Line to check.

        Returns:
            True if line is a speaker, False otherwise.

        """
        stripped = line.strip()
        return (
            stripped.isupper()
            and not stripped.startswith("[")
            and not re.match(r"^(ACT|Scene|PROLOGUE)", stripped)
        )

    def _save_pending_speech(
        self,
        current_scene: SceneData | None,
        current_speaker: str | None,
        current_speech_lines: list[str],
        speech_order: int,
    ) -> int:
        """
        Save current speech to scene if it exists.

        Args:
            current_scene: Current scene data or None.
            current_speaker: Current speaker name or None.
            current_speech_lines: List of speech text lines.
            speech_order: Current speech order number.

        Returns:
            Updated speech_order (incremented if speech was saved).

        """
        if (
            current_speaker is not None
            and current_speech_lines
            and current_scene is not None
        ):
            speech_data = SpeechData(
                speaker=current_speaker,
                text="\n".join(current_speech_lines),
                order=speech_order,
            )
            current_scene.speeches.append(speech_data)
            return speech_order + 1
        return speech_order

    def _save_current_scene_to_act(
        self, current_act: ActData | None, current_scene: SceneData | None
    ) -> None:
        """
        Save current scene to act if both exist.

        Args:
            current_act: Current act data or None.
            current_scene: Current scene data or None.

        """
        if current_act is not None and current_scene is not None:
            current_act.scenes.append(current_scene)

    def _save_current_act_to_play(
        self, play_data: PlayData, current_act: ActData | None
    ) -> None:
        """
        Save current act to play data if it exists.

        Args:
            play_data: Play data structure.
            current_act: Current act data or None.

        """
        if current_act is not None:
            play_data.acts.append(current_act)

    def _ensure_scene_exists(
        self, scene_order: int, speech_order: int
    ) -> SceneStateResult:
        """
        Create a default scene if one doesn't exist.

        Args:
            scene_order: Current scene order number.
            speech_order: Current speech order number.

        Returns:
            SceneStateResult containing new scene data and updated order values.

        """
        scene_order = 1
        current_scene = SceneData(name="Scene 1", order=scene_order)
        speech_order = 0
        return SceneStateResult(
            current_scene=current_scene,
            scene_order=scene_order,
            speech_order=speech_order,
        )

    def _handle_prologue(
        self,
        play_data: PlayData,
        state: ParserState,
    ) -> HandleResult:
        """
        Handle PROLOGUE marker and transition to new prologue act.

        Args:
            play_data: Play data structure.
            state: Current parser state.

        Returns:
            HandleResult containing updated state and lines to skip.

        """
        if state.current_act is not None:
            # Save any pending speech first
            state.speech_order = self._save_pending_speech(
                state.current_scene,
                state.current_speaker,
                state.current_speech_lines,
                state.speech_order,
            )
            # Save current scene to act before saving the act
            self._save_current_scene_to_act(state.current_act, state.current_scene)
            # Save previous act
            self._save_current_act_to_play(play_data, state.current_act)

        # Reset state for new prologue act
        state.reset_for_new_act("Prologue", 0)

        return HandleResult(state=state, lines_to_skip=2)

    def _handle_act(
        self,
        play_data: PlayData,
        state: ParserState,
        act_match: re.Match[str],
    ) -> HandleResult:
        """
        Handle ACT marker and transition to new act.

        Args:
            play_data: Play data structure.
            state: Current parser state.
            act_match: Regex match object containing act number.

        Returns:
            HandleResult containing updated state and lines to skip.

        """
        if state.current_act is not None:
            # Save any pending speech first
            state.speech_order = self._save_pending_speech(
                state.current_scene,
                state.current_speaker,
                state.current_speech_lines,
                state.speech_order,
            )
            # Save current scene to act before saving the act
            self._save_current_scene_to_act(state.current_act, state.current_scene)
            # Save previous act
            self._save_current_act_to_play(play_data, state.current_act)

        # Extract act number and reset state for new act
        act_order = int(act_match.group(1))
        state.reset_for_new_act(f"Act {act_order}", act_order)

        return HandleResult(state=state, lines_to_skip=2)

    def _handle_scene(
        self,
        state: ParserState,
        scene_match: re.Match[str],
    ) -> HandleResult:
        """
        Handle Scene marker and transition to new scene.

        Args:
            state: Current parser state.
            scene_match: Regex match object containing scene number.

        Returns:
            HandleResult containing updated state and lines to skip.

        """
        new_scene_order = int(scene_match.group(1))
        # Check if we already have a scene with this order in the current act.
        # This prevents duplicates when a scene was auto-created and then
        # explicitly marked.
        if (
            state.current_scene is not None
            and state.current_act is not None
            and state.current_scene.order == new_scene_order
        ):
            # We already have this scene, save any pending speech first
            state.speech_order = self._save_pending_speech(
                state.current_scene,
                state.current_speaker,
                state.current_speech_lines,
                state.speech_order,
            )
            # Continue with existing scene (don't reset speech_order to preserve order)
            state.current_speaker = None
            state.current_speech_lines = []
            state.scene_order = new_scene_order
            return HandleResult(state=state, lines_to_skip=2)

        # Save previous speech if we have one
        if state.current_speech_lines:
            state.speech_order = self._save_pending_speech(
                state.current_scene,
                state.current_speaker,
                state.current_speech_lines,
                state.speech_order,
            )
            state.current_speech_lines = []

        # Save current scene to act
        self._save_current_scene_to_act(state.current_act, state.current_scene)

        # Reset state for new scene
        state.reset_for_new_scene(f"Scene {new_scene_order}", new_scene_order)

        return HandleResult(state=state, lines_to_skip=2)

    def _handle_empty_line(
        self,
        lines: list[str],
        i: int,
        current_scene: SceneData | None,
        current_speaker: str | None,
        current_speech_lines: list[str],
        speech_order: int,
    ) -> SpeechStateResult:
        """
        Handle empty line which may separate speakers.

        Args:
            lines: List of all lines in the file.
            i: Current line index.
            current_scene: Current scene data or None.
            current_speaker: Current speaker name or None.
            current_speech_lines: List of current speech text lines.
            speech_order: Current speech order number.

        Returns:
            SpeechStateResult containing updated speech state.

        """
        # If we have a current speech, it might be ending
        if current_speech_lines and current_speaker:
            # Check if next non-empty line is a new speaker
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                next_non_empty = lines[j].strip()
                # Check if it's a speaker (ALL CAPS, not stage direction)
                if self._is_speaker_line(next_non_empty):
                    # Save current speech and prepare for new speaker
                    speech_order = self._save_pending_speech(
                        current_scene,
                        current_speaker,
                        current_speech_lines,
                        speech_order,
                    )
                    current_speech_lines = []
                    current_speaker = None
        return SpeechStateResult(
            current_speaker=current_speaker,
            current_speech_lines=current_speech_lines,
            speech_order=speech_order,
        )

    def _handle_speaker_line(
        self,
        line: str,
        current_scene: SceneData | None,
        current_speaker: str | None,
        current_speech_lines: list[str],
        speech_order: int,
    ) -> SpeechStateResult:
        """
        Handle speaker line which may include speech text on the same line.

        Args:
            line: Current line being processed.
            current_scene: Current scene data or None.
            current_speaker: Current speaker name or None.
            current_speech_lines: List of current speech text lines.
            speech_order: Current speech order number.

        Returns:
            SpeechStateResult containing updated speech state.

        """
        # Check if there's speech text on the same line
        # Look for pattern: SPEAKER NAME  speech text (2+ spaces or tab)
        speaker_match = re.match(r"^([A-Z][A-Z\s&']+?)(?:\s{2,}|\t)(.+)$", line)
        if speaker_match:
            # Speaker name and speech on same line
            speaker_name = speaker_match.group(1).strip()
            speech_start = speaker_match.group(2)
            # Save previous speech if speaker changed
            if current_speaker and current_speaker != speaker_name:
                speech_order = self._save_pending_speech(
                    current_scene, current_speaker, current_speech_lines, speech_order
                )
                current_speech_lines = []
            current_speaker = speaker_name
            current_speech_lines.append(speech_start)
        else:
            # Just speaker name, no speech on this line
            speaker_name = line.strip()
            # Save previous speech if speaker changed
            if current_speaker and current_speaker != speaker_name:
                speech_order = self._save_pending_speech(
                    current_scene, current_speaker, current_speech_lines, speech_order
                )
                current_speech_lines = []
            current_speaker = speaker_name

        return SpeechStateResult(
            current_speaker=current_speaker,
            current_speech_lines=current_speech_lines,
            speech_order=speech_order,
        )

    def _finalize_play_data(
        self,
        play_data: PlayData,
        state: ParserState,
    ) -> None:
        """
        Save final speech, scene, and act to play data.

        Args:
            play_data: Play data structure.
            state: Current parser state.

        """
        # Save final speech
        if state.current_speech_lines and state.current_speaker and state.current_scene:
            self._save_pending_speech(
                state.current_scene,
                state.current_speaker,
                state.current_speech_lines,
                state.speech_order,
            )

        # Save final scene
        if state.current_scene and state.current_act:
            self._save_current_scene_to_act(state.current_act, state.current_scene)

        # Save final act
        if state.current_act:
            self._save_current_act_to_play(play_data, state.current_act)

    def save_to_database(self, play_data: PlayData) -> None:
        """
        Save parsed play data to database.

        Args:
            play_data: Parsed play data structure.

        """
        # Get or create play
        play, created = Play.objects.get_or_create(title=play_data.title)
        if not created:
            # Delete existing acts and related data
            play.acts.all().delete()

        # Create acts
        for act_data in play_data.acts:
            act = Act.objects.create(
                play=play, name=act_data.name, order=act_data.order
            )

            # Create scenes
            for scene_data in act_data.scenes:
                scene = Scene.objects.create(
                    act=act, name=scene_data.name, order=scene_data.order
                )

                # Create speeches
                for speech_data in scene_data.speeches:
                    speaker, _ = Speaker.objects.get_or_create(name=speech_data.speaker)
                    Speech.objects.create(
                        speaker=speaker,
                        scene=scene,
                        text=speech_data.text,
                        order=speech_data.order,
                    )

    def generate_fixture(self, play_data: PlayData, output_path: str | Path) -> None:
        """
        Generate Django fixture file from parsed play data.

        Args:
            play_data: Parsed play data structure.
            output_path: Path where fixture file should be written.

        """
        fixture_data = []
        pk_counter = 1

        # Create play
        play_pk = pk_counter
        fixture_data.append(
            {
                "model": "core.play",
                "pk": play_pk,
                "fields": {"title": play_data.title},
            }
        )
        pk_counter += 1

        # Track pks for foreign keys
        act_pks = {}
        scene_pks = {}
        speaker_pks = {}

        # Create acts
        for act_data in play_data.acts:
            act_pk = pk_counter
            act_pks[(act_data.name, act_data.order)] = act_pk
            fixture_data.append(
                {
                    "model": "core.act",
                    "pk": act_pk,
                    "fields": {
                        "play": play_pk,
                        "name": act_data.name,
                        "order": act_data.order,
                    },
                }
            )
            pk_counter += 1

            # Create scenes
            for scene_data in act_data.scenes:
                scene_pk = pk_counter
                scene_pks[(act_pk, scene_data.name, scene_data.order)] = scene_pk
                fixture_data.append(
                    {
                        "model": "core.scene",
                        "pk": scene_pk,
                        "fields": {
                            "act": act_pk,
                            "name": scene_data.name,
                            "order": scene_data.order,
                        },
                    }
                )
                pk_counter += 1

                # Create speeches
                for speech_data in scene_data.speeches:
                    speaker_name = speech_data.speaker
                    if speaker_name not in speaker_pks:
                        speaker_pk = pk_counter
                        speaker_pks[speaker_name] = speaker_pk
                        fixture_data.append(
                            {
                                "model": "core.speaker",
                                "pk": speaker_pk,
                                "fields": {"name": speaker_name},
                            }
                        )
                        pk_counter += 1
                    else:
                        speaker_pk = speaker_pks[speaker_name]

                    fixture_data.append(
                        {
                            "model": "core.speech",
                            "pk": pk_counter,
                            "fields": {
                                "speaker": speaker_pk,
                                "scene": scene_pk,
                                "text": speech_data.text,
                                "order": speech_data.order,
                            },
                        }
                    )
                    pk_counter += 1

        # Write fixture file
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        with output_path_obj.open("w", encoding="utf-8") as f:
            json.dump(fixture_data, f, indent=2, ensure_ascii=False)
