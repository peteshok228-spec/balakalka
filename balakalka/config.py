"""Настройки: config.json рядом с программой, создаётся при первом запуске."""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
HISTORY_PATH = ROOT / "history.txt"

DEFAULTS = {
    # Комбинация клавиш: нажал — запись пошла, нажал ещё раз — текст вставлен.
    # Формат pynput: <ctrl>, <alt>, <shift>, <cmd>, <space>, буквы.
    "hotkey": "<ctrl>+<shift>+<space>",
    # Отменить текущую запись без вставки.
    "cancel_hotkey": "<ctrl>+<shift>+<backspace>",

    "language": "ru",

    # Распознавание речи: "local" (faster-whisper на вашем ПК)
    # или "openai" (любой OpenAI-совместимый сервис: OpenAI, Groq).
    "stt_backend": "local",
    "local_model": "large-v3-turbo",   # tiny / base / small / medium / large-v3 / large-v3-turbo
    "local_device": "auto",            # auto / cpu / cuda
    "openai_model": "gpt-4o-transcribe",
    "openai_base_url": None,           # для Groq: "https://api.groq.com/openai/v1"
    "openai_api_key": None,            # или переменная окружения OPENAI_API_KEY

    # Доводка текста через Claude: пунктуация, заглавные, созвучные слова.
    "polish": True,
    "claude_model": "claude-opus-5-5",
    "claude_effort": "low",            # low быстрее; medium/high — внимательнее, но дольше
    "anthropic_api_key": None,         # или переменная окружения ANTHROPIC_API_KEY
    "remove_fillers": True,            # убирать «э-э», «ну», «как бы», повторы
    # Ваши слова, имена и термины — помогают и Whisper, и Claude.
    "vocabulary": [],
    # Дополнительные пожелания к оформлению, например «пиши «ё»».
    "extra_instructions": "",

    # Что делать с готовым текстом.
    "auto_paste": True,                # вставить в активное окно (Ctrl+V)
    "restore_clipboard": True,         # вернуть прежнее содержимое буфера после вставки
    "save_history": True,              # дописывать каждую диктовку в history.txt
    "show_overlay": True,              # маленький индикатор поверх окон
    "sounds": True,
}


def load() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    else:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULTS, f, ensure_ascii=False, indent=2)
    # Ключи из config.json пробрасываем в окружение, чтобы SDK их подхватили.
    if cfg.get("anthropic_api_key"):
        os.environ.setdefault("ANTHROPIC_API_KEY", cfg["anthropic_api_key"])
    if cfg.get("openai_api_key"):
        os.environ.setdefault("OPENAI_API_KEY", cfg["openai_api_key"])
    return cfg
