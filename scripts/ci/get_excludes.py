#!/usr/bin/env python3
"""
Tiny helper for GitHub Actions.

Usage:
    python3 scripts/ci/get_excludes.py flows   # → prints "id1;id2;…"
    python3 scripts/ci/get_excludes.py nodes   # → prints "url1;url2;…"

It simply echoes the semicolon-joined list so the caller can redirect it
into the desired environment variable.
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


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"flows", "nodes"}:
        print("Usage: get_excludes.py [flows|nodes]", file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1]
    repo_root = Path(__file__).resolve().parents[2]   # <repo>/scripts/ci/…

    if mode == "flows":
        py_file = repo_root / "ex_app" / "lib" / "exclude_flows.py"
        var_name = "EXCLUDE_FLOWS_IDS"
    else:  # nodes
        py_file = repo_root / "ex_app" / "lib" / "exclude_nodes.py"
        var_name = "EXCLUDE_NODES_IDS"

    items = _import_list(py_file, var_name)
    print(";".join(items))


if __name__ == "__main__":
    main()
