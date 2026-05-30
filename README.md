# Guitar Tuner

Simple framebuffer guitar tuner for Linux.

## Run

```bash
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

`run.sh` starts the app without `sudo`. If `/dev/fb0` is not writable for the current user, the script prints a clear hint instead of switching silently into root mode.

## Dev mode

Enable debug timing output with:

```bash
FB_DEBUG_TIMING=1 ./run.sh
```

In dev mode the UI shows a small FPS counter in the top-right corner and prints render timing logs to the terminal.

## UI behavior

- The screen shows the detected note at the top.
- The center line is the main tuning indicator.
- `Now` and `Target` are shown at the bottom.
- When input sound disappears, the green part fades out smoothly.
- In silence, the green part and the target/current values reset to neutral.

## Dependencies

- `numpy`
- `Pillow`
- `python-dotenv`
- `sounddevice`

## Environment variables

- `FB0_PATH` - framebuffer device path, for example `/dev/fb0`
- `font_path` - path to a TTF font file
- `SOUNDDEVICE_INPUT_DEVICE` - optional manual input device index for `sounddevice`
- `GUITAR_TUNER_SILENCE_THRESHOLD` - silence gate threshold, default `0.01`
- `GUITAR_TUNER_ALLOW_ROOT=1` - allow running as root if you really need it

## Notes

- On Linux the app prefers ALSA capture via `arecord` when available.
- If `arecord` is not available, it falls back to `sounddevice`.
- The current UI is intentionally minimal to keep rendering light and smooth.
