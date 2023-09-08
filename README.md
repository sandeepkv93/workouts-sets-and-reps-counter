### Sets and Reps Counter

This is a simple python script that generates an audio file that counts sets and reps. It is intended to be used as a guide for workouts.

### Usage

```
usage: sets_and_reps_counter.py [-h] --rep_gap REP_GAP --reps REPS --sets SETS [--output_file OUTPUT_FILE]

Generate a guided sets and reps audio file.

options:
  -h, --help            show this help message and exit
  --rep_gap REP_GAP     The gap between reps in milliseconds.
  --reps REPS           The number of reps in each set.
  --sets SETS           The number of sets.
  --output_file OUTPUT_FILE
                        The output mp3 file name.
```

### Example

If you want to do 3 sets of 10 reps with a 1 second gap between reps, you would run the following command:

```
python3 sets_and_reps_counter.py --rep_gap 1000 --reps 10 --sets 3 --output_file 3x10.mp3
```

### Audio File Contents

Suppose you run the above command. The audio file will contain the following:

```
Set 1
1
1 second (1000 milliseconds) gap
2
1 second (1000 milliseconds) gap
3
1 second (1000 milliseconds) gap
4
1 second (1000 milliseconds) gap
5
1 second (1000 milliseconds) gap
6
1 second (1000 milliseconds) gap
7
1 second (1000 milliseconds) gap
8
1 second (1000 milliseconds) gap
9
1 second (1000 milliseconds) gap
10
1 second (1000 milliseconds) gap
Set 2
1
1 second (1000 milliseconds) gap
2
1 second (1000 milliseconds) gap
3
1 second (1000 milliseconds) gap
4
1 second (1000 milliseconds) gap
5
1 second (1000 milliseconds) gap
6
1 second (1000 milliseconds) gap
7
1 second (1000 milliseconds) gap
8
1 second (1000 milliseconds) gap
9
1 second (1000 milliseconds) gap
10
1 second (1000 milliseconds) gap
Set 3
1
1 second (1000 milliseconds) gap
2
1 second (1000 milliseconds) gap
3
1 second (1000 milliseconds) gap
4
1 second (1000 milliseconds) gap
5
1 second (1000 milliseconds) gap
6
1 second (1000 milliseconds) gap
7
1 second (1000 milliseconds) gap
8
1 second (1000 milliseconds) gap
9
1 second (1000 milliseconds) gap
10
1 second (1000 milliseconds) gap
```
