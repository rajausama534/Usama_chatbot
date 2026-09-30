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


def _normalise_name(text: str) -> str:
    return " ".join((text or "").casefold().split())


def _visible_whatsapp_text() -> str:
    """Best-effort Accessibility read of visible WhatsApp UI text.

    This deliberately fails closed: if macOS Accessibility cannot expose the
    chat title, the driver will refuse to type rather than guess.
    """
    script = r'''
tell application "System Events"
    if not (exists process "WhatsApp") then return ""
    tell process "WhatsApp"
        set frontmost to true
        if not (exists window 1) then return ""
        set outText to ""
        try
            set elems to entire contents of window 1
            repeat with e in elems
                try
                    if role of e is "AXStaticText" then
                        set v to value of e as text
                        if v is not "" then set outText to outText & v & linefeed
                    end if
                end try
            end repeat
        end try
        return outText
    end tell
end tell
'''
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=8)
    if r.returncode != 0:
        return ""
    return (r.stdout or "").strip()


def _contact_visible_exact(receiver: str) -> bool:
    want = _normalise_name(receiver)
    if not want:
        return False
    text = _visible_whatsapp_text()
    if not text:
        return False
    lines = [_normalise_name(x) for x in text.splitlines() if x.strip()]
    return want in lines


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
        pyautogui.press("esc")  # close the search surface before verification
        time.sleep(0.35)

        if "whatsapp" not in _front_app().lower():
            return False, "WhatsApp lost focus before the conversation opened"

        # Fail closed. Never type into a chat unless the requested contact name
        # is actually visible in WhatsApp's current conversation UI.
        if not _contact_visible_exact(receiver):
            return False, (
                f"Could not verify that the open chat is exactly '{receiver}'. "
                "Message was not typed or sent."
            )

        # Type only after exact recipient verification. Do NOT send yet.
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
