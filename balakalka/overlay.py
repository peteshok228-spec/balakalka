"""Маленькая плашка поверх всех окон: «Запись», «Обработка», «Готово»."""

import queue
import signal
import sys
import tkinter as tk

COLORS = {
    "recording": "#d93636",
    "processing": "#d98c1a",
    "done": "#2e9e4f",
    "error": "#7a7a7a",
}


class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", 0.92)
        except tk.TclError:
            pass
        self.label = tk.Label(
            self.root, font=("Segoe UI", 12, "bold"), fg="white", padx=16, pady=8
        )
        self.label.pack()
        self.root.withdraw()
        if sys.platform == "win32":
            self._never_take_focus()
        self._queue: queue.Queue = queue.Queue()
        self._hide_job = None
        self.root.after(50, self._poll)

    def _never_take_focus(self):
        # Иначе плашка может перехватить фокус, и Ctrl+V уйдёт в неё, а не в ваше окно.
        import ctypes

        self.root.update_idletasks()
        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(self.root.winfo_id())
        GWL_EXSTYLE, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW = -20, 0x08000000, 0x00000080
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)

    # Вызывается из любого потока.
    def show(self, state: str, text: str, hide_after_ms: int | None = None):
        self._queue.put((state, text, hide_after_ms))

    def hide(self):
        self._queue.put((None, None, None))

    def _poll(self):
        try:
            while True:
                state, text, hide_after = self._queue.get_nowait()
                self._apply(state, text, hide_after)
        except queue.Empty:
            pass
        self.root.after(50, self._poll)

    def _apply(self, state, text, hide_after):
        if self._hide_job:
            self.root.after_cancel(self._hide_job)
            self._hide_job = None
        if state is None:
            self.root.withdraw()
            return
        self.label.config(text=text, bg=COLORS[state])
        self.root.configure(bg=COLORS[state])
        self.root.update_idletasks()
        w, h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = self.root.winfo_screenheight() - h - 90
        self.root.geometry(f"+{x}+{y}")
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        if hide_after:
            self._hide_job = self.root.after(hide_after, self.root.withdraw)

    def run(self):
        signal.signal(signal.SIGINT, lambda *_: self.root.quit())
        self.root.mainloop()
