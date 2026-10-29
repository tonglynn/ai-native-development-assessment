"""Runs one hidden test file inside a task workspace (executed in a subprocess).

Usage: python -I _hidden_runner.py <hidden_test.py> <workspace>

Prints one line: ``__HIDDEN_RESULT__ {"name": {"passed": bool, "error": str}, ...}``
"""

import importlib.util
import json
import os
import sys

MARKER = "__HIDDEN_RESULT__"


def _reset_state() -> None:
    audit = sys.modules.get("ledgerly.audit")
    if audit is not None and hasattr(audit, "clear"):
        audit.clear()


def main() -> None:
    hidden_path, workspace = sys.argv[1], sys.argv[2]
    sys.path[:0] = [workspace, os.path.dirname(os.path.abspath(hidden_path))]
    results: dict[str, dict] = {}
    try:
        spec = importlib.util.spec_from_file_location("hidden_test", hidden_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except BaseException as exc:  # noqa: BLE001 - report import failures as data
        print(MARKER, json.dumps({"__import__": {"passed": False, "error": f"{type(exc).__name__}: {exc}"[:500]}}))
        return
    for name, fn in vars(module).items():
        if not (name.startswith("test_") and callable(fn)):
            continue
        _reset_state()
        try:
            fn()
            results[name] = {"passed": True, "error": ""}
        except BaseException as exc:  # noqa: BLE001
            results[name] = {"passed": False, "error": f"{type(exc).__name__}: {exc}"[:500]}
    print(MARKER, json.dumps(results))


if __name__ == "__main__":
    main()
