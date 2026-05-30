from dotenv import load_dotenv
import os
import math

load_dotenv()

ALL_NOTES = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]


def _env_float(name, default):
    value = os.getenv(name)
    return float(value) if value is not None else float(default)

class AppConfig:
    def __init__(self):
        self.sample_freq = int(_env_float("SAMPLE_FREQ", 44100))
        self.window_size = int(_env_float("WINDOW_SIZE", 22050))
        self.window_step = int(_env_float("WINDOW_STEP", 1024))
        self.analysis_stride = int(_env_float("ANALYSIS_STRIDE", 8))
        self.min_note_freq = _env_float("MIN_NOTE_FREQ", 38.0)
        self.max_guitar_freq = _env_float("MAX_GUITAR_FREQ", 1100.0)
        self.concert_pitch = _env_float("CONCERT_PITCH", 440.0)


def find_closest_note(pitch, *, concert_pitch, max_guitar_freq):
    if pitch <= 0 or pitch > max_guitar_freq:
        return "", 0.0

    # Use A4=440 Hz as the reference; this keeps note naming stable across octaves.
    semitone_index = int(round(math.log2(pitch / concert_pitch) * 12))
    closest_note = ALL_NOTES[semitone_index % 12] + str(4 + (semitone_index + 9) // 12)
    closest_pitch = concert_pitch * (2 ** (semitone_index / 12.0))
    return closest_note, closest_pitch
