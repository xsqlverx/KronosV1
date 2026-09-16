import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from kronos.credentials import SetupError, save_connection
from kronos.providers import find_key


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "config.json"
        self.store = MagicMock()
        self.store.get_password.return_value = "fake-test-key"
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_key_is_stored_and_verified_but_not_in_config(self):
        self.path.write_text('{"timeout":79,"max_tokens":1024}')
        save_connection(self.path, "groq", "model/id", "fake-test-key", self.store)
        self.store.set_password.assert_called_once_with("kronos", "groq", "fake-test-key")
        self.assertEqual(json.loads(self.path.read_text())["model"], "model/id")
        self.assertNotIn("fake-test-key", self.path.read_text())
        self.assertEqual(json.loads(self.path.read_text())["timeout"], 79)

    def test_storage_failure_preserves_existing_config_and_redacts_exception(self):
        self.path.write_text('{"model":"old"}')
        self.store.set_password.side_effect = RuntimeError("fake-test-key")
        with self.assertRaises(SetupError) as caught:
            save_connection(self.path, "groq", "model/id", "fake-test-key", self.store)
        self.assertNotIn("fake-test-key", str(caught.exception))
        self.assertEqual(json.loads(self.path.read_text())["model"], "old")
        self.assertEqual(len(list(self.path.parent.iterdir())), 1)

    def test_failed_readback_is_not_reported_as_saved(self):
        self.store.get_password.return_value = None
        with self.assertRaises(SetupError):
            save_connection(self.path, "groq", "model/id", "fake-test-key", self.store)
        self.assertFalse(self.path.exists())

    def test_invalid_input_does_not_touch_store(self):
        for provider, model, key in (("bad", "id", "key"), ("groq", "", "key"), ("groq", "id", ""), ("groq", "id", "key\nsecond")):
            with self.assertRaises(SetupError):
                save_connection(self.path, provider, model, key, self.store)
        self.store.set_password.assert_not_called()

    def test_environment_conflict_is_explained(self):
        with patch.dict(os.environ, {"KRONOS_MODEL": "other"}):
            with self.assertRaisesRegex(SetupError, "KRONOS_MODEL"):
                save_connection(self.path, "groq", "model/id", "fake-test-key", self.store)

    def test_saved_key_wins_over_old_environment_key(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "old-key"}), patch.dict("sys.modules", {"keyring": self.store}):
            self.assertEqual(find_key("groq"), "fake-test-key")


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication, QLineEdit
    from kronos.setup_ui import SetupDialog
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, "Install requirements-kronos.txt for native UI tests")
class SetupWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.window = SetupDialog(Path(self.temp.name) / "config.json")
        self.window.show()
        self.app.processEvents()
        self.addCleanup(self.window.close)

    def test_mask_show_paste_and_provider_change(self):
        self.assertEqual(self.window.key.echoMode(), QLineEdit.EchoMode.Password)
        # Do not overwrite the user's real clipboard during this test.
        clipboard = MagicMock()
        clipboard.text.return_value = "fake-test-key"
        with patch("kronos.setup_ui.QApplication.clipboard", return_value=clipboard):
            self.window.paste.click()
        self.assertEqual(self.window.key.text(), "fake-test-key")
        self.window.reveal.click()
        self.assertEqual(self.window.key.echoMode(), QLineEdit.EchoMode.Normal)
        self.window.provider_buttons["nvidia"].click()
        self.assertEqual(self.window.key.text(), "")
        self.assertEqual(self.window.key.echoMode(), QLineEdit.EchoMode.Password)

    def test_empty_key_shows_inline_error(self):
        self.window.save_button.click()
        self.assertIn("API key", self.window.status.text())
        self.assertIsNone(self.window.worker)

    def test_async_save_and_continue(self):
        self.window.key.setText("fake-test-key")
        with patch("kronos.setup_ui.save_connection") as save:
            self.window.save_button.click()
            for _ in range(100):
                QTest.qWait(10)
                if self.window.saved:
                    break
        self.assertTrue(self.window.saved)
        self.assertEqual(self.window.key.text(), "")
        self.assertIn("Continue", self.window.save_button.text())
        save.assert_called_once()
        self.window.save_button.click()
        self.assertEqual(self.window.result(), 1)

    def test_async_failure_keeps_form_editable(self):
        self.window.key.setText("fake-test-key")
        with patch("kronos.setup_ui.save_connection", side_effect=SetupError("Keychain unavailable")):
            self.window.save_button.click()
            for _ in range(100):
                QTest.qWait(10)
                if self.window.save_button.isEnabled():
                    break
        self.assertFalse(self.window.saved)
        self.assertTrue(self.window.key.isEnabled())
        self.assertIn("Keychain unavailable", self.window.status.text())
