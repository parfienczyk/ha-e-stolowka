"""Ładuje moduły integracji bez instalowania Home Assistanta.

`custom_components/e_stolowka/__init__.py` importuje Home Assistanta, więc
zwykły import pociągnąłby całe HA tylko po to, żeby przetestować parser HTML.
Rejestrujemy więc zastępczy pakiet, w którym importy względne (`from .const`)
nadal się rozwiązują, i ładujemy z niego tylko moduły niezależne od HA.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "e_stolowka"
PACKAGE = "e_stolowka_standalone"
STANDALONE_MODULES = ("const", "api")


def load_component() -> None:
    """Udostępnij moduły integracji pod nazwą pakietu `e_stolowka_standalone`."""
    if PACKAGE in sys.modules:
        return

    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(COMPONENT)]
    sys.modules[PACKAGE] = package

    for name in STANDALONE_MODULES:
        spec = importlib.util.spec_from_file_location(
            f"{PACKAGE}.{name}", COMPONENT / f"{name}.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"{PACKAGE}.{name}"] = module
        spec.loader.exec_module(module)


load_component()
