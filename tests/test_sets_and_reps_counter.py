import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydub import AudioSegment

import sets_and_reps_counter as src


class FakeTTS:
    def __init__(self, text: str, lang: str):
        self.payload = f"{lang}:{text}".encode("utf-8")

    def write_to_fp(self, buffer) -> None:
        buffer.write(self.payload)


class FlakyTTS:
    attempts = 0

    def __init__(self, text: str, lang: str):
        self.text = text
        self.lang = lang

    def write_to_fp(self, buffer) -> None:
        type(self).attempts += 1
        if type(self).attempts < 3:
            raise RuntimeError("temporary failure")
        buffer.write(f"{self.lang}:{self.text}".encode("utf-8"))


class ParserTests(unittest.TestCase):
    def test_parser_rejects_zero_sets(self) -> None:
        parser = src.create_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "--reps",
                    "10",
                    "--sets",
                    "0",
                    "--rep-gap",
                    "1",
                    "--set-gap",
                    "30",
                    "--output-file",
                    "workout.mp3",
                ]
            )

    def test_resolve_output_format_prefers_extension(self) -> None:
        self.assertEqual(src.resolve_output_format(Path("workout.wav"), None), "wav")
        self.assertEqual(src.resolve_output_format(Path("workout"), None), "mp3")


class AudioAssemblyTests(unittest.TestCase):
    def test_create_combined_rep_announcements_adds_gap_between_reps(self) -> None:
        reps = [AudioSegment.silent(duration=100), AudioSegment.silent(duration=120)]
        gap = AudioSegment.silent(duration=500)

        combined = src.create_combined_rep_announcements(reps, gap)

        self.assertEqual(len(combined), 720)

    def test_create_combined_set_announcements_adds_rest_and_start_gap(self) -> None:
        sets = [AudioSegment.silent(duration=50), AudioSegment.silent(duration=60)]
        reps = AudioSegment.silent(duration=200)
        set_gap = AudioSegment.silent(duration=1000)
        rest = AudioSegment.silent(duration=150)
        start_gap = AudioSegment.silent(duration=300)

        combined = src.create_combined_set_announcements(
            sets,
            reps,
            set_gap,
            rest_announcement=rest,
            set_start_gap_silence=start_gap,
        )

        self.assertEqual(len(combined), 50 + 300 + 200 + 150 + 1000 + 60 + 300 + 200)

    def test_create_countdown_audio_is_empty_without_announcements(self) -> None:
        self.assertEqual(
            len(src.create_countdown_audio([], AudioSegment.silent(duration=1000))), 0
        )


class SynthesisTests(unittest.TestCase):
    def test_synthesize_phrase_retries_before_success(self) -> None:
        FlakyTTS.attempts = 0
        sleep_calls = []

        result = src.synthesize_phrase(
            "Set 1",
            "en",
            tts_factory=FlakyTTS,
            sleep_fn=sleep_calls.append,
        )

        self.assertEqual(result, b"en:Set 1")
        self.assertEqual(sleep_calls, [1.0, 2.0])

    def test_load_or_generate_segment_writes_and_reuses_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            decoded_values = []

            def fake_decoder(payload: bytes) -> AudioSegment:
                decoded_values.append(payload)
                return AudioSegment.silent(duration=123)

            with patch.object(src, "audio_segment_from_mp3_bytes", side_effect=fake_decoder):
                first = src.load_or_generate_segment(
                    "Rest",
                    "en",
                    cache_dir,
                    use_cache=True,
                    tts_factory=FakeTTS,
                )
                second = src.load_or_generate_segment(
                    "Rest",
                    "en",
                    cache_dir,
                    use_cache=True,
                    tts_factory=FakeTTS,
                )

            self.assertEqual(len(first), 123)
            self.assertEqual(len(second), 123)
            self.assertEqual(decoded_values, [b"en:Rest", b"en:Rest"])
            self.assertEqual(len(list(cache_dir.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
