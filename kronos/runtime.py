"""Composition root; tools do not depend on providers or a particular UI."""
from pathlib import Path

from .apps import AppCatalog
from .contracts import Registry, Tool, integer, obj, string
from .files import Files
from .system import SETTINGS, System


def build_registry(roots: list[Path], confirm=None) -> Registry:
    apps, files, system = AppCatalog(), Files(roots, confirm), System()
    path = string("File/folder path. Relative paths resolve from the working directory; ~ means the user home.")
    pagination = {"offset": integer("Starting item offset", 0, 1_000_000), "limit": integer("Maximum returned items", 1, 100)}
    return Registry([
        Tool("apps_list", "Discover installed applications and return IDs. Query filters names; refresh rescans OS inventories. Paginate when needed.",
             obj({"query": string("App name filter", empty=True), "refresh": {"type": "boolean"}, **pagination}, []), apps.list),
        Tool("app_open", "Open an installed app by its exact name or discovered ID. Ambiguous matches require the user's choice. No hardcoded app list.",
             obj({"query": string("Installed app name or discovered ID")}), apps.open, True),
        Tool("files_list", "List a folder's immediate contents. Paginate large folders.",
             obj({"path": path, **pagination}, ["path"]), files.list),
        Tool("file_read", "Read a UTF-8 text file up to 100 KB. Binary documents are unsupported.", obj({"path": path}), files.read),
        Tool("folder_create", "Create a folder and missing parent folders.", obj({"path": path}), files.mkdir, True),
        Tool("file_write", "Write UTF-8 text up to 100 KB. Existing files require local user confirmation. Create parent folder first.",
             obj({"path": path, "content": string("Complete file contents", empty=True, maximum=100_000)}), files.write, True),
        Tool("file_copy", "Copy one file up to 50 MB to a new destination. Never overwrite. Directory copies are unsupported.",
             obj({"source": path, "destination": path}), files.copy, True),
        Tool("file_move", "Move one file to a new path. Never overwrite. Folder moves are unsupported.",
             obj({"source": path, "destination": path}), files.move, True),
        Tool("file_rename", "Rename one file within its folder; the new name must not already exist.",
             obj({"path": path, "name": string("New filename, not a path")}), files.rename, True),
        Tool("file_trash", "Move one file to recoverable OS Trash/Recycle Bin after local user confirmation. No permanent deletion or folder deletion.",
             obj({"path": path}), files.trash, True),
        Tool("system_get", "Read audio and brightness capabilities and current values. Does not change settings.", obj({}), system.get),
        Tool("volume_set", "Set absolute output volume from 0 to 100, then read back to verify. Does not change mute state.",
             obj({"percent": integer("Requested volume percentage")}), system.volume, True),
        Tool("mute_set", "Set an explicit output mute state, then read back to verify. Repeating does not toggle it.",
             obj({"muted": {"type": "boolean"}}), system.mute, True),
        Tool("brightness_set", "Set supported displays to an absolute brightness percentage. Unsupported hardware returns an explicit error.",
             obj({"percent": integer("Requested brightness percentage")}), system.brightness, True),
        Tool("settings_open", "Open system settings. Windows supports named sections; macOS currently opens the main Settings window.",
             obj({"section": {"type": "string", "enum": list(SETTINGS)}}, []), system.settings, True),
    ])
