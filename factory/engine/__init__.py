"""Engine - the headless core of the factory.

CARDINAL RULE: this package must never import PySide6/PyQt. GUI code lives only
in ``factory.gui`` and consumes engine events through ``factory.gui.bridge``.
A test (tests/engine/test_engine_purity.py) enforces this.
"""
