import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pydub import AudioSegment

import workout_audio_coach.cli as src


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

    def test_build_config_allows_preview_without_output(self) -> None:
        args = argparse.Namespace(
            reps=10,
            sets=3,
            rep_gap=1.0,
            set_gap=30.0,
            output_file=None,
            format=None,
            language="en",
            cache_dir=Path("cache"),
            no_cache=False,
            countdown=3,
            announce_rest=True,
            set_start_gap=1.0,
            preview=True,
            script_file=None,
            tts_attempts=3,
            tts_backoff=1.0,
        )

        config = src.build_config(args)

        self.assertTrue(config.preview)
        self.assertIsNone(config.output_file)
        self.assertIsNone(config.output_format)

    def test_build_config_requires_output_or_preview_or_script_file(self) -> None:
        args = argparse.Namespace(
            reps=10,
            sets=3,
            rep_gap=1.0,
            set_gap=30.0,
            output_file=None,
            format=None,
            language="en",
            cache_dir=Path("cache"),
            no_cache=False,
            countdown=3,
            announce_rest=True,
            set_start_gap=1.0,
            preview=False,
            script_file=None,
            tts_attempts=3,
            tts_backoff=1.0,
        )

        with self.assertRaisesRegex(ValueError, "either --output-file"):
            src.build_config(args)

    def test_resolve_output_format_prefers_extension(self) -> None:
        self.assertEqual(src.resolve_output_format(Path("workout.wav"), None), "wav")
        self.assertEqual(src.resolve_output_format(Path("workout"), None), "mp3")

    def test_resolve_output_format_requires_output_file(self) -> None:
        with self.assertRaisesRegex(ValueError, "--format requires --output-file"):
            src.resolve_output_format(None, "wav")


class WorkoutPlanTests(unittest.TestCase):
    def test_build_workout_plan_includes_countdown_rest_and_completion(self) -> None:
        config = src.WorkoutConfig(
            reps=2,
            sets=2,
            rep_gap=0.5,
            set_gap=10.0,
            output_file=Path("out.mp3"),
            output_format="mp3",
            language="en",
            cache_dir=Path("cache"),
            use_cache=True,
            countdown=3,
            announce_rest=True,
            set_start_gap=1.5,
            preview=False,
            script_file=None,
            tts_attempts=3,
            tts_initial_backoff=1.0,
        )

        plan = src.build_workout_plan(config)
        spoken = [step.spoken_text for step in plan]

        self.assertEqual(
            spoken,
            [
                "Starting in",
                "3",
                "2",
                "1",
                "Set 1",
                "1",
                "2",
                "Rest",
                "Set 2",
                "1",
                "2",
                "Workout complete",
            ],
        )
        self.assertEqual(plan[4].gap_after, 1.5)
        self.assertEqual(plan[5].gap_after, 0.5)
        self.assertEqual(plan[7].gap_after, 10.0)

    def test_build_workout_plan_uses_silence_step_when_rest_not_announced(self) -> None:
        config = src.WorkoutConfig(
            reps=1,
            sets=2,
            rep_gap=0.0,
            set_gap=20.0,
            output_file=None,
            output_format=None,
            language="en",
            cache_dir=Path("cache"),
            use_cache=True,
            countdown=0,
            announce_rest=False,
            set_start_gap=0.0,
            preview=True,
            script_file=None,
            tts_attempts=3,
            tts_initial_backoff=1.0,
        )

        plan = src.build_workout_plan(config)

        self.assertIn(src.WorkoutStep(spoken_text=None, gap_after=20.0), plan)

    def test_format_workout_plan_includes_summary_and_silence(self) -> None:
        config = src.WorkoutConfig(
            reps=1,
            sets=2,
            rep_gap=0.0,
            set_gap=20.0,
            output_file=None,
            output_format=None,
            language="en",
            cache_dir=Path("cache"),
            use_cache=True,
            countdown=0,
            announce_rest=False,
            set_start_gap=0.0,
            preview=True,
            script_file=None,
            tts_attempts=3,
            tts_initial_backoff=1.0,
        )

        preview = src.format_workout_plan(config, src.build_workout_plan(config))

        self.assertIn("Workout Audio Coach plan", preview)
        self.assertIn("[silence] [gap 20s]", preview)
        self.assertIn("Sets x reps: 2 x 1", preview)


class AudioAssemblyTests(unittest.TestCase):
    def test_build_workout_audio_adds_only_configured_silence(self) -> None:
        config = src.WorkoutConfig(
            reps=2,
            sets=1,
            rep_gap=0.5,
            set_gap=0.0,
            output_file=Path("out.mp3"),
            output_format="mp3",
            language="en",
            cache_dir=Path("cache"),
            use_cache=True,
            countdown=0,
            announce_rest=True,
            set_start_gap=1.0,
            preview=False,
            script_file=None,
            tts_attempts=3,
            tts_initial_backoff=1.0,
        )

        with patch.object(
            src,
            "load_or_generate_segment",
            return_value=AudioSegment.silent(duration=100),
        ) as loader:
            combined = src.build_workout_audio(config)

        self.assertEqual(loader.call_count, 4)
        self.assertEqual(len(combined), 1900)

    def test_create_combined_audio_preview_only_returns_none(self) -> None:
        config = src.WorkoutConfig(
            reps=1,
            sets=1,
            rep_gap=0.0,
            set_gap=0.0,
            output_file=None,
            output_format=None,
            language="en",
            cache_dir=Path("cache"),
            use_cache=True,
            countdown=0,
            announce_rest=True,
            set_start_gap=0.0,
            preview=False,
            script_file=None,
            tts_attempts=3,
            tts_initial_backoff=1.0,
        )

        result = src.create_combined_audio(config)

        self.assertIsNone(result)

    def test_create_combined_audio_exports_when_output_is_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "nested" / "workout.wav"
            config = src.WorkoutConfig(
                reps=1,
                sets=1,
                rep_gap=0.0,
                set_gap=0.0,
                output_file=output_file,
                output_format="wav",
                language="en",
                cache_dir=Path(tmpdir) / "cache",
                use_cache=True,
                countdown=0,
                announce_rest=True,
                set_start_gap=0.0,
                preview=False,
                script_file=None,
                tts_attempts=3,
                tts_initial_backoff=1.0,
            )
            audio = MagicMock()

            with patch.object(src, "build_workout_audio", return_value=audio):
                result = src.create_combined_audio(config)

            audio.export.assert_called_once_with(output_file, format="wav")
            self.assertEqual(result, output_file)


class PreviewOutputTests(unittest.TestCase):
    def test_maybe_write_script_preview_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_file = Path(tmpdir) / "plans" / "workout.txt"
            config = src.WorkoutConfig(
                reps=1,
                sets=1,
                rep_gap=0.0,
                set_gap=0.0,
                output_file=None,
                output_format=None,
                language="en",
                cache_dir=Path("cache"),
                use_cache=True,
                countdown=0,
                announce_rest=True,
                set_start_gap=0.0,
                preview=False,
                script_file=script_file,
                tts_attempts=3,
                tts_initial_backoff=1.0,
            )

            preview_text = src.maybe_write_script_preview(
                config,
                [src.WorkoutStep("Set 1"), src.WorkoutStep("Workout complete")],
            )

            self.assertTrue(script_file.exists())
            self.assertEqual(script_file.read_text(encoding="utf-8"), preview_text + "\n")


class SynthesisTests(unittest.TestCase):
    def test_synthesize_phrase_retries_before_success(self) -> None:
        FlakyTTS.attempts = 0
        sleep_calls = []

        result = src.synthesize_phrase(
            "Set 1",
            "en",
            attempts=3,
            initial_backoff_seconds=1.0,
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
