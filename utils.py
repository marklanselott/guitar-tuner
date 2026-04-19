from dotenv import load_dotenv; load_dotenv()
import numpy as np
import os

ALL_NOTES = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]
MAX_GUITAR_FREQ = float(os.getenv("MAX_GUITAR_FREQ"))
CONCERT_PITCH = float(os.getenv("CONCERT_PITCH"))

def find_closest_note(pitch):
    if pitch <= 40 or pitch > MAX_GUITAR_FREQ: 
        return "", 0.0
    
    i = int(np.round(np.log2(pitch / CONCERT_PITCH) * 12))
    closest_note = ALL_NOTES[i % 12] + str(4 + (i + 9) // 12)
    closest_pitch = CONCERT_PITCH * 2**(i / 12)
    return closest_note, closest_pitch