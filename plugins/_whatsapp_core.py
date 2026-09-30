"""
macOS WhatsApp driver for Usama.

Flow: open WhatsApp -> focus search -> search recipient -> open result ->
verify the active window is WhatsApp -> type message -> send.
The public send_message action owns the single final confirmation gate.
"""
from __future__ import annotations

import platform
import subprocess
import time

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.08
except Exception:
    pyautogui = None

try:
    import pyperclip
except Exception:
    pyperclip = None


def _paste(text: str) -> None:
    if pyautogui is None:
        raise RuntimeError("PyAutoGUI is not installed")
    if pyperclip is not None:
        pyperclip.copy(text)
        time.sleep(0.1)
        pyautogui.hotkey("command", "v")
    else:
        pyautogui.write(text, interval=0.02)


def _front_app() -> str:
    script = 'tell application "System Events" to get name of first application process whose frontmost is true'
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
    return (r.stdout or "").strip()


class _MacWhatsApp:
    def prepare_message_to(self, receiver: str, message: str):
        if platform.system() != "Darwin":
            return False, "macOS WhatsApp driver is only available on macOS"
        if pyautogui is None:
            return False, "PyAutoGUI is not installed"

        receiver = (receiver or "").strip()
        message = (message or "").strip()
        if not receiver or not message:
            return False, "recipient or message is empty"

        r = subprocess.run(["open", "-a", "WhatsApp"], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return False, "WhatsApp app could not be opened"
        time.sleep(2.0)

        if "whatsapp" not in _front_app().lower():
            return False, "WhatsApp is not the active application"

        # WhatsApp's own search shortcut. We do not use Cmd+F blindly in another app.
        pyautogui.hotkey("command", "f")
        time.sleep(0.5)
        pyautogui.hotkey("command", "a")
        pyautogui.press("delete")
        _paste(receiver)
        time.sleep(1.5)

        # Open the first matching conversation.
        pyautogui.press("down")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(1.0)

        if "whatsapp" not in _front_app().lower():
            return False, "WhatsApp lost focus before the conversation opened"

        # Type only after the recipient search/open step is complete. Do NOT send yet.
        _paste(message)
        time.sleep(0.25)

        if "whatsapp" not in _front_app().lower():
            return False, "WhatsApp lost focus while preparing the message"
        return True, ""

    def send_prepared(self):
        if platform.system() != "Darwin" or pyautogui is None:
            return False, "WhatsApp send control is unavailable"
        if "whatsapp" not in _front_app().lower():
            return False, "WhatsApp is not the active application"
        pyautogui.press("enter")
        time.sleep(0.5)
        if "whatsapp" not in _front_app().lower():
            return False, "WhatsApp lost focus while sending"
        return True, ""

    def send_message_to(self, receiver: str, message: str):
        ok, why = self.prepare_message_to(receiver, message)
        if not ok:
            return False, why
        return self.send_prepared()


_driver = _MacWhatsApp()


def get():
    if platform.system() != "Darwin":
        return None, "This bundled driver currently supports macOS only"
    if pyautogui is None:
        return None, "PyAutoGUI is not installed"
    return _driver, ""
