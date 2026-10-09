"""Балакалка: нажал комбинацию — говоришь — нажал ещё раз — текст вставлен."""

import os
import sys
import threading
import time
import traceback

from pynput import keyboard

from . import config
from .audio import Recorder, duration
from .output import beep, deliver

MIN_SECONDS = 0.4


class _Headless:
    """Заглушка вместо плашки, если show_overlay выключен."""

    def show(self, *args, **kwargs): pass
    def hide(self): pass


class App:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.recorder = Recorder()
        self.state = "idle"  # idle / recording / processing
        self.lock = threading.Lock()
        self.started_at = 0.0
        self.transcriber = None
        self.transcriber_ready = threading.Event()
        self.polisher = None
        self.overlay = _Headless()

        if cfg.get("polish", True):
            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("ВНИМАНИЕ: не указан ключ Claude (anthropic_api_key в config.json).\n"
                      "Текст будет вставляться без расстановки знаков и исправлений.\n")
            from .polish import Polisher
            self.polisher = Polisher(cfg)
        # Модель Whisper грузится в фоне: записывать можно сразу.
        threading.Thread(target=self._load_transcriber, daemon=True).start()

    def _load_transcriber(self):
        from .transcribe import make_transcriber
        try:
            self.transcriber = make_transcriber(self.cfg)
            print("Распознавание речи готово.")
        except Exception as e:
            print(f"Не удалось запустить распознавание речи: {e}")
        self.transcriber_ready.set()

    # --- горячие клавиши (вызываются из потока pynput, блокировать нельзя) ---

    def toggle(self):
        with self.lock:
            if self.state == "idle":
                self._start()
            elif self.state == "recording":
                self._stop()
            # во время обработки нажатие игнорируем

    def cancel(self):
        with self.lock:
            if self.state != "recording":
                return
            self.recorder.stop()
            self.state = "idle"
        beep(300, self.cfg)
        self.overlay.show("error", "Отменено", 1200)
        print("Запись отменена.")

    def _start(self):
        try:
            self.recorder.start()
        except Exception as e:
            self.overlay.show("error", "Нет доступа к микрофону", 3000)
            print(f"Микрофон: {e}")
            return
        self.state = "recording"
        self.started_at = time.time()
        beep(880, self.cfg)
        threading.Thread(target=self._tick, daemon=True).start()
        print("● Запись…")

    def _tick(self):
        while self.state == "recording":
            secs = int(time.time() - self.started_at)
            bars = "▮" * min(5, int(self.recorder.level * 60)) or "▯"
            self.overlay.show("recording", f"● Запись  {secs // 60}:{secs % 60:02d}  {bars}")
            time.sleep(0.2)

    def _stop(self):
        audio = self.recorder.stop()
        self.state = "processing"
        beep(520, self.cfg)
        threading.Thread(target=self._process, args=(audio,), daemon=True).start()

    # --- обработка ---

    def _process(self, audio):
        try:
            if duration(audio) < MIN_SECONDS:
                self.overlay.hide()
                return
            self.overlay.show("processing", "Распознаю речь…")
            self.transcriber_ready.wait()
            if self.transcriber is None:
                raise RuntimeError("распознавание речи не запущено, см. сообщения выше")
            raw = self.transcriber(audio)
            print(f"  сырой текст: {raw}")
            if not raw:
                self.overlay.show("error", "Ничего не расслышал", 1500)
                return

            text = raw
            if self.polisher:
                self.overlay.show("processing", "Расставляю знаки…")
                try:
                    text = self.polisher(raw)
                except Exception as e:
                    # Лучше вставить сырой текст, чем потерять диктовку.
                    print(f"  Claude недоступен ({e}), вставляю сырой текст.")
            print(f"  готово: {text}")
            deliver(text, self.cfg)
            self.overlay.show("done", "✓ Вставлено", 900)
        except Exception as e:
            traceback.print_exc()
            self.overlay.show("error", f"Ошибка: {e}"[:80], 4000)
        finally:
            self.state = "idle"


def main():
    cfg = config.load()
    app = App(cfg)

    hotkeys = keyboard.GlobalHotKeys({
        cfg["hotkey"]: app.toggle,
        cfg["cancel_hotkey"]: app.cancel,
    })
    hotkeys.start()

    print(f"\nБалакалка запущена. Настройки: {config.CONFIG_PATH}")
    print(f"  {cfg['hotkey']} — начать / закончить диктовку")
    print(f"  {cfg['cancel_hotkey']} — отменить запись")
    print("  Ctrl+C в этом окне — выход\n")

    try:
        # На macOS Tk и перехват клавиш pynput плохо уживаются в одном процессе.
        overlay = None
        if cfg.get("show_overlay", True) and sys.platform != "darwin":
            try:
                from .overlay import Overlay
                overlay = Overlay()
            except Exception as e:  # нет tkinter или графической среды
                print(f"Индикатор отключён: {e}")
        if overlay:
            app.overlay = overlay
            overlay.run()
        else:
            while hotkeys.is_alive():
                hotkeys.join(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        hotkeys.stop()
