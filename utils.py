import numpy as np
import os

CONCERT_PITCH = float(os.getenv("CONCERT_PITCH", 440))
ALL_NOTES = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]
MAX_GUITAR_FREQ = float(os.getenv("MAX_GUITAR_FREQ", 1500.0))
PERFECT_THRESHOLD = float(os.getenv("PERFECT_THRESHOLD", 1.2))

RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

UP = "\033[A"
CLR = "\033[K"

def find_closest_note(pitch):
    if pitch <= 40 or pitch > MAX_GUITAR_FREQ: 
        return "---", 0.0
    
    i = int(np.round(np.log2(pitch / CONCERT_PITCH) * 12))
    closest_note = ALL_NOTES[i % 12] + str(4 + (i + 9) // 12)
    closest_pitch = CONCERT_PITCH * 2**(i / 12)
    return closest_note, closest_pitch

def generate_colored_scale(diff, is_valid=True):
    total_elements = 21
    center = 10
    
    if not is_valid:
        return "[        ---        ]"
    
    shift = int(np.clip(diff / 0.5, -10, 10))
    color = GREEN if abs(diff) <= PERFECT_THRESHOLD else RED
    scale_list = ["|"] * total_elements
    scale_list[center + shift] = "_" 
    
    return f"{color}[{''.join(scale_list)}]{RESET}"