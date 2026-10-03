"""Safety regression tests for the macOS WhatsApp send path.

Run: python3 -m unittest discover -s tests
These tests mock macOS UI calls; they do not send any messages.
"""
import unittest
from unittest.mock import patch

from plugins import _whatsapp_core as wa


class WhatsAppSendSafetyTests(unittest.TestCase):
    def setUp(self):
        self.driver = wa._MacWhatsApp()

    def test_no_pending_draft_never_sends(self):
        with patch.object(wa, "pyautogui") as gui:
            sent, reason = self.driver.send_prepared()
            self.assertFalse(sent)
            self.assertIn("No verified", reason)
            gui.press.assert_not_called()

    def test_wrong_chat_never_sends(self):
        self.driver._prepared = ("Alice", "Hello")
        with patch.object(wa.platform, "system", return_value="Darwin"), \
             patch.object(wa, "pyautogui") as gui, \
             patch.object(wa, "_front_app", return_value="WhatsApp"), \
             patch.object(wa, "_contact_visible_exact", return_value=False):
            sent, reason = self.driver.send_prepared()
            self.assertFalse(sent)
            self.assertIn("Nothing was sent", reason)
            gui.press.assert_not_called()
            self.assertIsNone(self.driver._prepared)

    def test_send_key_is_not_delivery_proof(self):
        self.driver._prepared = ("Alice", "Hello")
        with patch.object(wa.platform, "system", return_value="Darwin"), \
             patch.object(wa, "pyautogui") as gui, \
             patch.object(wa, "_front_app", return_value="WhatsApp"), \
             patch.object(wa, "_contact_visible_exact", return_value=True):
            sent, reason = self.driver.send_prepared()
            self.assertFalse(sent)
            self.assertIn("unverified", reason)
            gui.press.assert_called_once_with("enter")
            self.assertIsNone(self.driver._prepared)


if __name__ == "__main__":
    unittest.main()
