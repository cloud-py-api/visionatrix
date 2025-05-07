#!/usr/bin/env python3
"""
Tiny helper for GitHub Actions *and* Docker builds.

Usage:
    python3 get_excludes.py flows   # → prints "id1;id2;…"
    python3 get_excludes.py nodes   # → prints "url1;url2;…"

It echoes a semicolon-joined list so callers can assign it to an environment variable, e.g.:

    VISIONATRIX_INSTALL_EXCLUDE_NODES="$(python /get_excludes.py nodes)"
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from collections.abc import Sequence


def _import_list(file: Path, var: str) -> Sequence[str]:
    spec = importlib.util.spec_from_file_location(file.stem, file)
    module = importlib.util.module_from_spec(spec)        # type: ignore[arg-type]
    spec.loader.exec_module(module)                       # type: ignore[attr-defined]
    value: list[str] | Sequence[str] = getattr(module, var, [])
    if not isinstance(value, list | tuple):
        raise TypeError(f"{file}:{var} is not a list/tuple")
    return value


def find_repo_root() -> Path:
    """
    Locate directory that contains  ex_app/lib/ .
    Strategy (first match wins):
        1. Walk up from this script's directory.
        2. Walk up from CWD (useful if script is executed via absolute path).
        3. Fallback to filesystem root (where Dockerfile copies it as /ex_app/lib).
    """
    def search_up(start: Path) -> Path | None:
        for p in [start, *list(start.parents)]:
            if (p / "ex_app" / "lib").is_dir():
                return p
        return None

    here = Path(__file__).resolve().parent
    return search_up(here) or search_up(Path.cwd()) or Path("/")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"flows", "nodes"}:
        print("Usage: get_excludes.py [flows|nodes]", file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1]
    repo_root = find_repo_root()   # <repo root> or "/" inside container

    if mode == "flows":
        py_file = repo_root / "ex_app" / "lib" / "exclude_flows.py"
        var_name = "EXCLUDE_FLOWS_IDS"
    else:
        py_file = repo_root / "ex_app" / "lib" / "exclude_nodes.py"
        var_name = "EXCLUDE_NODES_IDS"

    if not py_file.is_file():
        print(f"Error: cannot locate {py_file}", file=sys.stderr)
        sys.exit(2)

    items = _import_list(py_file, var_name)
    print(";".join(items))


if __name__ == "__main__":
    main()
