"""Готовый текст -> активное окно (через буфер обмена и Ctrl+V), звуки, история."""

import sys
import threading
import time
from datetime import datetime

import numpy as np
import pyperclip
import sounddevice as sd
from pynput.keyboard import Controller, Key

from .config import HISTORY_PATH

_keyboard = Controller()
_PASTE_MOD = Key.cmd if sys.platform == "darwin" else Key.ctrl


def deliver(text: str, cfg: dict):
    try:
        previous = pyperclip.paste()
    except Exception:
        previous = None
    pyperclip.copy(text)

    if cfg.get("auto_paste", True):
        time.sleep(0.05)
        with _keyboard.pressed(_PASTE_MOD):
            _keyboard.press("v")
            _keyboard.release("v")
        # Возвращаем прежний буфер, когда приложение уже забрало вставку.
        if cfg.get("restore_clipboard", True) and previous is not None:
            threading.Timer(0.6, lambda: pyperclip.copy(previous)).start()

    if cfg.get("save_history", True):
        with open(HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}]\n{text}\n\n")


def beep(freq: float, cfg: dict, duration: float = 0.08):
    if not cfg.get("sounds", True):
        return
    sr = 44100
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    tone = 0.2 * np.sin(2 * np.pi * freq * t) * np.hanning(len(t))
    try:
        sd.play(tone.astype(np.float32), sr)
    except Exception:
        pass
