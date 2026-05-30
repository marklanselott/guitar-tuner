import sounddevice as sd
import atexit
import fcntl
import itertools
import os
from pathlib import Path
import re
import shutil
import subprocess
import signal
import sys
import threading
import time

import numpy as np
from fb_display import FBDisplay
from tuner import GuitarEngine
from utils import AppConfig, find_closest_note

LOCK_PATH = Path.home() / ".cache" / "guitar-tuner" / "guitar-tuner.lock"
ALLOW_ROOT = os.getenv("GUITAR_TUNER_ALLOW_ROOT") == "1"


def acquire_single_instance_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(LOCK_PATH, "w")
    state = {"released": False}
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Guitar tuner is already running.")
        sys.exit(1)

    lock_file.write(str(os.getpid()))
    lock_file.flush()

    def release_lock():
        if state["released"]:
            return
        state["released"] = True
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            lock_file.close()
        except OSError:
            pass

    atexit.register(release_lock)
    return release_lock


def _find_input_device():
    preferred_names = ["fifine", "microphone", "usb"]

    raw_device = os.getenv("SOUNDDEVICE_INPUT_DEVICE")
    if raw_device is not None:
        try:
            return int(raw_device)
        except ValueError:
            pass

    try:
        default_device = sd.default.device
        if isinstance(default_device, (list, tuple)) and len(default_device) >= 1:
            input_device = default_device[0]
            if input_device is not None and input_device >= 0:
                sd.query_devices(input_device, "input")
                return input_device
    except Exception:
        pass

    try:
        devices = sd.query_devices()
    except Exception:
        devices = []

    candidates = []
    for index, device in enumerate(devices):
        if device.get("max_input_channels", 0) > 0:
            name = str(device.get("name", "")).lower()
            score = 0
            for token in preferred_names:
                if token in name:
                    score += 10
            if device.get("hostapi", 0) == 0:
                score += 1
            candidates.append((score, index, device))

    if candidates:
        candidates.sort(key=lambda item: (-item[0], item[1]))
        return candidates[0][1]

    try:
        cards = open("/proc/asound/cards").read().strip()
    except Exception:
        cards = ""

    if cards:
        match = re.search(r"\n\s*(\d+)\s+\[.*?\]:.*?(Microphone|USB-Audio|USB)", cards, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass

    return None


def _find_alsa_capture_device():
    try:
        cards = open("/proc/asound/cards").read()
    except Exception:
        return None

    for line in cards.splitlines():
        if "USB-Audio" in line and "Microphone" in line:
            match = re.match(r"\s*(\d+)\s+\[", line)
            if match:
                return int(match.group(1))

    for line in cards.splitlines():
        if "USB-Audio" in line:
            match = re.match(r"\s*(\d+)\s+\[", line)
            if match:
                return int(match.group(1))

    return None


def _run_arecord_stream(config, engine, display):
    card_index = _find_alsa_capture_device()
    if card_index is None:
        raise RuntimeError("No ALSA capture card found.")

    arecord = shutil.which("arecord")
    if not arecord:
        raise RuntimeError("arecord is not installed.")

    cmd = [
        arecord,
        "-D",
        "plughw:{},0".format(card_index),
        "-f",
        "S16_LE",
        "-r",
        str(config.sample_freq),
        "-c",
        "1",
        "-t",
        "raw",
        "-q",
    ]

    chunk_bytes = config.window_step * 2
    if chunk_bytes <= 0:
        chunk_bytes = 2048
    silence_threshold = float(os.getenv("GUITAR_TUNER_SILENCE_THRESHOLD", "0.01"))

    print("Using ALSA capture: {}".format(" ".join(cmd)))
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,
    )

    try:
        while True:
            raw = proc.stdout.read(chunk_bytes)
            if not raw:
                err = proc.stderr.read().decode(errors="ignore").strip()
                raise RuntimeError("arecord stopped unexpectedly: {}".format(err or "no data"))

            if len(raw) < 2:
                continue

            data = np.frombuffer(raw, dtype=np.int16)
            if data.size == 0:
                continue

            frames = data.reshape(-1, 1).astype(np.float32) / 32768.0
            signal_level = float(np.sqrt(np.mean(frames * frames))) if frames.size else 0.0
            if signal_level < silence_threshold:
                display.update(
                    note="",
                    target=0.0,
                    current=0.0,
                    diff=0.0,
                    is_valid=False,
                    spectrum=engine._last_spectrum,
                )
                continue

            current_freq = engine.process_data(frames)
            note_name, target_pitch = find_closest_note(
                current_freq,
                concert_pitch=config.concert_pitch,
                max_guitar_freq=config.max_guitar_freq,
            )
            diff = current_freq - target_pitch
            is_valid = current_freq >= config.min_note_freq and current_freq < config.max_guitar_freq

            display.update(
                note=note_name,
                target=target_pitch,
                current=current_freq,
                diff=diff,
                is_valid=is_valid,
                spectrum=engine._last_spectrum,
            )
    finally:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
        except Exception:
            pass
        try:
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=1)
        except Exception:
            pass


def main():
    if os.geteuid() == 0 and not ALLOW_ROOT:
        print("Refusing to run as root by default. Use regular user + framebuffer permissions, or set GUITAR_TUNER_ALLOW_ROOT=1.")
        sys.exit(1)

    release_lock = acquire_single_instance_lock()
    config = AppConfig()
    engine = GuitarEngine(config)
    display = FBDisplay()
    try:
        if shutil.which("arecord") and _find_alsa_capture_device() is not None:
            _run_arecord_stream(config, engine, display)
        else:
            input_device = _find_input_device()
            if input_device is not None:
                try:
                    print("Using input device: {}".format(sd.query_devices(input_device)["name"]))
                except Exception:
                    print("Using input device index: {}".format(input_device))

            if input_device is None:
                raise RuntimeError("No usable audio input device found.")

            tick = [0]

            def callback(indata, frames, time_info, status):
                signal_level = float(np.sqrt(np.mean(indata * indata))) if indata.size else 0.0
                if signal_level < float(os.getenv("GUITAR_TUNER_SILENCE_THRESHOLD", "0.01")):
                    display.update(note="", target=0.0, current=0.0, diff=0.0, is_valid=False, spectrum=engine._last_spectrum)
                    return

                current_freq = engine.process_data(indata)
                note_name, target_pitch = find_closest_note(
                    current_freq,
                    concert_pitch=config.concert_pitch,
                    max_guitar_freq=config.max_guitar_freq,
                )
                diff = current_freq - target_pitch
                is_valid = current_freq >= config.min_note_freq and current_freq < config.max_guitar_freq

                display.update(
                    note=note_name,
                    target=target_pitch,
                    current=current_freq,
                    diff=diff,
                    is_valid=is_valid,
                    spectrum=engine._last_spectrum,
                )
                if tick[0] % 20 == 0:
                    print("freq={:.2f}Hz note={} valid={}".format(current_freq, note_name or "-", is_valid))
                tick[0] += 1

            with sd.InputStream(
                channels=1,
                device=input_device,
                callback=callback,
                blocksize=config.window_step,
                samplerate=config.sample_freq,
            ):
                while True:
                    sd.sleep(100)
    except KeyboardInterrupt:
        pass
    except SystemExit:
        raise
    except Exception as exc:
        print(str(exc))
    finally:
        display.close()
        release_lock()


def _handle_termination(signum, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, _handle_termination)
signal.signal(signal.SIGTERM, _handle_termination)


if __name__ == "__main__":
    main()
