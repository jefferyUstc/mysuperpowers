---
name: python-pypi-release
description: Use when publishing a Python package to PyPI — first-ever upload of a new package or any subsequent version bump (patch / minor / major / post-release / pre-release). Triggers include "release a new version", "upload to PyPI", "publish to PyPI", "bump to X.Y.Z", "cut a release", "release a .postN", "tag and push to PyPI", "first PyPI release", "initial PyPI upload". Symptoms: user is editing pyproject.toml version, asking about twine/build/wheels, preparing dist/, or about to git tag a release.
---

# Python package release to PyPI — gated workflow

Covers both **first-ever upload** and **incremental update** of a package. Mode is auto-detected from PyPI; the main workflow is identical, with mode-specific gates clearly marked.

**Structure:** 13 gated steps — `[0a]` interpreter confirm + `[0]` preflight (`scripts/preflight.py`) + `[1]-[11]` release. Preflight is read-only and re-runnable; [1]-[11] progressively touch pyproject.toml → dist/ → git commit → tag → PyPI. Every gate fails closed with explicit rollback.

## When to use

Any of these user phrasings:

- "publish a new version to PyPI" / "release a new version"
- "upload to PyPI" / "cut a release"
- "bump to 1.2.4" / "release a .post2" / "release 1.0.1"
- "publish this package for the first time"
- "first release of <pkg>"
- "make an initial PyPI release"
- "tag and push to PyPI"

## When NOT to use

- Conda/mamba publication (use conda-build separately).
- Private/internal indexes (workflow adapts; only the upload URL differs).
- Packages with no `pyproject.toml` (modern build backend required; bootstrap with hatchling first).

## Core principles

1. **Gate before commit.** Pytest + wheel sanity must pass before any git commit or PyPI upload. If a gate fails, roll back.
2. **Wheel sanity ≠ source pytest.** A symbol listed in `__all__` but never imported at the package root passes source-level pytest (because test modules import from submodules directly) but fails `from pkg import X` after wheel install. The wheel-sanity gate is specifically to catch that class of bug.
3. **One release commit.** Everything (version bump + any bug-fix surfaced by sanity) goes in one commit titled `release <version>`. Trivial pre-release fixes may be bundled; substantive fixes should be a prior separate commit.
4. **Annotated tag with main-line release notes.** No internal audit codes (G1, M4, NEW-7 etc.) in commit messages or tag annotations. Describe user-visible behaviour.
5. **Rollback is routine, not exceptional.** If any gate fails, restore the working tree, delete the new-version dist artifacts, clean up temp venvs, and report. Do not try to shoehorn through.

## Preflight and mode detection

**Always run `scripts/preflight.py` first.** It's a comprehensive read-only checker that runs 7 sections (tooling, pyproject, inner package, filesystem, git, PyPI mode, PyPI auth), collects all errors to completion (no short-circuit), and exits 0 on clean or 1 on any error.

```bash
$PY "$SKILL_DIR/scripts/preflight.py"
```

`$SKILL_DIR` is the directory containing this `SKILL.md` (i.e. the `python-pypi-release/` folder under whichever `skills/` root the harness loaded this from). `$PY` is the Python interpreter confirmed in step `[0a]` below — never the bare `python` without that confirmation.

Example output (ggplot2-python UPDATE mode):

```
=== [1/7] tooling ===
  [OK]   python module: build / twine / packaging
  [OK]   tomllib available (stdlib)
=== [2/7] pyproject.toml ===
  [OK]   project.name = ggplot2-python
  [OK]   project.version = 4.0.2.9000.post2 (PEP 440 valid)
  [OK]   build-system.build-backend = hatchling.build
  [OK]   readme file exists: README.md
=== [3/7] inner package layout ===
  [OK]   inner pkg (hatch config): ggplot2_py
=== [4/7] filesystem ===
  [OK]   README.md
  [OK]   license file: LICENSE
=== [5/7] git ===
  [OK]   inside a git repo / origin reachable / working tree clean
=== [6/7] PyPI mode + name ===
  [OK]   MODE = update (ggplot2-python on PyPI; latest = 4.0.2.9000.post2)
=== [7/7] PyPI auth ===
  [OK]   ~/.pypirc [pypi] has credential (mode 600)

============================================================
PREFLIGHT: 0 error(s), 0 warning(s)
  package:  ggplot2-python
  current:  4.0.2.9000.post2
  inner:    ggplot2_py              # CORRECT (not naïve `ggplot2_python`)
  mode:     update
  on PyPI:  4.0.2.9000.post2
============================================================
```

### Exit-code gate

- `0` → proceed to step [1].
- `1` → STOP. Do NOT proceed. Fix every `[FAIL]` (and address `[WARN]`s that apply) then re-run preflight. Because `preflight.py` only reads, rerunning is free.

### What preflight protects against

| Issue class | Example | Caught here (vs in-flow) |
|---|---|---|
| Missing `build`/`twine` | Interpreter has neither | preflight [0] |
| Non-PEP 440 version | `version = "1.0-rc-x"` | preflight [0] |
| Dynamic version (not supported) | `dynamic = ["version"]` | preflight [0] |
| `readme` points to missing file | `readme = "README.md"` but file absent | preflight [0] |
| Inner pkg dir missing | hatch says `ggplot2_py` but dir gone | preflight [0] |
| `pip`-version-deprecated `pip index` | — | avoided (uses PyPI JSON API) |
| Name hijack | `ggplot2-python-evil` taken by someone | preflight [0] |
| Missing `~/.pypirc` AND env vars | first release on a fresh machine | preflight [0] |
| `~/.pypirc` world-readable | mode 644 instead of 600 | preflight [0] |
| Cannot reach origin | bad SSH key, no network | preflight [0] |
| Working tree dirty | uncommitted unrelated edits | preflight [0] (warns) |

### Inner-package detection (why this matters)

Naïve `echo $PKG \| tr - _` fails for **any package where distribution name ≠ inner package name**. Examples that would be mis-derived:

| Distribution | Naïve `tr - _` result | Actual inner (via hatch config) |
|---|---|---|
| `ggplot2-python` | `ggplot2_python` ❌ | `ggplot2_py` ✓ |
| `scikit-learn` | `scikit_learn` | `sklearn` ✓ |
| `beautifulsoup4` | `beautifulsoup4` | `bs4` ✓ |
| `pillow` | `pillow` | `PIL` ✓ |

`preflight.py` uses a 3-tier resolver:

1. `[tool.hatch.build.targets.wheel].packages[0]` — hatchling explicit (load-bearing).
2. `[tool.setuptools.packages]` — setuptools explicit list.
3. Heuristic: first top-level dir with `__init__.py`, excluding `tests/`, `docs/`, `build/`, `dist/`, `scripts/`, `validation/`, `port_reports/`, etc.

Downstream steps ([5] wheel sanity) use this `inner` value — wrong value would break sanity.

### After preflight

Ask the user to confirm the **target new version** (step [2]'s input).

```
UPDATE: current = <OLD>. Proposed: <NEW>. OK? (Y/N, or specify different)
NEW:    proposed initial: 0.1.0 (or 1.0.0 for stable API). OK?
```

If the name is TAKEN by someone else (preflight reports NEW mode but name hijack detected separately), ABORT — cannot publish to a name you don't own.

## Version bump taxonomy (all kinds go through the same workflow)

PEP 440 + SemVer conventions supported:

| Bump kind | From | To | When |
|---|---|---|---|
| **patch** | 1.0.0 | 1.0.1 | Bug fixes, no API changes, no new features. **Most common.** |
| **minor** | 1.0.0 | 1.1.0 | New backward-compatible features / API. |
| **major** | 1.0.0 | 2.0.0 | Breaking changes. Reserve for API removal / rename / semantic overhaul. |
| **post** | 1.0.0 | 1.0.0.post1 | Release-packaging fix (metadata typo, missing `__init__` import) with zero behavior change. **Avoid for real code fixes** — use patch. |
| **pre-alpha** | 1.0.0 | 1.1.0a1 | Early preview of upcoming minor. |
| **pre-beta** | 1.0.0 | 1.1.0b1 | Feature-complete preview. |
| **pre-rc** | 1.0.0 | 1.1.0rc1 | Release candidate. |
| **dev** | 1.0.0 | 1.1.0.dev1 | Development snapshot (rarely uploaded to PyPI). |

**Answer to "can I go 1.0.0 → 1.0.1?"**: Yes, that's a patch bump — normal flow.

When NEW mode: the user picks the starting version (defaults: `0.1.0` for early/beta projects, `1.0.0` for public-stable projects with a committed API).

## Prerequisites

All prerequisites are checked by `scripts/preflight.py` in step **[0]** of the workflow. The skill's workflow is **13 steps: [0a] interpreter confirm + [0] preflight + [1]-[11] release flow**. See `## Preflight and mode detection` above for the full list of what's verified; any `[FAIL]` from preflight means the release cannot proceed.

For reference, preflight verifies:
- Python modules `build`, `twine`, `packaging`, `tomllib`/`tomli`.
- `pyproject.toml` parseable with valid `[project]` + `[build-system]`; `version` PEP 440 compliant; `readme` reference resolves.
- Inner package layout (hatchling/setuptools config → heuristic scan).
- `README.md`, `LICENSE` present (warn if missing).
- Inside git repo; `origin` remote configured; `origin` fetchable; working tree clean.
- PyPI reachable; mode detected (UPDATE / NEW); name ownership confirmed.
- PyPI credentials present via `~/.pypirc` `[pypi]` or `TWINE_USERNAME`+`TWINE_PASSWORD` env; `~/.pypirc` permission hygiene; `[testpypi]` presence for NEW mode.

## Workflow (13 gated steps: [0a] interpreter confirm + [0] preflight + [1]-[11] release)

Before starting, the interpreter `$PY` must be confirmed (step `[0a]`) and the target version must be confirmed (see `### After preflight` above). With both in hand, execute strictly in order. At each gate, if failure → rollback (see "Rollback protocol").

### [0a] Confirm Python interpreter (NOT optional)

Every subsequent gate — preflight, pytest, build, `twine check`, wheel sanity — runs under a single interpreter referenced as `$PY`. Picking the wrong one (system `python` instead of the project's dev conda env, say) makes preflight's tooling check, pytest results, and wheel sanity all misleading. Wheel sanity in particular needs an interpreter whose env already satisfies the package's transitive C-extension deps (scipy / pycairo / GDAL / HDF5 / etc.) — see `references/sanity-venv-pitfalls.md`.

Do NOT silently default to `python` / `python3` / `sys.executable`. Elicit the choice explicitly.

1. Enumerate candidates on this machine:

   ```bash
   which python python3 2>/dev/null || true
   conda env list 2>/dev/null || true
   ```

2. Ask the user (and wait for an explicit answer):

   ```
   Which Python interpreter should I use for the entire release?
   Candidates on this host: <list from step 1>
   Please give an absolute path, e.g. /opt/conda/envs/<env>/bin/python.
   The project's dev env (where the package's runtime deps already
   import cleanly) is almost always the right answer.
   ```

3. Echo back before running anything else:

   ```bash
   PY="<user-provided absolute path>"
   "$PY" -c 'import sys, os; \
   print("executable:", sys.executable); \
   print("prefix    :", sys.prefix); \
   print("version   :", sys.version.split()[0]); \
   print("conda env :", os.environ.get("CONDA_DEFAULT_ENV", "<none>"))'
   ```

4. Ask `Use this interpreter for the release? (Y/N)`. Only on explicit `Y` proceed to `[0]`. On `N`, return to step 1.

Gate: `$PY` is set to a concrete absolute path AND the user has confirmed it. All downstream `$PY ...` invocations refer to this same interpreter.

### [0] Preflight (see "Preflight and mode detection" above)

```bash
"$PY" "$SKILL_DIR/scripts/preflight.py"
# exit 0 → proceed to [1];  exit 1 → STOP, fix, re-run.
```

Captures from preflight's stdout: `package`, `current`, `inner`, `mode`, `on PyPI`. Use these downstream (especially `inner` for [5] wheel sanity).

### [1] Full pytest at CURRENT working-tree

```bash
$PY -m pytest -q 2>&1 | tail -3
```

Gate: all tests must pass. This is the baseline — if red, the release is aborted.

- UPDATE mode: this is the "regression canary" at the already-shipped version's behavior.
- NEW mode: this is the "first-freeze" test — you're committing this test outcome as the package's shipping quality bar.

### [2] Set version (working-tree only, NOT committed)

**[2a] pyproject.toml**

```python
# Use Edit tool with exact anchor:
old_string: 'version = "<OLD_OR_PLACEHOLDER>"'
new_string: 'version = "<NEW>"'
```

NEW mode: your pyproject.toml already has SOME version (e.g. `0.0.0` or `0.1.0.dev0` as a placeholder). Replace it with the chosen starting version.

UPDATE mode: bump from the current value.

**[2b] Inner-package version constants (if present)**

Many packages also declare `__version__` inside the inner package. Look for a hardcoded string literal in the usual spots:

```bash
grep -RnE '^__version__[[:space:]]*=[[:space:]]*["'"'"']' <inner>/__init__.py <inner>/_version.py <inner>/version.py 2>/dev/null
```

If a literal turns up (e.g. `__version__ = "1.0.0"`), Edit it to `<NEW>` so it agrees with pyproject.toml. Skip if it reads `__version__ = importlib.metadata.version(...)` or similar — that auto-syncs from installed metadata. Also skip when pyproject has `dynamic = ["version"]` with `[tool.hatch.version] path = "..."` — in that case the file pointed at by `path` is the source of truth and pyproject is the dependent (you'll have edited that file in [2a] instead).

Verify: `grep "^version" pyproject.toml` shows `<NEW>`, and any literal `__version__` you found above also shows `<NEW>`. Do NOT commit yet.

### [3] Build wheel + sdist

```bash
# UPDATE mode: keep prior versions in dist/ for history; just delete new-version files if somehow present
# NEW mode: dist/ may not exist yet
rm -f dist/*<NEW>*
mkdir -p dist/

$PY -m build --outdir dist/ 2>&1 | tail -3
ls -la dist/*<NEW>*
```

Gate: both `.whl` and `.tar.gz` for `<NEW>` must exist.

### [4] twine metadata check

```bash
$PY -m twine check dist/*<NEW>*
```

Gate: both artifacts report PASSED.

Common metadata problems:
- Long description not parseable as the declared format (usually markdown vs reStructuredText mismatch in `readme.content-type`).
- Classifiers not from PyPI's whitelist.
- License metadata missing.

Fix in pyproject.toml, rebuild from [3], re-check. NEW mode is stricter — first upload often hits these.

### [5] Wheel sanity — extract + `sys.path` prepend

This is the critical gate. See `references/sanity-venv-pitfalls.md` for the full rationale.

```bash
EXTRACT=/tmp/check_<NEW>_extracted
WHEEL=$PACKAGE_ROOT/dist/<PKG>-<NEW>-py3-none-any.whl
rm -rf "$EXTRACT" && mkdir -p "$EXTRACT"
$PY -m zipfile -e "$WHEEL" "$EXTRACT"

# Verify wheel layout
ls "$EXTRACT"
find "$EXTRACT/<INNER_PKG_NAME>" -type f | wc -l
ls "$EXTRACT"/*.dist-info/

# API surface check — list every publicly-exported symbol
$PY <<PY
import sys
sys.path.insert(0, '$EXTRACT')                   # beats editable installs
for m in list(sys.modules):
    if m.startswith('<INNER_PKG_NAME>'):
        del sys.modules[m]
import <INNER_PKG_NAME>
assert '$EXTRACT' in <INNER_PKG_NAME>.__file__, (
    f'wheel not winning: {<INNER_PKG_NAME>.__file__}'
)

# UPDATE mode: enumerate NEW symbols since last release.
# NEW mode:    enumerate the public API described in README/docs.
from <INNER_PKG_NAME> import (
    # list symbols here
)
print('wheel API surface: all importable OK')
PY

# End-to-end smoke — exercise the package's hot path
$PY <<PY
import sys; sys.path.insert(0, '$EXTRACT')
for m in list(sys.modules):
    if m.startswith('<INNER_PKG_NAME>'):
        del sys.modules[m]
import <INNER_PKG_NAME> as pkg
# Run the package's minimal user-facing workflow — whatever a README Hello World exercises.
PY

# Metadata spot-check
cat "$EXTRACT"/*.dist-info/METADATA | grep -E "^(Name|Version)" | head
```

Gate: all of the above must pass. Common failures:

- **Missing top-level import** — symbol in `__all__` but never imported at package root. Fix with one-line Edit on `__init__.py`, then restart from [1]. **This gate's raison d'être.**
- **Wheel not winning** — editable install's `.pth` file beats `PYTHONPATH`. `sys.path.insert(0, EXTRACT)` inside the script wins. Always include the `assert EXTRACT in pkg.__file__` guard.
- **Missing runtime dep** — a transitive dep is unavailable. Declare it in pyproject.toml or relax the check-environment constraint.

If fix is trivial (1-2 lines), ask the user before bundling into the release commit vs restarting with a prior commit. If non-trivial, rollback + separate commit + restart.

### [5.5] (NEW mode only) TestPyPI dry run (strongly recommended)

First-ever releases benefit from a practice upload to https://test.pypi.org before the real upload. Catches metadata rendering issues (README on the PyPI page) and upload mechanics problems without burning a real version number.

```bash
# Requires ~/.pypirc with a [testpypi] section OR TWINE_REPOSITORY=testpypi
$PY -m twine upload --repository testpypi dist/*<NEW>*
# Install from TestPyPI (must allow fall-back to real PyPI for deps)
$PY -m pip install --index-url https://test.pypi.org/simple/ \
                   --extra-index-url https://pypi.org/simple/ \
                   "$PKG==<NEW>"
```

Gate (soft): the package page at `https://test.pypi.org/project/$PKG/<NEW>/` must render the README correctly and show expected metadata.

UPDATE mode: skip by default; only useful for major releases.

### [6] Commit (ONLY after gate [5] / [5.5] passes)

```bash
git add pyproject.toml           # plus any bundled fix files
git commit -m "release <NEW>

<optional 1-3 line prose body: describe any bundled fix>"
git log --oneline -3
```

Commit message rules:
- Title: literally `release <NEW>`. No decorations, no audit codes.
- Body: only if a non-trivial fix was bundled. Plain English.

NEW mode: this commit's parent should ideally be the commit where the package became feature-complete. If the working tree has many pre-existing uncommitted changes, ask the user whether to bundle them or split them first.

### [7] Push master

```bash
git push origin master   # or main
```

Gate: push succeeds. On rejection due to stale ref, pull-rebase/merge and retry. **Never force-push.**

### [8] Annotated tag

Tag format: `v<NEW>-<short_commit>` by default (inspired by the ggplot2-python convention). If the project has prior tags with a different convention, match that:

```bash
git tag -l --sort=-creatordate | head -3
```

Common conventions:
- `v<version>` (simple)
- `v<version>-<short_sha>` (audit-friendly; ggplot2-python style)
- `<version>` (some projects omit the `v`)
- `release/<version>` (rare)

Annotation message = release notes. Structure (flexible; adapt to project):

```
<NEW> — <one-line summary>

Behavior fixes
- ...

New functionality
- ...

Internals
- ...

pytest: <N> / <N> tests pass.
```

Rules for writing release notes:

- **No internal audit codes.** Never `G1`, `M4`, `NEW-7`, `Fix A`, etc.
- **User-visible phrasing.** Describe what the library now does differently.
- **Main-line only.** Skip refactoring noise, internal helper renames, non-user-visible dep bumps.
- **Group by intent**: fixes vs new functionality vs internals.
- **End with the pytest count** as a canary.

For NEW mode releases the structure shifts — release notes tell the first-time user what the package IS:

```
<NEW> — <project one-line tagline>

Initial public release.

Features
- ...

Known limitations
- ...

pytest: <N> / <N> tests pass.
```

Commands:

```bash
SHORT=$(git rev-parse --short HEAD)
TAG="v<NEW>-${SHORT}"   # adapt to project convention
git tag -a "$TAG" -m "$(cat <<'EOF'
<paste annotation>
EOF
)"
git push origin "$TAG"
git ls-remote --tags origin | grep "$TAG"    # verify visible
```

### [9] twine upload to PyPI — HARD CONFIRMATION GATE

**STOP. Do NOT run the upload command yet.** Print the command, the irreversibility warning, and wait for the user's explicit `Y`:

```
About to run:
  $PY -m twine upload dist/*<NEW>*

⚠ IRREVERSIBLE — once uploaded, this release CANNOT be modified:
  • The exact filename `<pkg>-<NEW>-*.whl` is burned on PyPI forever;
    even after a yank/delete, that filename can NEVER be re-uploaded.
  • Any subsequent fix requires bumping to <NEW>.post1 (or next patch),
    going through gates [1]-[8] again.
  • The release is publicly `pip install`-able within seconds.

Note: commit and tag are already pushed to origin (from [7] and [8]).
Saying N here leaves them in place; you can resume the upload manually
later with `$PY -m twine upload dist/*<NEW>*`.

Proceed with upload? (Y/N)
```

Only on explicit `Y` run the upload command below. On `N` (or anything other than an unambiguous yes), stop the workflow here and report the current state to the user; do not retry without a fresh confirmation.

```bash
$PY -m twine upload dist/*<NEW>*
```

Twine streams progress; final line shows the PyPI page URL. Note it for the user.

NEW mode caveat: first upload may require PyPI 2FA or a trusted-publisher setup depending on account. If upload fails with 401, verify `~/.pypirc` token has upload scope on this (new) project.

### [10] Verify on PyPI

```bash
$PY -m pip index versions $PKG
# expect: <NEW> appears as newest; prior versions still listed (UPDATE mode) or only <NEW> (NEW mode)
```

### [11] (optional) Forge Release

No automatic Release creation. The annotated tag is already pushed; user can UI-click "Create release from tag" on GitHub/GitLab. If user asks this skill to create it:

```bash
gh release create "$TAG" --title "$TAG" --notes "<paste annotation body>"
```

NEW mode: strongly recommend creating a GitHub Release for discoverability.

## Rollback protocol

If gates [1]/[3]/[4]/[5]/[5.5] fail before commit:

```bash
git restore pyproject.toml
rm -f dist/*<NEW>*
rm -rf /tmp/check_<NEW>_extracted /tmp/check_<NEW>
```

If [7] fails after commit: resolve conflicts, retry push.

If [8] tag push fails: `git tag -d <TAG>` locally, inspect, retry.

If [9] upload fails mid-stream: PyPI filename is now burned (no re-upload allowed). Increment to `<NEW>.post1` (or `<NEW+1>.0.0` if major) and restart from [2]. This is where a thorough [5] saves the most pain.

If release is live on PyPI but has a critical bug: **do NOT delete** (PyPI only allows this in emergencies). Cut a new patch/`.post1` with the fix. Yank the bad version via the PyPI web UI if needed.

## Decision-points checklist (ask the user)

| # | Decision | UPDATE default | NEW default |
|---|---|---|---|
| A | CHANGELOG.md entry? | Follow project convention | Create if absent (first release) |
| B | Annotated tag with release notes? | Yes | Yes |
| C | Clean-venv wheel sanity test? | Yes (always) | Yes (always) |
| D | TestPyPI dry run before PyPI? | Skip unless major | **Strongly recommended** |
| E | Create forge Release page? | Skip (UI later) | **Strongly recommended** |
| F | Bundle sanity-fix into release commit vs split? | Ask per-case | Ask per-case |
| G | (NEW only) Initial version (0.1.0 vs 1.0.0)? | N/A | Ask; default 0.1.0 if API unstable, 1.0.0 if API committed |

## Example invocations

### UPDATE mode — ggplot2-python `.post1` → `.post2`

```
USER: release .post2 for ggplot2-python

ASSISTANT asks [0a] for the Python interpreter to use → waits for user confirmation →
runs preflight [0] → reads name=ggplot2-python, current=4.0.2.9000.post1,
inner=ggplot2_py, mode=update →
proposes 4.0.2.9000.post2 → lists decisions A-F with UPDATE defaults →
waits for user OK →
executes [1]-[8] with rollback on any gate fail → STOPS at [9] for explicit
upload Y/N → on Y runs twine upload → [10]-[11] →
reports: PyPI URL, git tag, pytest count
```

### UPDATE mode — SemVer patch (1.0.0 → 1.0.1)

```
USER: release 1.0.1 for mypkg

ASSISTANT asks [0a] interpreter → runs preflight [0] → current=1.0.0, mode=update →
proposes 1.0.1 → same 13-step flow → reports result.
```

### NEW mode — first-ever upload of mylib

```
USER: publish mylib to PyPI for the first time

ASSISTANT asks [0a] interpreter → runs preflight [0] → name available, mode=new →
(preflight warns no [testpypi] section if any) →
asks: initial version 0.1.0 or 1.0.0? TestPyPI dry run? →
waits for user OK →
executes [1]-[11] including [5.5] TestPyPI →
reports: PyPI URL + "recommend creating a GitHub Release at <tag>"
```

## Project-specific adaptations

When starting, inspect these for local conventions to preserve:

- `git tag -l --sort=-creatordate | head` — tag format
- `ls dist/` — prior build artefacts
- `CHANGELOG.md` / `NEWS.md` — entry style
- README / docs — tone for release notes
- `.github/workflows/` — existing release automation (may conflict with this manual flow)

Defer to whatever local conventions exist unless the user explicitly asks to change them.

## Known pitfalls (encoded from real incidents)

1. **Fresh venv `pip install <wheel>` is unreliable on research machines** — scipy, pycairo, GDAL-backed packages need system libs not present in `python -m venv`. Use extract+sys.path (see `references/sanity-venv-pitfalls.md`).

2. **Editable installs beat PYTHONPATH.** `.pth` files inject ahead of `PYTHONPATH`. Use `sys.path.insert(0, EXTRACT)` inside the test script and assert `EXTRACT in pkg.__file__`.

3. **`__all__` listing ≠ import.** Adding a name to `__all__` without importing it at the package root fails `from pkg import <name>` silently under `import *`. Source-level pytest misses this. Wheel sanity catches it.

4. **PyPI filename conflict on re-upload.** Once `<pkg>-<ver>-*.whl` uploads, it cannot be re-uploaded (even after deletion). Bump to `<ver>.postN` or next patch.

5. **TestPyPI deps must allow fall-back to real PyPI.** Use both `--index-url https://test.pypi.org/simple/` AND `--extra-index-url https://pypi.org/simple/` when installing from TestPyPI.

6. **Trusted publishers need repo-specific config.** If PyPI was set up for GitHub Actions-based trusted publishing, manual uploads may need a different token.

7. **NEW mode: PyPI's README renderer differs from GitHub's.** Some Markdown extensions (MathJax, admonitions, Mermaid) don't render on PyPI. TestPyPI catches this before real upload.

## Files

- `scripts/preflight.py` — read-only prerequisite checker. Runs 7 sections; exits 0 on clean / 1 on any `[FAIL]`. Detects inner package via hatch/setuptools config (correct for `ggplot2-python → ggplot2_py`), uses PyPI JSON API (not deprecated `pip index`), parses `~/.pypirc` as INI. Collects all errors to completion (no short-circuit).
- `references/sanity-venv-pitfalls.md` — why fresh-venv sanity is unreliable on research machines; how extract+sys.path verifies the same things more cheaply.
