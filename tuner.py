import numpy as np
import scipy.fftpack
import scipy.signal
import os

SAMPLE_FREQ = int(os.getenv("SAMPLE_FREQ", 44100))
WINDOW_SIZE = int(os.getenv("WINDOW_SIZE", 44100))

class GuitarEngine:
    def __init__(self):
        self.buffer = np.zeros(WINDOW_SIZE)

    def process_data(self, indata):
        # Обновление буфера
        self.buffer = np.roll(self.buffer, -len(indata))
        self.buffer[-len(indata):] = indata[:, 0]

        # Преобразование Фурье с окном Ханнинга
        windowed_data = self.buffer * np.hanning(WINDOW_SIZE)
        magnitude_spec = abs(scipy.fftpack.fft(windowed_data))[:WINDOW_SIZE // 2]

        # Алгоритм HPS (Harmonic Product Spectrum)
        hps_spec = np.copy(magnitude_spec)
        for i in range(2, 5):
            decimated = scipy.signal.decimate(magnitude_spec, i)
            hps_spec[:len(decimated)] *= decimated

        max_ind = np.argmax(hps_spec)
        max_freq = max_ind * (SAMPLE_FREQ / WINDOW_SIZE)
        
        return max_freq