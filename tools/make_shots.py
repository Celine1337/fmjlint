#!/usr/bin/env python3
"""Regenerate docs/audit.png and docs/clean.png. Requires Pillow.

Run: python tools/make_demo.py && python tools/make_shots.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fmjlint as fl
import render_terminal as rt

CLEAN = {
    "schemaVersion": 1,
    "id": "examplemod",
    "version": "1.0.0",
    "name": "Example Mod",
    "license": "MIT",
    "entrypoints": {"main": ["com.example.ExampleMod"]},
    "depends": {"fabricloader": ">=0.15.0", "minecraft": "~1.21"},
}


def render(name, ansi, cmd, title):
    rt.render(rt.parse_ansi(ansi), title, cmd, os.path.join(ROOT, "docs", name + ".png"))


def main():
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    stats, issues = fl.audit(os.path.join(ROOT, "tests", "demo"))
    render("audit", fl.report(stats, issues, True, False),
           "python fmjlint.py tests/demo", "fmjlint — audit")
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "fabric.mod.json"), "w", encoding="utf-8") as fh:
            json.dump(CLEAN, fh)
        stats, issues = fl.audit(tmp)
        render("clean", fl.report(stats, issues, True, False),
               "python fmjlint.py src/main/resources", "fmjlint — clean")


if __name__ == "__main__":
    main()