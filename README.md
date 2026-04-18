# Workout Audio Coach

`workout-audio-coach` generates guided workout audio for fixed sets and reps. It can:

- speak set numbers, rep counts, rest cues, and a completion cue
- insert programmable countdown, rep, set, and set-start gaps
- preview the spoken script without touching Google TTS or ffmpeg
- export the preview plan to a text file
- cache synthesized speech clips for faster repeated runs

## Setup

Install dependencies with `uv`:

```bash
uv sync
```

## Requirements

- Python 3.12+
- Network access for Google Text-to-Speech when generating audio
- `ffmpeg` on your system so `pydub` can decode generated mp3 speech clips

## Usage

Generate an audio workout:

```bash
uv run workout-audio-coach \
  --reps 10 \
  --sets 3 \
  --rep-gap 1 \
  --set-gap 30 \
  --output-file workouts/3x10.mp3
```

Preview the workout script without generating audio:

```bash
uv run workout-audio-coach \
  --reps 10 \
  --sets 3 \
  --rep-gap 1 \
  --set-gap 30 \
  --preview
```

Write the preview plan to a file while also exporting audio:

```bash
uv run workout-audio-coach \
  --reps 8 \
  --sets 4 \
  --rep-gap 0.75 \
  --set-gap 20 \
  --script-file plans/4x8.txt \
  --output-file workouts/4x8.wav
```

The generated flow looks roughly like this:

```text
Starting in
3
2
1
Set 1
1
2
...
10
Rest
Set 2
...
Workout complete
```

## Useful Options

- `--countdown 0` disables the spoken countdown
- `--preview` prints the full workout script and exits if no output file is given
- `--script-file /path/to/plan.txt` writes the preview script to disk
- `--announce-rest` or `--no-announce-rest` toggles the spoken rest cue
- `--set-start-gap 1.5` changes the pause between `Set N` and the first rep
- `--tts-attempts 5` and `--tts-backoff 0.5` tune retry behavior for speech synthesis
- `--format wav` exports wav instead of inferring from the output filename
- `--language en` changes the gTTS language
- `--cache-dir /path/to/cache` changes where speech clips are cached
- `--no-cache` forces fresh speech generation for the current run
- `--verbose` enables debug logging

## CLI Help

```text
uv run workout-audio-coach --help
```

Backward-compatible script usage still works:

```bash
uv run python sets_and_reps_counter.py --reps 10 --sets 3 --rep-gap 1 --set-gap 30 --preview
```

## Development

Run the test suite with:

```bash
uv run python -m unittest discover -s tests -v
```
