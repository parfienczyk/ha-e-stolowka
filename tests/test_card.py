"""Karta Lovelace nie wstawia tekstu z encji jako HTML."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

HARNESS = Path(__file__).parent / "render_card.cjs"


def test_card_escapes_entity_text() -> None:
    """Tytuł, nazwa dania i wariant diety przechodzą przez escapeHtml."""
    node = shutil.which("node")
    assert node is not None, "Node jest potrzebny do renderu karty"
    result = subprocess.run(
        [node, str(HARNESS)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
