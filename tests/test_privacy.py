"""Hasła nie wchodzą do logów, a zrzuty stron nie wchodzą do gita."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_LOG_METHODS = frozenset({"debug", "info", "warning", "error", "exception", "critical"})
_SECRET_NAMES = frozenset(
    {
        "password",
        "email",
        "_password",
        "_email",
        "haslo",
        "hasło",
        "conf_password",
        "conf_email",
    }
)


def _python_sources() -> list[Path]:
    """Pliki integracji i skryptów, bez testów."""
    roots = (ROOT / "custom_components", ROOT / "scripts")
    return [path for root in roots for path in root.rglob("*.py")]


def _is_output_call(node: ast.Call) -> bool:
    """Czy wywołanie wypisuje coś użytkownikowi albo do logu."""
    func = node.func
    if isinstance(func, ast.Name) and func.id == "print":
        return True
    return isinstance(func, ast.Attribute) and func.attr in _LOG_METHODS


def _mentions_secret(node: ast.AST) -> bool:
    """Czy drzewo zawiera nazwę hasła albo e-maila."""
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id.casefold() in _SECRET_NAMES:
            return True
        if isinstance(child, ast.Attribute) and child.attr.casefold() in _SECRET_NAMES:
            return True
    return False


def test_credentials_are_not_logged() -> None:
    """Log i print nie dostają hasła ani e-maila — nawet w debug."""
    problems: list[str] = []
    for path in _python_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative = path.relative_to(ROOT)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_output_call(node):
                continue
            values = [*node.args, *(kw.value for kw in node.keywords)]
            if any(_mentions_secret(value) for value in values):
                problems.append(f"{relative}:{node.lineno}")
    assert problems == []


def test_env_and_dumps_stay_untracked() -> None:
    """`.env` i katalog `dump/` nie mogą trafić do repozytorium."""
    for path in (".env", "dump/strona.html"):
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", "--", path],
            cwd=ROOT,
            check=False,
        )
        assert ignored.returncode == 0, path

    tracked = subprocess.run(
        ["git", "ls-files", "--", "dump", ".env"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert tracked.stdout.strip() == ""
