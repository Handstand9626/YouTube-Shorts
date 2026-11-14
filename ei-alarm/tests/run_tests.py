#!/usr/bin/env python3
"""Offline checks for the Ei-Alarm! Luau scripts.

Runs three things with a Lua 5.1 interpreter (via the `lupa` package):

1. Syntax: every script under src/ must compile.
2. Rules: CoreSelfTest against EggCore (the same tests Studio runs at server start).
3. Walkthrough: the real server and client scripts against a small Roblox mock,
   played as a two-player session (tests/scenario.lua).

The scripts are written in the subset of Luau that is also valid Lua 5.1, which
is what makes this possible. It checks logic only. Physics, replication and
rendering still need the two-player test in Roblox Studio described in the README.

Usage:  pip install lupa  &&  python tests/run_tests.py
"""

import sys
from pathlib import Path

try:
    from lupa import lua51
except ImportError:
    sys.exit("lupa is missing. Install it with: pip install lupa")

TEST_DIR = Path(__file__).resolve().parent
SRC_DIR = TEST_DIR.parent / "src"


def new_runtime():
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.globals().SRC_DIR = str(SRC_DIR)
    lua.globals().TEST_DIR = str(TEST_DIR)
    return lua


def check_syntax():
    lua = new_runtime()
    compile_chunk = lua.eval("function(source, name) return loadstring(source, name) end")
    scripts = sorted(SRC_DIR.rglob("*.luau"))
    for path in scripts:
        result = compile_chunk(path.read_text(encoding="utf-8"), "@" + path.name)
        error = result[1] if isinstance(result, tuple) else None
        if error:
            raise SystemExit(f"Syntax error: {error}")
    print(f"Syntax: {len(scripts)} Skripte kompilieren")


def run_core_tests():
    lua = new_runtime()
    passed, failed, failures = lua.execute(
        """
        local Config = dofile(SRC_DIR .. "/ReplicatedStorage/EiAlarm/Config.luau")
        local EggCore = dofile(SRC_DIR .. "/ServerScriptService/EiAlarm/EggCore.luau")
        local CoreSelfTest = dofile(SRC_DIR .. "/ServerScriptService/EiAlarm/CoreSelfTest.luau")
        return CoreSelfTest.run(EggCore, Config, function() end)
        """
    )
    for failure in failures.values():
        print("  FEHLER", failure)
    print(f"Regeln: {passed} bestanden, {failed} fehlgeschlagen")
    if failed:
        raise SystemExit(1)


def run_scenario():
    lua = new_runtime()
    print("Durchlauf mit zwei Spielern:")
    lua.execute('dofile(TEST_DIR .. "/scenario.lua")')


if __name__ == "__main__":
    check_syntax()
    run_core_tests()
    run_scenario()
    print("Alles gruen.")
