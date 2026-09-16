from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from kronos.agent import Agent
from kronos.apps import App, AppCatalog
from kronos.contracts import Registry, Result, Tool, ToolError, obj, string, success
from kronos.files import Files
from kronos.providers import Client, Config, ProviderError
from kronos.runtime import build_registry
from kronos.system import System


class FilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.files = Files([self.root])

    def test_unicode_write_read_and_move(self):
        directory = self.root / "space ü folder"
        self.files.mkdir(str(directory))
        original = directory / "hello.txt"
        self.assertTrue(self.files.write(str(original), "Hello 🌍").ok)
        self.assertEqual(self.files.read(str(original)).data["content"], "Hello 🌍")
        copied = directory / "copy.txt"
        self.files.copy(str(original), str(copied))
        self.files.rename(str(copied), "renamed.txt")
        self.assertFalse(copied.exists())
        self.assertEqual((directory / "renamed.txt").read_text(encoding="utf-8"), "Hello 🌍")

    def test_overwrite_requires_interface_confirmation(self):
        target = self.root / "existing.txt"
        target.write_text("old")
        self.assertEqual(self.files.write(str(target), "new").code, "declined")
        self.assertEqual(target.read_text(), "old")
        self.files.confirm = lambda text: True
        self.assertTrue(self.files.write(str(target), "new").ok)
        self.assertEqual(target.read_text(), "new")

    def test_changed_during_confirmation_is_not_overwritten(self):
        target = self.root / "existing.txt"
        target.write_text("old")
        def approve(text):
            target.write_text("external edit")
            return True
        self.files.confirm = approve
        with self.assertRaisesRegex(ToolError, "changed"):
            self.files.write(str(target), "agent edit")
        self.assertEqual(target.read_text(), "external edit")

    def test_roots_and_binary_boundaries(self):
        with self.assertRaisesRegex(ToolError, "outside"):
            self.files.resolve(str(self.root / ".." / "escape"))
        with self.assertRaisesRegex(ToolError, "root"):
            self.files.resolve(str(self.root), mutation=True)
        target = self.root / "binary"
        target.write_bytes(b"\xff\x00")
        with self.assertRaises(ToolError):
            self.files.read(str(target))

    def test_copy_and_move_do_not_overwrite(self):
        a, b = self.root / "a", self.root / "b"
        a.write_text("first")
        b.write_text("second")
        with self.assertRaises(FileExistsError):
            self.files.copy(str(a), str(b))
        with self.assertRaises(ToolError):
            self.files.move(str(a), str(b))
        self.assertEqual(a.read_text(), "first")
        self.assertEqual(b.read_text(), "second")

    def test_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            link = self.root / "escape"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("Host does not allow test symlinks")
            with self.assertRaisesRegex(ToolError, "outside"):
                self.files.write(str(link / "bad.txt"), "bad")

    def test_large_read_is_rejected(self):
        target = self.root / "large.txt"
        target.write_bytes(b"a" * 100_001)
        with self.assertRaisesRegex(ToolError, "100 KB"):
            self.files.read(str(target))

    def test_trash_decline_does_not_call_backend(self):
        target = self.root / "keep.txt"
        target.write_text("keep")
        backend = MagicMock()
        with patch.dict(sys.modules, {"send2trash": SimpleNamespace(send2trash=backend)}):
            self.assertEqual(self.files.trash(str(target)).code, "declined")
        backend.assert_not_called()
        self.assertTrue(target.exists())


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.registry = build_registry([Path.cwd()])

    def test_bad_arguments_never_reach_handler(self):
        tool = self.registry.tools["volume_set"]
        tool.handler = MagicMock()
        for arguments in ({"percent": True}, {"percent": 101}, {"percent": "50"},
                          {"percent": 50, "confirmed": True}, None, {}, []):
            self.assertEqual(self.registry.execute("volume_set", arguments).code, "invalid_arguments")
        tool.handler.assert_not_called()

    def test_no_shell_tool_or_confirmation_parameter(self):
        self.assertNotIn("shell", self.registry.tools)
        for tool in self.registry.tools.values():
            self.assertNotIn("confirmed", tool.parameters["properties"])

    def test_missing_handler_result_is_not_success(self):
        registry = Registry([Tool("broken", "broken", obj({}), lambda: None)])
        self.assertFalse(registry.execute("broken", {}).ok)


class AppsTests(unittest.TestCase):
    def catalog(self, *apps):
        catalog = AppCatalog()
        catalog.apps = list(apps)
        catalog.refreshed = time.monotonic()
        return catalog

    def test_ambiguous_does_not_launch(self):
        cat = self.catalog(App.make("Studio One", "one", "bundle"), App.make("Studio Two", "two", "bundle"))
        with patch("kronos.apps.run") as execute:
            result = cat.open("studio")
        self.assertEqual(result.code, "ambiguous")
        execute.assert_not_called()

    def test_mac_launch_uses_discovered_path_as_single_argument(self):
        app = App.make("My Fancy App", "/Applications/My Fancy App.app", "bundle")
        cat = self.catalog(app)
        with patch("kronos.apps.run") as execute:
            result = cat.open(app.id)
        execute.assert_called_once_with(["open", "-a", app.target])
        self.assertEqual(result.code, "launch_requested")

    def test_shell_like_query_does_not_execute(self):
        cat = self.catalog(App.make("Editor", "editor", "start_apps"))
        with patch("kronos.apps.subprocess.Popen") as execute:
            result = cat.open("Editor & whoami")
        self.assertEqual(result.code, "not_found")
        execute.assert_not_called()

    def test_windows_uses_inventory_app_id(self):
        app = App.make("Store App", "Vendor.Package!App", "start_apps")
        cat = self.catalog(app)
        with patch("kronos.apps.subprocess.Popen") as execute:
            cat.open(app.id)
        execute.assert_called_once_with(["explorer.exe", "shell:AppsFolder\\Vendor.Package!App"])

    def test_pagination(self):
        cat = self.catalog(*(App.make(f"App {i}", str(i), "bundle") for i in range(5)))
        result = cat.list(offset=2, limit=2)
        self.assertEqual(result.data["total"], 5)
        self.assertEqual([a["name"] for a in result.data["apps"]], ["App 2", "App 3"])


def call(ident="1", name="write", arguments='{"text":"hello"}'):
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": ident, "type": "function", "function": {"name": name, "arguments": arguments}}
    ]}


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.handler = MagicMock(return_value=success("wrote"))
        self.registry = Registry([Tool("write", "write", obj({"text": string("text")}), self.handler, True)])

    def agent(self, replies):
        client = MagicMock()
        client.complete.side_effect = replies
        return Agent(client, self.registry), client

    def test_complete_loop_and_no_duplicate_mutation(self):
        agent, client = self.agent([call(), call("2"), {"content": "Done"}])
        self.assertEqual(agent.ask("write hello"), "Done")
        self.handler.assert_called_once_with(text="hello")
        messages = client.complete.call_args.args[0]
        outcomes = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
        self.assertEqual(outcomes[-1]["code"], "duplicate_suppressed")

    def test_invalid_json_duplicate_keys_and_unknown_args(self):
        for arguments in ('{', '{"text":"a","text":"b"}', '{"text":"a","confirm":true}', '{"text":NaN}'):
            with self.subTest(arguments=arguments):
                agent, _ = self.agent([call(arguments=arguments), {"content": "Invalid"}])
                agent.ask("test")
        self.handler.assert_not_called()

    def test_entire_invalid_envelope_batch_is_rejected(self):
        reply = call()
        reply["tool_calls"].append({"id": "2", "type": "function", "function": None})
        agent, _ = self.agent([reply])
        self.assertIn("batch was not executed", agent.ask("test"))
        self.handler.assert_not_called()

    def test_network_failure_after_action_does_not_repeat_it(self):
        agent, _ = self.agent([call(), ProviderError("timed out")])
        self.assertIn("timed out", agent.ask("test"))
        self.handler.assert_called_once()
        self.assertEqual(agent.turns[0][-2]["role"], "tool")
        self.assertEqual(agent.last_error, "timed out")

    def test_tool_batch_repeated_ids_is_rejected(self):
        reply = call()
        reply["tool_calls"].append(reply["tool_calls"][0])
        agent, _ = self.agent([reply])
        agent.ask("test")
        self.handler.assert_not_called()

    def test_round_budget(self):
        agent, client = self.agent([call(str(i)) for i in range(8)])
        self.assertIn("round limit", agent.ask("test"))
        self.assertEqual(client.complete.call_count, 8)
        self.handler.assert_called_once()


class ProviderTests(unittest.TestCase):
    def test_missing_key_is_actionable_without_network(self):
        client = Client(Config(model="test-model"), key="")
        client.opener = MagicMock()
        with self.assertRaisesRegex(ProviderError, "key"):
            client.complete([], [])
        client.opener.open.assert_not_called()

    def test_three_provider_endpoints_and_tool_payload(self):
        for provider, endpoint in (("groq", "https://api.groq.com/openai/v1/chat/completions"),
                                   ("nvidia", "https://integrate.api.nvidia.com/v1/chat/completions"),
                                   ("openrouter", "https://openrouter.ai/api/v1/chat/completions")):
            with self.subTest(provider=provider):
                client = Client(Config(provider=provider, model="chosen-model"), key="test-secret")
                response = MagicMock()
                response.__enter__.return_value.read.return_value = b'{"choices":[{"message":{"content":"hello"}}]}'
                client.opener = MagicMock()
                client.opener.open.return_value = response
                self.assertEqual(client.complete([], []), {"content": "hello"})
                request = client.opener.open.call_args.args[0]
                self.assertEqual(request.full_url, endpoint)
                self.assertEqual(json.loads(request.data)["model"], "chosen-model")
                self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")

    def test_openrouter_auto_uses_max_router_tier(self):
        client = Client(Config(provider="openrouter", model="openrouter/auto"), key="test-secret")
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"choices":[{"message":{"content":"hello"}}]}'
        client.opener = MagicMock()
        client.opener.open.return_value = response
        client.complete([], [])
        request = client.opener.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "openrouter/auto")
        self.assertEqual(payload["plugins"], [{"id": "auto-router", "cost_tier": "max"}])

    def test_http_body_with_secret_is_not_exposed(self):
        client = Client(Config(model="m"), key="test-secret")
        client.opener = MagicMock()
        client.opener.open.side_effect = urllib.error.HTTPError("https://example", 401, "test-secret", {}, io.BytesIO(b"test-secret"))
        with self.assertRaises(ProviderError) as caught:
            client.complete([], [])
        self.assertNotIn("test-secret", str(caught.exception))

    def test_truncated_output_is_rejected(self):
        client = Client(Config(model="m"), key="k")
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"choices":[{"finish_reason":"length","message":{}}]}'
        client.opener = MagicMock()
        client.opener.open.return_value = response
        with self.assertRaisesRegex(ProviderError, "truncated"):
            client.complete([], [])

    def test_config_rejects_raw_keys_and_invalid_types(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / "config.json"
            for data in ({"api_key": "secret"}, {"timeout": True}, {"provider": "unknown"}, {"provider": []}):
                path.write_text(json.dumps(data))
                with self.assertRaises(ProviderError):
                    Config.load(path)


class SystemTests(unittest.TestCase):
    def test_windows_volume_uses_scalar_and_readback(self):
        system = System()
        system.platform = "Windows"
        endpoint = MagicMock()
        endpoint.GetMasterVolumeLevelScalar.side_effect = [0.2, 0.5]
        endpoint.GetMute.return_value = 0
        with patch.object(system, "_endpoint", return_value=endpoint):
            self.assertTrue(system.volume(50).ok)
        endpoint.SetMasterVolumeLevelScalar.assert_called_once_with(0.5, None)

    def test_mute_is_explicit_not_toggle(self):
        system = System()
        system.platform = "Windows"
        endpoint = MagicMock()
        endpoint.GetMasterVolumeLevelScalar.return_value = 0.5
        endpoint.GetMute.side_effect = [0, 1]
        with patch.object(system, "_endpoint", return_value=endpoint):
            self.assertTrue(system.mute(True).ok)
        endpoint.SetMute.assert_called_once_with(1, None)

    def test_failed_readback_is_not_success(self):
        system = System()
        system.platform = "Windows"
        with patch.object(system, "volume_state", return_value={"volume": 10, "muted": False}), patch.object(system, "_endpoint"):
            self.assertEqual(system.volume(70).code, "verification_failed")

    def test_mac_volume_contract(self):
        system = System()
        system.platform = "Darwin"
        with patch("kronos.system.run", side_effect=[SimpleNamespace(stdout="20|false"), SimpleNamespace(stdout=""), SimpleNamespace(stdout="60|false")]) as execute:
            self.assertTrue(system.volume(60).ok)
        self.assertEqual(execute.call_args_list[1].args[0], ["osascript", "-e", "set volume output volume 60"])

    def test_mac_missing_brightness_utility_is_explicit(self):
        system = System()
        system.platform = "Darwin"
        with patch("kronos.system.shutil.which", return_value=None), patch("kronos.system.run") as execute:
            with self.assertRaisesRegex(ToolError, "optional brightness"):
                system.brightness(60)
        execute.assert_not_called()

    def test_windows_brightness_accepts_void_method_and_verifies(self):
        system = System()
        system.platform = "Windows"
        with patch.object(system, "brightness_state", side_effect=[[{"brightness": 60}], [{"brightness": 61}]]), patch("kronos.system.powershell", return_value="") as execute:
            self.assertTrue(system.brightness(61).ok)
        self.assertIn("$null -ne $r.ReturnValue", execute.call_args.args[0])

    def test_mac_settings_does_not_claim_section_navigation(self):
        system = System()
        system.platform = "Darwin"
        with patch("kronos.system.run"):
            self.assertIn("not implemented", system.settings("display").message)

    def test_mac_brightness_parses_upstream_output_and_verifies(self):
        system = System()
        system.platform = "Darwin"
        before = "display 0: main, active, awake, online, built-in, ID 0x1\ndisplay 0: brightness 0.600000\n"
        after = "display 0: main, active, awake, online, built-in, ID 0x1\ndisplay 0: brightness 0.800000\n"
        with patch("kronos.system.shutil.which", return_value="/opt/homebrew/bin/brightness"), patch("kronos.system.run", side_effect=[SimpleNamespace(stdout=before), SimpleNamespace(stdout=""), SimpleNamespace(stdout=after)]) as execute:
            self.assertTrue(system.brightness(80).ok)
        self.assertEqual(execute.call_args_list[1].args[0], ["/opt/homebrew/bin/brightness", "0.8"])


class StartupTests(unittest.TestCase):
    def test_tools_start_without_optional_dependencies_or_credentials(self):
        # -S excludes site-packages: proves UI, audio, SDK and OS libraries are lazy.
        process = subprocess.run([sys.executable, "-S", "-m", "kronos", "tools"], capture_output=True, text=True, timeout=15)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(len(json.loads(process.stdout)), 15)


if __name__ == "__main__":
    unittest.main()
