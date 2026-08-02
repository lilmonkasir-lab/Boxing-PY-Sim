#!/usr/bin/env python3
"""One-command launcher:  python3 play.py

Sets the game up and starts it.  Nothing else to install first.

Why this exists: `pip install -r requirements.txt` fails outright on most
current systems (Debian/Ubuntu/Fedora and Homebrew python mark themselves
"externally managed", PEP 668), which left people unable to start the game at
all.  This script sidesteps that by building a private virtual environment in
.venv/, installing pygame and numpy into it, and re-launching the game with
that interpreter.

Safe to re-run: if the environment is already good it just starts the game.
Any argument you pass is forwarded to the game, e.g.

    python3 play.py --difficulty Champion --rounds 12
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQUIRED = ("pygame", "numpy")
MIN_PYTHON = (3, 8)


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def _have_deps(python: str | Path) -> bool:
    """Can `python` import everything the game needs?"""
    code = "import pygame, numpy"
    try:
        r = subprocess.run([str(python), "-c", code],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return r.returncode == 0
    except OSError:
        return False


def _run_game(python: str | Path, argv: list[str]) -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    try:
        return subprocess.call([str(python), str(ROOT / "main.py"), *argv], env=env)
    except KeyboardInterrupt:
        return 0


def _die(msg: str) -> int:
    print("\n" + "-" * 68, file=sys.stderr)
    print(msg.strip(), file=sys.stderr)
    print("-" * 68, file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if sys.version_info < MIN_PYTHON:
        return _die(f"""
Boxing PY Sim needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer.
You are running Python {sys.version.split()[0]} ({sys.executable}).

Install a newer Python from https://www.python.org/downloads/ and retry.
""")

    # 1. Already runnable with the current interpreter?  Just play.
    if _have_deps(sys.executable):
        return _run_game(sys.executable, argv)

    # 2. Is there a working private environment from a previous run?
    vpy = _venv_python()
    if vpy.exists() and _have_deps(vpy):
        return _run_game(vpy, argv)

    # 3. Build one.
    print("First run: setting up a private environment in .venv/ "
          "(about 30 seconds, one time only)...")
    if not vpy.exists():
        r = subprocess.run([sys.executable, "-m", "venv", str(VENV)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return _die(f"""
Could not create a virtual environment.

{(r.stderr or r.stdout).strip()}

On Debian/Ubuntu the venv module ships separately:
    sudo apt install python3-venv python3-pip
Then run  python3 play.py  again.
""")

    print("Installing pygame and numpy...")
    r = subprocess.run([str(vpy), "-m", "pip", "install", "--upgrade", "pip",
                        "pygame>=2.1", "numpy>=1.21"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not _have_deps(vpy):
        tail = "\n".join((r.stderr or r.stdout).strip().splitlines()[-15:])
        return _die(f"""
Could not install the dependencies.

{tail}

Most often this is no internet connection, or a proxy blocking PyPI.
You can also install them yourself and run the game directly:

    {vpy} -m pip install pygame numpy
    {vpy} main.py
""")

    print("Done. Starting the game...\n")
    return _run_game(vpy, argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
