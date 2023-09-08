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
    parser.add_argument('--output_file', type=str, required=True, help='The output mp3 file name.')
    return parser

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
    return combined_rep_announcements

def create_combined_set_announcements(set_announcements: List[AudioSegment], combined_rep_announcements: AudioSegment, set_gap_silence: AudioSegment) -> AudioSegment:
    combined_set_announcements = AudioSegment.empty()
    for set_announcement in set_announcements:
        combined_set_announcements += set_announcement
        combined_set_announcements += combined_rep_announcements
        if set_announcement != set_announcements[-1]:
            combined_set_announcements += set_gap_silence
    return combined_set_announcements

def create_combined_audio(args):
    rep_gap_silence = AudioSegment.silent(duration=args.rep_gap * 1000)
    set_gap_silence = AudioSegment.silent(duration=args.set_gap * 1000)
    set_announcements = pregenerate_set_announcements(args.sets)
    rep_announcements = pregenerate_rep_announcements(args.reps)
    combined_rep_announcements = create_combined_rep_announcements(rep_announcements, rep_gap_silence)
    combined_set_announcements = create_combined_set_announcements(set_announcements, combined_rep_announcements, set_gap_silence)
    combined_set_announcements.export(args.output_file, format="mp3")
    print(f"MP3 file created: {args.output_file}")

if __name__ == "__main__":
    args = create_parser().parse_args()
    create_combined_audio(args)
