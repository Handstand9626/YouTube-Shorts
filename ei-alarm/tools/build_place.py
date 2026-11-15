#!/usr/bin/env python3
"""Builds Ei-Alarm.rbxlx, a Roblox place file with all scripts in the right services.

Open the result in Roblox Studio (File > Open from File, or drag it onto the
Studio window), then use File > Publish to Roblox As.

Usage:  python tools/build_place.py
"""

from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUT = ROOT / "Ei-Alarm.rbxlx"

_next_ref = 0


def item(class_name, name, children="", extra=""):
    global _next_ref
    _next_ref += 1
    return (
        f'<Item class="{class_name}" referent="RBX{_next_ref}">'
        f'<Properties><string name="Name">{escape(name)}</string>{extra}</Properties>'
        f"{children}</Item>\n"
    )


def script(class_name, name, path):
    source = (SRC / path).read_text(encoding="utf-8")
    if "]]>" in source:
        raise SystemExit(f"{path} contains ]]> and cannot be embedded as CDATA")
    return item(class_name, name, extra=f'<ProtectedString name="Source"><![CDATA[{source}]]></ProtectedString>')


def build():
    server = "ServerScriptService/EiAlarm/"
    tree = (
        item("Workspace", "Workspace", extra='<bool name="StreamingEnabled">false</bool>')
        + item(
            "ReplicatedStorage",
            "ReplicatedStorage",
            item("Folder", "EiAlarm", script("ModuleScript", "Config", "ReplicatedStorage/EiAlarm/Config.luau")),
        )
        + item(
            "ServerScriptService",
            "ServerScriptService",
            item(
                "Folder",
                "EiAlarm",
                script("Script", "Main", server + "Main.server.luau")
                + script("ModuleScript", "EggCore", server + "EggCore.luau")
                + script("ModuleScript", "MapBuilder", server + "MapBuilder.luau")
                + script("ModuleScript", "CoreSelfTest", server + "CoreSelfTest.luau"),
            ),
        )
        + item(
            "StarterPlayer",
            "StarterPlayer",
            item(
                "StarterPlayerScripts",
                "StarterPlayerScripts",
                script("LocalScript", "EiAlarmClient", "StarterPlayerScripts/EiAlarmClient.client.luau"),
            ),
        )
    )
    OUT.write_text('<roblox version="4">\n' + tree + "</roblox>\n", encoding="utf-8")
    print(f"{OUT.name}: {OUT.stat().st_size} Bytes")


if __name__ == "__main__":
    build()
