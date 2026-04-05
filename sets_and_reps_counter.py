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
    output_file: Path
    output_format: str
    language: str
    cache_dir: Path
    use_cache: bool
    countdown: int
    announce_rest: bool
    set_start_gap: float


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


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be 0 or greater")
    return parsed


def default_cache_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "sets-and-reps-counter"
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "sets-and-reps-counter"
    return Path.home() / ".cache" / "sets-and-reps-counter"


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a guided sets and reps audio file."
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
        required=True,
        help="The output audio file name.",
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
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser


def resolve_output_format(output_file: Path, explicit_format: str | None) -> str:
    if explicit_format:
        return explicit_format

    suffix = output_file.suffix.lower().lstrip(".")
    if suffix in SUPPORTED_OUTPUT_FORMATS:
        return suffix
    return "mp3"


def build_config(args: argparse.Namespace) -> WorkoutConfig:
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
        tts_factory=tts_factory,
        sleep_fn=sleep_fn,
    )
    if use_cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(audio_bytes)
        LOGGER.debug("Cached speech for %r at %s", phrase, cache_path)
    return audio_segment_from_mp3_bytes(audio_bytes)


def pregenerate_announcements(
    phrases: Iterable[str],
    language: str,
    cache_dir: Path,
    *,
    use_cache: bool = True,
    tts_factory=gTTS,
    sleep_fn=time.sleep,
) -> list[AudioSegment]:
    return [
        load_or_generate_segment(
            phrase,
            language,
            cache_dir,
            use_cache=use_cache,
            tts_factory=tts_factory,
            sleep_fn=sleep_fn,
        )
        for phrase in phrases
    ]


def interleave_with_gap(
    segments: Iterable[AudioSegment], gap: AudioSegment
) -> AudioSegment:
    combined = AudioSegment.empty()
    materialized_segments = list(segments)
    for index, segment in enumerate(materialized_segments):
        combined += segment
        if index < len(materialized_segments) - 1:
            combined += gap
    return combined


def create_combined_rep_announcements(
    rep_announcements: list[AudioSegment],
    rep_gap_silence: AudioSegment,
) -> AudioSegment:
    return interleave_with_gap(rep_announcements, rep_gap_silence)


def create_combined_set_announcements(
    set_announcements: list[AudioSegment],
    combined_rep_announcements: AudioSegment,
    set_gap_silence: AudioSegment,
    *,
    rest_announcement: AudioSegment | None = None,
    set_start_gap_silence: AudioSegment | None = None,
) -> AudioSegment:
    combined = AudioSegment.empty()
    start_gap = set_start_gap_silence or AudioSegment.empty()

    for index, set_announcement in enumerate(set_announcements):
        combined += set_announcement
        combined += start_gap
        combined += combined_rep_announcements
        if index < len(set_announcements) - 1:
            if rest_announcement is not None:
                combined += rest_announcement
            combined += set_gap_silence
    return combined


def create_countdown_audio(
    countdown_announcements: list[AudioSegment],
    countdown_gap_silence: AudioSegment,
) -> AudioSegment:
    if not countdown_announcements:
        return AudioSegment.empty()
    return interleave_with_gap(countdown_announcements, countdown_gap_silence)


def build_workout_audio(config: WorkoutConfig) -> AudioSegment:
    rep_gap_silence = AudioSegment.silent(duration=int(config.rep_gap * 1000))
    set_gap_silence = AudioSegment.silent(duration=int(config.set_gap * 1000))
    set_start_gap_silence = AudioSegment.silent(
        duration=int(config.set_start_gap * 1000)
    )
    countdown_gap_silence = AudioSegment.silent(
        duration=int(DEFAULT_COUNTDOWN_GAP_SECONDS * 1000)
    )

    set_phrases = [f"Set {number}" for number in range(1, config.sets + 1)]
    rep_phrases = [str(number) for number in range(1, config.reps + 1)]

    set_announcements = pregenerate_announcements(
        set_phrases,
        config.language,
        config.cache_dir,
        use_cache=config.use_cache,
    )
    rep_announcements = pregenerate_announcements(
        rep_phrases,
        config.language,
        config.cache_dir,
        use_cache=config.use_cache,
    )
    rest_announcement = None
    if config.announce_rest and config.sets > 1:
        rest_announcement = load_or_generate_segment(
            "Rest",
            config.language,
            config.cache_dir,
            use_cache=config.use_cache,
        )

    countdown_audio = AudioSegment.empty()
    if config.countdown > 0:
        countdown_phrases = ["Starting in"] + [
            str(number) for number in range(config.countdown, 0, -1)
        ]
        countdown_audio = create_countdown_audio(
            pregenerate_announcements(
                countdown_phrases,
                config.language,
                config.cache_dir,
                use_cache=config.use_cache,
            ),
            countdown_gap_silence,
        )

    combined_rep_announcements = create_combined_rep_announcements(
        rep_announcements,
        rep_gap_silence,
    )
    workout_audio = create_combined_set_announcements(
        set_announcements,
        combined_rep_announcements,
        set_gap_silence,
        rest_announcement=rest_announcement,
        set_start_gap_silence=set_start_gap_silence,
    )

    completion_announcement = load_or_generate_segment(
        "Workout complete",
        config.language,
        config.cache_dir,
        use_cache=config.use_cache,
    )

    return countdown_audio + workout_audio + completion_announcement


def create_combined_audio(args: argparse.Namespace | WorkoutConfig) -> Path:
    config = args if isinstance(args, WorkoutConfig) else build_config(args)
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
    create_combined_audio(args)


if __name__ == "__main__":
    main()
