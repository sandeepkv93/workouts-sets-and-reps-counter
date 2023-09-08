### Sets and Reps Counter

This is a simple python script that generates an audio file that counts sets and reps. It is intended to be used as a guide for workouts.

### Usage

```
usage: sets_and_reps_counter.py [-h] --reps REPS --sets SETS --rep_gap REP_GAP --set_gap SET_GAP [--output_file OUTPUT_FILE]

Generate a guided sets and reps audio file.

options:
  -h, --help            show this help message and exit
  --reps REPS           The number of reps in each set.
  --sets SETS           The number of sets.
  --rep_gap REP_GAP     The gap between reps in seconds.
  --set_gap SET_GAP     The gap between sets in seconds.
  --output_file OUTPUT_FILE
                        The output mp3 file name.
```

### Example

If you want to do 3 sets of 10 reps with a 1 second gap between reps, you would run the following command:

```
python3 sets_and_reps_counter.py --reps 10 --sets 3 --rep_gap 1 --set_gap 30 --output_file 3x10.mp3
```

### Audio File Contents

Suppose you run the above command. The audio file will contain the following:

```
Set 1
1
1 second gap
2
1 second gap
3
1 second gap
4
1 second gap
5
1 second gap
6
1 second gap
7
1 second gap
8
1 second gap
9
1 second gap
10
30 seconds gap
Set 2
1
1 second gap
2
1 second gap
3
1 second gap
4
1 second gap
5
1 second gap
6
1 second gap
7
1 second gap
8
1 second gap
9
1 second gap
10
30 seconds gap
Set 3
1
1 second gap
2
1 second gap
3
1 second gap
4
1 second gap
5
1 second gap
6
1 second gap
7
1 second gap
8
1 second gap
9
1 second gap
10
```
