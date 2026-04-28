# Clean-venv sanity: why it fails and how to work around it

## The naive approach and why it breaks

The "textbook" wheel sanity:

```bash
python -m venv /tmp/check
/tmp/check/bin/pip install <wheel>
/tmp/check/bin/python -c "import pkg; pkg.smoke()"
```

This is what every packaging guide shows. It fails on most research machines because:

1. **Transitive deps include C extensions with system-lib dependencies.** Common culprits in scientific Python:
   - `scipy` needs OpenBLAS or Accelerate at build time (if no prebuilt wheel matches the Python version/platform combo).
   - `pycairo` (drawn in by grid/graphics ports) needs cairo-dev system libs.
   - `rasterio`, `fiona`, `gdal` need GDAL+PROJ+GEOS system libs.
   - `h5py`, `netCDF4` need HDF5 headers.

2. **Fresh venv has no access to conda's system libs.** On research HPC nodes and shared servers, scientific libraries live inside conda envs (e.g., `/opt/conda/envs/<name>/lib`). A `python -m venv` creates a venv that inherits only the Python interpreter, not the conda-installed C libs. `pip install` then tries to build the missing deps from source, fails at `pkg-config: OpenBLAS not found`, and bails.

3. **`--only-binary=:all:` doesn't fix it.** That flag forces pip to reject source dists. But if prebuilt wheels don't exist for your Python version/OS/architecture combo (common for bleeding-edge Python or older Linux kernels), pip has nothing to fall back to and errors out with `ResolutionImpossible`.

## What fresh-venv sanity actually verifies

It verifies TWO things:
- **Your wheel installs via pip on a pristine machine.**
- **Your declared dependencies are complete and resolvable on PyPI alone.**

Both are important. But the SECOND is mostly about pyproject.toml metadata hygiene, which `twine check` catches. The FIRST (wheel layout, `__init__.py` imports, runtime behaviour) can be verified with a cheaper approach that works on broken-system machines.

## The extract + sys.path approach

```bash
EXTRACT=/tmp/check_wheel_extracted
rm -rf "$EXTRACT" && mkdir -p "$EXTRACT"
python -m zipfile -e path/to/pkg-<VER>-py3-none-any.whl "$EXTRACT"

# Use a Python interpreter whose env already has the runtime deps
# (typically the project's dev conda env)
python <<PY
import sys
sys.path.insert(0, '$EXTRACT')    # wheel contents win over site-packages

# Flush any cached package version (editable installs pre-import on startup)
for m in list(sys.modules):
    if m.startswith('<pkg>'):
        del sys.modules[m]

import <pkg>
assert '$EXTRACT' in <pkg>.__file__   # critical: prove the wheel won

# Verify every symbol that's supposed to be at the package root imports
from <pkg> import (
    # list symbols here, especially anything added this release
)

# Then run a short end-to-end that exercises the hot path
<pkg>.do_the_thing()
PY
```

### What this verifies

- **Wheel zip is valid.** Extraction would fail on a corrupted wheel.
- **Package directory layout is correct.** Both the importable package and the `*.dist-info/` metadata directory appear at the archive root.
- **Every symbol in `__all__` actually resolves at `pkg.<name>`.** This catches the "symbol in `__all__` but missing at package root" class of bug that source-level pytest cannot detect (because pytest imports from submodules directly).
- **The wheel's CODE runs against the declared runtime deps.** Because we use the dev env's Python, scipy/pycairo/GDAL are all already installed and at compatible versions.

### What this does NOT verify

- **Whether `pip install <pkg>` on a pristine machine would work.** For that you need either a pristine venv (often infeasible, see above) or TestPyPI (skip if your project doesn't use it).
- **Whether the minimum declared dep versions are actually sufficient.** Since the dev env typically has recent-enough versions, a too-low minimum in pyproject.toml can slip through. `twine check` catches some of this; comprehensive dep-minimum verification requires a separate CI matrix.

For most releases, the extract+sys.path check is the cost-effective middle ground: it catches the practical class of bugs that bite users immediately upon `pip install`, without requiring a functioning fresh-venv infrastructure.

## The "wheel not winning" trap

Even with `sys.path.insert(0, EXTRACT)`, you may find `<pkg>.__file__` pointing at `/path/to/dev/install/pkg/__init__.py` instead of the extracted wheel. This happens when:

- The project is installed with `pip install -e .` (editable/dev install).
- Editable installs drop a `<pkg>.pth` file into site-packages that adds the source directory to `sys.path` at interpreter startup — BEFORE your script runs.
- Your `sys.path.insert(0, EXTRACT)` runs after that, but importing `<pkg>` may still resolve via the earlier entry if caching gets involved.

**Defensive pattern** — always include these two guards:

```python
import sys
sys.path.insert(0, EXTRACT)             # beats startup-level .pth
for m in list(sys.modules):
    if m.startswith('<pkg>'):
        del sys.modules[m]              # flush any pre-import
import <pkg>
assert EXTRACT in <pkg>.__file__, \
    f'wheel not winning: {<pkg>.__file__}'    # fail loud if bypassed
```

The assertion is not optional. Without it, a failed "wheel won" state will be missed and the sanity test will validate the dev install, not the wheel you're about to publish.

## When to use a fresh venv anyway

Only when:

- The package is simple (no C-extension transitive deps) — pure-Python trees usually install cleanly in fresh venvs.
- You're releasing a MAJOR version and want maximum confidence.
- You have infrastructure (CI, Docker, a well-set-up test machine) that can genuinely produce a clean install.

For routine `.postN` or patch releases on a research HPC node, extract+sys.path is the right tool.
