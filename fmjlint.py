#!/usr/bin/env python3
"""fmjlint - validator for Fabric fabric.mod.json descriptors.

Checks schema version, mod id/version, entrypoints, dependency ranges and
environment; in jar mode it also verifies entrypoint classes and nested jars
exist. Single file, standard library only.
"""

import argparse
import json
import os
import re
import sys
import zipfile

__version__ = "1.0.0"

ERROR = "error"
WARN = "warning"

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
ENVIRONMENTS = {"*", "client", "server"}
DEP_KEYS = ("depends", "recommends", "breaks", "conflicts")
RANGE_BAD = re.compile(r"[^0-9A-Za-z.*xX><=~^| \-+,]")


class Issue:
    __slots__ = ("code", "severity", "file", "line", "message")

    def __init__(self, code, severity, file, line, message):
        self.code = code
        self.severity = severity
        self.file = file
        self.line = line
        self.message = message

    def as_dict(self):
        return {"code": self.code, "severity": self.severity, "file": self.file,
                "line": self.line, "message": self.message}


def valid_range(s):
    s = s.strip()
    if not s:
        return False
    if not re.search(r"[0-9xX*]", s):
        return False
    return not RANGE_BAD.search(s)


def entry_class(value):
    if isinstance(value, str):
        return value.split("::")[0]
    if isinstance(value, dict):
        v = value.get("value")
        if isinstance(v, str):
            return v.split("::")[0]
    return None


def validate(data, path, issues, jar_names=None):
    def add(code, sev, msg, line=1):
        issues.append(Issue(code, sev, path, line, msg))

    if not isinstance(data, dict):
        add("F000", ERROR, "fabric.mod.json must be a JSON object")
        return None
    if data.get("schemaVersion") != 1:
        add("F001", ERROR, "schemaVersion must be 1 (got %r)" % data.get("schemaVersion"))
    mod_id = data.get("id")
    if not mod_id:
        add("F002", ERROR, "missing required 'id'")
    elif not isinstance(mod_id, str) or not ID_RE.match(mod_id):
        add("F003", ERROR, "invalid mod id '%s' (lowercase a-z 0-9 - _)" % mod_id)
    if not data.get("version"):
        add("F004", ERROR, "missing required 'version'")
    if not data.get("name"):
        add("F005", WARN, "no display 'name' set")
    if not data.get("license"):
        add("F006", WARN, "no 'license' set")
    env = data.get("environment")
    if env is not None and env not in ENVIRONMENTS:
        add("F007", ERROR, "invalid environment '%s' (* / client / server)" % env)

    eps = data.get("entrypoints")
    if eps is not None:
        if not isinstance(eps, dict):
            add("F008", ERROR, "'entrypoints' must be an object")
        else:
            for group, entries in eps.items():
                if not isinstance(entries, list):
                    add("F008", ERROR, "entrypoint group '%s' must be a list" % group)
                    continue
                for e in entries:
                    cls = entry_class(e)
                    if cls is None:
                        add("F008", ERROR,
                            "entrypoint in '%s' must be a class string or {adapter, value}" % group)
                    elif jar_names is not None:
                        entry = cls.replace(".", "/") + ".class"
                        if entry not in jar_names:
                            add("F009", ERROR,
                                "entrypoint class '%s' not found in jar" % cls)

    for key in DEP_KEYS:
        deps = data.get(key)
        if deps is None:
            continue
        if not isinstance(deps, dict):
            add("F010", ERROR, "'%s' must be an object of modid -> version range" % key)
            continue
        for dep, rng in deps.items():
            ranges = rng if isinstance(rng, list) else [rng]
            for r in ranges:
                if not isinstance(r, str) or not valid_range(r):
                    add("F010", ERROR, "invalid version range %r for '%s' in %s" % (r, dep, key))
            if key == "depends" and mod_id and dep == mod_id:
                add("F011", ERROR, "mod depends on itself ('%s')" % mod_id)
    depends = data.get("depends") or {}
    breaks = data.get("breaks") or {}
    if isinstance(depends, dict) and isinstance(breaks, dict):
        both = set(depends) & set(breaks)
        if both:
            add("F016", WARN, "in both depends and breaks: %s" % ", ".join(sorted(both)))

    authors = data.get("authors")
    if authors is not None:
        if not isinstance(authors, list):
            add("F013", ERROR, "'authors' must be a list")
        else:
            for a in authors:
                if isinstance(a, str):
                    continue
                if isinstance(a, dict) and a.get("name"):
                    continue
                add("F013", ERROR, "author entry must be a string or {name, contact}")

    if jar_names is not None:
        for nested in data.get("jars") or []:
            f = nested.get("file") if isinstance(nested, dict) else None
            if f and f not in jar_names:
                add("F019", WARN, "nested jar '%s' not found in jar" % f)
    return mod_id


def collect(root):
    if os.path.isfile(root):
        return [root]
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "build", ".gradle", "node_modules")]
        for fn in sorted(filenames):
            if fn == "fabric.mod.json":
                found.append(os.path.join(dirpath, fn))
    return found


def audit(root):
    issues = []
    stats = {"files": 0, "mods": 0, "jar": 0}
    seen = {}
    if root.lower().endswith(".jar"):
        stats["jar"] = 1
        try:
            with zipfile.ZipFile(root) as zf:
                names = set(zf.namelist())
                stats["files"] = 1
                if "fabric.mod.json" not in names:
                    issues.append(Issue("F000", ERROR, os.path.basename(root), 1,
                                        "no fabric.mod.json at jar root"))
                else:
                    stats["mods"] += 1
                    try:
                        data = json.loads(zf.read("fabric.mod.json").decode("utf-8", "replace"))
                    except json.JSONDecodeError as exc:
                        issues.append(Issue("F000", ERROR, "fabric.mod.json", exc.lineno,
                                            "invalid JSON: %s" % exc.msg))
                        data = None
                    if data is not None:
                        validate(data, "fabric.mod.json", issues, jar_names=names)
        except (zipfile.BadZipFile, OSError) as exc:
            issues.append(Issue("F000", ERROR, root, 1, "cannot read jar: %s" % exc))
    else:
        for path in collect(root):
            rel = os.path.relpath(path, root) if os.path.isdir(root) else os.path.basename(path)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError as exc:
                issues.append(Issue("F000", ERROR, rel, 1, "cannot read: %s" % exc))
                continue
            stats["files"] += 1
            stats["mods"] += 1
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                issues.append(Issue("F000", ERROR, rel, exc.lineno, "invalid JSON: %s" % exc.msg))
                continue
            mod_id = validate(data, rel, issues)
            if mod_id:
                if mod_id in seen:
                    issues.append(Issue("F015", ERROR, rel, 1,
                                        "duplicate mod id '%s' (also in %s)" % (mod_id, seen[mod_id])))
                else:
                    seen[mod_id] = rel
    return stats, issues


def colorize(text, color, enabled):
    if not enabled:
        return text
    codes = {"red": "31", "green": "32", "yellow": "33", "bold": "1"}
    return "\x1b[%sm%s\x1b[0m" % (codes[color], text)


def report(stats, issues, color, as_json):
    errors = [i for i in issues if i.severity == ERROR]
    warns = [i for i in issues if i.severity == WARN]
    if as_json:
        return json.dumps({"summary": stats, "errors": len(errors), "warnings": len(warns),
                           "issues": [i.as_dict() for i in issues]}, indent=2)
    lines = [colorize("SUMMARY", "bold", color)]
    lines.append("  descriptors  %d" % stats["files"])
    lines.append("  mods         %d" % stats["mods"])
    if not issues:
        lines.append(colorize("clean: no issues found", "green", color))
        return "\n".join(lines)
    if errors:
        lines.append(colorize("ERRORS (%d)" % len(errors), "red", color))
        for i in errors:
            lines.append("  %s:%d: [%s] %s" % (i.file, i.line, i.code, i.message))
    if warns:
        lines.append(colorize("WARNINGS (%d)" % len(warns), "yellow", color))
        for i in warns:
            lines.append("  %s:%d: [%s] %s" % (i.file, i.line, i.code, i.message))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="fmjlint", description="Validator for Fabric fabric.mod.json descriptors.")
    parser.add_argument("path", help="fabric.mod.json, a directory, or a mod .jar")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--version", action="version", version="fmjlint " + __version__)
    opts = parser.parse_args(argv)
    if not os.path.exists(opts.path):
        sys.stderr.write("fmjlint: path not found: %s\n" % opts.path)
        return 2
    color = not opts.no_color and not os.environ.get("NO_COLOR") and sys.stdout.isatty()
    stats, issues = audit(opts.path)
    print(report(stats, issues, color, opts.json))
    errors = sum(1 for i in issues if i.severity == ERROR)
    warns = sum(1 for i in issues if i.severity == WARN)
    return 1 if (errors or (opts.strict and warns)) else 0


if __name__ == "__main__":
    sys.exit(main())