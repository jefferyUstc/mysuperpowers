#!/usr/bin/env python3
"""Preflight check for python-pypi-release skill.

Verifies every prerequisite that could cause the 11-step release
workflow to fail mid-way. All checks run to completion (not
short-circuit) so the user sees every problem at once.

Exit 0 = no errors (warnings allowed); exit 1 = at least one error.

Usage:
    cd <package-root>
    python path/to/preflight.py [--mode-hint auto|update|new]

The script never writes to disk, never modifies git state, never
touches PyPI. All operations are read-only.
"""
from __future__ import annotations

import argparse
import configparser
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# tomllib landed in Python 3.11; tomli is the 3.10 fallback
try:
    import tomllib  # type: ignore
except ImportError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

SECTIONS_TOTAL = 7


class Report:
    """Collects per-check outcomes. Never short-circuits."""

    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0
        self.info: dict = {}

    def section(self, idx: int, title: str) -> None:
        print(f"\n=== [{idx}/{SECTIONS_TOTAL}] {title} ===")

    def ok(self, msg: str) -> None:
        print(f"  [OK]   {msg}")

    def warn(self, msg: str) -> None:
        print(f"  [WARN] {msg}")
        self.warnings += 1

    def err(self, msg: str) -> None:
        print(f"  [FAIL] {msg}")
        self.errors += 1


# --------------------------------------------------------------------------- #
# [1/7] tooling                                                               #
# --------------------------------------------------------------------------- #
def check_tooling(r: Report) -> None:
    r.section(1, "tooling")

    # Echo back which interpreter is being checked so the caller can
    # verify this is the $PY they confirmed in step [0a], not some other
    # python that crept in via PATH / conda activation / editable-install .pth.
    r.ok(f"interpreter: {sys.executable}")
    r.ok(f"  prefix   : {sys.prefix}")
    r.ok(f"  version  : {sys.version.split()[0]}")
    conda_env = os.environ.get("CONDA_DEFAULT_ENV")
    if conda_env:
        r.ok(f"  conda env: {conda_env}")
    else:
        r.ok("  conda env: <none>")

    for mod in ("build", "twine", "packaging"):
        try:
            __import__(mod)
            r.ok(f"python module: {mod}")
        except ImportError:
            r.err(f"python module {mod!r} MISSING — pip install {mod}")
    if tomllib is None:
        r.err("neither stdlib `tomllib` (3.11+) nor `tomli` (3.10) importable")
    else:
        src = "stdlib" if sys.version_info >= (3, 11) else "tomli fallback"
        r.ok(f"tomllib available ({src})")


# --------------------------------------------------------------------------- #
# [2/7] pyproject.toml                                                        #
# --------------------------------------------------------------------------- #
def load_pyproject(r: Report):
    r.section(2, "pyproject.toml")
    pp = Path("pyproject.toml")
    if not pp.is_file():
        r.err("pyproject.toml NOT FOUND in current directory")
        return None
    if tomllib is None:
        return None  # already reported
    try:
        data = tomllib.loads(pp.read_text(encoding="utf-8"))
    except Exception as e:
        r.err(f"pyproject.toml parse failed: {e}")
        return None
    r.ok("pyproject.toml parseable")

    project = data.get("project", {})
    build_system = data.get("build-system", {})

    name = project.get("name", "")
    if name:
        r.ok(f"project.name = {name}")
        r.info["name"] = name
    else:
        r.err("project.name missing")

    # version may be static or declared as dynamic
    version = project.get("version", "")
    dynamic = project.get("dynamic", [])
    if version:
        try:
            from packaging.version import Version

            Version(version)
            r.ok(f"project.version = {version} (PEP 440 valid)")
            r.info["version"] = version
        except Exception as e:
            r.err(f"project.version {version!r} is NOT valid PEP 440: {e}")
    elif "version" in dynamic:
        r.warn("project.version is dynamic — this skill only auto-bumps static versions")
        r.info["version_dynamic"] = True
    else:
        r.err("project.version missing (and not declared as dynamic)")

    backend = build_system.get("build-backend", "")
    if backend:
        r.ok(f"build-system.build-backend = {backend}")
    else:
        r.err("build-system.build-backend missing")

    # README reference resolves?
    readme = project.get("readme")
    if isinstance(readme, str):
        if Path(readme).is_file():
            r.ok(f"readme file exists: {readme}")
        else:
            r.err(f"readme file NOT FOUND: {readme} (declared in pyproject.readme)")
    elif isinstance(readme, dict):
        rfile = readme.get("file")
        if rfile:
            if Path(rfile).is_file():
                r.ok(f"readme.file exists: {rfile}")
            else:
                r.err(f"readme.file NOT FOUND: {rfile}")

    return data


# --------------------------------------------------------------------------- #
# [3/7] inner package layout                                                  #
# --------------------------------------------------------------------------- #
def detect_inner_package(data: dict, r: Report):
    """Return the importable package directory name.

    Priority:
      1. [tool.hatch.build.targets.wheel].packages (first entry)
      2. [tool.setuptools.packages] list literal
      3. Heuristic: top-level directory containing __init__.py
         (excluding tests/docs/build/etc.)
    """
    r.section(3, "inner package layout")
    if not data:
        return None

    # Priority 1: hatch
    try:
        hatch_pkgs = data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
        if hatch_pkgs:
            pkg = str(hatch_pkgs[0]).rstrip("/")
            # May contain a subpath like "src/mypkg"
            pkg_dir = Path(pkg)
            init_py = pkg_dir / "__init__.py"
            if init_py.is_file():
                r.ok(f"inner pkg (hatch config): {pkg}")
                r.info["inner"] = pkg_dir.name
                r.info["inner_path"] = pkg
                return pkg_dir.name
            r.err(f"inner pkg (hatch config) {pkg} declared but {init_py} MISSING")
            return pkg_dir.name
    except (KeyError, TypeError):
        pass

    # Priority 2: setuptools explicit list
    try:
        set_pkgs = data["tool"]["setuptools"]["packages"]
        if isinstance(set_pkgs, list) and set_pkgs:
            pkg = set_pkgs[0]
            r.ok(f"inner pkg (setuptools explicit): {pkg}")
            r.info["inner"] = pkg
            return pkg
    except (KeyError, TypeError):
        pass

    # Priority 3: heuristic
    excluded = {
        "tests", "test", "docs", "doc", "examples", "example",
        "dist", "build", "site", "ci", "scripts", "bin",
        "validation", "port_reports",
    }
    candidates = []
    cwd = Path(".")
    for p in sorted(cwd.iterdir(), key=lambda x: x.name):
        if not p.is_dir():
            continue
        if p.name in excluded or p.name.startswith((".", "_")):
            continue
        if (p / "__init__.py").is_file():
            candidates.append(p.name)
    if len(candidates) == 1:
        pkg = candidates[0]
        r.ok(f"inner pkg (heuristic scan): {pkg}")
        r.info["inner"] = pkg
        return pkg
    if not candidates:
        r.err("no inner package directory with __init__.py found")
        return None
    r.warn(f"multiple candidate inner packages: {candidates}")
    r.warn(f"  first guess = {candidates[0]}; confirm manually if wrong")
    r.info["inner"] = candidates[0]
    r.info["inner_candidates"] = candidates
    return candidates[0]


# --------------------------------------------------------------------------- #
# [4/7] filesystem (README, LICENSE)                                          #
# --------------------------------------------------------------------------- #
def check_filesystem(r: Report) -> None:
    r.section(4, "filesystem")
    if Path("README.md").is_file():
        r.ok("README.md")
    elif Path("README.rst").is_file():
        r.ok("README.rst")
    else:
        r.warn("no README.md or README.rst (PyPI page will be empty)")

    for cand in ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENSE.rst", "COPYING"):
        if Path(cand).is_file():
            r.ok(f"license file: {cand}")
            break
    else:
        r.warn("no LICENSE file (PyPI recommends one)")


# --------------------------------------------------------------------------- #
# [5/7] git state                                                             #
# --------------------------------------------------------------------------- #
def check_git(r: Report) -> None:
    r.section(5, "git")

    def git(*args, check=True, timeout=30):
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=check,
            timeout=timeout,
        )

    try:
        git("rev-parse", "--is-inside-work-tree")
        r.ok("inside a git repo")
    except (subprocess.CalledProcessError, FileNotFoundError):
        r.err("not inside a git repo (or `git` not on PATH)")
        return

    try:
        res = git("remote", "get-url", "origin")
        r.ok(f"origin: {res.stdout.strip()}")
    except subprocess.CalledProcessError:
        r.err("no 'origin' remote configured")
        return

    res = git("status", "--porcelain", check=False)
    if not res.stdout.strip():
        r.ok("working tree clean")
    else:
        r.warn("working tree dirty — confirm changes are intentional:")
        for line in res.stdout.strip().splitlines()[:10]:
            print(f"         {line}")

    try:
        res = git("fetch", "--dry-run", "origin", check=False, timeout=30)
    except subprocess.TimeoutExpired:
        r.err("git fetch origin timed out after 30s (network/VPN/firewall?)")
        return
    if res.returncode == 0:
        r.ok("origin reachable (git fetch --dry-run OK)")
    else:
        # Show up to the last 3 lines of git's error output, not just one.
        output = (res.stderr or res.stdout).strip()
        lines = output.splitlines()[-3:] if output else ["<no output>"]
        r.err("cannot fetch from origin:")
        for line in lines:
            print(f"         {line}")


# --------------------------------------------------------------------------- #
# [6/7] PyPI mode + name availability                                         #
# --------------------------------------------------------------------------- #
def check_pypi_mode(r: Report, name: str):
    r.section(6, "PyPI mode + name")
    if not name:
        r.err("cannot detect mode without project.name")
        return None
    url = f"https://pypi.org/pypi/{name}/json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "python-pypi-release-preflight"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        info = data.get("info", {})
        releases = data.get("releases", {})
        latest = info.get("version", "")
        all_versions = sorted(releases.keys())
        r.ok(f"MODE = update ({name} on PyPI; latest = {latest})")
        if all_versions:
            tail = all_versions[-5:] if len(all_versions) > 5 else all_versions
            r.ok(f"  existing versions: {len(all_versions)} total; recent: {tail}")
        r.info["mode"] = "update"
        r.info["pypi_latest"] = latest
        r.info["pypi_versions"] = all_versions
        return "update"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            r.ok(f"MODE = new (name {name!r} appears AVAILABLE on PyPI)")
            r.info["mode"] = "new"
            return "new"
        r.err(f"PyPI query failed: HTTP {e.code} {e.reason}")
        return None
    except urllib.error.URLError as e:
        r.err(f"PyPI unreachable (network/DNS/firewall): {e.reason}")
        return None
    except Exception as e:
        r.err(f"PyPI query unexpected error: {type(e).__name__}: {e}")
        return None


# --------------------------------------------------------------------------- #
# [7/7] PyPI auth                                                             #
# --------------------------------------------------------------------------- #
def check_pypi_auth(r: Report, mode: str | None) -> None:
    r.section(7, "PyPI auth")
    env_user = os.getenv("TWINE_USERNAME")
    env_pass = os.getenv("TWINE_PASSWORD")
    if env_user and env_pass:
        masked = env_pass[:4] + "..." + env_pass[-4:] if len(env_pass) > 8 else "***"
        r.ok(f"env vars set (TWINE_USERNAME={env_user}, TWINE_PASSWORD={masked})")
        return

    pypirc = Path.home() / ".pypirc"
    if not pypirc.is_file():
        r.err("no ~/.pypirc and no TWINE_USERNAME/TWINE_PASSWORD env vars")
        _print_auth_remedy()
        return

    try:
        cp = configparser.ConfigParser()
        cp.read(pypirc)
    except Exception as e:
        r.err(f"~/.pypirc parse failed: {e}")
        _print_auth_remedy()
        return

    if not cp.has_section("pypi"):
        r.err("~/.pypirc has no [pypi] section")
        _print_auth_remedy()
        return

    token = cp.get("pypi", "password", fallback="") or cp.get("pypi", "api_token", fallback="")
    if not token:
        r.err("~/.pypirc [pypi] section has no `password` or `api_token`")
        _print_auth_remedy()
        return

    r.ok("~/.pypirc [pypi] has credential")
    username = cp.get("pypi", "username", fallback="")
    if username and username != "__token__":
        r.warn(f"[pypi].username = {username!r}; modern PyPI expects `__token__` with API token as password")

    # Permission hygiene
    try:
        mode_bits = pypirc.stat().st_mode & 0o777
        if mode_bits & 0o044:
            r.warn(f"~/.pypirc mode is {oct(mode_bits)[2:]} (group/world readable); recommend `chmod 600`")
        else:
            r.ok(f"~/.pypirc mode: {oct(mode_bits)[2:]}")
    except OSError:
        pass

    # TestPyPI section (used by NEW-mode [5.5] dry run)
    if mode == "new":
        if cp.has_section("testpypi"):
            tp_token = cp.get("testpypi", "password", fallback="")
            if tp_token:
                r.ok("~/.pypirc [testpypi] section has credential (NEW mode [5.5] will use it)")
            else:
                r.warn("~/.pypirc [testpypi] present but missing password; [5.5] TestPyPI dry run will fail")
        else:
            r.warn("~/.pypirc has no [testpypi] section; NEW mode [5.5] dry run will prompt or fail")


def _print_auth_remedy() -> None:
    print("         Fix by ONE of:")
    print("         A) write ~/.pypirc (see skill SKILL.md § auth); chmod 600 afterwards")
    print("         B) export TWINE_USERNAME=__token__")
    print("            export TWINE_PASSWORD=pypi-<your project-scoped token>")
    print("         Get a token: https://pypi.org/manage/account/token/")


# --------------------------------------------------------------------------- #
# main                                                                        #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Preflight check for python-pypi-release skill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--mode-hint",
        choices=("auto", "update", "new"),
        default="auto",
        help="optional; auto-detected from PyPI if not given",
    )
    args = ap.parse_args()

    r = Report()
    check_tooling(r)
    data = load_pyproject(r)
    if data:
        detect_inner_package(data, r)
    check_filesystem(r)
    check_git(r)
    mode = check_pypi_mode(r, r.info.get("name", ""))
    resolved_mode = mode or (args.mode_hint if args.mode_hint != "auto" else None)
    check_pypi_auth(r, resolved_mode)

    # Summary
    print()
    print("=" * 60)
    print(f"PREFLIGHT: {r.errors} error(s), {r.warnings} warning(s)")
    if r.info.get("name"):
        print(f"  package:  {r.info['name']}")
    if r.info.get("version"):
        print(f"  current:  {r.info['version']}")
    if r.info.get("inner"):
        print(f"  inner:    {r.info['inner']}")
    if r.info.get("mode"):
        print(f"  mode:     {r.info['mode']}")
    if r.info.get("pypi_latest"):
        print(f"  on PyPI:  {r.info['pypi_latest']}")
    print("=" * 60)

    return 1 if r.errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
