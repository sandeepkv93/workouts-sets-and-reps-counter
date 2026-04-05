### Sets and Reps Counter

This project generates guided workout audio files for fixed sets and reps. It speaks the set number, counts each rep, inserts timing gaps, adds an optional countdown, announces rest periods, and ends with a completion cue.

### Setup

Install dependencies with `uv`:

```bash
uv sync
```

### Requirements

- Python 3.12+
- Network access for Google Text-to-Speech
- `ffmpeg` available on your system so `pydub` can decode the generated mp3 speech clips

### Usage

Basic example:

```bash
uv run python sets_and_reps_counter.py \
  --reps 10 \
  --sets 3 \
  --rep-gap 1 \
  --set-gap 30 \
  --output-file 3x10.mp3
```

This produces audio shaped roughly like:

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

### Useful Options

- `--countdown 0` disables the spoken countdown
- `--announce-rest` or `--no-announce-rest` toggles the spoken rest cue
- `--set-start-gap 1.5` changes the pause between `Set N` and the first rep
- `--format wav` exports a wav file instead of inferring from the output filename
- `--language en` changes the gTTS language
- `--cache-dir /path/to/cache` changes where speech clips are cached
- `--no-cache` forces fresh speech generation for the current run
- `--verbose` enables debug logging

### CLI Help

```text
usage: sets_and_reps_counter.py [-h] --reps REPS --sets SETS --rep-gap REP_GAP
                                --set-gap SET_GAP --output-file OUTPUT_FILE
                                [--format {mp3,wav}] [--language LANGUAGE]
                                [--cache-dir CACHE_DIR] [--no-cache]
                                [--countdown COUNTDOWN]
                                [--announce-rest | --no-announce-rest]
                                [--set-start-gap SET_START_GAP] [--verbose]
```

### Development

Run the test suite with:

```bash
uv run python -m unittest discover -s tests -v
```
