import argparse
import os
import time
from typing import List

from gtts import gTTS
from pydub import AudioSegment


def create_parser():
    parser = argparse.ArgumentParser(description='Generate a guided sets and reps audio file.')
    parser.add_argument('--reps', type=int, required=True, help='The number of reps in each set.')
    parser.add_argument('--sets', type=int, required=True, help='The number of sets.')
    parser.add_argument('--rep_gap', type=int, required=True, help='The gap between reps in seconds.')
    parser.add_argument('--set_gap', type=int, required=True, help='The gap between sets in seconds.')
    parser.add_argument('--output_file', type=str, required=False, help='The output mp3 file name.')
    return parser

def get_rep_gap_silence(rep_gap: int) -> AudioSegment:
    return AudioSegment.silent(duration=rep_gap)

def get_set_gap_silence(set_gap: int) -> AudioSegment:
    return AudioSegment.silent(duration=set_gap)

def pregenerate_set_announcements(sets: int) -> List[AudioSegment]:
    set_announcements = []
    for number in range(1, sets+1):
        tts = gTTS(f"Set {number}")
        filename = f"set_{number}.mp3"
        tts.save(filename)
        set_announcements.append(AudioSegment.from_mp3(filename))
        os.remove(filename)
        time.sleep(1)  # add delay to avoid hitting the rate limit
    return set_announcements

def pregenerate_rep_announcements(reps: int) -> List[AudioSegment]:
    rep_announcements = []
    for number in range(1, reps+1):
        tts = gTTS(str(number))
        filename = f"rep_{number}.mp3"
        tts.save(filename)
        rep_announcements.append(AudioSegment.from_mp3(filename))
        os.remove(filename)
        time.sleep(1)  # add delay to avoid hitting the rate limit
    return rep_announcements

def create_combined_rep_announcements(rep_announcements: List[AudioSegment], rep_gap_silence: AudioSegment) -> AudioSegment:
    combined_rep_announcements = AudioSegment.empty()
    for i, rep_announcement in enumerate(rep_announcements):
        combined_rep_announcements += rep_announcement
        if i < len(rep_announcements) - 1:
            combined_rep_announcements += rep_gap_silence
    print("Created combined rep announcements")
    return combined_rep_announcements

def create_combined_set_announcements(set_announcements: List[AudioSegment], combined_rep_announcements: AudioSegment, set_gap_silence: AudioSegment) -> AudioSegment:
    combined_set_announcements = AudioSegment.empty()
    for set_announcement in set_announcements:
        combined_set_announcements += set_announcement
        combined_set_announcements += combined_rep_announcements
        if set_announcement != set_announcements[-1]:
            combined_set_announcements += set_gap_silence
    print("Created combined set announcements")
    return combined_set_announcements

def create_combined_audio(args):
    sets = args.sets
    reps = args.reps
    rep_gap = args.rep_gap * 1000
    set_gap = args.set_gap * 1000
    if args.output_file is None:
        output_file_name = f"{reps}reps_for_{sets}sets_with_{rep_gap}ms_gap.mp3"
    else:
        output_file_name = args.output_file
    rep_gap_silence = get_rep_gap_silence(rep_gap)
    set_gap_silence = get_set_gap_silence(set_gap)
    set_announcements = pregenerate_set_announcements(sets)
    rep_announcements = pregenerate_rep_announcements(reps)
    combined_rep_announcements = create_combined_rep_announcements(rep_announcements, rep_gap_silence)
    combined_set_announcements = create_combined_set_announcements(set_announcements, combined_rep_announcements, set_gap_silence)
    combined_set_announcements.export(output_file_name, format="mp3")
    print(f"MP3 file created: {output_file_name}")

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    create_combined_audio(args)
