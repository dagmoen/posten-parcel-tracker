"""Test setup.

These tests exercise the provider-agnostic and provider layers, which have no
Home Assistant dependency. Home Assistant requires Python 3.12+, and the
integration's ``__init__.py`` uses 3.12 syntax, so we register lightweight shim
packages for ``custom_components`` and ``custom_components.parcel_tracker`` that
point at the real source directory WITHOUT executing the HA-coupled package
``__init__.py``. Submodules (models, aggregate, events, status, parser,
providers, ...) then import normally via the package ``__path__``.

Full config-flow/coordinator/entity tests that need the Home Assistant test
harness require Python 3.12+ and pytest-homeassistant-custom-component.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CC_DIR = ROOT / "custom_components"
PKG_DIR = CC_DIR / "parcel_tracker"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _shim(name: str, path: Path) -> None:
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    module.__path__ = [str(path)]  # marks it as a package
    sys.modules[name] = module


# Register parent packages as namespace-like shims so importing e.g.
# ``custom_components.parcel_tracker.aggregate`` does not run the real
# ``custom_components/parcel_tracker/__init__.py``.
_shim("custom_components", CC_DIR)
_shim("custom_components.parcel_tracker", PKG_DIR)
