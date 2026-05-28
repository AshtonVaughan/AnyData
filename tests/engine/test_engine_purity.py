"""Cardinal-rule test: factory/engine/ must never import PySide6 or PyQt.

If this test fails, the engine has been polluted with GUI imports and the
strict layering of the project has been broken.
"""

from __future__ import annotations

import pathlib
import re

ENGINE_DIR = pathlib.Path(__file__).resolve().parents[2] / "factory" / "engine"

_FORBIDDEN = re.compile(
    r"^\s*(?:import|from)\s+(?:PySide6|PyQt5|PyQt6)\b",
    re.MULTILINE,
)


def test_engine_has_no_qt_imports() -> None:
    offenders: list[str] = []
    for path in ENGINE_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if _FORBIDDEN.search(text):
            offenders.append(str(path.relative_to(ENGINE_DIR.parent.parent)))
    assert not offenders, (
        "Engine purity violation: Qt imports found in: "
        + ", ".join(offenders)
        + ". The engine must remain headless."
    )
