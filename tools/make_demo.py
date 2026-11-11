#!/usr/bin/env python3
"""Write tests/demo: fabric.mod.json descriptors with one of each issue."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(ROOT, "tests", "demo")

BROKEN = {
    "schemaVersion": 2,
    "id": "Bad_ID",
    "version": "1.0.0",
    "environment": "both",
    "entrypoints": {"main": "not-a-list"},
    "depends": {"minecraft": "abc"},
}

DUP = {"schemaVersion": 1, "id": "dupmod", "version": "1.0", "name": "Dup", "license": "MIT"}


def main():
    for rel, data in (("broken/fabric.mod.json", BROKEN),
                      ("a/fabric.mod.json", DUP), ("b/fabric.mod.json", DUP)):
        path = os.path.join(DEMO, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    print("wrote", DEMO)


if __name__ == "__main__":
    main()