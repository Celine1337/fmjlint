<p align="center"><img src="docs/style/hero.png" alt="fmjlint — Fabric mod metadata validator" width="100%"></p>

<p align="center">
  <a href="README.ru.md"><img src="docs/style/pill-ru.png" alt="README RU" height="42"></a>
  <a href="https://github.com/Celine1337/fmjlint/releases"><img src="docs/style/pill-release.png" alt="Releases" height="42"></a>
  <a href="https://github.com/Celine1337/fmjlint/actions/workflows/ci.yml"><img src="docs/style/pill-ci.png" alt="CI" height="42"></a>
  <a href="LICENSE"><img src="docs/style/pill-license.png" alt="MIT" height="42"></a>
</p>

<img src="docs/style/sec-about-en.png" alt="About" width="100%">

Validator for [Fabric](https://fabricmc.net) `fabric.mod.json` descriptors. A
malformed mod metadata file makes Fabric Loader skip or crash your mod with an
opaque error. fmjlint reads `fabric.mod.json` — or a whole mod `.jar` — and
flags the problems before you ship:

- wrong `schemaVersion`, missing / invalid `id` and `version`;
- bad `environment`, malformed `entrypoints` and dependency version ranges;
- entrypoint classes and nested jars that do not exist inside the jar;
- duplicate mod ids across a multi-module tree.

Single file, standard library only, Python 3.9+.

<img src="docs/style/sec-features-en.png" alt="Features" width="100%">

- Validates the Fabric metadata schema fields: `schemaVersion`, `id`, `version`,
  `name`, `license`, `environment`, `entrypoints`, `authors`, `jars`.
- Dependency keys `depends` / `recommends` / `breaks` / `conflicts` with a
  permissive version-range syntax check (`>=`, `~`, `^`, `*`, `x`, `||`, …).
- Three input modes: one descriptor, a directory (duplicate-id detection), or a
  built `.jar` (entrypoint class + nested jar presence).
- `--json` machine-readable report; exit code `1` on errors for CI gating;
  `--strict` also fails on warnings.
- Colored ANSI output, `--no-color` and `NO_COLOR`.

<img src="docs/style/sec-checks-en.png" alt="Checks" width="100%">

| Code | Severity | Meaning |
|------|----------|---------|
| F000 | error | unreadable file / jar, missing descriptor, or invalid JSON |
| F001 | error | `schemaVersion` must be `1` |
| F002 | error | missing required `id` |
| F003 | error | `id` not lowercase `a-z 0-9 - _` |
| F004 | error | missing required `version` |
| F005 | warning | no display `name` |
| F006 | warning | no `license` |
| F007 | error | `environment` not `*` / `client` / `server` |
| F008 | error | malformed `entrypoints` group or entry |
| F009 | error | entrypoint class not present in the jar |
| F010 | error | malformed dependency map or version range |
| F011 | error | mod depends on itself |
| F013 | error | malformed `authors` entry |
| F015 | error | duplicate mod id across scanned descriptors |
| F016 | warning | same mod in both `depends` and `breaks` |
| F019 | warning | nested jar listed but not present in the jar |

<img src="docs/style/sec-stack-en.png" alt="Tech stack" width="100%">

<img src="docs/style/chips.png" alt="Python 3.9+, unittest, JSON; GitHub Actions, Pillow, zipfile" width="100%">

<img src="docs/style/sec-quick-en.png" alt="Quick start" width="100%">

```console
$ python fmjlint.py src/main/resources/fabric.mod.json
$ python fmjlint.py .                      # whole tree, duplicate ids
$ python fmjlint.py build/libs/mymod.jar
$ python fmjlint.py . --json
```

```
SUMMARY
  descriptors  3
  mods         3
ERRORS (6)
  b/fabric.mod.json:1: [F015] duplicate mod id 'dupmod' (also in a/fabric.mod.json)
  broken/fabric.mod.json:1: [F001] schemaVersion must be 1 (got 2)
  broken/fabric.mod.json:1: [F003] invalid mod id 'Bad_ID' (lowercase a-z 0-9 - _)
  broken/fabric.mod.json:1: [F007] invalid environment 'both' (* / client / server)
  broken/fabric.mod.json:1: [F008] entrypoint group 'main' must be a list
  broken/fabric.mod.json:1: [F010] invalid version range 'abc' for 'minecraft' in depends
WARNINGS (2)
  broken/fabric.mod.json:1: [F005] no display 'name' set
  broken/fabric.mod.json:1: [F006] no 'license' set
```

Exit codes: `0` — clean (or warnings only), `1` — errors (or warnings with
`--strict`), `2` — bad path.

Limits, on purpose: version-range checking is syntactic, not a full semver
solver; it cannot know whether a dependency is actually installed.

<img src="docs/style/sec-shots-en.png" alt="Screenshots" width="100%">

![audit report](docs/audit.png)

![clean report](docs/clean.png)

<img src="docs/style/sec-tests-en.png" alt="Tests" width="100%">

```console
$ python -m unittest discover -s tests -v
```

22 tests cover every check, jar mode, duplicate ids and exit codes. The demo
tree and all images are regenerable:

```console
$ python tools/make_demo.py       # tests/demo with one of each issue
$ pip install pillow
$ python tools/make_shots.py      # docs/audit.png, docs/clean.png
$ python tools/make_style.py tools/style.json docs/style
```

<img src="docs/style/stats.png" alt="22 tests, 3 OSes in CI, v1.0.0" width="100%">

[MIT](LICENSE) © Celine1337