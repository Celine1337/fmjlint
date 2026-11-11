import contextlib
import io
import json
import os
import tempfile
import unittest
import zipfile

import fmjlint as fl

CLEAN = {
    "schemaVersion": 1,
    "id": "examplemod",
    "version": "1.0.0",
    "name": "Example Mod",
    "license": "MIT",
    "environment": "*",
    "entrypoints": {"main": ["com.example.ExampleMod"]},
    "depends": {"fabricloader": ">=0.15.0", "minecraft": "~1.21"},
}


def write(root, rel, data):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def codes(issues):
    return sorted(i.code for i in issues)


class Checks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def run_src(self, data, rel="fabric.mod.json"):
        write(self.root, rel, data)
        return fl.audit(self.root)

    def test_clean(self):
        _, issues = self.run_src(CLEAN)
        self.assertEqual(issues, [])

    def test_f001_schema(self):
        d = dict(CLEAN, schemaVersion=2)
        _, issues = self.run_src(d)
        self.assertIn("F001", codes(issues))

    def test_f002_f004_missing(self):
        _, issues = self.run_src({"schemaVersion": 1})
        self.assertIn("F002", codes(issues))
        self.assertIn("F004", codes(issues))

    def test_f003_bad_id(self):
        _, issues = self.run_src(dict(CLEAN, id="Bad_ID"))
        self.assertIn("F003", codes(issues))

    def test_f005_f006_warnings(self):
        d = {k: v for k, v in CLEAN.items() if k not in ("name", "license")}
        _, issues = self.run_src(d)
        self.assertIn("F005", codes(issues))
        self.assertIn("F006", codes(issues))

    def test_f007_environment(self):
        _, issues = self.run_src(dict(CLEAN, environment="both"))
        self.assertIn("F007", codes(issues))

    def test_f008_entrypoints(self):
        _, issues = self.run_src(dict(CLEAN, entrypoints={"main": "not-a-list"}))
        self.assertIn("F008", codes(issues))

    def test_f008_entry_object(self):
        d = dict(CLEAN, entrypoints={"main": [{"adapter": "kotlin", "value": "com.X"}]})
        _, issues = self.run_src(d)
        self.assertNotIn("F008", codes(issues))

    def test_f010_bad_range(self):
        _, issues = self.run_src(dict(CLEAN, depends={"minecraft": "abc"}))
        self.assertIn("F010", codes(issues))

    def test_f010_good_ranges(self):
        d = dict(CLEAN, depends={"minecraft": ">=1.20 <1.22", "fabricloader": "*"})
        _, issues = self.run_src(d)
        self.assertNotIn("F010", codes(issues))

    def test_f011_self_depend(self):
        _, issues = self.run_src(dict(CLEAN, depends={"examplemod": "*"}))
        self.assertIn("F011", codes(issues))

    def test_f013_authors(self):
        _, issues = self.run_src(dict(CLEAN, authors=[{"contact": {}}]))
        self.assertIn("F013", codes(issues))

    def test_f016_depends_breaks(self):
        _, issues = self.run_src(dict(CLEAN, breaks={"othermod": "*"},
                                      depends={"othermod": "*"}))
        self.assertIn("F016", codes(issues))

    def test_f015_duplicate_id(self):
        write(self.root, "a/fabric.mod.json", CLEAN)
        write(self.root, "b/fabric.mod.json", CLEAN)
        _, issues = fl.audit(self.root)
        self.assertIn("F015", codes(issues))

    def test_bad_json(self):
        path = os.path.join(self.root, "fabric.mod.json")
        with open(path, "w") as fh:
            fh.write("{ nope")
        _, issues = fl.audit(self.root)
        self.assertIn("F000", codes(issues))


class JarMode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def make_jar(self, with_class=True):
        path = os.path.join(self.root, "mod.jar")
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("fabric.mod.json", json.dumps(CLEAN))
            if with_class:
                zf.writestr("com/example/ExampleMod.class", b"\xca\xfe\xba\xbe")
        return path

    def test_jar_clean(self):
        _, issues = fl.audit(self.make_jar())
        self.assertEqual(issues, [])

    def test_jar_missing_entrypoint(self):
        _, issues = fl.audit(self.make_jar(with_class=False))
        self.assertIn("F009", codes(issues))

    def test_jar_no_descriptor(self):
        path = os.path.join(self.root, "empty.jar")
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("x.txt", "hi")
        _, issues = fl.audit(path)
        self.assertIn("F000", codes(issues))


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return fl.main(args)

    def test_exit_clean(self):
        write(self.root, "fabric.mod.json", CLEAN)
        self.assertEqual(self._run([self.root, "--no-color"]), 0)

    def test_exit_error(self):
        write(self.root, "fabric.mod.json", {"schemaVersion": 1})
        self.assertEqual(self._run([self.root, "--no-color"]), 1)

    def test_exit_bad_path(self):
        self.assertEqual(self._run([os.path.join(self.root, "nope")]), 2)

    def test_json(self):
        write(self.root, "fabric.mod.json", {"schemaVersion": 1})
        stats, issues = fl.audit(self.root)
        out = json.loads(fl.report(stats, issues, False, True))
        self.assertGreaterEqual(out["errors"], 2)


if __name__ == "__main__":
    unittest.main()