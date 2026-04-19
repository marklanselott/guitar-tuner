from utils import find_closest_note, MAX_GUITAR_FREQ
from fb_display import FBDisplay
from tuner import GuitarEngine
import sounddevice as sd
import os

WINDOW_STEP = int(os.getenv("WINDOW_STEP"))
SAMPLE_FREQ = int(os.getenv("SAMPLE_FREQ"))

engine = GuitarEngine()
display = FBDisplay()

def callback(indata, frames, time, status):
    current_freq = engine.process_data(indata)
    note_name, target_pitch = find_closest_note(current_freq)
    diff = current_freq - target_pitch
    
    is_valid = (40 < current_freq < MAX_GUITAR_FREQ)

    display.update(
        note=note_name,
        target=target_pitch,
        current=current_freq,
        diff=diff,
        is_valid=is_valid
    )

if __name__ == "__main__":
    try:
        with sd.InputStream(
            channels=1, 
            callback=callback, 
            blocksize=WINDOW_STEP, 
            samplerate=SAMPLE_FREQ
        ):
            while True:
                sd.sleep(100)
    except KeyboardInterrupt:
        display.close()