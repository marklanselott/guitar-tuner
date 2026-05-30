import numpy as np

from utils import AppConfig


class GuitarEngine:
    def __init__(self, config=None):
        self.config = config or AppConfig()
        self.buffer = np.zeros(self.config.window_size, dtype=np.float32)
        self.window = np.hanning(self.config.window_size).astype(np.float32)
        self.freq_bins = np.fft.rfftfreq(self.config.window_size, d=1.0 / self.config.sample_freq)
        self.analysis_stride = max(1, int(self.config.analysis_stride))
        self._tick = 0
        self._last_freq = 0.0
        self._last_spectrum = np.zeros(96, dtype=np.float32)

    def process_data(self, indata):
        samples = np.asarray(indata[:, 0], dtype=np.float32)
        block_size = len(samples)

        if block_size >= self.config.window_size:
            self.buffer[:] = samples[-self.config.window_size:]
        else:
            self.buffer = np.roll(self.buffer, -block_size)
            self.buffer[-block_size:] = samples

        self._tick += 1
        if self._tick % self.analysis_stride != 0:
            return self._last_freq

        windowed_data = self.buffer * self.window
        magnitude_spec = np.abs(np.fft.rfft(windowed_data))
        self._last_spectrum = self._build_display_spectrum(magnitude_spec)

        hps_spec = magnitude_spec.copy()
        max_harmonic = 3
        for harmonic in range(2, max_harmonic + 1):
            downsampled = magnitude_spec[::harmonic]
            hps_spec[: len(downsampled)] *= downsampled

        if len(hps_spec) < 2:
            return self._last_freq

        max_ind = int(np.argmax(hps_spec[1:])) + 1
        self._last_freq = float(self.freq_bins[max_ind])
        return self._last_freq

    def _build_display_spectrum(self, magnitude_spec):
        usable = magnitude_spec[: min(len(magnitude_spec), 2048)]
        if usable.size < 2:
            return self._last_spectrum

        compressed = np.log1p(usable).astype(np.float32)
        compressed = compressed[: len(compressed) // 2]
        if compressed.size < 2:
            return self._last_spectrum

        target_bins = 96
        source_x = np.linspace(0.0, 1.0, compressed.size, dtype=np.float32)
        target_x = np.linspace(0.0, 1.0, target_bins, dtype=np.float32)
        resampled = np.interp(target_x, source_x, compressed).astype(np.float32)

        if resampled.max() > 0:
            resampled = resampled / resampled.max()

        smooth = np.copy(resampled)
        if smooth.size >= 5:
            smooth[2:-2] = (
                resampled[:-4]
                + 2 * resampled[1:-3]
                + 3 * resampled[2:-2]
                + 2 * resampled[3:-1]
                + resampled[4:]
            ) / 9.0

        return smooth
