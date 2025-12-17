from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import django.db.utils
from django.db.models import Max

from demo.core.models import Act, Play, Scene, Speaker, Speech
from demo.logging import logger


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
    #: The order of the scene within the act.
    order: int
    #: The speeches in the scene.
    speeches: list[SpeechData] = field(default_factory=list)


@dataclass
class ActData:
    """Represents an act within a play."""

    #: The name of the act.
    name: str
    #: The order of the act within the play.
    order: int
    #: The scenes in the act.
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

    #: The play data.
    play_data: PlayData
    #: The current act.
    current_act: ActData | None = None
    #: The current scene.
    current_scene: SceneData | None = None
    #: The current speech lines.
    current_speech_lines: list[str] = field(default_factory=list)
    #: The current act order number in the play.
    act_order: int = 0
    #: The current scene order number in its act.
    scene_order: int = 0
    #: The current speech order number in its scene.
    speech_order: int = 0

    @classmethod
    def new(cls, title: str) -> ParserState:
        """
        Create initial parser state.

        Args:
            title: Title of the play.

        Returns:
            New ParserState instance with default values.

        """
        return cls(play_data=PlayData(title=title))

    @property
    def play(self) -> PlayData:
        """
        Get the play data.

        Returns:
            PlayData containing the play data.

        """
        return self.play_data

    def add_act(self, act: ActData) -> None:
        """
        Reset state when starting a new act.

        Args:
            act: New act data.
            order: Order number of the new act.

        """
        self.current_act = act
        self.current_scene = None
        self.current_speaker = None
        self.current_speech_lines = []
        self.act_order += 1
        self.scene_order = 0
        self.speech_order = 0
        self.play_data.acts.append(act)
        act.order = self.act_order

    def add_scene(self, scene: SceneData) -> None:
        """
        Reset state when starting a new scene.

        Args:
            scene: New scene data.
            order: Order number of the new scene.

        """
        self.current_scene = scene
        self.current_speaker = None
        self.current_speech_lines = []
        self.scene_order += 1
        self.speech_order = 0
        self.current_act.scenes.append(scene)
        scene.order = self.scene_order

    def add_speech(self, speech: SpeechData) -> None:
        """
        Add a speech to the current scene.

        Args:
            speech: The speech data to add.

        """
        if not self.current_scene:
            scene = SceneData(name=f"Act {self.current_act.order} Prologue", order=0)
            self.add_scene(scene)
            self.current_scene = scene
            self.scene_order += 1
        self.current_scene.speeches.append(speech)
        self.speech_order += 1
        speech.order = self.speech_order


class PlayImporter:
    """
    Import a play text file in the standard format used by the `Folger
    Shakespeare Library <https://shakespeare.folger.edu/shakespeares-works/>`_.


    Important:
        You'll want to download the file as text and save it as a .txt file, and
        then you'll want to prepare the file by removing all before the first
        ACT or PROLOGUE marker.

    Args:
        input_file_path: Path to the input play text file.
        title: Title of the play.

    Keyword Args:
        output_fixture_path: Path to the output fixture file.
        dry_run: Whether to run in dry run mode.

    """

    #: The number of lines required for a heading chunk.
    HEADING_LINES: Final[int] = 2
    #: The regex pattern for a prologue marker.
    PROLOGUE_MARKER_REGEX: Final[re.Pattern[str]] = re.compile(
        r"^PROLOGUE$", re.IGNORECASE
    )
    #: The regex pattern for a act marker.
    ACT_MARKER_REGEX: Final[re.Pattern[str]] = re.compile(r"^ACT (\d+)$")
    #: The regex pattern for a scene marker.
    SCENE_MARKER_REGEX: Final[re.Pattern[str]] = re.compile(r"^Scene (\d+)$")
    #: Regex pattern for a stage direction block.
    STAGE_DIRECTION_BLOCK_REGEX: Final[re.Pattern[str]] = re.compile(
        r"^\[.*\]$", re.DOTALL | re.MULTILINE
    )
    #: Regex pattern for the first line of a speech.
    SPEECH_FIRST_LINE_REGEX: Final[re.Pattern[str]] = re.compile(
        r"""^
            ([A-Z]+(?:\s+[A-Z]+)*)      # speaker
            ,?                          # optional comma
            (?:                         # optional remainder
                (?=.*[ \t]{2,})         # ← if a real separator exists later
                \s*(.*)                 #   treat everything as dialogue
            |                           # otherwise
                \s*(\[[^\]]*\])         #   stage-only line
            )?
            $
        """,
        re.VERBOSE,
    )

    def __init__(
        self,
        input_file_path: Path,
        title: str | None = None,
        output_fixture_path: Path | None = None,
        dry_run: bool = False,
    ):
        self.input_file_path = input_file_path
        self.title = title
        self.output_fixture_path = output_fixture_path
        self.dry_run = dry_run

    def run(self) -> tuple[Play | None, bool]:
        """
        Import a play text file in the standard format.

        Raises:
            FileNotFoundError: If the input file is not found.

        Returns:
            tuple[Play, bool] | None: A tuple containing the created or retrieved play
            and a boolean indicating if a new play was created.

        """
        if not self.input_file_path.exists():
            msg = f"File not found: {self.input_file_path}"
            raise FileNotFoundError(msg)

        play_data = self.parse()

        play = None
        created = False
        if not self.dry_run:
            play, created = self.save_to_database(play_data)
        return play, created

    def parse(self) -> PlayData:
        """
        Parse the play text file and return structured data.

        Returns:
            PlayData containing parsed play data with title and acts.

        """
        with self.input_file_path.open(encoding="utf-8") as f:
            text = f.read()

        # Look through text and split into chunks based on empty lines
        # and lines that start with [ (stage direction).
        # The second regex is a lookahead to split on lines that start with [,
        # importantly WHILE keeping the [ in the chunk.
        chunks = re.split(r"\n{2,}|\n(?=\[)", text)
        # Now loop through the chunks, updating the state to mark
        # which act, scene, and speech we're currently parsing.
        state = ParserState.new(self.title)
        for chunk in chunks:
            lines = chunk.splitlines()
            # Check if chunk is a prologue
            if prologue := self.extract_prologue(lines):
                state.add_act(prologue)
            # Check if chunk is an act
            elif act := self.extract_act(lines):
                state.add_act(act)
            # Check if chunk is a scene
            elif scene := self.extract_scene(lines):
                state.add_scene(scene)
            elif stage_direction := self.extract_stage_direction(chunk):
                state.add_speech(stage_direction)
            elif speech := self.extract_speech(chunk):
                state.add_speech(speech)
            else:
                speech = self.extract_bare_text(chunk, state)
                state.add_speech(speech)
        return state.play

    def is_heading_chunk(self, lines: str) -> bool:
        """
        Check if a text chunk is a heading chunk.

        Heading chunks have these characteristics:

        * There are two and only two lines.
        * The first line is the heading name.
        * The second line is an underline (all '=' characters).

        Args:
            lines: List of lines to check.

        Returns:
            True if chunk is a heading chunk, False otherwise.

        """
        if len(lines) != self.HEADING_LINES:
            return False
        next_line = lines[1].strip()
        return bool(self.is_underline_line(next_line))

    def is_underline_line(self, line: str) -> bool:
        """
        Check if line is an underline marker (all '=' characters).

        Args:
            line: Line to check.

        Returns:
            True if line is an underline, False otherwise.

        """
        return line and all(c == "=" for c in line)

    def extract_prologue(self, lines: list[str]) -> ActData | None:
        """
        Check if a text chhnk is a PROLOGUE marker.

        A Prologue intro will look like this::

            PROLOGUE
            ========

        * Two and only two lines are expected.
        * The first line must be "PROLOGUE" (case-sensitive).
        * The second line must be an underline (all '=' characters).

        Args:
            lines: List of lines to check.

        Returns:
            ActData if chunk is PROLOGUE marker, None otherwise.

        """
        if not self.is_heading_chunk(lines):
            return None
        line = lines[0].strip()
        if line.upper() == "PROLOGUE":
            act = ActData(name="Prologue", order=0)
            act.scenes.append(SceneData(name="Prologue", order=0))
            return act
        return None

    def extract_act(self, lines: list[str]) -> ActData | None:
        """
        Check if line is an ACT marker.

        An Act will look like this::

            ACT 1
            =====

        * Two and only two lines are expected.
        * The first line must be "ACT", with a space and then a number.
        * The second line must be an underline (all '=' characters).

        Args:
            lines: List of lines to check.

        Returns:
            ActData if lines is ACT marker, None otherwise.

        """
        if not self.is_heading_chunk(lines):
            return None
        line = lines[0].strip().upper()
        if act_match := self.ACT_MARKER_REGEX.search(line):
            return ActData(name=line, order=int(act_match.group(1)))
        return None

    def extract_scene(self, lines: list[str]) -> SceneData | None:
        """
        Check if line is a Scene marker.

        A Scene marker will look like this::

            Scene 1
            =======

        * Two and only two lines are expected.
        * The first line must be "Scene", with a space and then a number.
        * The second line must be an underline (all '=' characters).

        Args:
            lines: List of lines to check.

        Returns:
            SceneData if chunk is Scene marker, None otherwise.

        """
        if not self.is_heading_chunk(lines):
            return None
        line = lines[0].strip()
        if scene_match := self.SCENE_MARKER_REGEX.search(line):
            return SceneData(name=line, order=int(scene_match.group(1)))
        return None

    def extract_stage_direction(self, chunk: str) -> SpeechData | None:
        """
        Check if line is a stage direction (enclosed in brackets).

        A stage direction block could look like any of the following:

        * ``[Enter Chorus as Prologue.]``
        * ``[Enter the two Bishops of Canterbury and Ely.]``
        * ``[Enter the King of England, Humphrey Duke of
            Gloucester, Bedford, Clarence, Warwick, Westmoreland,
            and Exeter, with other Attendants.]  Note: this spans multiple lines.
        * ``[Enter Ambassadors of France, with Attendants.
            ]``  Note: this spans multiple lines.
        * [They exit.]

        Note:
            We return a SpeechData object with the speaker "Stage Directions"
            and the text of the stage direction block.  The order must be set by
            the caller.

        Args:
            chunk: Text chunk to check.

        Returns:
            True if line is stage direction, False otherwise.

        """
        if match := self.STAGE_DIRECTION_BLOCK_REGEX.search(chunk):
            return SpeechData(
                speaker="Stage Directions",
                text=match.group(0),
                order=0,
            )
        return None

    def extract_speech(self, chunk: str) -> SpeechData | None:
        """
        Check if the chunk is a speech. If so, extract the speaker's name and
        the speech text, and return a SpeechData object. Otherwise, return None.

        A speech has the following characteristics:

        * A speech MUST contain at least one line.
        * A speech MUST contain a speaker's name.
        * The speaker's name MUST be the first word(s) in the first line.
        * The speaker's name MUST be in all caps.
        * The speaker's name MUST be followed either by a comma and a space,
          OR by two spaces.
        * If it is a comma and a space, then the next bit of text are stage
          directions, after which will be two spaces before the speech text.

        Example:
            Speaker and speech text all on one line::

                BISHOP OF ELY  We are blessed in the change.

            Here "BISHOP OF ELY" is the speaker's name and "We are blessed in
            the change." is the speech text.  Note that between "ELY" and "We"
            there are two spaces.

            For this example, the SpeechData object would be::

            .. code-block:: python

                SpeechData(
                    speaker="BISHOP OF ELY",
                    text="We are blessed in the change.",
                    order=0,
                )

        Example:
            Speaker and speech text that starts on the line after the speaker's name
            and continues on the next line(s)::

                BISHOP OF CANTERBURY  'Twould drink the cup and
                all.

            For this example, the SpeechData object would be::

            .. code-block:: python

                SpeechData(
                    speaker="BISHOP OF CANTERBURY",
                    text="'Twould drink the cup and all.",
                    order=0,
                )

        Example:
            Speaker and speech text on separate lines::

                BISHOP OF ELY
                We are blessed in the change.

            For this example, the SpeechData object would be::

            .. code-block:: python

                SpeechData(
                    speaker="BISHOP OF ELY",
                    text="We are blessed in the change.",
                    order=0,
                )

            Another example::

                BISHOP OF ELY
                The strawberry grows underneath the nettle,
                And wholesome berries thrive and ripen best
                Neighbored by fruit of baser quality;
                And so the Prince obscured his contemplation
                Under the veil of wildness, which, no doubt,
                Grew like the summer grass, fastest by night,
                Unseen yet crescive in his faculty.

            For this example, the SpeechData object would be::

                .. code-block:: python

                    SpeechData(
                        speaker="BISHOP OF ELY",
                        text="The strawberry grows underneath the nettle,\nAnd wholesome berries thrive and ripen best\nNeighbored by fruit of baser quality;\nAnd so the Prince obscured his contemplation\nUnder the veil of wildness, which, no doubt,\nGrew like the summer grass, fastest by night,\nUnseen yet crescive in his faculty.",
                        order=0,
                    )

            Here "BISHOP OF ELY" is the speaker's name and "We are blessed in
            the change." is the speech text.

        Example:
            Sometimes there will be stage directions between the speaker's name
            and the speech text. For example, the following is a valid speech::

                BISHOP OF ELY, [Enter the King of England]  We are blessed
                in the change.

            For this example, the SpeechData object would be::

            .. code-block:: python

                SpeechData(
                    speaker="BISHOP OF ELY",
                    text="[Enter the King of England]  We are blessed in the change.",
                    order=0,
                )

        Args:
            chunk: Text chunk to check.

        Returns:
            SpeechData if chunk is a speech, None otherwise.

        """  # noqa: D301, E501
        # Remove trailing spaces from all lines
        lines = [line.rstrip() for line in chunk.splitlines()]
        if not lines:
            return None

        first_line = lines[0]
        if not first_line.strip():
            return None

        # Regex: Match leading all-caps words (optionally multi-word), then
        # optional separator, then rest of line
        match = self.SPEECH_FIRST_LINE_REGEX.match(first_line)
        if not match:
            return None

        speaker = match.group(1)
        first_line_speech = (match.group(2) or "").strip()

        speech_lines = []
        if first_line_speech:
            speech_lines.append(first_line_speech)
        # Remaining lines are always part of the speech text (if present)
        if len(lines) > 1:
            speech_lines.extend(line for line in lines[1:] if line.strip() != "")

        speech_text = "\n".join(speech_lines)
        if not speech_text:
            return None

        return SpeechData(
            speaker=speaker,
            text=speech_text,
            order=0,
        )

    def extract_bare_text(self, chunk: str, state: ParserState) -> SpeechData:
        """
        Very occasionally, a speaker will begin a speech, be interrupted by a
        stage direction, and then continue the speech.  For the most part, the
        stage direction will be in the midst of the chunk, but sometimes it will
        be separated from the speech and its continuation a blank lines.

        In this case, we need to find the speaker previous to the stage
        direction, extract the speaker name, and create a new SpeechData object
        for the bare text, attaching the speaker name to the bare text.

        It's not honest to Shakepeare, but it workse better for the data model.

        Important:
            This method should appear as the last resort in the chunks processing
            loop in :meth:`parse`. so that it is only called if all other extraction
            methods fail.

        Args:
            chunk: Text chunk to check.
            state: Parser state.

        Returns:
            SpeechData object for the bare text.

        """
        # Look through state.current_scene.speeches in reverse order, looking for
        # the last speech that has a speaker name that is not "Stage Directions".
        for speech in reversed(state.current_scene.speeches):
            if speech.speaker and speech.speaker != "Stage Directions":
                return SpeechData(
                    speaker=speech.speaker,
                    text=chunk.strip(),
                    order=0,
                )
        msg = f"No speaker found for chunk: {chunk.strip()}"
        raise ValueError(msg)

    def save_to_database(self, play_data: PlayData) -> tuple[Play, bool]:
        """
        Save parsed play data to database.

        Args:
            play_data: Parsed play data structure.

        Returns:
            tuple[Play, bool]: A tuple containing the created or retrieved play
            and a boolean indicating if a new play was created.

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
        return play, created

    def generate_fixture(self, output_fixture_path: Path) -> None:
        """
        Generate Django fixture file from parsed play data.

        Args:
            output_fixture_path: Path where fixture file should be written.

        """
        play_data = self.parse()
        fixture_data = []
        try:
            play_pk_counter = Play.objects.aggregate(Max("pk"))["pk__max"] or 0
            speech_pk_counter = Speech.objects.aggregate(Max("pk"))["pk__max"] or 1
            act_pk_counter = Act.objects.aggregate(Max("pk"))["pk__max"] or 1
            scene_pk_counter = Scene.objects.aggregate(Max("pk"))["pk__max"] or 1
            speaker_pk_counter = Speaker.objects.aggregate(Max("pk"))["pk__max"] or 1
        except django.db.utils.OperationalError:
            logger.warning("play_importer.generate_fixture.no-database")
            play_pk_counter = 1
            speech_pk_counter = 1
            act_pk_counter = 1
            scene_pk_counter = 1
            speaker_pk_counter = 1
        else:
            play_pk_counter += 1
            speech_pk_counter += 1
            act_pk_counter += 1
            scene_pk_counter += 1
            speaker_pk_counter += 1

        logger.info(
            "play_importer.generate_fixture.pks",
            play_pk_counter=play_pk_counter,
            speech_pk_counter=speech_pk_counter,
            act_pk_counter=act_pk_counter,
            scene_pk_counter=scene_pk_counter,
            speaker_pk_counter=speaker_pk_counter,
        )

        # Create play
        play_pk = play_pk_counter
        fixture_data.append(
            {
                "model": "core.play",
                "pk": play_pk,
                "fields": {"title": play_data.title},
            }
        )

        # Track pks for foreign keys
        act_pks = {}
        scene_pks = {}
        speaker_pks = {}

        # Create acts
        for act_data in play_data.acts:
            act_pk = act_pk_counter
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
            act_pk_counter += 1

            # Create scenes
            for scene_data in act_data.scenes:
                scene_pk = scene_pk_counter
                scene_pks[(act_pk, scene_data.name, scene_data.order)] = scene_pk
                fixture_data.append(
                    {
                        "model": "core.scene",
                        "pk": scene_pk,
                        "fields": {
                            "play": play_pk,
                            "act": act_pk,
                            "name": scene_data.name,
                            "order": scene_data.order,
                        },
                    }
                )
                scene_pk_counter += 1

                # Create speeches
                for speech_data in scene_data.speeches:
                    speaker_name = speech_data.speaker
                    if speaker_name not in speaker_pks:
                        try:
                            speaker = Speaker.objects.get(name=speaker_name)
                        except Speaker.DoesNotExist:
                            speaker_pk = speaker_pk_counter
                            fixture_data.append(
                                {
                                    "model": "core.speaker",
                                    "pk": speaker_pk,
                                    "fields": {"name": speaker_name},
                                }
                            )
                            speaker_pk_counter += 1
                        else:
                            speaker_pk = speaker.pk
                        speaker_pks[speaker_name] = speaker_pk
                    else:
                        speaker_pk = speaker_pks[speaker_name]

                    speech_pk = speech_pk_counter
                    fixture_data.append(
                        {
                            "model": "core.speech",
                            "pk": speech_pk,
                            "fields": {
                                "speaker": speaker_pk,
                                "scene": scene_pk,
                                "text": speech_data.text,
                                "order": speech_data.order,
                            },
                        }
                    )
                    speech_pk_counter += 1

        # Write fixture file
        output_path_obj = Path(output_fixture_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        with output_path_obj.open("w", encoding="utf-8") as f:
            json.dump(fixture_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    importer = PlayImporter(
        input_file_path=Path("data/henry-v.txt"),
        title="Henry V",
        output_fixture_path=Path("/tmp/henry-v.json"),  # noqa: S108
        dry_run=False,
    )
    importer.run()
