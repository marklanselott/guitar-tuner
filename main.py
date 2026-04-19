from utils import find_closest_note, generate_colored_scale, MAX_GUITAR_FREQ, UP, CLR
from dotenv import load_dotenv; load_dotenv()
from tuner import GuitarEngine
import sounddevice as sd
import sys, os

UP = "\033[A"    
CLR = "\033[K"    

WINDOW_STEP = int(os.getenv("WINDOW_STEP", 4000))
SAMPLE_FREQ = int(os.getenv("SAMPLE_FREQ", 44100))

engine = GuitarEngine()

def callback(indata, frames, time, status):
    if status:
        sys.stderr.write(f"{status}\n")
    
    current_freq = engine.process_data(indata)
    
    note_name, target_pitch = find_closest_note(current_freq)
    diff = current_freq - target_pitch
    
    is_valid = (current_freq > 40 and current_freq < MAX_GUITAR_FREQ)
    scale_visual = generate_colored_scale(diff, is_valid=is_valid)

    display_pitch = target_pitch if is_valid else 0.0
    display_freq = current_freq if is_valid else 0.0

    sys.stdout.write(f"{'НОТА:':<12} {note_name:<10}{CLR}\n")
    sys.stdout.write(f"{'ЦЕЛЬ:':<12} {display_pitch:<7.2f} Hz{CLR}\n")
    sys.stdout.write(f"{'СЕЙЧАС:':<12} {display_freq:<7.2f} Hz{CLR}\n")
    sys.stdout.write(f"{scale_visual}{CLR}\n")
    
    sys.stdout.write(UP * 4)
    sys.stdout.flush()

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
        print("\n" * 4 + "Тюнер остановлен.")
        sys.exit()