from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable

from gtts import gTTS
from pydub import AudioSegment


__version__ = "0.2.0"
LOGGER = logging.getLogger(__name__)
DEFAULT_SET_START_GAP_SECONDS = 1.0
DEFAULT_COUNTDOWN_GAP_SECONDS = 1.0
SUPPORTED_OUTPUT_FORMATS = ("mp3", "wav")


@dataclass(frozen=True)
class WorkoutConfig:
    reps: int
    sets: int
    rep_gap: float
    set_gap: float
    output_file: Path | None
    output_format: str | None
    language: str
    cache_dir: Path
    use_cache: bool
    countdown: int
    announce_rest: bool
    set_start_gap: float
    preview: bool
    script_file: Path | None
    tts_attempts: int
    tts_initial_backoff: float


@dataclass(frozen=True)
class WorkoutStep:
    spoken_text: str | None
    gap_after: float = 0.0


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be 0 or greater")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return parsed


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be 0 or greater")
    return parsed


def default_cache_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "workout-audio-coach"
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "workout-audio-coach"
    return Path.home() / ".cache" / "workout-audio-coach"


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or preview a guided workout audio file."
    )
    parser.add_argument(
        "--reps",
        type=positive_int,
        required=True,
        help="The number of reps in each set.",
    )
    parser.add_argument(
        "--sets",
        type=positive_int,
        required=True,
        help="The number of sets.",
    )
    parser.add_argument(
        "--rep-gap",
        "--rep_gap",
        dest="rep_gap",
        type=non_negative_float,
        required=True,
        help="The gap between reps in seconds.",
    )
    parser.add_argument(
        "--set-gap",
        "--set_gap",
        dest="set_gap",
        type=non_negative_float,
        required=True,
        help="The gap between sets in seconds.",
    )
    parser.add_argument(
        "--output-file",
        "--output_file",
        dest="output_file",
        type=Path,
        help="The output audio file name. Optional for preview-only runs.",
    )
    parser.add_argument(
        "--format",
        choices=SUPPORTED_OUTPUT_FORMATS,
        help="Output format. Defaults to the output file extension or mp3.",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language to use for gTTS speech synthesis.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=default_cache_dir(),
        help="Directory used to cache generated speech clips.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable the on-disk speech cache for this run.",
    )
    parser.add_argument(
        "--countdown",
        type=non_negative_int,
        default=3,
        help="Countdown seconds spoken before the first set. Use 0 to disable.",
    )
    parser.add_argument(
        "--announce-rest",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Speak a rest cue before each set gap.",
    )
    parser.add_argument(
        "--set-start-gap",
        type=non_negative_float,
        default=DEFAULT_SET_START_GAP_SECONDS,
        help="Pause in seconds between the set announcement and the first rep.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print the workout script instead of only writing audio.",
    )
    parser.add_argument(
        "--script-file",
        type=Path,
        help="Write the workout script preview to a text file.",
    )
    parser.add_argument(
        "--tts-attempts",
        type=positive_int,
        default=3,
        help="Maximum speech synthesis attempts for each phrase.",
    )
    parser.add_argument(
        "--tts-backoff",
        type=positive_float,
        default=1.0,
        help="Initial retry backoff in seconds for speech synthesis.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def resolve_output_format(output_file: Path | None, explicit_format: str | None) -> str | None:
    if output_file is None:
        if explicit_format:
            raise ValueError("--format requires --output-file")
        return None

    if explicit_format:
        return explicit_format

    suffix = output_file.suffix.lower().lstrip(".")
    if suffix in SUPPORTED_OUTPUT_FORMATS:
        return suffix
    return "mp3"


def build_config(args: argparse.Namespace) -> WorkoutConfig:
    if args.output_file is None and not args.preview and args.script_file is None:
        raise ValueError(
            "either --output-file or one of --preview/--script-file is required"
        )

    return WorkoutConfig(
        reps=args.reps,
        sets=args.sets,
        rep_gap=args.rep_gap,
        set_gap=args.set_gap,
        output_file=args.output_file,
        output_format=resolve_output_format(args.output_file, args.format),
        language=args.language,
        cache_dir=args.cache_dir,
        use_cache=not args.no_cache,
        countdown=args.countdown,
        announce_rest=args.announce_rest,
        set_start_gap=args.set_start_gap,
        preview=args.preview,
        script_file=args.script_file,
        tts_attempts=args.tts_attempts,
        tts_initial_backoff=args.tts_backoff,
    )


def phrase_cache_path(cache_dir: Path, phrase: str, language: str) -> Path:
    digest = hashlib.sha256(f"{language}\0{phrase}".encode("utf-8")).hexdigest()
    return cache_dir / f"{digest}.mp3"


def audio_segment_from_mp3_bytes(audio_bytes: bytes) -> AudioSegment:
    return AudioSegment.from_file(BytesIO(audio_bytes), format="mp3")


def synthesize_phrase(
    phrase: str,
    language: str,
    *,
    attempts: int = 3,
    initial_backoff_seconds: float = 1.0,
    tts_factory=gTTS,
    sleep_fn=time.sleep,
) -> bytes:
    delay = initial_backoff_seconds
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            buffer = BytesIO()
            tts_factory(text=phrase, lang=language).write_to_fp(buffer)
            return buffer.getvalue()
        except Exception as exc:  # pragma: no cover - network/library failure path
            last_error = exc
            if attempt == attempts:
                break
            LOGGER.warning(
                "Speech synthesis failed for %r on attempt %s/%s; retrying in %.1fs",
                phrase,
                attempt,
                attempts,
                delay,
            )
            sleep_fn(delay)
            delay *= 2

    raise RuntimeError(f"Unable to synthesize speech for {phrase!r}") from last_error


def load_or_generate_segment(
    phrase: str,
    language: str,
    cache_dir: Path,
    *,
    use_cache: bool = True,
    attempts: int = 3,
    initial_backoff_seconds: float = 1.0,
    tts_factory=gTTS,
    sleep_fn=time.sleep,
) -> AudioSegment:
    cache_path = phrase_cache_path(cache_dir, phrase, language)
    if use_cache and cache_path.exists():
        LOGGER.debug("Loaded cached speech for %r from %s", phrase, cache_path)
        return audio_segment_from_mp3_bytes(cache_path.read_bytes())

    audio_bytes = synthesize_phrase(
        phrase,
        language,
        attempts=attempts,
        initial_backoff_seconds=initial_backoff_seconds,
        tts_factory=tts_factory,
        sleep_fn=sleep_fn,
    )
    if use_cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(audio_bytes)
        LOGGER.debug("Cached speech for %r at %s", phrase, cache_path)
    return audio_segment_from_mp3_bytes(audio_bytes)


def build_workout_plan(config: WorkoutConfig) -> list[WorkoutStep]:
    plan: list[WorkoutStep] = []

    if config.countdown > 0:
        countdown_phrases = ["Starting in"] + [
            str(number) for number in range(config.countdown, 0, -1)
        ]
        for index, phrase in enumerate(countdown_phrases):
            gap_after = DEFAULT_COUNTDOWN_GAP_SECONDS
            if index == len(countdown_phrases) - 1:
                gap_after = 0.0
            plan.append(WorkoutStep(spoken_text=phrase, gap_after=gap_after))

    for set_number in range(1, config.sets + 1):
        plan.append(WorkoutStep(spoken_text=f"Set {set_number}", gap_after=config.set_start_gap))
        for rep_number in range(1, config.reps + 1):
            gap_after = config.rep_gap if rep_number < config.reps else 0.0
            plan.append(WorkoutStep(spoken_text=str(rep_number), gap_after=gap_after))

        if set_number < config.sets:
            if config.announce_rest:
                plan.append(WorkoutStep(spoken_text="Rest", gap_after=config.set_gap))
            elif config.set_gap > 0:
                plan.append(WorkoutStep(spoken_text=None, gap_after=config.set_gap))

    plan.append(WorkoutStep(spoken_text="Workout complete"))
    return plan


def format_workout_plan(config: WorkoutConfig, plan: list[WorkoutStep]) -> str:
    spoken_cues = sum(1 for step in plan if step.spoken_text is not None)
    total_silence = sum(step.gap_after for step in plan)
    lines = [
        "Workout Audio Coach plan",
        f"Sets x reps: {config.sets} x {config.reps}",
        f"Spoken cues: {spoken_cues}",
        f"Programmed silence: {total_silence:g}s",
        "",
    ]

    for index, step in enumerate(plan, start=1):
        label = step.spoken_text or "[silence]"
        if step.gap_after > 0:
            lines.append(f"{index:02d}. {label} [gap {step.gap_after:g}s]")
        else:
            lines.append(f"{index:02d}. {label}")

    return "\n".join(lines)


def build_workout_audio(config: WorkoutConfig) -> AudioSegment:
    plan = build_workout_plan(config)
    unique_phrases = list(
        dict.fromkeys(step.spoken_text for step in plan if step.spoken_text is not None)
    )
    rendered_phrases = {
        phrase: load_or_generate_segment(
            phrase,
            config.language,
            config.cache_dir,
            use_cache=config.use_cache,
            attempts=config.tts_attempts,
            initial_backoff_seconds=config.tts_initial_backoff,
        )
        for phrase in unique_phrases
    }

    combined = AudioSegment.empty()
    for step in plan:
        if step.spoken_text is not None:
            combined += rendered_phrases[step.spoken_text]
        if step.gap_after > 0:
            combined += AudioSegment.silent(duration=int(step.gap_after * 1000))

    return combined


def maybe_write_script_preview(config: WorkoutConfig, plan: list[WorkoutStep]) -> str:
    preview_text = format_workout_plan(config, plan)
    if config.preview:
        print(preview_text)
    if config.script_file is not None:
        config.script_file.parent.mkdir(parents=True, exist_ok=True)
        config.script_file.write_text(preview_text + "\n", encoding="utf-8")
    return preview_text


def create_combined_audio(args: argparse.Namespace | WorkoutConfig) -> Path | None:
    config = args if isinstance(args, WorkoutConfig) else build_config(args)
    plan = build_workout_plan(config)
    maybe_write_script_preview(config, plan)

    if config.output_file is None:
        LOGGER.info("Preview-only run completed without audio export.")
        return None

    LOGGER.info(
        "Generating workout audio: %s sets x %s reps to %s",
        config.sets,
        config.reps,
        config.output_file,
    )
    combined_audio = build_workout_audio(config)
    config.output_file.parent.mkdir(parents=True, exist_ok=True)
    combined_audio.export(config.output_file, format=config.output_format)
    LOGGER.info("Audio file created: %s", config.output_file)
    return config.output_file


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    try:
        create_combined_audio(args)
    except ValueError as exc:
        parser.error(str(exc))

