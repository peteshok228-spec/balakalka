"""Речь -> сырой текст. Два варианта: локальный faster-whisper или облачный API."""

import numpy as np

from .audio import to_wav_bytes


def _vocab_prompt(cfg: dict) -> str | None:
    # Whisper подстраивается под стиль и слова из подсказки: знакомые термины
    # распознаются правильнее, а пример с пунктуацией подталкивает её расставлять.
    words = cfg.get("vocabulary") or []
    base = "Привет. Сейчас я продиктую текст, с запятыми и точками."
    return f"{base} Термины: {', '.join(words)}." if words else base


class LocalTranscriber:
    def __init__(self, cfg: dict):
        from faster_whisper import WhisperModel

        device = cfg["local_device"]
        if device == "auto":
            try:
                import ctranslate2

                device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
            except Exception:
                device = "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        print(f"Загружаю модель Whisper «{cfg['local_model']}» ({device})… "
              "Первый раз она скачивается, это может занять несколько минут.")
        self.model = WhisperModel(cfg["local_model"], device=device, compute_type=compute_type)
        self.cfg = cfg

    def __call__(self, audio: np.ndarray) -> str:
        segments, _ = self.model.transcribe(
            audio,
            language=self.cfg["language"],
            initial_prompt=_vocab_prompt(self.cfg),
            vad_filter=True,  # вырезает тишину — меньше «галлюцинаций» на паузах
            beam_size=5,
        )
        return " ".join(s.text.strip() for s in segments).strip()


class ApiTranscriber:
    """OpenAI или любой совместимый сервис (Groq: whisper-large-v3-turbo)."""

    def __init__(self, cfg: dict):
        from openai import OpenAI

        self.client = OpenAI(base_url=cfg.get("openai_base_url") or None)
        self.cfg = cfg

    def __call__(self, audio: np.ndarray) -> str:
        result = self.client.audio.transcriptions.create(
            model=self.cfg["openai_model"],
            file=("speech.wav", to_wav_bytes(audio), "audio/wav"),
            language=self.cfg["language"],
            prompt=_vocab_prompt(self.cfg),
        )
        return result.text.strip()


def make_transcriber(cfg: dict):
    if cfg["stt_backend"] == "openai":
        return ApiTranscriber(cfg)
    return LocalTranscriber(cfg)
