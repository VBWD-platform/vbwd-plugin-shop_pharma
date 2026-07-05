"""S101.1 — neither core nor the shop module may reference shop_pharma.

The pharma module depends on shop (and core); the reverse is forbidden. This
oracle greps core's ``vbwd/`` and the shop module's source for any
``shop_pharma`` reference. If it trips, a pharma concept leaked upstream — move
it back into the pharma module.
"""
import os

_BACKEND_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
CORE_ROOT = os.path.join(_BACKEND_ROOT, "vbwd")
SHOP_ROOT = os.path.join(_BACKEND_ROOT, "plugins", "shop", "shop")


def _python_files(root):
    for current_dir, _dirs, files in os.walk(root):
        if "__pycache__" in current_dir:
            continue
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(current_dir, name)


def _offenders(root, token):
    found = []
    for path in _python_files(root):
        with open(path, "r", encoding="utf-8") as handle:
            if token in handle.read():
                found.append(path)
    return found


def test_core_does_not_reference_shop_pharma():
    assert not _offenders(
        CORE_ROOT, "shop_pharma"
    ), "Core references shop_pharma — core must stay agnostic"


def test_shop_module_does_not_reference_shop_pharma():
    assert not _offenders(
        SHOP_ROOT, "shop_pharma"
    ), "The shop module references shop_pharma — shop must stay agnostic"
