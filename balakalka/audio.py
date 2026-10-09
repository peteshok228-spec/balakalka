"""Запись с микрофона в память: 16 кГц, моно — то, что ждёт Whisper."""

import io
import threading
import wave

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000


class Recorder:
    def __init__(self):
        self._chunks: list[np.ndarray] = []
        self._stream = None
        self._lock = threading.Lock()
        self.level = 0.0  # громкость последнего блока, для индикатора

    def start(self):
        self._chunks = []
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=self._callback
        )
        self._stream.start()

    def _callback(self, indata, frames, time, status):
        with self._lock:
            self._chunks.append(indata[:, 0].copy())
        self.level = float(np.sqrt(np.mean(indata**2)))

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            audio = np.concatenate(self._chunks) if self._chunks else np.zeros(0, np.float32)
            self._chunks = []
        return audio


def duration(audio: np.ndarray) -> float:
    return len(audio) / SAMPLE_RATE


def to_wav_bytes(audio: np.ndarray) -> bytes:
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()
