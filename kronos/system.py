"""OS settings adapters. Platform imports occur only inside the relevant branch."""
from __future__ import annotations

import json
import platform
import re
import shutil

from .apps import powershell, run
from .contracts import Result, ToolError, success


SETTINGS = {
    "home": "ms-settings:", "display": "ms-settings:display",
    "sound": "ms-settings:sound", "network": "ms-settings:network",
    "apps": "ms-settings:appsfeatures", "privacy": "ms-settings:privacy",
}


class System:
    def __init__(self):
        self.platform = platform.system()

    def _endpoint(self):
        try:
            from pycaw.pycaw import AudioUtilities
            device = AudioUtilities.GetSpeakers()
            return device.EndpointVolume
        except ImportError:
            raise ToolError("missing_dependency", "Windows volume requires pycaw; install requirements-kronos.txt.") from None
        except Exception:
            raise ToolError("audio_unavailable", "Windows could not access the default audio output device.") from None

    def volume_state(self) -> dict:
        if self.platform == "Windows":
            endpoint = self._endpoint()
            return {"volume": round(endpoint.GetMasterVolumeLevelScalar() * 100), "muted": bool(endpoint.GetMute())}
        if self.platform == "Darwin":
            output = run(["osascript", "-e", 'set s to get volume settings', "-e",
                          'return (output volume of s as text) & "|" & (output muted of s as text)']).stdout.strip()
            parts = output.split("|")
            if len(parts) != 2 or parts[1] not in ("true", "false"):
                raise ToolError("invalid_os_response", "Could not read macOS volume settings.")
            return {"volume": int(parts[0]), "muted": parts[1] == "true"}
        raise ToolError("unsupported", "Volume control supports Windows and macOS.")

    def volume(self, percent: int) -> Result:
        before = self.volume_state()
        if self.platform == "Windows":
            self._endpoint().SetMasterVolumeLevelScalar(percent / 100, None)
        elif self.platform == "Darwin":
            run(["osascript", "-e", f"set volume output volume {percent}"])
        after = self.volume_state()
        if abs(after["volume"] - percent) > 1:
            return Result(False, "verification_failed", "Volume read-back did not match the requested value.", {"before": before, "after": after})
        return success("Volume set and verified.", before=before, after=after)

    def mute(self, muted: bool) -> Result:
        before = self.volume_state()
        if self.platform == "Windows":
            self._endpoint().SetMute(int(muted), None)
        elif self.platform == "Darwin":
            run(["osascript", "-e", "set volume " + ("with" if muted else "without") + " output muted"])
        after = self.volume_state()
        if after["muted"] != muted:
            return Result(False, "verification_failed", "Mute read-back did not match the requested state.", {"before": before, "after": after})
        return success("Mute state set and verified.", before=before, after=after)

    def brightness_state(self) -> list[dict]:
        if self.platform == "Windows":
            raw = powershell("$ErrorActionPreference='Stop'; @(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness) | Select-Object InstanceName,CurrentBrightness | ConvertTo-Json -Compress")
            records = json.loads(raw) if raw.strip() else []
            if isinstance(records, dict):
                records = [records]
            if not records:
                raise ToolError("unsupported", "This display does not expose Windows WMI brightness control (common with external monitors).")
            return [{"display": r["InstanceName"], "brightness": int(r["CurrentBrightness"])} for r in records]
        if self.platform == "Darwin":
            binary = shutil.which("brightness")
            if binary is None:
                raise ToolError("unsupported", "Absolute macOS brightness needs the optional brightness utility and a supported display. Use settings_open(display) for now.")
            output = run([binary, "-l"]).stdout
            values = re.findall(r"display\s+(\d+):.*?brightness\s+([0-9.]+)", output)
            if not values:
                raise ToolError("unsupported", "The brightness utility reported no controllable displays.")
            return [{"display": ident, "brightness": round(float(value) * 100)} for ident, value in values]
        raise ToolError("unsupported", "Brightness supports Windows and macOS only.")

    def brightness(self, percent: int) -> Result:
        before = self.brightness_state()
        if self.platform == "Windows":
            powershell("$ErrorActionPreference='Stop'; $monitors=@(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods); "
                       "if ($monitors.Count -eq 0) { throw 'No controllable displays' }; "
                       f"foreach ($monitor in $monitors) {{ $r=Invoke-CimMethod -InputObject $monitor -MethodName WmiSetBrightness -Arguments @{{Timeout=[uint32]0;Brightness=[byte]{percent}}}; if ($null -ne $r.ReturnValue -and $r.ReturnValue -ne 0) {{ throw 'Brightness method failed' }} }}")
        elif self.platform == "Darwin":
            run([shutil.which("brightness"), str(percent / 100)])
        after = self.brightness_state()
        if not after or any(abs(item["brightness"] - percent) > 2 for item in after):
            return Result(False, "verification_failed", "Brightness read-back did not match on every controllable display.", {"before": before, "after": after})
        return success("Brightness set and verified on controllable displays.", before=before, after=after)

    def get(self) -> Result:
        capabilities = {}
        for name, read in (("audio", self.volume_state), ("brightness", self.brightness_state)):
            try:
                capabilities[name] = {"available": True, "state": read()}
            except (ToolError, OSError, ValueError) as exc:
                capabilities[name] = {"available": False, "reason": str(exc)}
        return success("System capabilities checked without changing settings.", platform=self.platform, capabilities=capabilities)

    def settings(self, section: str = "home") -> Result:
        if self.platform == "Windows":
            import os
            os.startfile(SETTINGS[section])
            return Result(True, "launch_requested", f"Asked Windows to open {section} settings; window readiness is not verified.")
        if self.platform == "Darwin":
            run(["open", "-b", "com.apple.systempreferences"])
            return Result(True, "launch_requested", "Asked macOS to open System Settings. Select the requested section in the window; direct pane navigation is not implemented.", {"section": section})
        raise ToolError("unsupported", "Settings launcher supports Windows and macOS.")
